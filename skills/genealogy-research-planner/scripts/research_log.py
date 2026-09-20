#!/usr/bin/env python3
"""Keep a genealogical research log and find the gaps in a GEDCOM file.

Standard library only (Python 3.9+). The log is a JSON file of questions
and searches. Negative results are first-class: a search that found
nothing is stored with its exact scope so it is never repeated blindly.

Subcommands::

    init LOG.json [--title T]
    question LOG.json add "Find the parents of Jean Dupont…" [--xref @I12@] [--id Q1]
    question LOG.json status Q1 open|probable|proven|abandoned [--note "…"]
    add LOG.json --question Q1 --record "état civil, mariages" --repository "AD Rhône" \
        --scope "Lyon 1815-1820, tables décennales + actes" --keys "Dupont Dupond" \
        --result found|negative|partial|pending|blocked [--citation "…"] [--proves "…"] [--note "…"]
    done LOG.json S3 found|negative|partial [--citation "…"] [--note "…"]   (close a pending search)
    list LOG.json [--question Q1] [--result negative]
    next LOG.json                       pending/blocked searches and open questions without a plan
    report LOG.json [--out report.md]   Markdown report
    gaps FILE.ged [--xref @I12@] [--json] [--min-year 1500]
                                        people with missing or unsourced vital facts, as questions

Add --json to list/next for machine-readable output.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Optional

RESULTS = {"found", "negative", "partial", "pending", "blocked"}
STATUSES = {"open", "probable", "proven", "abandoned"}


# ------------------------------------------------------------------ log --

def load(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"ERROR: {path} not found; run 'init' first")
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: {path} is not valid JSON: {exc}")


def save(path: str, log: dict) -> None:
    log["updated"] = dt.date.today().isoformat()
    Path(path).write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def next_id(items: list[dict], prefix: str) -> str:
    nums = [int(i["id"][len(prefix):]) for i in items if i["id"].startswith(prefix) and i["id"][len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1) if nums else 1}"


def cmd_init(a) -> int:
    if Path(a.log).exists():
        sys.exit(f"ERROR: {a.log} already exists")
    save(a.log, {"title": a.title or "Research log", "created": dt.date.today().isoformat(), "questions": [], "searches": []})
    print(f"created {a.log}")
    return 0


def cmd_question(a) -> int:
    log = load(a.log)
    if a.action == "add":
        qid = a.id or next_id(log["questions"], "Q")
        if any(q["id"] == qid for q in log["questions"]):
            sys.exit(f"ERROR: question {qid} exists")
        log["questions"].append({"id": qid, "text": a.text, "xref": a.xref, "status": "open",
                                 "created": dt.date.today().isoformat(), "notes": []})
        save(a.log, log)
        print(f"{qid}: {a.text}")
    else:
        q = next((q for q in log["questions"] if q["id"] == a.text), None)
        if q is None:
            sys.exit(f"ERROR: no question {a.text}")
        if a.status not in STATUSES:
            sys.exit(f"ERROR: status must be one of {sorted(STATUSES)}")
        q["status"] = a.status
        if a.note:
            q["notes"].append({"date": dt.date.today().isoformat(), "text": a.note})
        save(a.log, log)
        print(f"{q['id']} → {a.status}")
    return 0


def cmd_add(a) -> int:
    log = load(a.log)
    if a.question and not any(q["id"] == a.question for q in log["questions"]):
        sys.exit(f"ERROR: no question {a.question}; add it first")
    if a.result not in RESULTS:
        sys.exit(f"ERROR: result must be one of {sorted(RESULTS)}")
    if a.result == "negative" and not a.scope:
        sys.exit("ERROR: a negative result needs --scope (place, years, register/images covered)")
    sid = next_id(log["searches"], "S")
    log["searches"].append({"id": sid, "question": a.question, "date": a.date or dt.date.today().isoformat(),
                            "record": a.record, "repository": a.repository, "scope": a.scope, "keys": a.keys,
                            "result": a.result, "citation": a.citation, "proves": a.proves, "note": a.note})
    save(a.log, log)
    print(f"{sid} [{a.result}] {a.record} @ {a.repository}: {a.scope}")
    return 0


def cmd_done(a) -> int:
    log = load(a.log)
    s = next((s for s in log["searches"] if s["id"] == a.search), None)
    if s is None:
        sys.exit(f"ERROR: no search {a.search}")
    if a.result not in {"found", "negative", "partial"}:
        sys.exit("ERROR: result must be found, negative or partial")
    s["result"] = a.result
    s["completed"] = dt.date.today().isoformat()
    if a.citation:
        s["citation"] = a.citation
    if a.note:
        s["note"] = (s.get("note") or "") + ("\n" if s.get("note") else "") + a.note
    save(a.log, log)
    print(f"{s['id']} → {a.result}")
    return 0


def cmd_list(a) -> int:
    log = load(a.log)
    rows = [s for s in log["searches"] if (not a.question or s["question"] == a.question) and (not a.result or s["result"] == a.result)]
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    for s in rows:
        print(f"{s['id']} {s['date']} [{s['result']:8}] {s.get('question') or '-':4} {s['record']} @ {s['repository']} | {s['scope'] or ''}"
              + (f" | {s['citation']}" if s.get("citation") else ""))
    if not rows:
        print("no searches")
    return 0


def cmd_next(a) -> int:
    log = load(a.log)
    pending = [s for s in log["searches"] if s["result"] in {"pending", "blocked"}]
    planned = {s["question"] for s in log["searches"]}
    unplanned = [q for q in log["questions"] if q["status"] == "open" and q["id"] not in planned]
    if a.json:
        print(json.dumps({"pending": pending, "open_without_plan": unplanned}, indent=2, ensure_ascii=False))
        return 0
    for s in pending:
        print(f"{s['id']} [{s['result']}] {s.get('question') or '-'}: {s['record']} @ {s['repository']} | {s['scope'] or ''}" + (f" ({s['note']})" if s.get("note") else ""))
    for q in unplanned:
        print(f"{q['id']} open, no search planned: {q['text']}")
    if not pending and not unplanned:
        print("nothing pending")
    return 0


def cmd_report(a) -> int:
    log = load(a.log)
    out = [f"# {log.get('title', 'Research log')}", "", f"Updated {log.get('updated', '')}. "
           f"{len(log['questions'])} questions, {len(log['searches'])} searches "
           f"({sum(1 for s in log['searches'] if s['result'] == 'negative')} negative).", ""]
    for q in log["questions"]:
        out.append(f"## {q['id']} ({q['status']}): {q['text']}")
        if q.get("xref"):
            out.append(f"Tree record: `{q['xref']}`")
        out.append("")
        searches = [s for s in log["searches"] if s["question"] == q["id"]]
        if searches:
            out.append("| Search | Date | Record | Repository | Scope | Keys | Result | Citation / note |")
            out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for s in searches:
                note = " ".join(x for x in (s.get("citation"), s.get("proves"), s.get("note")) if x)
                out.append(f"| {s['id']} | {s['date']} | {s['record']} | {s['repository']} | {s['scope'] or ''} | {s.get('keys') or ''} | {s['result']} | {note.replace('|', '/')} |")
            out.append("")
        for n in q.get("notes", []):
            out.append(f"- {n['date']}: {n['text']}")
        if q.get("notes"):
            out.append("")
    orphans = [s for s in log["searches"] if not s.get("question")]
    if orphans:
        out.append("## Searches not tied to a question")
        for s in orphans:
            out.append(f"- {s['id']} {s['date']} [{s['result']}] {s['record']} @ {s['repository']}: {s['scope'] or ''}")
        out.append("")
    pending = [s for s in log["searches"] if s["result"] in {"pending", "blocked"}]
    out.append("## Next actions")
    for s in pending:
        out.append(f"- {s['id']} ({s['result']}): {s['record']} @ {s['repository']}, {s['scope'] or ''}")
    for q in log["questions"]:
        if q["status"] == "open" and not any(s["question"] == q["id"] for s in log["searches"]):
            out.append(f"- Plan searches for {q['id']}: {q['text']}")
    if len(out) and out[-1] == "## Next actions":
        out.append("- none")
    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)
    return 0


# ----------------------------------------------------------------- gaps --

LINE = re.compile(r"^(\d+) (?:(@[^@ ]+@) )?([A-Za-z0-9_]+)(?: (.*))?$")


def read_gedcom(path: str) -> tuple[dict, dict]:
    """Minimal parser: returns (indis, fams) as dicts of xref -> record tree (nested dicts of lists)."""
    data = Path(path).read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    records: dict[str, dict] = {}
    stack: list[dict] = []
    for raw in text.splitlines():
        m = LINE.match(raw.rstrip("\r"))
        if not m:
            continue
        level, xref, tag, value = int(m.group(1)), m.group(2), m.group(3), m.group(4) or ""
        node = {"tag": tag, "value": value, "children": []}
        if level == 0:
            if xref:
                records[xref] = node
            stack = [node]
            continue
        while len(stack) > level:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
            stack.append(node)
    indis = {x: r for x, r in records.items() if r["tag"] == "INDI"}
    fams = {x: r for x, r in records.items() if r["tag"] == "FAM"}
    return indis, fams


def child(node: dict, tag: str) -> Optional[dict]:
    return next((c for c in node["children"] if c["tag"] == tag), None)


def children(node: dict, tag: str) -> list[dict]:
    return [c for c in node["children"] if c["tag"] == tag]


def name_of(indi: dict) -> str:
    n = child(indi, "NAME")
    return n["value"].replace("/", "").strip() if n else "(no name)"


def year_of(date_value: str) -> Optional[int]:
    m = re.search(r"\b(\d{3,4})\b", date_value or "")
    return int(m.group(1)) if m else None


def event_state(rec: dict, tags: tuple[str, ...]) -> tuple[str, Optional[str], bool]:
    """Return (state, date, sourced): state in missing / undated / dated."""
    for t in tags:
        ev = child(rec, t)
        if ev:
            d = child(ev, "DATE")
            sourced = bool(children(ev, "SOUR")) or bool(children(rec, "SOUR"))
            return ("dated" if d and d["value"] else "undated"), (d["value"] if d else None), sourced
    return "missing", None, False


def cmd_gaps(a) -> int:
    indis, fams = read_gedcom(a.file)
    targets = [a.xref] if a.xref else list(indis)
    questions = []
    for x in targets:
        indi = indis.get(x)
        if indi is None:
            sys.exit(f"ERROR: no individual {x}")
        name = name_of(indi)
        b_state, b_date, b_src = event_state(indi, ("BIRT", "CHR", "BAPM"))
        d_state, d_date, d_src = event_state(indi, ("DEAT", "BURI"))
        by = year_of(b_date or "")
        if by and by < a.min_year:
            continue
        if by and dt.date.today().year - by < 100 and d_state == "missing":
            continue  # possibly living: not a research target
        approx = bool(b_date and re.match(r"^(ABT|EST|CAL|BEF|AFT|BET)", b_date))
        items = []
        if b_state == "missing":
            items.append(("birth", "no birth or baptism event", "high"))
        elif b_state == "undated":
            items.append(("birth", "birth without a date", "high"))
        elif approx:
            items.append(("birth", f"birth only approximate ({b_date})", "medium"))
        elif not b_src:
            items.append(("birth", f"birth {b_date} has no source citation", "medium"))
        if d_state == "missing":
            items.append(("death", "no death or burial event", "medium"))
        elif not d_src and d_state == "dated":
            items.append(("death", f"death {d_date} has no source citation", "low"))
        famcs = children(indi, "FAMC")
        if not famcs:
            items.append(("parents", "no parents in the tree", "high"))
        else:
            fam = fams.get(famcs[0]["value"])
            if fam:
                if not child(fam, "HUSB"):
                    items.append(("parents", "father unknown", "high"))
                if not child(fam, "WIFE"):
                    items.append(("parents", "mother unknown", "high"))
                if not children(fam, "SOUR") and not children(famcs[0], "SOUR"):
                    items.append(("parents", "parent link has no source citation", "medium"))
        for fs in children(indi, "FAMS"):
            fam = fams.get(fs["value"])
            if fam is None:
                continue
            m_state, m_date, m_src = event_state(fam, ("MARR",))
            other = child(fam, "WIFE" if child(fam, "HUSB") and child(fam, "HUSB")["value"] == x else "HUSB")
            spouse = name_of(indis[other["value"]]) if other and other["value"] in indis else "unknown spouse"
            if m_state == "missing":
                items.append(("marriage", f"union with {spouse} has no marriage event", "high"))
            elif m_state == "undated":
                items.append(("marriage", f"marriage with {spouse} undated", "medium"))
            elif not m_src:
                items.append(("marriage", f"marriage with {spouse} ({m_date}) has no source citation", "medium"))
        for kind, what, prio in items:
            questions.append({"xref": x, "name": name, "born": b_date, "topic": kind, "gap": what, "priority": prio,
                              "question": f"Find the {kind} of {name} ({x}{', born ' + b_date if b_date else ''}): {what}."})
    order = {"high": 0, "medium": 1, "low": 2}
    questions.sort(key=lambda q: (order[q["priority"]], q["name"]))
    if a.json:
        print(json.dumps(questions, indent=2, ensure_ascii=False))
        return 0
    for q in questions:
        print(f"[{q['priority']:6}] {q['question']}")
    print(f"{len(questions)} gaps in {len(targets)} individual(s)")
    return 0


# ----------------------------------------------------------------- main --

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("log"); p.add_argument("--title"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("question"); p.add_argument("log"); p.add_argument("action", choices=["add", "status"])
    p.add_argument("text", help="question text (add) or question id (status)"); p.add_argument("status", nargs="?")
    p.add_argument("--xref"); p.add_argument("--id"); p.add_argument("--note"); p.set_defaults(fn=cmd_question)
    p = sub.add_parser("add"); p.add_argument("log"); p.add_argument("--question"); p.add_argument("--record", required=True)
    p.add_argument("--repository", required=True); p.add_argument("--scope"); p.add_argument("--keys")
    p.add_argument("--result", required=True); p.add_argument("--citation"); p.add_argument("--proves"); p.add_argument("--note")
    p.add_argument("--date"); p.set_defaults(fn=cmd_add)
    p = sub.add_parser("done"); p.add_argument("log"); p.add_argument("search"); p.add_argument("result")
    p.add_argument("--citation"); p.add_argument("--note"); p.set_defaults(fn=cmd_done)
    p = sub.add_parser("list"); p.add_argument("log"); p.add_argument("--question"); p.add_argument("--result"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("next"); p.add_argument("log"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_next)
    p = sub.add_parser("report"); p.add_argument("log"); p.add_argument("--out"); p.set_defaults(fn=cmd_report)
    p = sub.add_parser("gaps"); p.add_argument("file"); p.add_argument("--xref"); p.add_argument("--json", action="store_true")
    p.add_argument("--min-year", type=int, default=1500); p.set_defaults(fn=cmd_gaps)
    a = ap.parse_args(argv)
    if a.cmd == "question" and a.action == "status" and not a.status:
        ap.error("question status needs: question LOG Qn STATUS")
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
