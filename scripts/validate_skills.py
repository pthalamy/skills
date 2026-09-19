#!/usr/bin/env python3
"""Validate every skill in the repository.

Checks, for each directory under ``skills/``:

* a ``SKILL.md`` file exists (exact casing);
* it starts with a YAML frontmatter block delimited by ``---`` lines;
* ``name`` is present, kebab-case (lowercase letters, digits, hyphens),
  at most 64 characters, and equal to the directory name;
* ``description`` is present, non-empty and at most 1024 characters
  (the Agent Skills limit, comfortably inside Claude Code's 1536);
* ``compatibility``, when present, is at most 500 characters;
* the body is not empty and is warned about above 500 lines;
* frontmatter keys outside the Agent Skills specification produce a
  portability warning (they are ignored by agents other than the one that
  defines them; Claude Code's own fields are recognised and named).

Also checks that ``.claude-plugin/marketplace.json`` and
``.claude-plugin/plugin.json`` are valid JSON with the required fields.

Only the standard library is used, so the script runs anywhere Python 3.9+ is
available. The frontmatter parser is intentionally small: it handles
``key: value`` pairs, quoted values and folded/literal multi-line scalars
(``>``, ``>-``, ``|``, ``|-``), which covers everything a SKILL.md needs.

Usage::

    python3 scripts/validate_skills.py            # validate skills/
    python3 scripts/validate_skills.py --path templates  # validate another tree
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
SOFT_MAX_BODY_LINES = 500

# Fields defined by the Agent Skills specification (https://agentskills.io).
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Fields Claude Code adds on top of the spec. Other agents ignore them.
CLAUDE_CODE_FIELDS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
    "user-invocable", "disallowed-tools", "context", "agent", "background",
    "model", "effort", "shell", "paths", "hooks",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: Path, msg: str) -> None:
        self.errors.append(f"{rel(where)}: {msg}")

    def warn(self, where: Path, msg: str) -> None:
        self.warnings.append(f"{rel(where)}: {msg}")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter, body). frontmatter is None when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :])
    return None, text


def parse_frontmatter(block: str) -> dict[str, str]:
    """Minimal YAML subset parser sufficient for SKILL.md frontmatter."""
    data: dict[str, str] = {}
    key: str | None = None
    mode: str | None = None  # None, "folded" or "literal"
    buffer: list[str] = []

    def flush() -> None:
        nonlocal key, mode, buffer
        if key is None:
            return
        if mode == "folded":
            data[key] = " ".join(part.strip() for part in buffer if part.strip())
        elif mode == "literal":
            data[key] = "\n".join(buffer).strip()
        key, mode, buffer = None, None, []

    for raw in block.splitlines():
        if raw.lstrip().startswith("#") and not raw.startswith(" "):
            continue  # top-level comment
        if raw and not raw[0].isspace():
            flush()
            match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if value in (">", ">-", "|", "|-"):
                mode = "folded" if value.startswith(">") else "literal"
                buffer = []
            else:
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                data[key] = value
                key, mode = None, None
        elif key is not None and mode is not None:
            buffer.append(raw)
        # Nested mappings (e.g. metadata:) are skipped on purpose.
    flush()
    return data


def validate_skill_dir(skill_dir: Path, report: Report) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        variants = [p for p in skill_dir.iterdir() if p.name.lower() == "skill.md"]
        hint = f" (found {variants[0].name}, casing must be SKILL.md)" if variants else ""
        report.error(skill_dir, f"missing SKILL.md{hint}")
        return

    text = skill_md.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        report.error(skill_md, "no YAML frontmatter block (must start with '---')")
        return
    meta = parse_frontmatter(frontmatter)

    name = meta.get("name", "")
    if not name:
        report.error(skill_md, "frontmatter is missing 'name'")
    else:
        if not NAME_RE.match(name):
            report.error(skill_md, f"name '{name}' must be kebab-case (a-z, 0-9, hyphens)")
        if len(name) > MAX_NAME:
            report.error(skill_md, f"name is {len(name)} chars, max {MAX_NAME}")
        if name != skill_dir.name:
            report.error(skill_md, f"name '{name}' does not match directory '{skill_dir.name}'")

    description = meta.get("description", "")
    if not description:
        report.error(skill_md, "frontmatter is missing 'description'")
    elif len(description) > MAX_DESCRIPTION:
        report.error(skill_md, f"description is {len(description)} chars, max {MAX_DESCRIPTION}")

    compatibility = meta.get("compatibility", "")
    if compatibility and len(compatibility) > MAX_COMPATIBILITY:
        report.error(skill_md, f"compatibility is {len(compatibility)} chars, max {MAX_COMPATIBILITY}")

    for field in sorted(meta):
        if field in SPEC_FIELDS:
            continue
        if field in CLAUDE_CODE_FIELDS:
            report.warn(skill_md, f"'{field}' is a Claude Code only field; other agents ignore it")
        else:
            report.warn(skill_md, f"'{field}' is not an Agent Skills spec field; consider metadata:")

    if not body.strip():
        report.error(skill_md, "body is empty")
    body_lines = len(body.splitlines())
    if body_lines > SOFT_MAX_BODY_LINES:
        report.warn(
            skill_md,
            f"body is {body_lines} lines; consider moving material to references/",
        )


def validate_manifests(report: Report) -> None:
    plugin_dir = ROOT / ".claude-plugin"
    for filename, required in (
        ("marketplace.json", ("name", "owner", "plugins")),
        ("plugin.json", ("name", "description", "version")),
    ):
        path = plugin_dir / filename
        if not path.is_file():
            report.error(path, "missing")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.error(path, f"invalid JSON: {exc}")
            continue
        for field in required:
            if field not in data:
                report.error(path, f"missing required field '{field}'")
        if filename == "marketplace.json":
            if not isinstance(data.get("owner"), dict) or "name" not in data.get("owner", {}):
                report.error(path, "'owner' must be an object with a 'name'")
            for plugin in data.get("plugins", []):
                for field in ("name", "source"):
                    if field not in plugin:
                        report.error(path, f"plugin entry missing '{field}'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--path",
        default="skills",
        help="directory containing skill sub-directories (default: skills)",
    )
    parser.add_argument(
        "--skip-manifests",
        action="store_true",
        help="do not validate .claude-plugin/*.json",
    )
    args = parser.parse_args(argv)

    report = Report()
    skills_root = (ROOT / args.path).resolve()
    if not skills_root.is_dir():
        report.error(skills_root, "directory not found")
    else:
        skill_dirs = sorted(
            p for p in skills_root.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
        for skill_dir in skill_dirs:
            validate_skill_dir(skill_dir, report)
        print(f"Checked {len(skill_dirs)} skill(s) in {rel(skills_root)}/")

    if not args.skip_manifests:
        validate_manifests(report)

    for line in report.warnings:
        print(f"WARNING {line}")
    for line in report.errors:
        print(f"ERROR   {line}")

    if report.errors:
        print(f"\n{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        return 1
    print(f"OK ({len(report.warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
