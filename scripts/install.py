#!/usr/bin/env python3
"""Install the skills in this repository into one or more AI coding agents.

Every agent that supports the Agent Skills standard (https://agentskills.io)
discovers skills as ``<skills-dir>/<skill-name>/SKILL.md``. Only the location
of ``<skills-dir>`` differs between tools. This script knows those locations
and links (default) or copies each ``skills/<name>`` folder into them.

Symlinks keep this clone as the single source of truth: ``git pull`` updates
every agent at once. Use ``--mode copy`` on filesystems without symlink
support (e.g. Windows without Developer Mode) or when the agent syncs the
directory to the cloud and cannot follow links.

Examples::

    python3 scripts/install.py --list                      # show known agents
    python3 scripts/install.py --agent claude-code codex   # user scope, symlinks
    python3 scripts/install.py --agent all --mode copy
    python3 scripts/install.py --agent agents --scope project --project-dir ~/work/app
    python3 scripts/install.py --agent cursor --skill my-skill other-skill
    python3 scripts/install.py --agent all --uninstall

Only the standard library is used.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"

CROSS_AGENT_USER = "~/.agents/skills"
CROSS_AGENT_PROJECT = ".agents/skills"


@dataclass(frozen=True)
class AgentSpec:
    key: str
    label: str
    user_dir: str | None  # None when the tool has no user-level directory
    project_dir: str | None
    note: str = ""


# Directories come from each tool's official documentation as of 2026-09.
# When a tool reads the shared ``.agents/skills`` convention, that is what
# we use so one install serves several agents at once.
AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        "agents",
        "Cross-agent (.agents/skills)",
        CROSS_AGENT_USER,
        CROSS_AGENT_PROJECT,
        "Read natively by Codex, Cursor, Copilot, Gemini CLI, OpenCode, Amp, "
        "Goose, Zed, Warp, Windsurf, Junie, Devin, Augment, Letta, Antigravity.",
    ),
    AgentSpec("claude-code", "Claude Code (Anthropic)", "~/.claude/skills", ".claude/skills"),
    AgentSpec("codex", "OpenAI Codex", CROSS_AGENT_USER, CROSS_AGENT_PROJECT,
              "Also scans ~/.codex/skills."),
    AgentSpec("cursor", "Cursor", "~/.cursor/skills", ".cursor/skills",
              "Also reads .agents/skills."),
    AgentSpec("copilot", "GitHub Copilot / VS Code", "~/.copilot/skills", ".github/skills",
              "Also reads .agents/skills and .claude/skills."),
    AgentSpec("gemini", "Gemini CLI (Google)", "~/.gemini/skills", ".gemini/skills",
              "Also reads .agents/skills."),
    AgentSpec("opencode", "OpenCode", "~/.config/opencode/skills", ".opencode/skills",
              "Also reads .agents/skills and .claude/skills."),
    AgentSpec("amp", "Amp (Sourcegraph)", "~/.config/agents/skills", CROSS_AGENT_PROJECT),
    AgentSpec("goose", "Goose (Block)", CROSS_AGENT_USER, CROSS_AGENT_PROJECT),
    AgentSpec("factory", "Factory Droid", "~/.factory/skills", ".factory/skills"),
    AgentSpec("windsurf", "Windsurf", None, ".windsurf/skills",
              "No user-level directory; use 'agents' for a global install."),
    AgentSpec("cline", "Cline", "~/.cline/skills", ".cline/skills"),
    AgentSpec("kiro", "Kiro", "~/.kiro/skills", ".kiro/skills",
              "Does not read .agents/skills."),
    AgentSpec("zed", "Zed", CROSS_AGENT_USER, CROSS_AGENT_PROJECT),
    AgentSpec("warp", "Warp", "~/.warp/skills", ".warp/skills",
              "Also reads .agents/skills."),
    AgentSpec("augment", "Augment", "~/.augment/skills", ".augment/skills"),
    AgentSpec("letta", "Letta", "~/.letta/skills", CROSS_AGENT_PROJECT),
)
AGENT_BY_KEY = {a.key: a for a in AGENTS}


def discover_skills() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def resolve_targets(agent_keys: list[str], scope: str, project_dir: Path) -> dict[Path, list[str]]:
    """Map each destination directory to the agents that use it (deduplicated)."""
    targets: dict[Path, list[str]] = {}
    for key in agent_keys:
        spec = AGENT_BY_KEY[key]
        raw = spec.user_dir if scope == "user" else spec.project_dir
        if raw is None:
            print(f"skip    {spec.label}: no {scope}-level skills directory")
            continue
        dest = Path(raw).expanduser() if scope == "user" else project_dir / raw
        targets.setdefault(dest.resolve() if dest.exists() else dest, []).append(spec.label)
    return targets


def points_into_repo(link: Path) -> bool:
    try:
        return link.is_symlink() and link.resolve().is_relative_to(SKILLS_DIR.resolve())
    except (OSError, RuntimeError):
        return False


def install_one(src: Path, dest_dir: Path, mode: str, force: bool, dry_run: bool) -> str:
    dest = dest_dir / src.name
    if dest.is_symlink() or dest.exists():
        if dest.is_symlink() and mode == "symlink" and points_into_repo(dest) \
                and dest.resolve() == src.resolve():
            return "ok      (already linked)"
        if not force:
            return "exists  (use --force to replace)"
        if not dry_run:
            remove_path(dest)
    if dry_run:
        return f"would {mode}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        try:
            dest.symlink_to(src.resolve(), target_is_directory=True)
        except OSError as exc:
            return f"FAILED  symlink: {exc} (try --mode copy)"
        return "linked"
    shutil.copytree(src, dest)
    return "copied"


def uninstall_one(src: Path, dest_dir: Path, force: bool, dry_run: bool) -> str:
    dest = dest_dir / src.name
    if not (dest.is_symlink() or dest.exists()):
        return "absent"
    if dest.is_symlink() and not points_into_repo(dest):
        return "kept    (symlink points elsewhere)"
    if not dest.is_symlink() and not force:
        return "kept    (copied directory; use --force to delete)"
    if not dry_run:
        remove_path(dest)
    return "would remove" if dry_run else "removed"


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def print_agent_table() -> None:
    width = max(len(a.key) for a in AGENTS)
    print(f"{'key'.ljust(width)}  {'user directory'.ljust(28)}  project directory")
    for a in AGENTS:
        user = a.user_dir or "-"
        proj = a.project_dir or "-"
        print(f"{a.key.ljust(width)}  {user.ljust(28)}  {proj}")
        if a.note:
            print(f"{''.ljust(width)}  {a.note}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples::", 1)[1] if "Examples::" in __doc__ else None,
    )
    parser.add_argument("--agent", nargs="+", metavar="AGENT",
                        help="agent keys to install into, or 'all' (see --list)")
    parser.add_argument("--scope", choices=("user", "project"), default="user",
                        help="user-level (default) or project-level directory")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd(),
                        help="project root for --scope project (default: current directory)")
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink",
                        help="symlink (default) or copy each skill folder")
    parser.add_argument("--skill", nargs="+", metavar="NAME",
                        help="only these skills (default: every skill in skills/)")
    parser.add_argument("--force", action="store_true",
                        help="replace existing entries (install) or delete copies (uninstall)")
    parser.add_argument("--uninstall", action="store_true", help="remove instead of install")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen")
    parser.add_argument("--list", action="store_true", help="list known agents and exit")
    args = parser.parse_args(argv)

    if args.list:
        print_agent_table()
        return 0
    if not args.agent:
        parser.error("--agent is required (or use --list)")

    keys = list(AGENT_BY_KEY) if "all" in args.agent else args.agent
    unknown = [k for k in keys if k not in AGENT_BY_KEY]
    if unknown:
        parser.error(f"unknown agent(s): {', '.join(unknown)}. See --list.")

    skills = discover_skills()
    if args.skill:
        by_name = {s.name: s for s in skills}
        missing = [n for n in args.skill if n not in by_name]
        if missing:
            parser.error(f"unknown skill(s): {', '.join(missing)}")
        skills = [by_name[n] for n in args.skill]
    if not skills:
        print("No skills found in skills/. Nothing to do.")
        return 0

    targets = resolve_targets(keys, args.scope, args.project_dir.resolve())
    failures = 0
    for dest_dir, labels in targets.items():
        print(f"\n{dest_dir}  [{', '.join(labels)}]")
        for src in skills:
            if args.uninstall:
                status = uninstall_one(src, dest_dir, args.force, args.dry_run)
            else:
                status = install_one(src, dest_dir, args.mode, args.force, args.dry_run)
            if status.startswith("FAILED"):
                failures += 1
            print(f"  {status:<40} {src.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
