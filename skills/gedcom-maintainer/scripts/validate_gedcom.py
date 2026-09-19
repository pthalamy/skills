#!/usr/bin/env python3
"""Structural and genealogical sanity checks for a GEDCOM 5.5 / 5.5.1 / 7.0 file.

Dependency-free (Python 3.9+). Checks:

* encoding: declared CHAR vs actual bytes, BOM, CRLF, ANSEL/ANSI fallbacks
* line syntax, level jumps, HEAD/TRLR, duplicate xrefs, GEDCOM 7 @VOID@
* every pointer resolves to a record of the expected type
* reciprocal links: INDI.FAMS <-> FAM.HUSB/WIFE and INDI.FAMC <-> FAM.CHIL
* family roles: a person who is both spouse and child, duplicate spouses,
  SEX vs HUSB/WIFE role (warning only)
* date syntax for every DATE, including calendar escapes and ranges
* chronology: death before birth, burial before death, baptism before birth,
  child born before a parent or long after a father's death, implausible
  parental ages, marriage before a spouse's birth or in childhood, lifespan
* NAME vs GIVN/SURN consistency, missing surname slashes
* CONC in GEDCOM 7, over-long lines in 5.x, orphan NOTE/SOUR/OBJE/REPO records

Severity: ERROR breaks the file or the graph; WARNING is very likely wrong
but a human must decide; INFO is worth knowing. Exit status 0 = no errors,
1 = errors (or warnings with --strict), 2 = could not read the file.

Usage::

    python3 validate_gedcom.py FILE.ged
    python3 validate_gedcom.py FILE.ged --json
    python3 validate_gedcom.py FILE.ged --strict --max-findings 200
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gedcom_lib import (  # noqa: E402
    POINTER_TAGS, ROOT_TYPES, TEXT_ROOTS, VOID, GDate, Gedcom, Node,
    display_name, event_date, parse, parse_date,
)

MAX_LINE_55 = 255
MIN_PARENT_AGE = 13
MAX_MOTHER_AGE = 50
MAX_FATHER_AGE = 80
MIN_MARRIAGE_AGE = 12
MAX_LIFESPAN = 110
POSTHUMOUS_MONTHS = 10
LIVING_YEARS = 100


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, severity: str, code: str, message: str, line: Optional[int] = None,
            xref: Optional[str] = None) -> None:
        self.items.append({"severity": severity, "code": code, "line": line, "xref": xref, "message": message})

    def error(self, code: str, message: str, line: Optional[int] = None, xref: Optional[str] = None) -> None:
        self.add("ERROR", code, message, line, xref)

    def warn(self, code: str, message: str, line: Optional[int] = None, xref: Optional[str] = None) -> None:
        self.add("WARNING", code, message, line, xref)

    def info(self, code: str, message: str, line: Optional[int] = None, xref: Optional[str] = None) -> None:
        self.add("INFO", code, message, line, xref)

    def count(self, severity: str) -> int:
        return sum(1 for i in self.items if i["severity"] == severity)


def check_encoding(g: Gedcom, f: Findings) -> None:
    declared = g.declared_charset
    if g.bom:
        f.info("encoding.bom", "file starts with a byte-order mark; keep it when writing back")
    if g.crlf:
        f.info("encoding.crlf", "file uses CRLF line endings; keep them when writing back")
    if declared in {"UTF-8", "UTF8"} and g.used_encoding != "utf-8":
        f.error("encoding.mismatch", f"HEAD.CHAR says UTF-8 but the bytes are not valid UTF-8 (decoded as {g.used_encoding})")
    elif declared == "ANSEL":
        f.warn("encoding.ansel", "file is declared ANSEL; structure was checked byte-transparently, "
               "so accented characters were not validated. Convert to UTF-8 only as a deliberate, whole-file step")
    elif declared in {"ANSI", "ASCII"} and g.used_encoding == "utf-8":
        pass
    elif declared in {"ANSI", "ASCII"}:
        f.info("encoding.ansi", f"file is declared {declared}; decoded as {g.used_encoding}")
    elif not declared:
        f.warn("encoding.undeclared", "HEAD has no CHAR line; the encoding was guessed as " + g.used_encoding)
    elif g.used_encoding.startswith("latin-1"):
        f.warn("encoding.unknown", f"HEAD.CHAR is '{declared}' and the bytes are not UTF-8; decoded byte-transparently")
    if g.major >= 7 and declared and declared != "UTF-8":
        f.error("encoding.v7", "GEDCOM 7 requires UTF-8")


def check_structure(g: Gedcom, f: Findings) -> None:
    for line, msg in g.syntax_errors:
        f.error("syntax", msg, line)
    if not g.records or g.records[0].tag != "HEAD":
        f.error("structure.head", "file does not start with a HEAD record", 1)
    if not g.records or g.records[-1].tag != "TRLR":
        f.error("structure.trlr", "file does not end with a TRLR record", len(g.raw_lines))
    if not g.version:
        f.warn("structure.version", "HEAD.GEDC.VERS missing; assuming 5.5.1")
    seen: set[str] = set()
    for rec in g.records:
        if rec.level != 0:
            continue
        if rec.tag in {"HEAD", "TRLR"}:
            if rec.xref:
                f.error("structure.xref", f"{rec.tag} must not carry an xref", rec.line)
            continue
        if not rec.xref:
            f.error("structure.xref", f"level 0 {rec.tag} record has no xref", rec.line)
        elif rec.xref in seen:
            f.error("structure.duplicate", f"duplicate xref {rec.xref}", rec.line, rec.xref)
        else:
            seen.add(rec.xref)
        if rec.tag not in ROOT_TYPES and not rec.tag.startswith("_"):
            f.warn("structure.roottype", f"uncommon level 0 record type {rec.tag}", rec.line, rec.xref)
        if rec.xref == VOID:
            f.error("structure.void", "@VOID@ cannot be a record identifier", rec.line)

    for rec in g.records:
        for node in rec.walk():
            if node.tag == "CONC" and g.major >= 7:
                f.error("structure.conc", "CONC is not allowed in GEDCOM 7; join the text onto the previous line", node.line, rec.xref)
            if node.tag in {"CONC", "CONT"} and node.parent and node.parent.tag in {"CONC", "CONT"}:
                f.error("structure.cont", f"{node.tag} nested under {node.parent.tag}; continuation lines sit at the same level", node.line, rec.xref)
            if g.major < 7 and len(g.raw_lines[node.line - 1]) > MAX_LINE_55:
                f.warn("structure.linelength", f"line is {len(g.raw_lines[node.line - 1])} chars; GEDCOM 5.5.1 limits lines to {MAX_LINE_55}, split with CONC", node.line, rec.xref)
            if node.value and "@" in node.value and not node.is_pointer() and node.tag not in {"DATE"} \
                    and re.search(r"(?<!@)@(?!@)(?!#)", node.value) and g.major < 7 and node.tag in {"NOTE", "CONT", "CONC", "TEXT", "PAGE", "TITL"}:
                f.info("structure.at", "unescaped '@' in text; GEDCOM 5.5.1 expects '@@'", node.line, rec.xref)


def check_pointers(g: Gedcom, f: Findings) -> None:
    referenced: set[str] = set()
    for rec in g.records:
        for node in rec.walk():
            if node.level == 0 or not node.is_pointer():
                continue
            target = node.value
            if target == VOID:
                if g.major < 7:
                    f.error("pointer.void", "@VOID@ is a GEDCOM 7 construct; remove the line or point to a real record", node.line, rec.xref)
                continue
            expected = POINTER_TAGS.get(node.tag)
            if expected is None:
                # Custom tag or unusual place for a pointer; still make sure it resolves.
                if target not in g.by_xref:
                    f.warn("pointer.unresolved", f"{node.tag} points to {target}, which does not exist", node.line, rec.xref)
                else:
                    referenced.add(target)
                continue
            actual = g.type_of(target)
            if actual is None:
                f.error("pointer.unresolved", f"{node.tag} points to {target}, which does not exist", node.line, rec.xref)
            elif actual != expected and not (expected == "NOTE" and actual == "SNOTE"):
                f.error("pointer.type", f"{node.tag} points to a {actual} record, expected {expected}", node.line, rec.xref)
            else:
                referenced.add(target)
    for rec in g.records:
        if rec.xref and rec.tag in TEXT_ROOTS and rec.xref not in referenced:
            f.warn("orphan.record", f"{rec.tag} record {rec.xref} is referenced by nothing; a leftover from a merge or deletion?", rec.line, rec.xref)


def check_links(g: Gedcom, f: Findings) -> None:
    fams = {r.xref: r for r in g.of_type("FAM") if r.xref}
    indis = {r.xref: r for r in g.of_type("INDI") if r.xref}

    for fam in fams.values():
        spouses = [n for n in fam.children if n.tag in {"HUSB", "WIFE"} and n.is_pointer()]
        children = [n for n in fam.all("CHIL") if n.is_pointer()]
        for tag in ("HUSB", "WIFE"):
            if len(fam.all(tag)) > 1:
                f.error("role.duplicate", f"family has more than one {tag}; each union is its own FAM record", fam.line, fam.xref)
        spouse_ids = {n.value for n in spouses}
        child_ids = [n.value for n in children]
        for cid, count in Counter(child_ids).items():
            if count > 1:
                f.error("role.duplicatechild", f"{cid} is listed as CHIL {count} times", fam.line, fam.xref)
        for cid in set(child_ids) & spouse_ids:
            f.error("role.selfparent", f"{cid} is both a spouse and a child of this family", fam.line, fam.xref)
        for n in spouses:
            indi = indis.get(n.value)
            if indi is None:
                continue
            if not any(x.value == fam.xref for x in indi.all("FAMS")):
                f.error("link.fams", f"{fam.xref} names {n.value} as {n.tag} but {n.value} has no 'FAMS {fam.xref}'", n.line, fam.xref)
            sex = indi.get("SEX")
            if sex and ((n.tag == "HUSB" and sex == "F") or (n.tag == "WIFE" and sex == "M")):
                f.warn("role.sex", f"{n.value} is SEX {sex} but listed as {n.tag}; check the sex or the role", n.line, fam.xref)
        for n in children:
            indi = indis.get(n.value)
            if indi is None:
                continue
            if not any(x.value == fam.xref for x in indi.all("FAMC")):
                f.error("link.famc", f"{fam.xref} lists {n.value} as CHIL but {n.value} has no 'FAMC {fam.xref}'", n.line, fam.xref)
        if not spouses and not children:
            f.warn("orphan.family", "family has neither spouses nor children", fam.line, fam.xref)

    for indi in indis.values():
        for n in indi.all("FAMS"):
            fam = fams.get(n.value)
            if fam is None:
                continue
            if not any(x.value == indi.xref for x in fam.children if x.tag in {"HUSB", "WIFE"}):
                f.error("link.fams", f"{indi.xref} has 'FAMS {n.value}' but that family lists it as neither HUSB nor WIFE", n.line, indi.xref)
        famcs = [n for n in indi.all("FAMC")]
        for n in famcs:
            fam = fams.get(n.value)
            if fam is None:
                continue
            if not any(x.value == indi.xref for x in fam.all("CHIL")):
                f.error("link.famc", f"{indi.xref} has 'FAMC {n.value}' but that family does not list it as CHIL", n.line, indi.xref)
        birth_links = [n for n in famcs if (n.get("PEDI") or "birth").lower() in {"birth", "biological"}]
        if len(birth_links) > 1:
            f.warn("role.multiparents", f"{indi.xref} has {len(birth_links)} birth families; mark adoptive/foster links with PEDI or resolve the duplicate", indi.line, indi.xref)
        if not famcs and not indi.all("FAMS"):
            f.info("orphan.individual", f"{indi.xref} ({display_name(indi)}) is linked to no family", indi.line, indi.xref)


def _report_date_problems(g: Gedcom, f: Findings) -> None:
    for rec in g.records:
        for node in rec.walk():
            if node.tag != "DATE" or node.parent is None:
                continue
            if node.parent.tag in {"CHAN", "CREA"} or (rec.tag == "HEAD"):
                continue
            gd = parse_date(node.value)
            for p in gd.problems:
                f.warn("date.syntax", f"{node.parent.tag} DATE '{node.value}': {p}", node.line, rec.xref)
            if gd.phrase:
                f.info("date.phrase", f"{node.parent.tag} DATE is a free-text phrase; software cannot sort it. Prefer ABT/BEF/AFT plus a note", node.line, rec.xref)
            if gd.year and not gd.phrase and gd.year > _dt.date.today().year:
                f.warn("date.future", f"{node.parent.tag} DATE '{node.value}' is in the future", node.line, rec.xref)


def _first(indi: Node, *tags: str) -> tuple[Optional[GDate], str]:
    for t in tags:
        gd = event_date(indi, t)
        if gd and gd.year:
            return gd, t
    return None, ""


def _before(a: GDate, b: GDate, slack: int = 0) -> bool:
    """True when every possible reading of a ends before every reading of b."""
    _, a_hi = a.bounds(slack)
    b_lo, _ = b.bounds(slack)
    return a_hi is not None and b_lo is not None and a_hi < b_lo


def _gap_years(earlier: GDate, later: GDate) -> Optional[float]:
    """Smallest possible gap in years from earlier to later (None if unknown)."""
    e_lo, e_hi = earlier.bounds()
    l_lo, l_hi = later.bounds()
    if e_hi is None or l_lo is None:
        return None
    return l_lo - e_hi


def _max_gap_years(earlier: GDate, later: GDate) -> Optional[float]:
    e_lo, _ = earlier.bounds()
    _, l_hi = later.bounds()
    if e_lo is None or l_hi is None:
        return None
    return l_hi - e_lo


def check_chronology(g: Gedcom, f: Findings) -> None:
    indis = {r.xref: r for r in g.of_type("INDI") if r.xref}
    for indi in indis.values():
        name = display_name(indi)
        birth, btag = _first(indi, "BIRT", "CHR", "BAPM")
        death, dtag = _first(indi, "DEAT", "BURI", "CREM")
        b_exact = event_date(indi, "BIRT")
        for tag in ("CHR", "BAPM"):
            ev = event_date(indi, tag)
            if b_exact and b_exact.year and ev and ev.year and _before(ev, b_exact):
                f.warn("chrono.baptism", f"{name}: {tag} precedes BIRT", indi.line, indi.xref)
        d_exact = event_date(indi, "DEAT")
        for tag in ("BURI", "CREM"):
            ev = event_date(indi, tag)
            if d_exact and d_exact.year and ev and ev.year and _before(ev, d_exact):
                f.warn("chrono.burial", f"{name}: {tag} precedes DEAT", indi.line, indi.xref)
        if birth and death:
            if _before(death, birth):
                f.error("chrono.deathbeforebirth", f"{name}: {dtag} {death.raw} precedes {btag} {birth.raw}", indi.line, indi.xref)
            gap = _gap_years(birth, death)
            if gap is not None and gap > MAX_LIFESPAN:
                f.warn("chrono.lifespan", f"{name}: lifespan of at least {gap:.0f} years", indi.line, indi.xref)
        if birth and not death and birth.year and _dt.date.today().year - (birth.gregorian_year() or birth.year) < LIVING_YEARS:
            f.info("privacy.living", f"{name}: born {birth.raw} with no death event; possibly living, keep personal details minimal", indi.line, indi.xref)

    for fam in g.of_type("FAM"):
        husb = indis.get(fam.get("HUSB") or "")
        wife = indis.get(fam.get("WIFE") or "")
        marr = event_date(fam, "MARR")
        parents = [(husb, "HUSB"), (wife, "WIFE")]
        for parent, role in parents:
            if parent is None:
                continue
            pname = display_name(parent)
            pbirth, _ = _first(parent, "BIRT", "CHR", "BAPM")
            pdeath, _ = _first(parent, "DEAT", "BURI")
            if marr and marr.year:
                if pbirth and _before(marr, pbirth):
                    f.error("chrono.marriagebeforebirth", f"MARR {marr.raw} precedes birth of {role} {pname}", fam.line, fam.xref)
                elif pbirth:
                    gap = _max_gap_years(pbirth, marr)
                    if gap is not None and gap < MIN_MARRIAGE_AGE:
                        f.warn("chrono.childmarriage", f"{role} {pname} was under {MIN_MARRIAGE_AGE} at MARR {marr.raw}", fam.line, fam.xref)
                if pdeath and _before(pdeath, marr):
                    f.warn("chrono.marriageafterdeath", f"MARR {marr.raw} follows death of {role} {pname} ({pdeath.raw})", fam.line, fam.xref)
            for chil in fam.all("CHIL"):
                child = indis.get(chil.value)
                if child is None:
                    continue
                cbirth, _ = _first(child, "BIRT", "CHR", "BAPM")
                if not cbirth:
                    continue
                cname = display_name(child)
                pedi = next((n.get("PEDI") for n in child.all("FAMC") if n.value == fam.xref), None)
                if pedi and pedi.lower() not in {"birth", "biological"}:
                    continue  # adoptive/foster/step links are not bound by biology
                if pbirth:
                    if _before(cbirth, pbirth):
                        f.error("chrono.childbeforeparent", f"{cname} ({cbirth.raw}) born before {role} {pname} ({pbirth.raw})", chil.line, fam.xref)
                    else:
                        age_max = _max_gap_years(pbirth, cbirth)
                        age_min = _gap_years(pbirth, cbirth)
                        if age_max is not None and age_max < MIN_PARENT_AGE:
                            f.warn("chrono.parentage", f"{role} {pname} was under {MIN_PARENT_AGE} at birth of {cname}", chil.line, fam.xref)
                        limit = MAX_MOTHER_AGE if role == "WIFE" else MAX_FATHER_AGE
                        if age_min is not None and age_min > limit:
                            f.warn("chrono.parentage", f"{role} {pname} was over {limit} at birth of {cname}; same-name parent or wrong family?", chil.line, fam.xref)
                if pdeath:
                    gap = _gap_years(pdeath, cbirth)
                    if gap is not None and gap > (POSTHUMOUS_MONTHS / 12 if role == "HUSB" else 0):
                        f.error("chrono.posthumous", f"{cname} born {cbirth.raw}, {gap:.1f} years after death of {role} {pname} ({pdeath.raw})", chil.line, fam.xref)


def check_names(g: Gedcom, f: Findings) -> None:
    for indi in g.of_type("INDI"):
        names = indi.all("NAME")
        if not names:
            f.warn("name.missing", f"{indi.xref} has no NAME", indi.line, indi.xref)
            continue
        for n in names:
            m = re.search(r"/([^/]*)/", n.value)
            if not m:
                f.warn("name.slashes", f"NAME '{n.value}' has no /Surname/ delimiters; software cannot tell given names from the surname", n.line, indi.xref)
            surn, givn = n.get("SURN"), n.get("GIVN")
            if m and surn and m.group(1).strip().casefold() != surn.strip().casefold():
                f.warn("name.surn", f"SURN '{surn}' differs from the /{m.group(1)}/ in NAME", n.line, indi.xref)
            if givn:
                given_part = re.sub(r"/[^/]*/", " ", n.value).split()
                if givn.strip().casefold() not in " ".join(given_part).casefold():
                    f.warn("name.givn", f"GIVN '{givn}' is not part of NAME '{n.value}'", n.line, indi.xref)
        sex = indi.get("SEX")
        if sex and sex not in {"M", "F", "U", "X"}:
            f.warn("name.sex", f"SEX '{sex}' is not one of M, F, U, X", indi.line, indi.xref)


def check_citations(g: Gedcom, f: Findings) -> None:
    fact_tags = {"BIRT", "DEAT", "MARR", "CHR", "BAPM", "BURI", "DIV", "ADOP"}
    unsourced = 0
    for rec in g.of_type("INDI") + g.of_type("FAM"):
        for ev in rec.children:
            if ev.tag in fact_tags and not ev.all("SOUR") and not rec.all("SOUR"):
                unsourced += 1
            for s in ev.all("SOUR"):
                q = s.get("QUAY")
                if q and q not in {"0", "1", "2", "3"}:
                    f.warn("cite.quay", f"QUAY '{q}' must be 0-3", s.line, rec.xref)
    if unsourced:
        f.info("cite.unsourced", f"{unsourced} vital events (birth, death, marriage, baptism, burial) carry no SOUR citation")


def summarize(g: Gedcom) -> dict:
    counts = Counter(r.tag for r in g.records)
    years = []
    for indi in g.of_type("INDI"):
        for t in ("BIRT", "DEAT"):
            gd = event_date(indi, t)
            if gd and gd.year:
                years.append(gd.gregorian_year())
    return {
        "file": g.path,
        "version": g.version or "unknown",
        "declared_charset": g.declared_charset or "none",
        "used_encoding": g.used_encoding,
        "bom": g.bom,
        "crlf": g.crlf,
        "records": {k: v for k, v in sorted(counts.items())},
        "year_range": [min(years), max(years)] if years else None,
    }


def run(path: str) -> tuple[dict, Findings]:
    g = parse(path)
    f = Findings()
    check_encoding(g, f)
    check_structure(g, f)
    check_pointers(g, f)
    check_links(g, f)
    _report_date_problems(g, f)
    check_chronology(g, f)
    check_names(g, f)
    check_citations(g, f)
    order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    f.items.sort(key=lambda i: (order[i["severity"]], i["line"] or 0))
    return summarize(g), f


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--no-info", action="store_true", help="hide INFO findings")
    ap.add_argument("--max-findings", type=int, default=500, help="cap printed findings (default 500)")
    args = ap.parse_args(argv)

    try:
        summary, f = run(args.file)
    except (OSError, UnicodeError) as exc:
        if args.json:
            print(json.dumps({"file": args.file, "result": "UNREADABLE", "error": str(exc)}))
        else:
            print(f"ERROR: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2

    errors, warnings, infos = f.count("ERROR"), f.count("WARNING"), f.count("INFO")
    failed = errors > 0 or (args.strict and warnings > 0)
    items = [i for i in f.items if not (args.no_info and i["severity"] == "INFO")]
    if args.json:
        print(json.dumps({**summary, "counts": {"errors": errors, "warnings": warnings, "info": infos},
                          "findings": items[:args.max_findings], "truncated": len(items) > args.max_findings,
                          "result": "FAIL" if failed else "PASS"}, indent=2, ensure_ascii=False))
        return 1 if failed else 0

    recs = ", ".join(f"{v} {k}" for k, v in summary["records"].items() if k not in {"HEAD", "TRLR"})
    print(f"{summary['file']}: GEDCOM {summary['version']}, CHAR {summary['declared_charset']} "
          f"(read as {summary['used_encoding']}{', BOM' if summary['bom'] else ''}{', CRLF' if summary['crlf'] else ''})")
    print(f"records: {recs}" + (f"; events span {summary['year_range'][0]}-{summary['year_range'][1]}" if summary["year_range"] else ""))
    for i in items[:args.max_findings]:
        where = f"line {i['line']}" if i["line"] else "file"
        who = f" {i['xref']}" if i["xref"] else ""
        print(f"{i['severity']}: {where}{who}: {i['message']}  [{i['code']}]")
    if len(items) > args.max_findings:
        print(f"... {len(items) - args.max_findings} more findings hidden (raise --max-findings)")
    print(f"RESULT: {'FAIL' if failed else 'PASS'} ({errors} errors, {warnings} warnings, {infos} info)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
