#!/usr/bin/env python3
"""Small, dependency-free structural validator for GEDCOM 5.x files."""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

LINE = re.compile(r"^(\d+)\s+(?:(@[A-Za-z0-9_:-]+@)\s+)?([A-Za-z0-9_]+)(?:\s(.*))?$")
XREF = re.compile(r"^@[A-Za-z0-9_:-]+@$")
ROOT_TYPES = {"HEAD", "TRLR", "INDI", "FAM", "NOTE", "SOUR", "OBJE", "REPO", "SUBM", "SUBN"}


def main(path: str) -> int:
    p = Path(path)
    text = p.read_bytes().decode("utf-8-sig")
    lines = text.splitlines()
    errors: list[str] = []
    warnings: list[str] = []
    records: dict[str, tuple[str, int]] = {}
    refs: dict[str, list[int]] = defaultdict(list)
    current = None

    for number, line in enumerate(lines, 1):
        if "\t" in line:
            warnings.append(f"line {number}: tab character")
        match = LINE.match(line)
        if not match:
            errors.append(f"line {number}: invalid GEDCOM line")
            continue
        level, xref, tag, value = match.groups()
        level = int(level)
        if level == 0:
            current = xref or tag
            if not xref and tag not in {"HEAD", "TRLR"}:
                errors.append(f"line {number}: level 0 record has no xref")
            elif tag not in ROOT_TYPES:
                warnings.append(f"line {number}: uncommon level 0 record type {tag}")
            elif xref and xref in records:
                errors.append(f"line {number}: duplicate xref {xref}")
            elif xref:
                records[xref] = (tag, number)
        elif current is None:
            errors.append(f"line {number}: subordinate line before first record")
        # Only a value occupying a pointer-bearing tag is structural. Notes
        # often quote historical xrefs such as @F0065@ as plain text.
        if value and tag in {"FAMC", "FAMS", "HUSB", "WIFE", "CHIL", "NOTE", "SOUR", "OBJE", "REPO", "SUBM"}:
            if tag in {"FAMC", "FAMS", "HUSB", "WIFE", "CHIL"} and XREF.fullmatch(value):
                refs[value].append(number)
            elif tag in {"NOTE", "SOUR", "OBJE", "REPO", "SUBM"} and XREF.fullmatch(value):
                refs[value].append(number)
        if number > 1:
            previous = LINE.match(lines[number - 2])
            if previous and level > int(previous.group(1)) + 1:
                errors.append(f"line {number}: level jumps from {previous.group(1)} to {level}")

    for pointer, locations in refs.items():
        if pointer not in records:
            errors.append(f"unresolved pointer {pointer} at lines {', '.join(map(str, locations[:5]))}")

    for number, line in enumerate(lines, 1):
        match = re.match(r"^1\s+(FAMC|FAMS|HUSB|WIFE|CHIL)\s+(@[^ ]+@)$", line)
        if match and match.group(2) in records:
            expected = "FAM" if match.group(1) in {"FAMC", "FAMS"} else "INDI"
            actual = records[match.group(2)][0]
            if actual != expected:
                errors.append(f"line {number}: {match.group(1)} points to {actual}, expected {expected}")

    print(f"{p}: {len(records)} records")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    print("RESULT: " + ("FAIL" if errors else "PASS"))
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} FILE.ged", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
