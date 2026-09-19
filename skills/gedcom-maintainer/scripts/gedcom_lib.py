#!/usr/bin/env python3
"""Shared, dependency-free GEDCOM reader used by the bundled scripts.

Handles GEDCOM 5.5, 5.5.1 and 7.0 line syntax, detects the declared and the
actual encoding, and exposes a small record tree plus date parsing helpers.
Only the standard library is used (Python 3.9+).
"""
from __future__ import annotations

import re
from datetime import date as _date
from dataclasses import dataclass, field
from typing import Iterator, Optional

LINE_RE = re.compile(r"^(\d+) (?:(@[^@ ]+@) )?([A-Za-z0-9_]+)(?: (.*))?$")
XREF_RE = re.compile(r"^@[^@ ]+@$")
VOID = "@VOID@"

# Tags whose value is a pointer to another record (GEDCOM 5.5.1 and 7.0).
POINTER_TAGS = {
    "FAMC": "FAM", "FAMS": "FAM", "HUSB": "INDI", "WIFE": "INDI", "CHIL": "INDI",
    "ALIA": "INDI", "ASSO": "INDI", "ANCI": "SUBM", "DESI": "SUBM", "SUBM": "SUBM",
    "SUBN": "SUBN", "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR", "OBJE": "OBJE",
    "REPO": "REPO",
}
ROOT_TYPES = {"HEAD", "TRLR", "INDI", "FAM", "NOTE", "SNOTE", "SOUR", "OBJE", "REPO", "SUBM", "SUBN"}
TEXT_ROOTS = {"NOTE", "SNOTE", "SOUR", "OBJE", "REPO", "SUBM"}


@dataclass
class Node:
    level: int
    tag: str
    value: str
    line: int
    xref: Optional[str] = None
    children: list["Node"] = field(default_factory=list)
    parent: Optional["Node"] = field(default=None, repr=False)

    def child(self, tag: str) -> Optional["Node"]:
        for c in self.children:
            if c.tag == tag:
                return c
        return None

    def all(self, tag: str) -> list["Node"]:
        return [c for c in self.children if c.tag == tag]

    def get(self, *path: str) -> Optional[str]:
        node: Optional[Node] = self
        for tag in path:
            node = node.child(tag) if node else None
        return node.value if node else None

    def text(self) -> str:
        """Value with CONT/CONC continuation lines folded in."""
        out = self.value
        for c in self.children:
            if c.tag == "CONT":
                out += "\n" + c.value
            elif c.tag == "CONC":
                out += c.value
        return out

    def walk(self) -> Iterator["Node"]:
        yield self
        for c in self.children:
            yield from c.walk()

    def is_pointer(self) -> bool:
        return bool(self.value) and XREF_RE.fullmatch(self.value) is not None


@dataclass
class Gedcom:
    path: str
    records: list[Node]
    by_xref: dict[str, Node]
    version: str
    declared_charset: str
    used_encoding: str
    bom: bool
    crlf: bool
    syntax_errors: list[tuple[int, str]]
    raw_lines: list[str]

    @property
    def major(self) -> int:
        try:
            return int(self.version.split(".")[0])
        except ValueError:
            return 5

    def head(self) -> Optional[Node]:
        return next((r for r in self.records if r.tag == "HEAD"), None)

    def of_type(self, tag: str) -> list[Node]:
        return [r for r in self.records if r.tag == tag]

    def type_of(self, xref: str) -> Optional[str]:
        node = self.by_xref.get(xref)
        return node.tag if node else None


def _sniff_charset(data: bytes) -> tuple[str, bool]:
    """Return (declared CHAR value or '', has_bom)."""
    if data.startswith(b"\xef\xbb\xbf"):
        return _declared(data[3:].decode("utf-8", "replace")), True
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "UNICODE", True
    return _declared(data[:4000].decode("latin-1")), False


def _declared(head_text: str) -> str:
    m = re.search(r"^1 CHAR (.+)$", head_text, re.M)
    return m.group(1).strip().upper() if m else ""


def decode(data: bytes) -> tuple[str, str, str, bool]:
    """Decode raw bytes. Returns (text, declared_charset, used_encoding, bom)."""
    declared, bom = _sniff_charset(data)
    if declared == "UNICODE" or data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), declared or "UNICODE", "utf-16", bom
    if bom:
        return data[3:].decode("utf-8", "replace"), declared, "utf-8", True
    try:
        return data.decode("utf-8"), declared, "utf-8", False
    except UnicodeDecodeError:
        pass
    # ANSEL has no stdlib codec; ANSI usually means cp1252. Both are single-byte
    # so a byte-transparent decoding keeps line structure intact for checks.
    if declared in {"ANSI", "ASCII"}:
        return data.decode("cp1252", "replace"), declared, "cp1252", False
    return data.decode("latin-1"), declared or "?", "latin-1 (byte-transparent)", False


def parse(path: str) -> Gedcom:
    with open(path, "rb") as fh:
        data = fh.read()
    text, declared, used, bom = decode(data)
    crlf = "\r\n" in text
    raw_lines = text.splitlines()
    records: list[Node] = []
    by_xref: dict[str, Node] = {}
    syntax_errors: list[tuple[int, str]] = []
    stack: list[Node] = []

    for number, line in enumerate(raw_lines, 1):
        if not line.strip():
            syntax_errors.append((number, "blank line"))
            continue
        m = LINE_RE.match(line.rstrip("\r"))
        if not m:
            # tolerate leading spaces / tabs, but report them
            m = LINE_RE.match(re.sub(r"^\s+", "", line).replace("\t", " ", 1))
            syntax_errors.append((number, "invalid GEDCOM line" if not m else "leading whitespace or tab delimiter"))
            if not m:
                continue
        level, xref, tag, value = int(m.group(1)), m.group(2), m.group(3), m.group(4) or ""
        node = Node(level=level, tag=tag, value=value, line=number, xref=xref)
        if level == 0:
            records.append(node)
            if xref and xref not in by_xref:
                by_xref[xref] = node
            stack = [node]
            continue
        if not stack:
            syntax_errors.append((number, "subordinate line before first record"))
            continue
        while stack and stack[-1].level >= level:
            stack.pop()
        if not stack or stack[-1].level != level - 1:
            syntax_errors.append((number, f"level jumps to {level}"))
            # attach to the nearest ancestor so later checks still see it
            stack = stack or [records[-1]]
        node.parent = stack[-1]
        stack[-1].children.append(node)
        stack.append(node)

    version = ""
    head = next((r for r in records if r.tag == "HEAD"), None)
    if head:
        version = head.get("GEDC", "VERS") or ""
        if not declared:
            declared = (head.get("CHAR") or "").upper()
    return Gedcom(path, records, by_xref, version, declared, used, bom, crlf, syntax_errors, raw_lines)


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------

MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}
FRENCH_MONTHS = {m: i for i, m in enumerate(
    ["VEND", "BRUM", "FRIM", "NIVO", "PLUV", "VENT", "GERM", "FLOR", "PRAI", "MESS", "THER", "FRUC", "COMP"], 1)}
HEBREW_MONTHS = {"TSH", "CSH", "KSL", "TVT", "SHV", "ADR", "ADS", "NSN", "IYR", "SVN", "TMZ", "AAV", "ELL"}
CALENDARS = {"GREGORIAN", "JULIAN", "FRENCH R", "FRENCH_R", "HEBREW", "ROMAN", "UNKNOWN"}
APPROX = {"ABT", "CAL", "EST"}
RANGE = {"BEF", "AFT", "BET", "FROM", "TO", "INT"}


@dataclass
class GDate:
    raw: str
    calendar: str = "GREGORIAN"
    modifier: str = ""            # ABT, CAL, EST, BEF, AFT, BET, FROM, TO, INT, or ""
    year: Optional[int] = None    # first date's year
    month: Optional[int] = None
    day: Optional[int] = None
    year2: Optional[int] = None   # second date of BET/AND or FROM/TO
    month2: Optional[int] = None
    day2: Optional[int] = None
    phrase: bool = False          # (free text) only
    problems: list[str] = field(default_factory=list)

    @property
    def approximate(self) -> bool:
        return self.modifier in APPROX

    def gregorian_year(self) -> Optional[int]:
        """Nominal year of the (first) date in the Gregorian calendar, for display."""
        if self.year is None:
            return None
        return int(_frac(self.year, self.month, self.day, self.calendar, True))

    def bounds(self, slack_years: int = 0) -> tuple[Optional[float], Optional[float]]:
        """Earliest and latest possible day as fractional Gregorian years (None = open).

        Non-Gregorian calendars are converted so that chronology checks compare
        like with like: French Republican dates exactly, Hebrew dates roughly.
        """
        if self.year is None:
            return None, None
        cal = self.calendar
        a_lo, a_hi = _frac(self.year, self.month, self.day, cal, True), _frac(self.year, self.month, self.day, cal, False)
        if self.modifier == "BEF":
            return None, a_hi
        if self.modifier == "AFT":
            return a_lo, None
        if self.modifier in {"BET", "FROM"} and self.year2 is not None:
            return a_lo, _frac(self.year2, self.month2, self.day2, cal, False)
        if self.modifier == "TO":
            return None, a_hi
        if self.approximate or slack_years:
            s = slack_years if not self.approximate else max(slack_years, 2)
            return a_lo - s, a_hi + s
        return a_lo, a_hi


FRENCH_EPOCH = _date(1792, 9, 22).toordinal()
FRENCH_SEXTILE = {3, 7, 11, 15, 20}  # sextile (leap) years actually observed / decreed


def french_to_gregorian(year: int, month: int, day: int) -> _date:
    """Convert a French Republican date (year I = 1792) to a Gregorian date."""
    days = (year - 1) * 365 + sum(1 for y in FRENCH_SEXTILE if y < year) + (month - 1) * 30 + (day - 1)
    return _date.fromordinal(FRENCH_EPOCH + days)


def _frac(year: int, month: Optional[int], day: Optional[int], calendar: str, low: bool) -> float:
    """Fractional Gregorian year for the earliest (low) or latest reading."""
    if calendar in {"FRENCH R", "FRENCH_R"}:
        m = month if month else (1 if low else 13)
        d = day if day else (1 if low else (5 if m == 13 else 30))
        try:
            g = french_to_gregorian(year, m, d)
            return g.year + (g.month - 1) / 12 + (g.day - 1) / 372
        except (ValueError, OverflowError):
            pass
    if calendar == "HEBREW":
        year = year - 3760 if low else year - 3759
        month = day = None
    m = month or (1 if low else 12)
    d = day or (1 if low else 31)
    return year + (m - 1) / 12 + (d - 1) / 372


def _leap(year: int, calendar: str) -> bool:
    if calendar == "JULIAN":
        return year % 4 == 0
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _parse_simple(tokens: list[str], calendar: str, gd: GDate) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Parse [day] [month] year [/yy] [B.C.] into a tuple; record problems on gd."""
    day = month = year = None
    toks = [t for t in tokens if t not in {"B.C.", "BC", "BCE"}]
    if not toks:
        return None, None, None
    # year, possibly dual-dated 1699/00 or 1699/1700
    y = toks[-1]
    ym = re.fullmatch(r"(\d{1,4})(?:/(\d{2,4}))?", y)
    if not ym:
        gd.problems.append(f"unrecognised year '{y}'")
        return None, None, None
    year = int(ym.group(1))
    if ym.group(2) and calendar not in {"GREGORIAN", "JULIAN"}:
        gd.problems.append("dual year only makes sense for Julian/Gregorian dates")
    rest = toks[:-1]
    if len(rest) >= 1:
        mtok = rest[-1].upper()
        table = FRENCH_MONTHS if calendar in {"FRENCH R", "FRENCH_R"} else MONTHS
        if calendar == "HEBREW":
            if mtok not in HEBREW_MONTHS:
                gd.problems.append(f"unknown Hebrew month '{mtok}'")
            month = None
        elif mtok in table:
            month = table[mtok]
        elif mtok in FRENCH_MONTHS:
            gd.problems.append(f"'{mtok}' is a French Republican month; prefix the date with @#DFRENCH R@")
        else:
            gd.problems.append(f"unknown month '{mtok}'" + (" (spell out the month: 3 MAR 1850, not 03/03/1850)" if mtok.isdigit() else ""))
    if len(rest) == 2:
        if rest[0].isdigit():
            day = int(rest[0])
        else:
            gd.problems.append(f"unrecognised day '{rest[0]}'")
    elif len(rest) > 2:
        gd.problems.append("too many date components")
    if day is not None and month is not None and calendar in {"GREGORIAN", "JULIAN"}:
        lengths = [31, 29 if _leap(year, calendar) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if not 1 <= day <= lengths[month - 1]:
            gd.problems.append(f"day {day} does not exist in that month")
    elif day is not None and calendar in {"FRENCH R", "FRENCH_R"}:
        if not 1 <= day <= (6 if month == 13 else 30):
            gd.problems.append(f"day {day} does not exist in that French Republican month")
    return year, month, day


def parse_date(raw: str) -> GDate:
    gd = GDate(raw=raw.strip())
    s = gd.raw
    if not s:
        gd.problems.append("empty date")
        return gd
    if s.startswith("(") and s.endswith(")"):
        gd.phrase = True
        return gd
    m = re.match(r"^@#D([A-Z _]+)@\s*(.*)$", s)
    if m:
        gd.calendar = m.group(1).strip()
        if gd.calendar not in CALENDARS:
            gd.problems.append(f"unknown calendar escape '{gd.calendar}'")
        s = m.group(2)
    toks = s.split()
    if not toks:
        gd.problems.append("calendar escape without a date")
        return gd
    head = toks[0].upper()
    if head in {"BET", "FROM"}:
        sep = "AND" if head == "BET" else "TO"
        gd.modifier = head
        upper = [t.upper() for t in toks]
        if sep in upper:
            i = upper.index(sep)
            gd.year, gd.month, gd.day = _parse_simple(toks[1:i], gd.calendar, gd)
            gd.year2, gd.month2, gd.day2 = _parse_simple(toks[i + 1:], gd.calendar, gd)
            if gd.year and gd.year2 and (gd.year2, gd.month2 or 0, gd.day2 or 0) < (gd.year, gd.month or 0, gd.day or 0):
                gd.problems.append("range end precedes range start")
        elif head == "FROM":
            gd.year, gd.month, gd.day = _parse_simple(toks[1:], gd.calendar, gd)
        else:
            gd.problems.append("BET without AND")
        return gd
    if head in APPROX | {"BEF", "AFT", "TO", "INT"}:
        gd.modifier = head
        toks = toks[1:]
        if head == "INT" and "(" in s:
            toks = s[len("INT"):s.index("(")].split()
    gd.year, gd.month, gd.day = _parse_simple(toks, gd.calendar, gd)
    return gd


def event_date(node: Node, tag: str) -> Optional[GDate]:
    ev = node.child(tag)
    if not ev:
        return None
    d = ev.child("DATE")
    return parse_date(d.value) if d and d.value else None


def display_name(indi: Node) -> str:
    n = indi.child("NAME")
    return n.value.replace("/", "").strip() if n else "(no name)"


def surname(indi: Node) -> str:
    n = indi.child("NAME")
    if not n:
        return ""
    m = re.search(r"/([^/]*)/", n.value)
    if m:
        return m.group(1).strip()
    return n.get("SURN") or ""
