#!/usr/bin/env python3
"""Read-only helper to look inside a GEDCOM file without loading it whole.

Large trees do not fit in an agent's context. Use this to find the records
you need, print them with their relationships and sources, and diff two
versions of a file to build the change log. Dependency-free (Python 3.9+).

Subcommands::

    summary FILE                 counts, version, encoding, year span, top surnames
    find FILE QUERY [options]    individuals whose name matches (case/accents folded)
        --born YEAR [--tolerance N]   restrict to a birth year (default +/- 2)
        --place TEXT                  restrict to a place substring in any event
    show FILE XREF [XREF...]     an INDI, FAM, SOUR, NOTE or REPO with everything linked
    refs FILE XREF               every line anywhere that points to XREF
    diff OLD NEW                 records added, removed and changed between two files
    raw FILE XREF                the record's raw lines, ready to edit

Add --json to any subcommand for machine-readable output.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gedcom_lib import Gedcom, Node, display_name, event_date, parse, surname  # noqa: E402

EVENTS = ["BIRT", "CHR", "BAPM", "DEAT", "BURI", "CREM", "MARR", "DIV", "ADOP", "RESI", "OCCU", "CENS", "EVEN"]


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).casefold()


def birth_year(indi: Node) -> Optional[int]:
    for t in ("BIRT", "CHR", "BAPM"):
        gd = event_date(indi, t)
        if gd and gd.year:
            return gd.gregorian_year()
    return None


def death_year(indi: Node) -> Optional[int]:
    for t in ("DEAT", "BURI"):
        gd = event_date(indi, t)
        if gd and gd.year:
            return gd.gregorian_year()
    return None


def one_line(indi: Node) -> str:
    b, d = birth_year(indi), death_year(indi)
    span = f"{b or '?'}-{d or ''}" if (b or d) else ""
    return f"{indi.xref} {display_name(indi)} ({indi.get('SEX') or '?'}) {span}".rstrip()


# ---------------------------------------------------------------- summary --

def cmd_summary(g: Gedcom, args) -> dict:
    counts = Counter(r.tag for r in g.records)
    indis = g.of_type("INDI")
    years = [y for y in (birth_year(i) for i in indis) if y]
    surnames = Counter(surname(i) for i in indis if surname(i))
    places = Counter()
    for rec in indis + g.of_type("FAM"):
        for n in rec.walk():
            if n.tag == "PLAC" and n.value:
                places[n.value] += 1
    sourced = sum(1 for i in indis if any(n.tag == "SOUR" for n in i.walk()))
    custom = Counter(n.tag for r in g.records for n in r.walk() if n.tag.startswith("_"))
    return {
        "file": g.path, "version": g.version or "unknown", "charset": g.declared_charset or "none",
        "encoding": g.used_encoding, "bom": g.bom, "crlf": g.crlf, "software": g.head().get("SOUR") if g.head() else None,
        "records": dict(sorted(counts.items())), "birth_year_range": [min(years), max(years)] if years else None,
        "individuals_with_any_source": sourced, "top_surnames": surnames.most_common(15),
        "top_places": places.most_common(10), "custom_tags": dict(custom.most_common()),
    }


def print_summary(d: dict) -> None:
    print(f"{d['file']}: GEDCOM {d['version']} from {d['software'] or 'unknown software'}, CHAR {d['charset']} "
          f"(read as {d['encoding']}{', BOM' if d['bom'] else ''}{', CRLF' if d['crlf'] else ''})")
    print("records: " + ", ".join(f"{v} {k}" for k, v in d["records"].items() if k not in {"HEAD", "TRLR"}))
    if d["birth_year_range"]:
        print(f"births span {d['birth_year_range'][0]}-{d['birth_year_range'][1]}")
    print(f"individuals with at least one source: {d['individuals_with_any_source']}/{d['records'].get('INDI', 0)}")
    print("surnames: " + ", ".join(f"{s} ({n})" for s, n in d["top_surnames"]))
    print("places: " + ", ".join(f"{p} ({n})" for p, n in d["top_places"]))
    if d["custom_tags"]:
        print("custom tags (preserve as-is): " + ", ".join(f"{t} ({n})" for t, n in d["custom_tags"].items()))


# ------------------------------------------------------------------- find --

def cmd_find(g: Gedcom, args) -> list[dict]:
    q = fold(args.query)
    out = []
    for indi in g.of_type("INDI"):
        names = [fold(n.value.replace("/", " ")) for n in indi.all("NAME")]
        if not any(all(part in nm for part in q.split()) for nm in names):
            continue
        by = birth_year(indi)
        if args.born is not None and (by is None or abs(by - args.born) > args.tolerance):
            continue
        if args.place:
            pf = fold(args.place)
            if not any(n.tag == "PLAC" and pf in fold(n.value) for n in indi.walk()):
                continue
        out.append({"xref": indi.xref, "name": display_name(indi), "sex": indi.get("SEX"), "birth": birth_year(indi),
                    "death": death_year(indi), "line": indi.line, "summary": one_line(indi)})
    return out


# ------------------------------------------------------------------- show --

def event_dict(ev: Node, g: Gedcom) -> dict:
    d = {"tag": ev.tag, "value": ev.value or None, "date": ev.get("DATE"), "place": ev.get("PLAC"), "sources": []}
    if ev.child("TYPE"):
        d["type"] = ev.get("TYPE")
    for s in ev.all("SOUR"):
        d["sources"].append(cite_dict(s, g))
    notes = [note_text(n, g) for n in ev.all("NOTE")]
    if notes:
        d["notes"] = notes
    return d


def cite_dict(s: Node, g: Gedcom) -> dict:
    d = {"source": s.value if s.is_pointer() else None, "inline": None if s.is_pointer() else s.text(),
         "page": s.get("PAGE"), "quay": s.get("QUAY"), "data_date": s.get("DATA", "DATE"), "text": None}
    if s.is_pointer():
        src = g.by_xref.get(s.value)
        if src:
            d["title"] = src.get("TITL")
    t = s.child("DATA")
    if t and t.child("TEXT"):
        d["text"] = t.child("TEXT").text()
    return {k: v for k, v in d.items() if v is not None}


def note_text(n: Node, g: Gedcom) -> str:
    if n.is_pointer():
        rec = g.by_xref.get(n.value)
        return f"{n.value}: {rec.text() if rec else '(missing)'}"
    return n.text()


def indi_dict(indi: Node, g: Gedcom) -> dict:
    d = {"xref": indi.xref, "type": "INDI", "line": indi.line,
         "names": [{"name": n.value, "type": n.get("TYPE"), "givn": n.get("GIVN"), "surn": n.get("SURN"), "nick": n.get("NICK")} for n in indi.all("NAME")],
         "sex": indi.get("SEX"), "events": [event_dict(e, g) for e in indi.children if e.tag in EVENTS],
         "parents": [], "unions": [], "notes": [note_text(n, g) for n in indi.all("NOTE")],
         "sources": [cite_dict(s, g) for s in indi.all("SOUR")],
         "custom": {n.tag: n.value for n in indi.children if n.tag.startswith("_")}}
    for fc in indi.all("FAMC"):
        fam = g.by_xref.get(fc.value)
        entry = {"family": fc.value, "pedigree": fc.get("PEDI") or "birth"}
        if fam:
            for role in ("HUSB", "WIFE"):
                p = g.by_xref.get(fam.get(role) or "")
                entry[role.lower()] = one_line(p) if p else None
        d["parents"].append(entry)
    for fs in indi.all("FAMS"):
        fam = g.by_xref.get(fs.value)
        entry = {"family": fs.value}
        if fam:
            other = fam.get("WIFE") if fam.get("HUSB") == indi.xref else fam.get("HUSB")
            o = g.by_xref.get(other or "")
            entry["spouse"] = one_line(o) if o else None
            entry["marriage"] = event_dict(fam.child("MARR"), g) if fam.child("MARR") else None
            entry["children"] = [one_line(g.by_xref[c.value]) if c.value in g.by_xref else c.value for c in fam.all("CHIL")]
        d["unions"].append(entry)
    return d


def fam_dict(fam: Node, g: Gedcom) -> dict:
    d = {"xref": fam.xref, "type": "FAM", "line": fam.line}
    for role in ("HUSB", "WIFE"):
        p = g.by_xref.get(fam.get(role) or "")
        d[role.lower()] = one_line(p) if p else fam.get(role)
    d["children"] = []
    for c in fam.all("CHIL"):
        child = g.by_xref.get(c.value)
        pedi = next((n.get("PEDI") for n in child.all("FAMC") if n.value == fam.xref), None) if child else None
        d["children"].append({"summary": one_line(child) if child else c.value, "pedigree": pedi or "birth"})
    d["events"] = [event_dict(e, g) for e in fam.children if e.tag in EVENTS]
    d["notes"] = [note_text(n, g) for n in fam.all("NOTE")]
    d["sources"] = [cite_dict(s, g) for s in fam.all("SOUR")]
    return d


def generic_dict(rec: Node, g: Gedcom) -> dict:
    d = {"xref": rec.xref, "type": rec.tag, "line": rec.line, "text": rec.text() or None,
         "fields": {c.tag: c.text() for c in rec.children if c.tag not in {"CONT", "CONC"}},
         "referenced_by": [r.xref for r in g.records if r.xref != rec.xref and any(n.is_pointer() and n.value == rec.xref for n in r.walk())]}
    return d


def cmd_show(g: Gedcom, args) -> list[dict]:
    out = []
    for x in args.xrefs:
        x = x if x.startswith("@") else f"@{x}@"
        rec = g.by_xref.get(x)
        if rec is None:
            out.append({"xref": x, "error": "no such record"})
        elif rec.tag == "INDI":
            out.append(indi_dict(rec, g))
        elif rec.tag == "FAM":
            out.append(fam_dict(rec, g))
        else:
            out.append(generic_dict(rec, g))
    return out


def print_show(items: list[dict]) -> None:
    for d in items:
        if "error" in d:
            print(f"{d['xref']}: {d['error']}")
            continue
        print(f"== {d['xref']} ({d['type']}, line {d['line']})")
        if d["type"] == "INDI":
            for n in d["names"]:
                extra = " ".join(f"{k}={v}" for k, v in n.items() if k != "name" and v)
                print(f"  NAME {n['name']}" + (f"  [{extra}]" if extra else ""))
            print(f"  SEX {d['sex'] or '?'}")
            for e in d["events"]:
                _print_event(e, "  ")
            for p in d["parents"]:
                print(f"  child of {p['family']} ({p['pedigree']}): father {p.get('husb') or '-'}; mother {p.get('wife') or '-'}")
            for u in d["unions"]:
                print(f"  union {u['family']} with {u.get('spouse') or '-'}")
                if u.get("marriage"):
                    _print_event(u["marriage"], "    ")
                for c in u.get("children", []):
                    print(f"    child {c}")
        elif d["type"] == "FAM":
            print(f"  HUSB {d.get('husb') or '-'}")
            print(f"  WIFE {d.get('wife') or '-'}")
            for c in d["children"]:
                print(f"  CHIL {c['summary']}" + (f" ({c['pedigree']})" if c["pedigree"] != "birth" else ""))
            for e in d["events"]:
                _print_event(e, "  ")
        else:
            for k, v in d["fields"].items():
                print(f"  {k} {v}")
            if d["text"]:
                print(f"  TEXT {d['text']}")
            print(f"  referenced by: {', '.join(d['referenced_by']) or 'nothing'}")
        for n in d.get("notes", []):
            print(f"  NOTE {n}")
        for s in d.get("sources", []):
            print(f"  SOUR {_cite(s)}")
        if d.get("custom"):
            print("  custom: " + ", ".join(f"{k} {v}" for k, v in d["custom"].items()))


def _cite(s: dict) -> str:
    parts = [s.get("source") or "(inline)", s.get("title"), s.get("page"), f"QUAY {s['quay']}" if s.get("quay") else None]
    return " | ".join(p for p in parts if p)


def _print_event(e: dict, indent: str) -> None:
    head = f"{indent}{e['tag']}" + (f" ({e['type']})" if e.get("type") else "") + (f" {e['value']}" if e.get("value") else "")
    print(f"{head}: {e.get('date') or 'no date'}" + (f", {e['place']}" if e.get("place") else ""))
    for s in e["sources"]:
        print(f"{indent}  SOUR {_cite(s)}")
    for n in e.get("notes", []):
        print(f"{indent}  NOTE {n}")


# ------------------------------------------------------------------- refs --

def cmd_refs(g: Gedcom, args) -> list[dict]:
    x = args.xref if args.xref.startswith("@") else f"@{args.xref}@"
    out = []
    for rec in g.records:
        for n in rec.walk():
            if n.level > 0 and n.is_pointer() and n.value == x:
                out.append({"line": n.line, "record": rec.xref, "record_type": rec.tag, "tag": n.tag,
                            "context": n.parent.tag if n.parent and n.parent.level > 0 else None,
                            "raw": g.raw_lines[n.line - 1]})
    return out


# -------------------------------------------------------------------- raw --

def cmd_raw(g: Gedcom, args) -> dict:
    x = args.xref if args.xref.startswith("@") else f"@{args.xref}@"
    rec = g.by_xref.get(x)
    if rec is None:
        return {"xref": x, "error": "no such record"}
    end = max(n.line for n in rec.walk())
    return {"xref": x, "first_line": rec.line, "last_line": end, "lines": g.raw_lines[rec.line - 1:end]}


# ------------------------------------------------------------------- diff --

def record_lines(g: Gedcom, rec: Node) -> list[str]:
    end = max(n.line for n in rec.walk())
    return g.raw_lines[rec.line - 1:end]


def cmd_diff(old: Gedcom, new: Gedcom) -> dict:
    o = {r.xref: r for r in old.records if r.xref}
    n = {r.xref: r for r in new.records if r.xref}
    added = [{"xref": x, "type": n[x].tag, "summary": display_name(n[x]) if n[x].tag == "INDI" else n[x].tag} for x in n if x not in o]
    removed = [{"xref": x, "type": o[x].tag, "summary": display_name(o[x]) if o[x].tag == "INDI" else o[x].tag} for x in o if x not in n]
    changed = []
    for x in o:
        if x in n:
            a, b = record_lines(old, o[x]), record_lines(new, n[x])
            if a != b:
                sa, sb = set(a), set(b)
                changed.append({"xref": x, "type": n[x].tag, "summary": display_name(n[x]) if n[x].tag == "INDI" else n[x].tag,
                                "removed_lines": [l for l in a if l not in sb], "added_lines": [l for l in b if l not in sa]})
    head_changed = (old.head() and new.head() and record_lines(old, old.head()) != record_lines(new, new.head()))
    return {"old": old.path, "new": new.path, "added": added, "removed": removed, "changed": changed, "head_changed": bool(head_changed),
            "encoding_changed": (old.used_encoding, old.bom, old.crlf) != (new.used_encoding, new.bom, new.crlf)}


def print_diff(d: dict) -> None:
    print(f"{d['old']} -> {d['new']}: {len(d['added'])} added, {len(d['removed'])} removed, {len(d['changed'])} changed")
    if d["encoding_changed"]:
        print("WARNING: encoding, BOM or line endings changed between the two files")
    for a in d["added"]:
        print(f"+ {a['xref']} {a['summary']}")
    for r in d["removed"]:
        print(f"- {r['xref']} {r['summary']}")
    for c in d["changed"]:
        print(f"~ {c['xref']} {c['summary']}")
        for l in c["removed_lines"]:
            print(f"    - {l}")
        for l in c["added_lines"]:
            print(f"    + {l}")
    if d["head_changed"]:
        print("~ HEAD changed")


# ------------------------------------------------------------------- main --

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("summary"); p.add_argument("file")
    p = sub.add_parser("find"); p.add_argument("file"); p.add_argument("query")
    p.add_argument("--born", type=int); p.add_argument("--tolerance", type=int, default=2); p.add_argument("--place")
    p = sub.add_parser("show"); p.add_argument("file"); p.add_argument("xrefs", nargs="+")
    p = sub.add_parser("refs"); p.add_argument("file"); p.add_argument("xref")
    p = sub.add_parser("raw"); p.add_argument("file"); p.add_argument("xref")
    p = sub.add_parser("diff"); p.add_argument("old"); p.add_argument("new")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "diff":
            result = cmd_diff(parse(args.old), parse(args.new))
        else:
            g = parse(args.file)
            result = {"summary": cmd_summary, "find": cmd_find, "show": cmd_show, "refs": cmd_refs, "raw": cmd_raw}[args.cmd](g, args)
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "summary":
        print_summary(result)
    elif args.cmd == "find":
        for r in result:
            print(f"{r['summary']}  (line {r['line']})")
        if not result:
            print("no match")
    elif args.cmd == "show":
        print_show(result)
    elif args.cmd == "refs":
        for r in result:
            print(f"line {r['line']} in {r['record']} ({r['record_type']}): {r['raw']}")
        if not result:
            print("no references")
    elif args.cmd == "raw":
        if "error" in result:
            print(f"{result['xref']}: {result['error']}")
        else:
            print(f"lines {result['first_line']}-{result['last_line']}")
            print("\n".join(result["lines"]))
    elif args.cmd == "diff":
        print_diff(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
