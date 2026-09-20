#!/usr/bin/env python3
"""Validate a record transcription JSON and turn it into GEDCOM fragments.

Standard library only (Python 3.9+). The JSON follows
assets/transcription-schema.json. Subcommands::

    validate FILE.json            structural checks (required fields, enums,
                                  ids, dates); exit 1 on errors
    gedcom FILE.json [options]    GEDCOM 5.5.1 fragments: a SOUR record,
                                  one INDI per person, FAM records for the
                                  parent couple and the marriage, citations
                                  on every fact
        --source-xref @S3@            reuse an existing SOUR record
        --map p1=@I12@ [p2=@I14@ ...] bind persons to existing xrefs
        --indi-start 9001             first number for new @I…@ xrefs
        --fam-start 9001              first number for new @F…@ xrefs
        --no-text                     omit DATA.TEXT (the literal transcription)
    date "12 vendémiaire an IV"   Republican date in words → GEDCOM + Gregorian
    summary FILE.json             one-screen human summary

Xrefs the script invents are placeholders; whoever integrates the fragments
(the gedcom-maintainer skill) replaces them with the tree's real records.
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

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE.parent / "assets" / "transcription-schema.json"
MAX_LINE = 255

# ----------------------------------------------------------------- dates --

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
FR_MONTHS = ["vendemiaire", "brumaire", "frimaire", "nivose", "pluviose", "ventose", "germinal",
             "floreal", "prairial", "messidor", "thermidor", "fructidor", "complementaire"]
FR_ABBR = ["VEND", "BRUM", "FRIM", "NIVO", "PLUV", "VENT", "GERM", "FLOR", "PRAI", "MESS", "THER", "FRUC", "COMP"]
FR_EPOCH = dt.date(1792, 9, 22).toordinal()
FR_SEXTILE = {3, 7, 11, 15, 20}
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50}
UNITS = {"un": 1, "une": 1, "premier": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7,
         "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
         "seize": 16, "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
         "septante": 70, "octante": 80, "huitante": 80, "nonante": 90, "cent": 100, "cents": 100, "mil": 1000,
         "mille": 1000}


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def words_to_int(text: str) -> Optional[int]:
    """'vingt six', 'quatre vingt neuf', 'mil sept cent quatre vingt neuf' → int."""
    toks = [t for t in re.split(r"[\s\-]+", fold(text)) if t and t not in {"et", "e", "eme", "ieme", "iesme"}]
    if not toks:
        return None
    total = current = 0
    for t in toks:
        t = re.sub(r"(ieme|iesme|eme)$", "", t)
        if t.isdigit():
            current += int(t)
            continue
        if t not in UNITS:
            return None
        v = UNITS[t]
        if v == 100:
            current = (current or 1) * 100
        elif v == 1000:
            total += (current or 1) * 1000
            current = 0
        else:
            current += v
    return total + current


def roman_to_int(s: str) -> Optional[int]:
    s = s.upper()
    if not s or any(c not in ROMAN for c in s):
        return None
    total = 0
    for i, c in enumerate(s):
        v = ROMAN[c]
        if i + 1 < len(s) and ROMAN[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def french_to_gregorian(year: int, month: int, day: int) -> dt.date:
    days = (year - 1) * 365 + sum(1 for y in FR_SEXTILE if y < year) + (month - 1) * 30 + (day - 1)
    return dt.date.fromordinal(FR_EPOCH + days)


def parse_republican(text: str) -> Optional[tuple[int, int, int]]:
    """Parse '12 vendémiaire an IV', 'le treize vendemiaire an quatre', '3e jour complémentaire an 2'."""
    t = fold(text)
    t = re.sub(r"\b(le|du|de|la|l|republique|francaise|une|et|indivisible|jour|jours|au)\b", " ", t)
    t = re.sub(r"[',.]", " ", t)
    m = re.search(r"(.+?)\s*(" + "|".join(FR_MONTHS) + r"|sans[\s-]*culottides?)\s*(?:an\s*)?(.+)$", t)
    if not m:
        return None
    day_txt, month_txt, year_txt = m.group(1), m.group(2), m.group(3).strip()
    month = 13 if month_txt.startswith("sans") else FR_MONTHS.index(month_txt) + 1
    day = words_to_int(day_txt) if not re.fullmatch(r"\s*\d+\s*[a-z]*\s*", day_txt) else int(re.search(r"\d+", day_txt).group())
    year_txt = re.sub(r"\s+", " ", year_txt).strip()
    year = int(year_txt) if year_txt.isdigit() else (roman_to_int(year_txt.replace(" ", "")) or words_to_int(year_txt))
    if not day or not year or not 1 <= day <= 30 or not 1 <= year <= 14:
        return None
    return year, month, day


def republican_to_gedcom(year: int, month: int, day: int) -> str:
    return f"@#DFRENCH R@ {day} {FR_ABBR[month - 1]} {year}"


def iso_to_gedcom(iso: str) -> str:
    parts = iso.split("-")
    y = str(int(parts[0]))
    if len(parts) == 1:
        return y
    mon = MONTHS[int(parts[1]) - 1]
    if len(parts) == 2:
        return f"{mon} {y}"
    return f"{int(parts[2])} {mon} {y}"


def gedcom_date(d: Optional[dict]) -> Optional[str]:
    """Best GEDCOM date value for a schema date object."""
    if not d:
        return None
    q = d.get("qualifier") or ""
    if d.get("gedcom"):
        value = d["gedcom"]
    elif d.get("calendar") == "french_republican" and parse_republican(d.get("as_written", "")):
        value = republican_to_gedcom(*parse_republican(d["as_written"]))
    elif d.get("iso"):
        value = iso_to_gedcom(d["iso"])
    else:
        return None
    if q and not value.upper().startswith(q):
        value = f"{q} {value}"
    return value


def date_year(d: Optional[dict]) -> Optional[int]:
    if not d:
        return None
    if d.get("iso"):
        return int(d["iso"][:4])
    rep = parse_republican(d.get("as_written", "")) if d.get("calendar") == "french_republican" else None
    if rep:
        return french_to_gregorian(*rep).year
    m = re.search(r"\b(1[5-9]\d\d|20\d\d)\b", d.get("gedcom", "") or "")
    return int(m.group(1)) if m else None


# ------------------------------------------------------------ validation --

def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _resolve(schema: dict, node: dict) -> dict:
    if "$ref" in node:
        path = node["$ref"].split("/")[1:]
        target = schema
        for p in path:
            target = target[p]
        merged = dict(target)
        merged.update({k: v for k, v in node.items() if k != "$ref"})
        return merged
    return node


def check(schema: dict, node: dict, value, path: str, errors: list[str]) -> None:
    """Small JSON Schema subset: type, required, properties, additionalProperties, enum, pattern, items, min/max."""
    node = _resolve(schema, node)
    t = node.get("type")
    if t == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object"); return
        for r in node.get("required", []):
            if r not in value:
                errors.append(f"{path}: missing required '{r}'")
        props = node.get("properties", {})
        for k, v in value.items():
            if k in props:
                check(schema, props[k], v, f"{path}/{k}", errors)
            elif node.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected field '{k}'")
    elif t == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array"); return
        if "minItems" in node and len(value) < node["minItems"]:
            errors.append(f"{path}: needs at least {node['minItems']} item(s)")
        for i, item in enumerate(value):
            check(schema, node["items"], item, f"{path}[{i}]", errors)
    elif t == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string"); return
        if "enum" in node and value not in node["enum"]:
            errors.append(f"{path}: '{value}' not one of {node['enum']}")
        if "pattern" in node and not re.fullmatch(node["pattern"], value):
            errors.append(f"{path}: '{value}' does not match {node['pattern']}")
    elif t == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer"); return
        if "enum" in node and value not in node["enum"]:
            errors.append(f"{path}: {value} not one of {node['enum']}")
        if "minimum" in node and value < node["minimum"] or "maximum" in node and value > node["maximum"]:
            errors.append(f"{path}: {value} out of range")
    elif t == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number")


def semantic_checks(doc: dict, errors: list[str], warnings: list[str]) -> None:
    ids = [p["id"] for p in doc.get("persons", [])]
    if len(ids) != len(set(ids)):
        errors.append("persons: duplicate ids")
    roles = [p["role"] for p in doc.get("persons", [])]
    if "subject" not in roles:
        errors.append("persons: no person with role 'subject'")
    if doc.get("event", {}).get("type") == "marriage" and sum(1 for r in roles if r == "subject") != 2:
        errors.append("marriage: exactly two persons with role 'subject' expected (party 1 and 2)")
    if doc.get("event", {}).get("type") == "marriage":
        for p in doc["persons"]:
            if p["role"] == "subject" and p.get("party") not in (1, 2):
                errors.append(f"persons/{p['id']}: marriage subjects need 'party' 1 or 2")
    for p in doc.get("persons", []):
        rt = p.get("related_to")
        if rt and rt not in ids:
            errors.append(f"persons/{p['id']}: related_to '{rt}' is not a person id")
        if p["role"] in {"father", "mother", "godfather", "godmother", "spouse", "previous_spouse", "father_of_spouse", "mother_of_spouse"} and not rt:
            warnings.append(f"persons/{p['id']}: role '{p['role']}' without related_to; assumed relative to the subject")
        if not p.get("names", {}).get("surname_as_written") and not p.get("names", {}).get("given_as_written"):
            warnings.append(f"persons/{p['id']}: no name at all")
        if p.get("sex") is None and p["role"] in {"subject", "father", "mother", "godfather", "godmother"}:
            warnings.append(f"persons/{p['id']}: sex not set for role '{p['role']}'")
        age = p.get("age") or {}
        if age.get("years") and age.get("qualifier") is None:
            warnings.append(f"persons/{p['id']}: age without qualifier; assumed 'exact'")
    for m in doc.get("marginal_mentions", []):
        for pid in m.get("persons", []):
            if pid not in ids:
                errors.append(f"marginal_mentions: person '{pid}' is not a person id")
    for where, d in _iter_dates(doc):
        if d.get("calendar") == "french_republican" and not d.get("gedcom") and not parse_republican(d.get("as_written", "")):
            warnings.append(f"{where}: Republican date not parseable from as_written; set 'gedcom' explicitly")
        if not d.get("iso") and not d.get("gedcom") and not (d.get("calendar") == "french_republican" and parse_republican(d.get("as_written", ""))):
            warnings.append(f"{where}: date has only as_written; no GEDCOM date will be emitted")
        if d.get("iso"):
            try:
                parts = [int(x) for x in d["iso"].split("-")]
                if len(parts) == 3:
                    dt.date(*parts)
                elif len(parts) == 2 and not 1 <= parts[1] <= 12:
                    raise ValueError
            except ValueError:
                errors.append(f"{where}: iso date '{d['iso']}' is not a real date")
    act_year = date_year(doc.get("document", {}).get("act_date"))
    ev_year = date_year(doc.get("event", {}).get("date"))
    if act_year and ev_year and ev_year > act_year:
        errors.append("event date is after the act date")
    if doc.get("document", {}).get("source_type") == "derivative" and doc.get("document", {}).get("citation", {}).get("quay", 0) > 2:
        warnings.append("citation.quay 3 on a derivative source; the original act would be QUAY 3")
    if doc.get("transcription", {}).get("literal", "").count("[?]") > 5:
        warnings.append("more than five doubtful readings; consider asking for a better image")


DATE_KEYS = {"date", "act_date", "birth", "death", "baptism", "burial"}


def _iter_dates(doc: dict):
    """Yield (path, date_object) for every schema date in the document."""
    def walk(node, path, key):
        if isinstance(node, dict):
            is_date = "as_written" in node and "years" not in node and "months" not in node and (
                key in DATE_KEYS and "normalised" not in node and "detail" not in node
                or any(k in node for k in ("iso", "calendar", "gedcom", "qualifier")))
            if is_date and not (key in {"birth", "death"} and ("date" in node or "place" in node)):
                yield path, node
                return
            for k, v in node.items():
                yield from walk(v, f"{path}/{k}", k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]", key)
    yield from walk(doc, "", "")


def validate(doc: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    check(load_schema(), load_schema(), doc, "", errors)
    if not errors:
        semantic_checks(doc, errors, warnings)
    return errors, warnings


# ------------------------------------------------------------ GEDCOM out --

class Emitter:
    def __init__(self, no_text: bool = False) -> None:
        self.lines: list[str] = []
        self.no_text = no_text

    def line(self, level: int, tag: str, value: str = "", xref: str = "") -> None:
        head = f"{level} {xref + ' ' if xref else ''}{tag}"
        if not value:
            self.lines.append(head)
            return
        value = value.replace("\r", "")
        first, *rest = value.split("\n")
        self._emit_wrapped(level, head, first)
        for part in rest:
            self._emit_wrapped(level + 1, f"{level + 1} CONT", part)

    def _emit_wrapped(self, level: int, head: str, text: str) -> None:
        room = MAX_LINE - len(head) - 1
        chunk, text = text[:room], text[room:]
        # do not split right after a space: importers drop it
        while chunk.endswith(" ") and text:
            text = chunk[-1] + text
            chunk = chunk[:-1]
        self.lines.append(f"{head} {chunk}".rstrip() if chunk else head)
        while text:
            head2 = f"{level + 1} CONC"
            room = MAX_LINE - len(head2) - 1
            chunk, text = text[:room], text[room:]
            while chunk.endswith(" ") and text:
                text = chunk[-1] + text
                chunk = chunk[:-1]
            self.lines.append(f"{head2} {chunk}")


def quay_for(doc: dict) -> int:
    cit = doc["document"].get("citation", {})
    if "quay" in cit:
        return cit["quay"]
    return {"original": 3, "duplicate": 3, "derivative": 1, "authored": 0}.get(doc["document"].get("source_type", "original"), 2)


def place_value(p: Optional[dict]) -> Optional[str]:
    if not p:
        return None
    return p.get("normalised") or p.get("as_written")


def person_name(p: dict) -> tuple[str, str, str]:
    n = p.get("names", {})
    given = n.get("given_normalised") or n.get("given_as_written") or ""
    surn = n.get("surname_normalised") or n.get("surname_as_written") or ""
    return f"{given} /{surn}/".strip(), given, surn


def emit_citation(e: Emitter, level: int, doc: dict, sxref: str, with_text: bool, note: Optional[str] = None, secondary: bool = False) -> None:
    """Write a citation. secondary=True caps QUAY at 2: the act reports the fact second-hand (an age, a parent's death)."""
    cit = doc["document"]["citation"]
    e.line(level, "SOUR", sxref)
    e.line(level + 1, "PAGE", cit["page_string"])
    e.line(level + 1, "QUAY", str(min(quay_for(doc), 2) if secondary else quay_for(doc)))
    act = gedcom_date(doc["document"].get("act_date"))
    text = doc["transcription"].get("literal", "") if (with_text and not e.no_text) else ""
    if act or text:
        e.line(level + 1, "DATA")
        if act:
            e.line(level + 2, "DATE", act)
        if text:
            e.line(level + 2, "TEXT", text)
    if note:
        e.line(level + 1, "NOTE", note)


def age_birth_date(p: dict, act_year: Optional[int]) -> Optional[str]:
    age = p.get("age") or {}
    if not act_year or not age.get("years"):
        return None
    year = act_year - int(age["years"])
    q = age.get("qualifier", "exact")
    if q in {"majeur", "mineur", "unknown"}:
        return None
    return f"{'ABT' if q == 'about' else 'CAL'} {year}"


EVENT_TAG = {"birth": "BIRT", "baptism": "BAPM", "marriage": "MARR", "marriage_contract": "MARC", "banns": "MARB",
             "death": "DEAT", "burial": "BURI", "census": "CENS", "military_registration": "EVEN", "notarial_act": "EVEN", "other": "EVEN"}
RELA = {"godfather": "godfather", "godmother": "godmother", "witness": "witness", "declarant": "declarant",
        "informant": "informant", "midwife": "midwife", "officiant": "officiant", "employer": "employer", "other": "associate"}


def to_gedcom(doc: dict, source_xref: Optional[str], mapping: dict[str, str], indi_start: int, fam_start: int, no_text: bool) -> str:
    e = Emitter(no_text=no_text)
    d = doc["document"]
    ev = doc["event"]
    persons = {p["id"]: p for p in doc["persons"]}
    act_year = date_year(d.get("act_date"))
    act_date = gedcom_date(d.get("act_date"))

    # xrefs
    xref: dict[str, str] = {}
    n = indi_start
    for pid in persons:
        if pid in mapping:
            xref[pid] = mapping[pid]
        else:
            xref[pid] = f"@I{n}@"
            n += 1
    fam_n = fam_start
    sxref = source_xref or "@S9001@"

    subjects = [p for p in doc["persons"] if p["role"] == "subject"]
    subj_by_party = {p.get("party", 1): p for p in subjects}

    def subject_of(p: dict) -> dict:
        rt = p.get("related_to")
        return persons.get(rt) if rt and persons.get(rt) else subjects[0]

    # family records: parents of each subject; the marriage couple
    fams: list[dict] = []
    for s in subjects:
        father = next((p for p in doc["persons"] if p["role"] == "father" and subject_of(p) is s), None)
        mother = next((p for p in doc["persons"] if p["role"] == "mother" and subject_of(p) is s), None)
        if father or mother:
            fams.append({"xref": f"@F{fam_n}@", "husb": father, "wife": mother, "chil": [s], "kind": "parents"})
            fam_n += 1
    if ev["type"] in {"marriage", "marriage_contract", "banns"} and len(subj_by_party) == 2:
        fams.append({"xref": f"@F{fam_n}@", "husb": subj_by_party[1], "wife": subj_by_party[2], "chil": [], "kind": "union"})
        fam_n += 1
    for p in doc["persons"]:
        if p["role"] == "spouse" and ev["type"] not in {"marriage", "marriage_contract", "banns"}:
            s = subject_of(p)
            husb, wife = (s, p) if s.get("sex") != "F" else (p, s)
            fams.append({"xref": f"@F{fam_n}@", "husb": husb, "wife": wife, "chil": [], "kind": "spouse"})
            fam_n += 1
    spouse_parent_fams: dict[str, dict] = {}
    for p in doc["persons"]:
        if p["role"] in {"father_of_spouse", "mother_of_spouse"}:
            target = persons.get(p.get("related_to") or "")
            if target is None:
                continue
            fam = spouse_parent_fams.setdefault(target["id"], {"xref": f"@F{fam_n}@", "husb": None, "wife": None, "chil": [target], "kind": "parents"})
            if fam["husb"] is None and fam["wife"] is None:
                fam_n += 1
            fam["husb" if p["role"] == "father_of_spouse" else "wife"] = p
    fams.extend(spouse_parent_fams.values())

    def fams_as_spouse(p: dict) -> list[str]:
        return [f["xref"] for f in fams if (f["husb"] is p or f["wife"] is p)]

    def fams_as_child(p: dict) -> list[str]:
        return [f["xref"] for f in fams if p in f["chil"]]

    e.lines.append(f"# GEDCOM 5.5.1 fragments generated from a record transcription ({d['type']}, act {act_date or d['act_date'].get('as_written')})")
    e.lines.append("# Placeholder xrefs (@I9001@, @F9001@, @S9001@) must be replaced or merged into the target file.")

    # source record
    if not source_xref:
        e.line(0, "SOUR", xref=sxref)
        title = d["citation"].get("source_title") or d.get("register", {}).get("title") or f"{d['type']} record"
        e.line(1, "TITL", title)
        reg = d.get("register", {})
        if reg.get("repository"):
            e.line(1, "NOTE", f"Repository: {reg['repository']}" + (f"; reference {reg['reference']}" if reg.get("reference") else ""))
        if d.get("location_in_register", {}).get("url"):
            e.line(1, "NOTE", f"URL: {d['location_in_register']['url']}")

    # individuals
    main_tag = EVENT_TAG[ev["type"]]
    for p in doc["persons"]:
        if p["role"] == "officiant":
            continue
        ix = xref[p["id"]]
        name, given, surn = person_name(p)
        e.line(0, "INDI", xref=ix)
        e.line(1, "NAME", name)
        if given:
            e.line(2, "GIVN", given)
        if surn:
            e.line(2, "SURN", surn)
        nm = p.get("names", {})
        if nm.get("title"):
            e.line(2, "NPFX", nm["title"])
        if nm.get("dit"):
            e.line(1, "NAME", f"{given} /{nm['dit']}/")
            e.line(2, "TYPE", "aka")
        aw = f"{nm.get('given_as_written', '')} {nm.get('surname_as_written', '')}".strip()
        if aw and aw != f"{given} {surn}".strip():
            e.line(2, "NOTE", f"Written '{aw}' in the act")
        if nm.get("signature_spelling"):
            e.line(2, "NOTE", f"Signs '{nm['signature_spelling']}'")
        if p.get("sex"):
            e.line(1, "SEX", p["sex"])

        is_subject = p["role"] == "subject"
        if is_subject and ev["type"] not in {"marriage", "marriage_contract", "banns"}:
            if main_tag != "EVEN" or ev["type"] != "other":
                e.line(1, main_tag)
                if main_tag == "EVEN":
                    e.line(2, "TYPE", d.get("subtype") or ev["type"])
                evd = gedcom_date(ev.get("date")) or (act_date if ev["type"] in {"baptism", "burial", "census"} else None)
                if evd:
                    e.line(2, "DATE", evd)
                if place_value(ev.get("place")):
                    e.line(2, "PLAC", place_value(ev.get("place")))
                if ev.get("details"):
                    e.line(2, "NOTE", ev["details"])
                emit_citation(e, 2, doc, sxref, with_text=True)
            rel = ev.get("related_dates", {}) or {}
            relp = ev.get("related_places", {}) or {}
            for key, tag in (("birth", "BIRT"), ("death", "DEAT"), ("baptism", "BAPM"), ("burial", "BURI")):
                if key in rel and tag != main_tag:
                    e.line(1, tag)
                    gd = gedcom_date(rel[key])
                    if gd:
                        e.line(2, "DATE", gd)
                    if place_value(relp.get(key)):
                        e.line(2, "PLAC", place_value(relp.get(key)))
                    emit_citation(e, 2, doc, sxref, with_text=False, note=f"Stated in the {ev['type']} act as '{rel[key].get('as_written')}'", secondary=(key not in {"birth"} or ev["type"] != "baptism"))
        # facts stated about any person
        if p.get("birth", {}).get("date") or p.get("birth", {}).get("place"):
            e.line(1, "BIRT")
            gd = gedcom_date(p["birth"].get("date"))
            if gd:
                e.line(2, "DATE", gd)
            if place_value(p["birth"].get("place")):
                e.line(2, "PLAC", place_value(p["birth"].get("place")))
            emit_citation(e, 2, doc, sxref, with_text=False, note="Birth data as stated in this act (secondary information)", secondary=True)
        elif age_birth_date(p, act_year):
            e.line(1, "BIRT")
            e.line(2, "DATE", age_birth_date(p, act_year))
            emit_citation(e, 2, doc, sxref, with_text=False, note=f"From age '{p['age'].get('as_written', p['age'].get('years'))}' at the act date", secondary=True)
        if p.get("death", {}).get("date") or p.get("death", {}).get("place"):
            e.line(1, "DEAT")
            gd = gedcom_date(p["death"].get("date"))
            if gd:
                e.line(2, "DATE", gd)
            if place_value(p["death"].get("place")):
                e.line(2, "PLAC", place_value(p["death"].get("place")))
            emit_citation(e, 2, doc, sxref, with_text=False, note="Death as stated in this act", secondary=True)
        elif p.get("status") == "deceased" and act_date:
            e.line(1, "DEAT")
            e.line(2, "DATE", f"BEF {act_date}")
            emit_citation(e, 2, doc, sxref, with_text=False, note="Described as deceased (feu/défunt) in this act", secondary=True)
        if p.get("occupation"):
            e.line(1, "OCCU", p["occupation"])
            if act_date:
                e.line(2, "DATE", act_date)
            emit_citation(e, 2, doc, sxref, with_text=False)
        if place_value(p.get("residence")):
            e.line(1, "RESI")
            if act_date:
                e.line(2, "DATE", act_date)
            e.line(2, "PLAC", place_value(p["residence"]))
            if p["residence"].get("detail"):
                e.line(2, "ADDR", p["residence"]["detail"])
            emit_citation(e, 2, doc, sxref, with_text=False)
        for fx in fams_as_spouse(p):
            e.line(1, "FAMS", fx)
        for fx in fams_as_child(p):
            e.line(1, "FAMC", fx)
        # associations from the subject's side are emitted on the subject below
        if is_subject:
            for q in doc["persons"]:
                if q["role"] in RELA and subject_of(q) is p:
                    e.line(1, "ASSO", xref[q["id"]])
                    rela = RELA[q["role"]]
                    if q.get("relationship_as_written"):
                        rela += f" ({q['relationship_as_written']})"
                    e.line(2, "RELA", rela)
                    emit_citation(e, 2, doc, sxref, with_text=False)
            for m in doc.get("marginal_mentions", []):
                if p["id"] in (m.get("persons") or [subjects[0]["id"]]):
                    tag = {"death": "DEAT", "marriage": "MARR", "divorce": "DIV", "adoption": "ADOP"}.get(m["type"])
                    if tag in {"MARR", "DIV"}:
                        continue  # belong to a FAM the integrator must identify; kept in the note below
                    if tag:
                        e.line(1, tag)
                        gd = gedcom_date(m.get("date"))
                        if gd:
                            e.line(2, "DATE", gd)
                        if place_value(m.get("place")):
                            e.line(2, "PLAC", place_value(m.get("place")))
                        emit_citation(e, 2, doc, sxref, with_text=False, note=f"Marginal mention: {m['text']}")
                    else:
                        e.line(1, "NOTE", f"Marginal mention ({m['type']}): {m['text']}")
                        emit_citation(e, 2, doc, sxref, with_text=False)
        if p.get("signature") and p["signature"] != "not_stated":
            e.line(1, "NOTE", {"signed": "Signed the act", "mark": "Made a mark on the act", "declared_unable": "Declared not knowing how to sign", "absent": "Not present at the act"}[p["signature"]] + (f" ({d['act_date'].get('as_written')})" if d.get("act_date") else ""))
        if p.get("notes"):
            e.line(1, "NOTE", p["notes"])
        if p.get("confidence") == "low":
            e.line(1, "NOTE", "Reading confidence LOW for this person's identity fields; verify against the image")
        if p.get("relationship_as_written") and p["role"] not in RELA:
            e.line(1, "NOTE", f"Described in the act as '{p['relationship_as_written']}'")

    # families
    for f in fams:
        e.line(0, "FAM", xref=f["xref"])
        if f["husb"]:
            e.line(1, "HUSB", xref[f["husb"]["id"]])
        if f["wife"]:
            e.line(1, "WIFE", xref[f["wife"]["id"]])
        for c in f["chil"]:
            e.line(1, "CHIL", xref[c["id"]])
        if f["kind"] == "union":
            e.line(1, main_tag)
            evd = gedcom_date(ev.get("date")) or act_date
            if evd:
                e.line(2, "DATE", evd)
            if place_value(ev.get("place")):
                e.line(2, "PLAC", place_value(ev.get("place")))
            if ev.get("details"):
                e.line(2, "NOTE", ev["details"])
            emit_citation(e, 2, doc, sxref, with_text=True)
            for m in doc.get("marginal_mentions", []):
                if m["type"] == "divorce":
                    e.line(1, "DIV")
                    gd = gedcom_date(m.get("date"))
                    if gd:
                        e.line(2, "DATE", gd)
                    emit_citation(e, 2, doc, sxref, with_text=False, note=f"Marginal mention: {m['text']}" + (f" ({m['authority']})" if m.get("authority") else ""))
        elif f["kind"] == "parents":
            emit_citation(e, 1, doc, sxref, with_text=False, note="Parentage as stated in this act")
        else:
            emit_citation(e, 1, doc, sxref, with_text=False, note="Union as stated in this act")

    # open items
    unc = doc.get("uncertainties", [])
    qs = doc.get("questions_for_user", [])
    if unc or qs:
        e.lines.append("# Open items (not GEDCOM):")
        for u in unc:
            e.lines.append(f"#  - {u['field']}: read '{u['reading']}'" + (f", alternatives {u['alternatives']}" if u.get("alternatives") else "") + (f" ({u['reason']})" if u.get("reason") else ""))
        for q in qs:
            e.lines.append(f"#  - question: {q}")
    return "\n".join(e.lines) + "\n"


# ----------------------------------------------------------------- summary --

def summary(doc: dict) -> str:
    d, ev = doc["document"], doc["event"]
    out = [f"{d['type']} act, {d.get('subtype', '')}".rstrip(", "),
           f"act date: {d['act_date'].get('as_written')} → {gedcom_date(d['act_date']) or '?'}",
           f"event: {ev['type']} {gedcom_date(ev.get('date')) or ''} {place_value(ev.get('place')) or ''}".rstrip(),
           f"source: {d.get('source_type', 'original')} → QUAY {quay_for(doc)}; {d['citation']['page_string']}", "persons:"]
    for p in doc["persons"]:
        name, _, _ = person_name(p)
        bits = [p["role"] + (f" (party {p['party']})" if p.get("party") else ""), name.replace("/", "")]
        if p.get("age", {}).get("as_written"):
            bits.append(p["age"]["as_written"])
        if p.get("occupation"):
            bits.append(p["occupation"])
        if place_value(p.get("residence")):
            bits.append("of " + place_value(p["residence"]))
        if p.get("status") == "deceased":
            bits.append("deceased")
        if p.get("signature") and p["signature"] != "not_stated":
            bits.append(p["signature"])
        out.append("  " + p["id"] + ": " + ", ".join(bits))
    if doc.get("marginal_mentions"):
        out.append("marginal mentions: " + "; ".join(f"{m['type']} {gedcom_date(m.get('date')) or ''}".strip() for m in doc["marginal_mentions"]))
    if doc.get("uncertainties"):
        out.append(f"uncertainties: {len(doc['uncertainties'])}")
    return "\n".join(out)


# -------------------------------------------------------------------- main --

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("file"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("gedcom"); p.add_argument("file")
    p.add_argument("--source-xref"); p.add_argument("--map", nargs="+", action="extend", default=[], metavar="pN=@Ixx@")
    p.add_argument("--indi-start", type=int, default=9001); p.add_argument("--fam-start", type=int, default=9001)
    p.add_argument("--no-text", action="store_true")
    p = sub.add_parser("date"); p.add_argument("text")
    p = sub.add_parser("summary"); p.add_argument("file")
    args = ap.parse_args(argv)

    if args.cmd == "date":
        rep = parse_republican(args.text)
        if not rep:
            print(f"cannot parse '{args.text}' as a French Republican date", file=sys.stderr)
            return 1
        y, m, d = rep
        g = french_to_gregorian(y, m, d)
        print(f"{republican_to_gedcom(y, m, d)}  =  {g.day} {MONTHS[g.month - 1]} {g.year}  ({g.isoformat()})")
        return 0

    try:
        doc = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    errors, warnings = validate(doc)

    if args.cmd == "validate":
        if args.json:
            print(json.dumps({"file": args.file, "errors": errors, "warnings": warnings, "result": "FAIL" if errors else "PASS"}, indent=2, ensure_ascii=False))
        else:
            for w in warnings:
                print(f"WARNING: {w}")
            for er in errors:
                print(f"ERROR: {er}")
            print(f"RESULT: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings)")
        return 1 if errors else 0

    if errors:
        for er in errors:
            print(f"ERROR: {er}", file=sys.stderr)
        print("fix validation errors before generating GEDCOM", file=sys.stderr)
        return 1
    if args.cmd == "summary":
        print(summary(doc))
        return 0
    mapping = {}
    for m in args.map:
        if "=" not in m:
            print(f"ERROR: --map expects p1=@I12@, got '{m}'", file=sys.stderr)
            return 2
        k, v = m.split("=", 1)
        mapping[k] = v
    for w in warnings:
        print(f"# WARNING: {w}")
    sys.stdout.write(to_gedcom(doc, args.source_xref, mapping, args.indi_start, args.fam_start, args.no_text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
