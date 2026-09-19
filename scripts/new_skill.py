#!/usr/bin/env python3
"""Create a new skill directory from the template.

Usage::

    python3 scripts/new_skill.py my-skill-name

Copies ``templates/skill-template/SKILL.md`` to ``skills/my-skill-name/SKILL.md``
and replaces the placeholder name and title. Refuses to overwrite an existing
skill. Add ``references/``, ``scripts/`` or ``assets/`` sub-directories yourself
when the skill needs them.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "skill-template" / "SKILL.md"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if len(argv) == 2 else 2

    name = argv[1]
    if not NAME_RE.match(name) or len(name) > 64:
        print(f"error: '{name}' must be kebab-case (a-z, 0-9, hyphens), max 64 chars")
        return 2

    target_dir = ROOT / "skills" / name
    target = target_dir / "SKILL.md"
    if target.exists():
        print(f"error: {target.relative_to(ROOT)} already exists")
        return 1

    title = " ".join(part.capitalize() for part in name.split("-"))
    content = TEMPLATE.read_text(encoding="utf-8")
    content = content.replace("name: skill-template", f"name: {name}", 1)
    content = content.replace("# Skill Name", f"# {title}", 1)

    target_dir.mkdir(parents=True)
    target.write_text(content, encoding="utf-8")
    print(f"Created {target.relative_to(ROOT)}")
    print("Next: write the description in the frontmatter, then run")
    print("  python3 scripts/validate_skills.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
