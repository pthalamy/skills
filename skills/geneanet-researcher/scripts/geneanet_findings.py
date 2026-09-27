#!/usr/bin/env python3
"""Build Geneanet URLs, check them against robots.txt, and turn Geneanet
findings into a validated file, a Markdown report and research-log entries.

Standard library only (Python 3.9+). The script never touches the network:
pages are read with the agent's URL-fetch tool, and this script prepares
the URLs and processes what was recorded.

Subcommands::

    url search --nom NOM [--prenom P] [--place L] [--from Y] [--to Y]
               [--variants] [--size 50] [--page N]
    url person --tree OWNER --nom NOM --prenom P [--oc N]
    url names  --tree OWNER --nom NOM          surname index of one tree (m=N)
    url releve --project ID [--entry N]        relevé collaboratif entry or project
    check URL [URL ...]                        robots.txt verdict from the snapshot
    init FINDINGS.json --subject "…"           start a findings file
    validate FINDINGS.json [--json]            structure and consistency checks
    refs FINDINGS.json [--write]               pull cote, view, act number, archive,
                                               register and URL out of source_verbatim
    report FINDINGS.json [--out REPORT.md]     Markdown report
    log FINDINGS.json LOG.json [--question Q1] append to a genealogy-research-planner log

The findings format is documented in assets/findings-example.json.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urlsplit

WWW = "https://www.geneanet.org"
GW = "https://gw.geneanet.org"
SIZES = {10, 20, 30, 40, 50, 100}

# Facts in the order a life runs; the report sorts by it.
FACT_ORDER = ["name", "birth", "baptism", "parents", "sibling", "occupation", "residence", "census", "military",
              "marriage", "spouse", "child", "divorce", "death", "burial", "other"]
FACTS = set(FACT_ORDER)
ORIGIN_KINDS = {"tree", "releve", "cercle", "register", "cemetery", "other"}
STATUSES = {"record", "repository", "derivative", "unsourced", "not-visible", "snippet-only"}
LOCATIONS = {"event", "sources-section", "notes", "record-fields", "project-page", "search-snippet", "other"}
SEARCH_RESULTS = {"found", "negative", "partial", "blocked"}
DATED_FACTS = {"birth", "baptism", "marriage", "divorce", "death", "burial"}
NO_DATE = "(no normalised date)"

# ------------------------------------------------------------- robots --

ROBOTS_SNAPSHOT = "2026-09-27"
ROBOTS = {
    "gw.geneanet.org": [
        ("disallow", "/pdf/"), ("disallow", "/treeprint/"),
        ("disallow", "/*m="), ("disallow", "/*m=NG"), ("allow", "/*m=N"), ("allow", "/*m=P"),
        ("disallow", "/*color="), ("disallow", "/*carto="), ("disallow", "/*&s1="), ("disallow", "/*&s2="),
        ("disallow", "/*&s3="), ("disallow", "/*ei="), ("disallow", "/*&dag="), ("disallow", "/*templ="),
        ("disallow", "/*type=graph"), ("disallow", "/*type=links"), ("disallow", "/*type=carto"),
        ("disallow", "/*type=stats"),
    ],
    "www.geneanet.org": [("allow", "/mon_compte/file/")] + [("disallow", p) for p in (
        "/alert/", "/annuaire/fonds/", "/bibliotheque-genealogie/api/", "/boutique/index.php?controller=cart",
        "/archives/ouvrages/", "/fonds/redirect/", "/fonds/individus/niveaux/", "/beta/access", "/cercles/",
        "/compare/", "/individus/compare/", "/indexation?share_hash=", "/mon_compte/", "/messagerie/",
        "/moderation/", "/ml/", "/search/preferences/", "/premium/payment/", "/subscribe/", "/sys/sources/",
        "/variantes/noms/", "/community/contributions/", "/archives/livres/", "/premium/confirm/",
        "/cimetieres/upload/", "/cemetery/upload/", "/blog/cms/", "/genealogyblog/cms/",
    )],
}


def _rule_regex(pattern: str) -> re.Pattern:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    return re.compile("^" + "".join(".*" if c == "*" else re.escape(c) for c in body) + ("$" if anchored else ""))


def robots_verdict(url: str) -> tuple[str, Optional[str], str]:
    """Return (verdict, matching rule, note); verdict is allowed, disallowed or unknown."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    note = ""
    if host == "geneanet.org" or (host.endswith(".geneanet.org") and host not in ROBOTS):
        rules, note = ROBOTS["www.geneanet.org"], "rules of www.geneanet.org assumed"
    else:
        rules = ROBOTS.get(host)
    if rules is None:
        return "unknown", None, "no snapshot for this host"
    target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    best: Optional[tuple[str, str]] = None
    for kind, pat in rules:
        if _rule_regex(pat).match(target):
            if best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and kind == "allow"):
                best = (kind, pat)
    if best is None or best[0] == "allow":
        return "allowed", (f"Allow: {best[1]}" if best else None), note
    return "disallowed", f"Disallow: {best[1]}", note


# ---------------------------------------------------------------- urls --

def gw_key(text: str) -> str:
    """GeneWeb key: lowercase, no accents, runs of other characters as '+'."""
    t = text.strip().lower()
    for a, b in (("œ", "oe"), ("æ", "ae"), ("ß", "ss")):
        t = t.replace(a, b)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "+", t).strip("+")


def search_url(nom: str, prenom: str = "", place: str = "", year_from: Optional[int] = None,
               year_to: Optional[int] = None, variants: bool = False, size: int = 50, page: int = 1) -> str:
    if size not in SIZES:
        raise ValueError(f"size must be one of {sorted(SIZES)}")
    params = [("go", "1"), ("nom", nom.strip()), ("prenom", prenom.strip())]
    if place.strip():
        params.append(("place__0__", place.strip()))
    if year_from or year_to:
        params += [("type_periode", "between"), ("from", str(year_from or "")), ("to", str(year_to or ""))]
    if variants:
        params.append(("with_variantes_nom", "1"))
    params.append(("size", str(size)))
    if page and page > 1:
        params.append(("page", str(page)))
    return f"{WWW}/fonds/individus/?{urlencode(params)}"


def _owner(tree: str) -> str:
    owner = tree.strip().strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", owner):
        raise ValueError(f"'{tree}' does not look like a Geneanet tree owner name")
    return owner.lower()


def person_url(tree: str, nom: str, prenom: str, oc: Optional[int] = None) -> str:
    url = f"{GW}/{_owner(tree)}?lang=fr&n={gw_key(nom)}"
    if oc:
        url += f"&oc={int(oc)}"
    return url + f"&p={gw_key(prenom)}"


def names_url(tree: str, nom: str) -> str:
    return f"{GW}/{_owner(tree)}?lang=fr&m=N&v={gw_key(nom)}"


def releve_url(project: int, entry: Optional[int] = None) -> str:
    return f"{WWW}/releves-collaboratifs/view/{int(project)}" + (f"/{int(entry)}" if entry is not None else "")


def owner_of(url: str) -> Optional[str]:
    parts = urlsplit(url or "")
    if (parts.hostname or "").lower() != "gw.geneanet.org":
        return None
    seg = parts.path.strip("/").split("/")[0]
    return seg.lower() or None


# ---------------------------------------------------------------- refs --

def fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip()


_DASH = r"[-–—]"
_LABEL = r"(?:naissance|bapt[eê]me|union|mariage|d[ée]c[eè]s|inhumation|s[ée]pulture|personne|famille)"
RE_LABELS = re.compile(r"(?:^|(?<=[\n;])|(?<=\s[-–]\s))\s*[-*•]?\s*(?P<l>" + _LABEL + r"(?:\s*(?:,|et)\s*" + _LABEL
                       + r")*)\s*:", re.I)
LABEL_FACTS = {"naissance": {"birth"}, "bapteme": {"baptism"}, "union": {"marriage", "divorce", "spouse"},
               "mariage": {"marriage", "divorce", "spouse"}, "deces": {"death"}, "inhumation": {"burial"},
               "sepulture": {"burial"}, "famille": {"marriage", "divorce", "spouse", "parents", "child", "sibling"}}
RE_COTE = re.compile(
    r"\bc[oô]tes?\b\s*(?:archives?\s*)?(?:[:=]\s*|n[°o]\s*)?"
    r"(?P<v>[A-Za-z0-9][A-Za-z0-9 _./\-]*?)"
    r"(?=\s*(?:" + _DASH + r"\s|[,;()]|$)|\s+(?:vues?|images?|folios?|f[°o]|p\.|pages?|actes?)\b)", re.I)
RE_BARE_COTE = re.compile(r"(?<![\w/])(?P<v>\d{1,2}\s?E\s?(?:DEPOT\s?)?\d+(?:/\w+)*|\d{0,2}\s?MIR?\s?\d+(?:/\d+)*"
                          r"|E\s?DEPOT\s?\d+(?:/\w+)*)(?![\w/])")
RE_VIEW = re.compile(r"\b(?:vues?|images?|img\.?)\s*(?:n[°o]\s*)?"
                     r"(?P<v>\d+(?:\s*(?:/|-|–|,|à|et)\s*\d+)*)", re.I)
RE_FOLIO = re.compile(r"\b(?:folios?|f[°o]|pages?|p\.)\s*(?P<v>\d+\s*(?:r[°o]?|v[°o]?)?)(?![\w/])", re.I)
RE_ACT = re.compile(r"\bactes?\s*(?:n[°o]\.?|num[ée]ro|no\.)\s*(?P<v>\d+)\b|\bactes?\s+(?P<w>\d+)\b", re.I)
RE_URL = re.compile(r"<?(https?://[^\s<>\"')]+)>?")
RE_ARCHIVE = re.compile(
    r"(?i:archives?\s+(?:d[ée]partementales|municipales|communales|nationales|dioc[ée]saines|r[ée]gionales))"
    r"(?:\s+(?i:de\s+la|de\s+l['’]|du|des|de|d['’])\s*[A-ZÀ-Ý][\w'’\-]*(?:[\s\-](?:et[\s\-])?[A-ZÀ-Ý][\w'’\-]*)*)?"
    r"|\bAD\s?(?:\d{2,3}|2A|2B)\b"
    r"|\bAD\s+(?:(?i:de\s+la|de\s+l['’]|du|des|de|d['’])\s*)?[A-ZÀ-Ý][\w'’\-]+(?:[\s\-][A-ZÀ-Ý][\w'’\-]+)*"
    r"|\b(?i:mairie|archives?)\s+(?:(?i:de\s+la|de\s+l['’]|du|des|de|d['’])\s*)?[A-ZÀ-Ý][\w'’\-]+"
    r"(?:[\s\-][A-ZÀ-Ý][\w'’\-]+)*")
RE_REGISTER = re.compile(r"\b(?i:registres?)\s+(?P<v>.+?)(?=\s+c[oô]tes?\b|\s+vues?\b|\s+images?\b|\s*" + _DASH
                         + r"\s|[,;]|$)")
ACT_TYPES = {"naissance": "birth", "bapteme": "baptism", "mariage": "marriage", "deces": "death",
             "sepulture": "burial", "inhumation": "burial", "divorce": "divorce"}
RE_ACT_TYPE = re.compile(r"\bactes?\s+(?:de\s+|d')?(naissance|bapteme|mariage|deces|sepulture|inhumation|divorce)\b"
                         r"(?!\s+(?:des|de\s+ses|de\s+leurs?)\s+(?:parents|pere|mere))")
COMPATIBLE = {"birth": {"birth", "baptism"}, "baptism": {"baptism", "birth"}, "marriage": {"marriage"},
              "divorce": {"divorce", "marriage"}, "death": {"death", "burial"}, "burial": {"burial", "death"}}


def segment_for(text: str, fact: Optional[str]) -> str:
    """The part of a labelled source block that belongs to the fact.

    GeneWeb 'Sources' blocks read 'Naissance: …', 'Union: …', 'Décès: …',
    'Personne: …', 'Famille: …'. Without labels, or for an unlabelled fact,
    the whole text is returned."""
    marks = list(RE_LABELS.finditer(text or ""))
    if not marks or not fact:
        return text or ""
    segs = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        labels = {re.sub(r"\s+", "", fold(x)) for x in re.split(r",|\bet\b", m.group("l"), flags=re.I)}
        segs.append((labels, text[m.end():end].strip(" \n;-–")))
    hits = [s for labels, s in segs if any(fact in LABEL_FACTS.get(l, set()) for l in labels)]
    if not hits:
        hits = [s for labels, s in segs if "personne" in labels]
    return "; ".join(hits) if hits else text


def extract_refs(text: str, fact: Optional[str] = None) -> dict:
    """Heuristic locators in a verbatim source line. Only non-empty fields are returned.

    A URL to another Geneanet tree is a derivative citation: it goes in
    'cites', never in 'url'."""
    text = segment_for(text or "", fact)
    out: dict = {}
    m = RE_ARCHIVE.search(text)
    if m:
        out["archive"] = m.group(0).strip()
    m = RE_REGISTER.search(text)
    if m:
        out["register"] = m.group("v").strip()
    m = RE_COTE.search(text) or RE_BARE_COTE.search(text)
    if m:
        out["cote"] = m.group("v").strip()
    views = [v.group("v").strip() for v in RE_VIEW.finditer(text)]
    if not views:
        views = [v.group(0).strip() for v in RE_FOLIO.finditer(text)]
    if views:
        out["view"] = "; ".join(dict.fromkeys(views))
    m = RE_ACT.search(text)
    if m:
        out["act"] = (m.group("v") or m.group("w")).strip()
    urls = list(dict.fromkeys(u.rstrip(".,;") for u in RE_URL.findall(text)))
    trees = [u for u in urls if (urlsplit(u).hostname or "").lower() == "gw.geneanet.org"]
    others = [u for u in urls if u not in trees]
    if trees:
        out["cites"] = "; ".join(trees)
    if others:
        deep = [u for u in others if urlsplit(u).path.strip("/") or urlsplit(u).query]
        out["url"] = "; ".join(deep or others[:1])
    types = list(dict.fromkeys(ACT_TYPES[t] for t in RE_ACT_TYPE.findall(fold(text))))
    if types:
        out["act_type"] = ", ".join(types)
    return out


# ------------------------------------------------------------ findings --

def load(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"ERROR: {path} not found")
    except json.JSONDecodeError as exc:
        sys.exit(f"ERROR: {path} is not valid JSON: {exc}")


def save(path: str, doc: dict) -> None:
    doc["updated"] = dt.date.today().isoformat()
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def has_locator(f: dict) -> bool:
    ref = f.get("record_ref") or {}
    if any(ref.get(k) for k in ("cote", "view", "act", "url", "register")):
        return True
    return bool(re.search(r"\d|https?://", f.get("source_verbatim") or ""))


def check(doc: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for key in ("subject", "persons", "findings"):
        if key not in doc:
            errors.append(f"missing top-level '{key}'")
    persons = doc.get("persons") or []
    searches = doc.get("searches") or []
    findings = doc.get("findings") or []
    ids: set = set()
    for kind, items in (("person", persons), ("search", searches), ("finding", findings)):
        for i, item in enumerate(items):
            iid = item.get("id")
            if not iid:
                errors.append(f"{kind} #{i + 1} has no id")
            elif iid in ids:
                errors.append(f"duplicate id {iid}")
            ids.add(iid)
    person_ids = {p.get("id") for p in persons}
    search_ids = {s.get("id") for s in searches}
    finding_ids = {f.get("id") for f in findings}
    for p in persons:
        if not p.get("name"):
            errors.append(f"{p.get('id')}: person has no name")
        if not p.get("identity"):
            warnings.append(f"{p.get('id')}: no identity criteria; a name alone does not identify a person")
    for s in searches:
        sid = s.get("id")
        if s.get("result") not in SEARCH_RESULTS:
            errors.append(f"{sid}: result must be one of {sorted(SEARCH_RESULTS)}")
        if not s.get("url") and not s.get("scope"):
            errors.append(f"{sid}: a search needs its url or scope")
        if s.get("result") == "negative" and not s.get("scope"):
            errors.append(f"{sid}: a negative result needs a scope (query, place, years, pages read)")
        if s.get("result") == "blocked" and not s.get("note"):
            warnings.append(f"{sid}: blocked search without a note saying why")
    for f in findings:
        fid = f.get("id")
        origin = f.get("origin") or {}
        status = f.get("source_status")
        verbatim = (f.get("source_verbatim") or "").strip()
        loc = f.get("source_location")
        if f.get("person") not in person_ids:
            errors.append(f"{fid}: unknown person {f.get('person')!r}")
        if f.get("fact") not in FACTS:
            errors.append(f"{fid}: fact must be one of {FACT_ORDER}")
        if not (f.get("as_shown") or "").strip():
            errors.append(f"{fid}: as_shown is empty; copy the fact as the page shows it")
        if origin.get("kind") not in ORIGIN_KINDS:
            errors.append(f"{fid}: origin.kind must be one of {sorted(ORIGIN_KINDS)}")
        url = origin.get("url") or ""
        if not url:
            errors.append(f"{fid}: origin.url is required")
        if status not in STATUSES:
            errors.append(f"{fid}: source_status must be one of {sorted(STATUSES)}")
        if loc is not None and loc not in LOCATIONS:
            errors.append(f"{fid}: source_location must be one of {sorted(LOCATIONS)}")
        if status in {"record", "repository", "derivative"} and not verbatim:
            errors.append(f"{fid}: status {status} needs source_verbatim, copied exactly")
        if status == "unsourced" and verbatim:
            errors.append(f"{fid}: status unsourced but source_verbatim is filled; choose the right status")
        if status == "not-visible" and not (f.get("remarks") or "").strip():
            warnings.append(f"{fid}: not-visible without remarks saying why (Premium, login, masked)")
        if status == "snippet-only" and loc != "search-snippet":
            warnings.append(f"{fid}: snippet-only finding should have source_location search-snippet")
        if loc == "search-snippet" and status not in {"snippet-only", "not-visible"}:
            warnings.append(f"{fid}: a search snippet shows no source; use snippet-only and read the page "
                            f"if it can be fetched")
        if origin.get("search") and origin["search"] not in search_ids:
            errors.append(f"{fid}: origin.search {origin['search']!r} is not a search id")
        if f.get("copy_of"):
            if f["copy_of"] == fid or f["copy_of"] not in finding_ids:
                errors.append(f"{fid}: copy_of {f['copy_of']!r} is not another finding")
        if not origin.get("accessed"):
            warnings.append(f"{fid}: origin.accessed (date the page was read) is missing")
        if f.get("fact") in DATED_FACTS and not f.get("date") and status != "not-visible":
            warnings.append(f"{fid}: dated fact without a normalised date; conflicts cannot be checked")
        if origin.get("kind") == "tree":
            url_owner = owner_of(url)
            if not origin.get("owner"):
                warnings.append(f"{fid}: tree finding without origin.owner")
            elif url_owner and url_owner != origin["owner"].lower():
                warnings.append(f"{fid}: origin.owner {origin['owner']!r} differs from the URL's tree {url_owner!r}")
            if status == "record" and not has_locator(f):
                warnings.append(f"{fid}: status record but no cote, view, act number, date or URL in the source")
        if origin.get("kind") == "releve" and url and "releves-collaboratifs" not in url:
            warnings.append(f"{fid}: releve finding whose URL is not a releves-collaboratifs page")
        if url:
            verdict, rule, _ = robots_verdict(url)
            if verdict == "disallowed" and loc != "search-snippet":
                warnings.append(f"{fid}: {url} is refused by robots.txt ({rule}); record it from the search "
                                f"snippet (snippet-only, search-snippet) instead of as a page read")
        fact = f.get("fact")
        if fact in COMPATIBLE and verbatim:
            named = {t.strip() for t in (extract_refs(verbatim, fact).get("act_type") or "").split(",") if t.strip()}
            if named and not named & COMPATIBLE[fact]:
                warnings.append(f"{fid}: the source of this {fact} names only {', '.join(sorted(named))} act(s); "
                                f"record it as written and flag it in remarks")
    return errors, warnings


def cmd_url(a) -> int:
    try:
        if a.kind == "search":
            print(search_url(a.nom, a.prenom or "", a.place or "", a.year_from, a.year_to, a.variants, a.size, a.page))
        elif a.kind == "person":
            if not (a.tree and a.nom and a.prenom):
                sys.exit("ERROR: url person needs --tree, --nom and --prenom")
            print(person_url(a.tree, a.nom, a.prenom, a.oc))
        elif a.kind == "names":
            if not (a.tree and a.nom):
                sys.exit("ERROR: url names needs --tree and --nom")
            print(names_url(a.tree, a.nom))
        else:
            if a.project is None:
                sys.exit("ERROR: url releve needs --project")
            print(releve_url(a.project, a.entry))
    except ValueError as exc:
        sys.exit(f"ERROR: {exc}")
    return 0


def cmd_check(a) -> int:
    worst = 0
    for url in a.urls:
        verdict, rule, note = robots_verdict(url)
        extra = "; ".join(x for x in (rule, note) if x)
        print(f"{verdict.upper():10} {url}" + (f"  ({extra})" if extra else ""))
        worst = max(worst, 1 if verdict == "disallowed" else 0)
    print(f"robots.txt snapshot of {ROBOTS_SNAPSHOT}; the fetch tool's own refusal is authoritative")
    return worst


def cmd_init(a) -> int:
    if Path(a.file).exists():
        sys.exit(f"ERROR: {a.file} already exists")
    today = dt.date.today().isoformat()
    save(a.file, {"subject": a.subject, "created": today, "persons": [], "searches": [], "findings": []})
    print(f"created {a.file}")
    return 0


def cmd_validate(a) -> int:
    errors, warnings = check(load(a.file))
    if a.json:
        print(json.dumps({"errors": errors, "warnings": warnings}, indent=2, ensure_ascii=False))
    else:
        for e in errors:
            print(f"ERROR {e}")
        for w in warnings:
            print(f"WARNING {w}")
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_refs(a) -> int:
    doc = load(a.file)
    changed = 0
    for f in doc.get("findings", []):
        if f.get("source_status") not in {"record", "repository", "derivative"} or not f.get("source_verbatim"):
            continue
        found = extract_refs(f["source_verbatim"], f.get("fact"))
        ref = f.setdefault("record_ref", {})
        added = {k: v for k, v in found.items() if not ref.get(k)}
        ref.update(added)
        if not ref:
            del f["record_ref"]
        if added:
            changed += 1
            print(f"{f.get('id')}: " + "; ".join(f"{k}={v}" for k, v in added.items()))
    if a.write and changed:
        save(a.file, doc)
        print(f"updated {changed} finding(s) in {a.file}; check each extracted value against the verbatim text")
    elif changed:
        print(f"{changed} finding(s) would change; rerun with --write to save")
    else:
        print("nothing to extract")
    return 0


# --------------------------------------------------------------- dates --

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12, "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
          "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
RE_SIMPLE_DATE = re.compile(r"(?:(\d{1,2})\s+)?(?:([a-z]+)\.?\s+)?(\d{3,4})")


def parse_date(text: str) -> Optional[tuple]:
    """(earliest year, latest year, month, day) from GEDCOM or French dates.

    '13 DEC 1863' and '13 décembre 1863' are exact; 'ABT 1863' (also CAL,
    EST, vers, ca) spans two years either side; 'BEF 1900', 'AFT 1850' and
    'BET 1850 AND 1860' are open or closed ranges. Anything else gives None."""
    t = fold(text).replace("1er", "1")
    m = re.fullmatch(r"(?:bet|entre)\s+(\d{3,4})\s+(?:and|et)\s+(\d{3,4})", t)
    if m:
        return int(m.group(1)), int(m.group(2)), None, None
    m = re.fullmatch(r"(bef|avant|aft|apres)\s+(.+)", t)
    if m:
        inner = parse_date(m.group(2))
        if not inner:
            return None
        return (None, inner[1], None, None) if m.group(1) in ("bef", "avant") else (inner[0], None, None, None)
    m = re.fullmatch(r"(?:abt|cal|est|vers|ca\.?|env\.?|environ)\s+(\d{3,4})", t)
    if m:
        y = int(m.group(1))
        return y - 2, y + 2, None, None
    m = RE_SIMPLE_DATE.fullmatch(t)
    if not m or (m.group(2) and m.group(2) not in MONTHS):
        return None
    y = int(m.group(3))
    return y, y, (MONTHS[m.group(2)] if m.group(2) else None), (int(m.group(1)) if m.group(1) else None)


def dates_compatible(a: tuple, b: tuple) -> bool:
    lo = max(x for x in (a[0], b[0], -10 ** 6) if x is not None)
    hi = min(x for x in (a[1], b[1], 10 ** 6) if x is not None)
    if lo > hi:
        return False
    exact = a[0] is not None and a[0] == a[1] and b[0] is not None and b[0] == b[1]
    if exact:
        return all(x is None or y is None or x == y for x, y in zip(a[2:], b[2:]))
    return True


# -------------------------------------------------------------- report --

def num(fid: str) -> tuple:
    m = re.search(r"\d+", str(fid or ""))
    return (re.sub(r"\d+", "", str(fid or "")), int(m.group(0)) if m else 0)


def name_key(text: str) -> str:
    """A name as shown, without dates, years, 'ca', crosses and punctuation."""
    t = fold(re.sub(r"\(.*?\)", " ", text or ""))
    t = re.sub(r"\b(ca|vers|env|environ|ne|nee|mort|morte|decede|decedee)\b|[†+*/]|\d+", " ", t)
    return re.sub(r"[^a-z]+", " ", t).strip()


def place_key(text: str) -> str:
    first = re.split(r"[,(]", text or "")[0]
    return re.sub(r"[^a-z]+", " ", fold(first)).strip()


def cell(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).replace("|", "\\|").strip()


def origin_label(f: dict) -> str:
    o = f.get("origin") or {}
    default = {"tree": f"Arbre de {o.get('owner') or '?'}", "releve": "Relevé collaboratif",
               "cercle": "Index d'association", "register": "Registre Geneanet", "cemetery": "Cimetière"}
    label = o.get("label") or default.get(o.get("kind"), o.get("kind") or "?")
    return f"[{cell(label)}]({o.get('url')})" if o.get("url") else cell(label)


def locator(f: dict) -> str:
    """What to open: the event (type, place, date) then everything the source gives."""
    ref = f.get("record_ref") or {}
    what = f.get("fact") or "?"
    named = {t.strip() for t in (ref.get("act_type") or "").split(",") if t.strip()}
    if named and what in COMPATIBLE and not named & COMPATIBLE[what]:
        what += f" (the source names a {', '.join(sorted(named))} act)"
    event = ", ".join(x for x in (what, f.get("place"), f.get("date")) if x)
    parts = [f"{k} {ref[k]}" if k in ("cote", "view", "act") else str(ref[k])
             for k in ("archive", "register", "cote", "view", "act", "url") if ref.get(k)]
    detail = "; ".join(parts) if parts else (f.get("source_verbatim") or "")
    return f"{event}: {detail}" if detail else event


def source_key(f: dict) -> str:
    ref = f.get("record_ref") or {}
    if ref.get("cote") or ref.get("url") or ref.get("act"):
        return fold(" ".join(str(ref.get(k) or "") for k in ("cote", "view", "act", "url")))
    return fold(f.get("source_verbatim") or "")


def quay(f: dict) -> int:
    kind, status = (f.get("origin") or {}).get("kind"), f.get("source_status")
    if status in {"not-visible", "snippet-only"}:
        return 0
    if kind in {"releve", "cercle", "register", "cemetery"}:
        return 1
    return 1 if status in {"record", "repository"} else 0


def locatable(f: dict) -> bool:
    """A repository-only citation still locates an act when the event's date and place are known."""
    p = parse_date(f.get("date") or "")
    return bool(f.get("place") and p and p[0] is not None and p[0] == p[1])


def event_key(f: dict) -> tuple:
    return f.get("person"), f.get("fact"), fold(f.get("date") or ""), place_key(f.get("place") or "")


def comparisons(pf: list[dict]) -> list[str]:
    out: list[str] = []
    for fact in FACT_ORDER:
        fs = [f for f in pf if f.get("fact") == fact and f.get("source_status") != "not-visible"]
        if fact == "spouse":
            fs = fs + [dict(f, as_shown=f["spouse"]) for f in pf if f.get("fact") == "marriage" and f.get("spouse")]
        if len(fs) < 2:
            continue
        if fact in DATED_FACTS:
            dated = [(f, parse_date(f.get("date") or "")) for f in fs]
            conflict = any(
                (pa and pb and not dates_compatible(pa, pb))
                or ((not pa or not pb) and fa.get("date") and fb.get("date") and fold(fa["date"]) != fold(fb["date"]))
                for i, (fa, pa) in enumerate(dated) for fb, pb in dated[i + 1:])
            places: dict = {}
            for f in fs:
                if f.get("place"):
                    places.setdefault(place_key(f["place"]), []).append(f)
            groups: dict = {}
            for f in fs:
                groups.setdefault(fold(f.get("date") or "") or NO_DATE, []).append(f)
            label = "Conflict" if conflict or len(places) > 1 else "Agreement"
            rows = []
            for _, gs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
                rows.append((gs[0].get("date") or NO_DATE, gs))
            if len(places) > 1:
                rows.append(("places: " + "; ".join(f"{gs[0]['place']} ({', '.join(g['id'] for g in gs)})"
                                                    for gs in places.values()), []))
        else:
            groups = {}
            for f in fs:
                groups.setdefault(name_key(f.get("as_shown")), []).append(f)
            label = "Differing values" if len(groups) > 1 else "Agreement"
            rows = [(gs[0].get("as_shown"), gs) for _, gs in sorted(groups.items(), key=lambda kv: -len(kv[1]))]
        if label == "Agreement" and all(g.get("source_status") == "unsourced" for _, gs in rows for g in gs):
            label = "Agreement, all unsourced"
        out.append(f"**{label} on {fact}:**")
        for shown, gs in rows:
            if not gs:
                out.append(f"- {cell(shown)}")
                continue
            cited = {source_key(g) for g in gs if not g.get("copy_of") and g.get("source_status") in {"record", "repository"}}
            copies = sum(1 for g in gs if g.get("copy_of"))
            out.append(f"- {cell(shown)}: {', '.join(g['id'] for g in sorted(gs, key=lambda g: num(g['id'])))}; "
                       f"{len(cited)} distinct source citation(s)" + (f", {copies} marked as copies" if copies else ""))
        out.append("")
    return out


def build_report(doc: dict) -> str:
    persons = doc.get("persons") or []
    findings = sorted(doc.get("findings") or [], key=lambda f: num(f.get("id")))
    searches = doc.get("searches") or []
    errors, warnings = check(doc)
    by_id = {f.get("id"): f for f in findings}
    counts = ", ".join(f"{sum(1 for f in findings if f.get('source_status') == s)} {s}" for s in
                       ("record", "repository", "derivative", "unsourced", "not-visible", "snippet-only"))
    out = [f"# Geneanet findings: {doc.get('subject', '')}", "",
           f"Updated {doc.get('updated') or doc.get('created') or ''}. {len(persons)} person(s), "
           f"{len(searches)} search(es), {len(findings)} finding(s): {counts}.", ""]
    if errors:
        out += ["> The findings file has validation errors; fix them before relying on this report.", ""]
    for p in persons:
        pf = [f for f in findings if f.get("person") == p.get("id")]
        out.append(f"## {p.get('id')}: {p.get('name')}")
        if p.get("identity"):
            out.append(f"Identity criteria: {p['identity']}" + (f" (tree record `{p['xref']}`)" if p.get("xref") else ""))
        out.append("")
        if not pf:
            out += ["No findings.", ""]
            continue
        out += ["| # | Fact | As shown | Where | Source (verbatim) | Status | QUAY |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        rank = {k: i for i, k in enumerate(FACT_ORDER)}
        ordered = sorted(pf, key=lambda x: (rank.get(x.get("fact"), 99), num(x.get("id"))))
        for f in ordered:
            status = f.get("source_status") or "?"
            if f.get("copy_of"):
                status += f", copy of {f['copy_of']}"
            src = f.get("source_verbatim") or ("*no source stated*" if f.get("source_status") == "unsourced" else "")
            out.append(f"| {f.get('id')} | {f.get('fact')} | {cell(f.get('as_shown'))} | {origin_label(f)} | "
                       f"{cell(src)} | {cell(status)} | {quay(f)} |")
        out.append("")
        remarks = [f"- {f['id']}: {cell(f['remarks'])}" for f in sorted(pf, key=lambda x: num(x.get("id"))) if f.get("remarks")]
        if remarks:
            out += ["Remarks:", ""] + remarks + [""]
        out += comparisons(pf)
    out += ["## Records to open", "",
            "Cited precisely enough to open (status record), one line per act:", ""]
    seen: set = set()
    events: set = set()
    rows = []
    for f in findings:
        if f.get("source_status") != "record" or f.get("copy_of"):
            continue
        key = (f.get("person"), f.get("fact"), fold(f.get("date") or ""), source_key(f))
        events.add(event_key(f))
        if key in seen:
            continue
        seen.add(key)
        rows.append(f"- {f.get('person')} {cell(locator(f))} (from {f.get('id')}, {origin_label(f)})")
    out += (rows or ["- none"]) + [""]
    rows = []
    for f in findings:
        if f.get("source_status") == "repository" and not f.get("copy_of") and locatable(f):
            if event_key(f) not in events:
                events.add(event_key(f))
                rows.append(f"- {f.get('person')} {cell(locator(f))} (from {f.get('id')}, {origin_label(f)})")
    if rows:
        out += ["Archive named, act to find by its date and place (status repository):", ""] + rows + [""]
    out += ["## Unsourced facts", ""]
    rows = [f"- {f.get('id')} {f.get('person')} {f.get('fact')}: {cell(f.get('as_shown'))} ({origin_label(f)})"
            for f in findings if f.get("source_status") == "unsourced"]
    out += (rows or ["- none"]) + [""]
    out += ["## Repetition and copies", "",
            "Trees repeat one another; agreement between unsourced trees is not corroboration.", ""]
    rows = []
    for f in findings:
        if f.get("copy_of") and f["copy_of"] in by_id:
            rows.append(f"- {f['id']} is marked as a copy of {f['copy_of']}")
        cites = (f.get("record_ref") or {}).get("cites")
        if cites:
            rows.append(f"- {f['id']} cites another tree as its source: {cites}")
    texts: dict = {}
    for f in findings:
        if f.get("source_verbatim") and f.get("source_status") in {"record", "repository", "derivative"}:
            texts.setdefault((f.get("person"), f.get("fact"), fold(f["source_verbatim"])), []).append(f)
    for (person, fact, _), fs in texts.items():
        owners = {(g.get("origin") or {}).get("owner") or (g.get("origin") or {}).get("url") for g in fs}
        if len(owners) > 1:
            rows.append(f"- {person} {fact}: the same source text in {len(owners)} trees "
                        f"({', '.join(g['id'] for g in fs)}); probably copied")
    bare: dict = {}
    for f in findings:
        if f.get("source_status") == "unsourced" and f.get("fact") in DATED_FACTS | {"parents", "spouse"}:
            key = fold(f.get("date") or "") if f.get("fact") in DATED_FACTS else name_key(f.get("as_shown"))
            bare.setdefault((f.get("person"), f.get("fact"), key), []).append(f)
    for (person, fact, _), fs in bare.items():
        owners = {(g.get("origin") or {}).get("owner") or (g.get("origin") or {}).get("url") for g in fs}
        if len(owners) > 1:
            rows.append(f"- {person} {fact}: {cell(fs[0].get('as_shown'))} given by {len(owners)} trees without "
                        f"a source ({', '.join(g['id'] for g in fs)})")
    out += (rows or ["- none detected"]) + [""]
    flagged = [w for w in warnings if "names only" in w]
    out += ["## Inconsistencies inside the sources", ""]
    out += ([f"- {w}" for w in flagged] or ["- none detected"]) + [""]
    rows = [f"- {f.get('id')} {f.get('person')} {f.get('fact')}: {cell(f.get('as_shown'))} ({origin_label(f)})"
            + (f"; {cell(f['remarks'])}" if f.get("remarks") else "")
            for f in findings if f.get("source_status") == "snippet-only"]
    if rows:
        out += ["## Seen only in search results", "", "The page behind these was not read or cannot be fetched.", ""]
        out += rows + [""]
    out += ["## Not readable", ""]
    rows = [f"- {f.get('id')} {f.get('person')} {f.get('fact')}: {cell(f.get('remarks'))} ({origin_label(f)})"
            for f in findings if f.get("source_status") == "not-visible"]
    rows += [f"- {s.get('id')}: {cell(s.get('scope') or s.get('url'))}: {cell(s.get('note'))}"
             for s in searches if s.get("result") == "blocked"]
    out += (rows or ["- none"]) + [""]
    if searches:
        out += ["## Searches", "", "| # | Date | Scope | Keys | Result | Hits | Note |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for s in searches:
            scope = f"[{cell(s.get('scope') or 'query')}]({s['url']})" if s.get("url") else cell(s.get("scope"))
            out.append(f"| {s.get('id')} | {s.get('date', '')} | {scope} | {cell(s.get('keys'))} | {s.get('result')} | "
                       f"{s.get('hits', '')} | {cell(s.get('note'))} |")
        out.append("")
    return "\n".join(out)


def cmd_report(a) -> int:
    text = build_report(load(a.file))
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)
    return 0


# ----------------------------------------------------------------- log --

def _next_id(items: list, prefix: str) -> str:
    nums = [int(i["id"][len(prefix):]) for i in items
            if str(i.get("id", "")).startswith(prefix) and str(i["id"])[len(prefix):].isdigit()]
    return f"{prefix}{(max(nums) + 1) if nums else 1}"


def cmd_log(a) -> int:
    doc = load(a.file)
    errors, _ = check(doc)
    if errors:
        sys.exit(f"ERROR: {a.file} has {len(errors)} validation error(s); run validate first")
    path = Path(a.log)
    today = dt.date.today().isoformat()
    if path.exists():
        log = load(a.log)
    else:
        log = {"title": "Research log", "created": today, "questions": [], "searches": []}
    if a.question and not any(q.get("id") == a.question for q in log.get("questions", [])):
        sys.exit(f"ERROR: no question {a.question} in {a.log}; add it with research_log.py first")
    done = {s.get("origin") for s in log["searches"] if s.get("origin")}
    tag = Path(a.file).name
    added = 0
    for s in doc.get("searches", []):
        origin = f"geneanet:{tag}#{s['id']}"
        if origin in done:
            continue
        n = [f for f in doc.get("findings", []) if (f.get("origin") or {}).get("search") == s["id"]]
        cited = sum(1 for f in n if f.get("source_status") == "record")
        log["searches"].append({
            "id": _next_id(log["searches"], "S"), "question": a.question, "date": s.get("date") or today,
            "record": "Geneanet: trees, relevés, indexes", "repository": "Geneanet",
            "scope": s.get("scope") or s.get("url"), "keys": s.get("keys"), "result": s["result"],
            "citation": (f"{len(n)} finding(s), {cited} citing a record" if n else None),
            "proves": None, "note": " ".join(x for x in (s.get("url"), s.get("note")) if x) or None, "origin": origin})
        added += 1
    seen: set = set()
    events: set = set()
    ordered = sorted(doc.get("findings", []), key=lambda f: (f.get("source_status") != "record", num(f.get("id"))))
    for f in ordered:
        status = f.get("source_status")
        if f.get("copy_of") or not (status == "record" or (status == "repository" and locatable(f))):
            continue
        if status == "record":
            key = (f.get("person"), f.get("fact"), fold(f.get("date") or ""), source_key(f))
            events.add(event_key(f))
        else:
            key = event_key(f)
            if key in events:
                continue
            events.add(key)
        origin = f"geneanet:{tag}#{f['id']}"
        if key in seen or origin in done:
            continue
        seen.add(key)
        ref = f.get("record_ref") or {}
        log["searches"].append({
            "id": _next_id(log["searches"], "S"), "question": a.question, "date": today,
            "record": f"{f.get('fact')} act " + ("cited" if status == "record" else "located")
                      + " on Geneanet",
            "repository": ref.get("archive") or "?", "scope": locator(f), "keys": None, "result": "pending",
            "citation": None, "proves": f"{f.get('fact')} of {f.get('person')} as shown: {f.get('as_shown')}",
            "note": f"lead from {(f.get('origin') or {}).get('url')}; source as written: {f.get('source_verbatim')}",
            "origin": origin})
        added += 1
    log["updated"] = today
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"appended {added} search(es) to {a.log}")
    return 0


# ---------------------------------------------------------------- main --

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("url", help="build a Geneanet URL")
    p.add_argument("kind", choices=["search", "person", "names", "releve"])
    p.add_argument("--nom", default=""); p.add_argument("--prenom"); p.add_argument("--place")
    p.add_argument("--from", dest="year_from", type=int); p.add_argument("--to", dest="year_to", type=int)
    p.add_argument("--variants", action="store_true"); p.add_argument("--size", type=int, default=50)
    p.add_argument("--page", type=int, default=1); p.add_argument("--tree"); p.add_argument("--oc", type=int)
    p.add_argument("--project", type=int); p.add_argument("--entry", type=int); p.set_defaults(fn=cmd_url)
    p = sub.add_parser("check", help="robots.txt verdict"); p.add_argument("urls", nargs="+"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("init"); p.add_argument("file"); p.add_argument("--subject", required=True); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("validate"); p.add_argument("file"); p.add_argument("--json", action="store_true"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("refs"); p.add_argument("file"); p.add_argument("--write", action="store_true"); p.set_defaults(fn=cmd_refs)
    p = sub.add_parser("report"); p.add_argument("file"); p.add_argument("--out"); p.set_defaults(fn=cmd_report)
    p = sub.add_parser("log"); p.add_argument("file"); p.add_argument("log"); p.add_argument("--question"); p.set_defaults(fn=cmd_log)
    a = ap.parse_args(argv)
    if a.cmd == "url" and a.kind == "search" and not a.nom:
        ap.error("url search needs --nom")
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
