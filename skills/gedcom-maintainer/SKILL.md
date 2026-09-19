---
name: gedcom-maintainer
description: >-
  Maintain, inspect, enrich and safely update GEDCOM (.ged) genealogy files as
  an evidence-backed graph: find people and families by xref, add or correct
  names, dates, places, relationships and source citations only when a cited
  record supports them, grade certainty with QUAY, record conflicts and
  hypotheses in notes instead of overwriting, merge duplicates without losing
  data, and validate structure, links, dates and chronology after every edit
  with a change log. Use whenever the user mentions a GEDCOM or .ged file, a
  family-tree export from Gramps, Ancestry, MyHeritage, Geneanet, Heredis,
  FamilySearch or similar, civil or parish register acts (birth, baptism,
  marriage, death, burial), ancestors or descendants, or asks to merge, clean,
  verify, source or update a family tree, even if they never say GEDCOM.
license: MIT
compatibility: Requires Python 3.9+ for the bundled scripts (standard library only).
metadata:
  author: Pierre Thalamy
  category: data
---

# GEDCOM Maintainer

Maintain a genealogical dataset as an evidence-backed graph. The GEDCOM is
the user's working research file: every fact in it should be traceable to a
record, every uncertainty visible, and every edit reversible. Treat a
plausible match as a hypothesis until a record names it, because the most
common way a tree goes wrong is a same-name person quietly grafted onto the
wrong family. This skill gives you a workflow, the genealogical standards
the workflow rests on, and three scripts so you never have to load a large
file into context or hand-check pointers.

## When to use

Any task that reads or changes a `.ged` file, or that turns genealogical
records (acts, censuses, images, another tree) into changes to one. Not for
writing narrative family histories or for building a new tree from scratch
with no file; for those, produce the text or ask which software the user
will import into and create a minimal valid GEDCOM 5.5.1 only if asked.

## Workflow

1. **Copy and characterise the file.** Work on a copy, keep the original
   untouched. Run `python3 scripts/inspect_gedcom.py summary FILE` to learn
   the GEDCOM version, encoding, byte-order mark, line endings, exporting
   software, record counts and custom tags. Preserve all of those on
   output; a lost BOM or a mixed encoding breaks re-import.
2. **Baseline validation.** Run `python3 scripts/validate_gedcom.py FILE`
   (add `--json` to parse the result). Note pre-existing errors so you can
   tell them from ones you introduce, and do not "fix" unrelated findings
   unless asked.
3. **Locate the target records by xref, not by name.** Use
   `inspect_gedcom.py find FILE "name" --born YEAR` to list candidates and
   `inspect_gedcom.py show FILE @I12@` to see one person or family with
   their events, sources, parents, unions and children. When several people
   share a name, apply the identity checklist in
   `references/evidence-and-gedcom.md` before choosing.
4. **Classify the evidence** for each change you are about to make. Read
   `references/evidence-and-gedcom.md` for the Genealogical Proof Standard,
   the original/derivative, primary/secondary and direct/indirect
   distinctions, and the working levels:
   - **Documented**: an original record, seen, names the fact. Enter it,
     cite it, `QUAY 3` (or `2` for a derivative copy).
   - **Corroborated**: independent records agree, or a tree exposes a
     checkable source. Enter it, cite each record, `QUAY 1`-`2`, note what
     is still missing.
   - **Hypothesis**: fits, but no record names it. Do not create the link.
     Record the hypothesis and the record that would test it in a `NOTE`.
5. **Edit the raw lines** with `inspect_gedcom.py raw FILE @I12@` to get the
   exact block and line numbers, then change only those lines. Follow
   `references/gedcom-conventions.md` for citation structure, event tags,
   date syntax and calendars, `PEDI` for adoption, `CONC`/`CONT` and the
   255-character limit in 5.5.1, and for what changes in GEDCOM 7. Write
   both halves of every relationship (`FAMS`/`FAMC` and `HUSB`/`WIFE`/`CHIL`).
6. **Preserve, do not overwrite.** When a record contradicts the file,
   keep the better-supported value canonical, keep the other with its own
   citation, and write a dated `NOTE` naming both values, their sources
   and the record that would settle it. Never delete a sourced claim to
   make a tree tidier, and never replace a sourced value with an unsourced one.
7. **Validate again** and compare: `validate_gedcom.py NEW` must show no new
   errors, and `inspect_gedcom.py diff OLD NEW` lists every record you
   touched. Anything in the diff you cannot explain is a mistake.
8. **Deliver** the updated file plus a change log built from
   `assets/change-log-template.md`.

## Genealogical rules

- **Cite so someone else can find it**: archive or site, collection or
  register, commune or parish, year, act number, page or image number,
  permalink and access date, in `SOUR`/`PAGE`. Grade the citation with
  `QUAY`. A citation the reader cannot follow is not a citation.
- **A public tree is a lead, not a source.** It corroborates only when it
  exposes a record you can check; cite the record, not the tree. Never
  copy an unsourced ancestor chain because names and dates line up.
- **Same name is not same person.** Require at least two matching details
  beyond the name (parents, spouse, place, occupation, age within a few
  years, recurring witnesses). Watch for infant deaths followed by a
  namesake sibling: that is two individuals, not one corrected date.
- **Use the event the record documents.** A baptism is `BAPM`/`CHR`, a
  burial is `BURI`; enter `BIRT` or `DEAT` alongside only if the act states
  them. Distinguish the date of the event from the date of the act.
- **Never invent precision.** Use `ABT`, `CAL`, `EST`, `BEF`, `AFT`, `BET … AND`
  when the record gives an age or a bound; enter French Republican and
  Julian dates as written with their calendar escape. No numeric months,
  no guessed days or places.
- **Model relationships honestly.** Each union is its own `FAM`. Adoption,
  foster and step links use `PEDI` and a note; a presumed father is a note
  on the child, not a `HUSB`. Attach children to the family the record
  names, never by household proximity.
- **Keep spellings and names as recorded.** One canonical `NAME` per
  person, variants and married names as extra `NAME` structures with
  `TYPE` or in the citation; women under their birth surname; transcribe
  handwriting literally with `[?]` for doubt, never "corrected".
- **Sanity-check chronology.** Mothers under 15 or over 50, children born
  long after a father's death, marriages in childhood, baptisms before
  births and lifespans past 105 are almost always identity errors. The
  validator flags them; look before dismissing one.
- **Protect living people.** Anyone born within 100 years with no death
  event may be alive: keep name and links, leave out exact dates,
  addresses and anything personal, and honour privacy flags.

## GEDCOM editing conventions

- Match the file's version and dialect; do not convert a 5.5.1 file to 7
  (or the reverse) during a targeted edit. In 7.0 there is no `CONC`,
  `@VOID@` is a legal placeholder and enumerations are upper-case.
- One level-0 record per xref; never renumber or reuse xrefs, because the
  user's other exports and notes refer to them.
- Reuse an existing `SOUR` record for the same register or collection and
  put the act-level detail in the citation's `PAGE`. Create a new `SOUR`
  only for a new collection.
- Preserve every custom `_TAG`, `CHAN` structure, existing note and
  source-generated identifier. Update `CHAN.DATE` if the file uses it.
- No wholesale reformatting, re-sorting or re-encoding: the diff must show
  only genealogical changes.

## Deliverables

Provide the updated GEDCOM and a change log following
`assets/change-log-template.md`: validation before and after, every record
added, changed, removed or merged with its evidence and level, conflicts
and hypotheses left open with the record that would decide each, and
anything requested that the evidence did not support. Run
`inspect_gedcom.py diff OLD NEW` to make sure the log and the file agree.

## Scripts

All three are standard-library Python 3.9+ and accept `--json`.

- `scripts/validate_gedcom.py FILE [--json] [--strict]`: encoding vs
  declaration, syntax and levels, duplicate and dangling xrefs, pointer
  types, reciprocal `FAMS`/`FAMC` ↔ `HUSB`/`WIFE`/`CHIL` links, family roles,
  date syntax for every calendar, chronology, `NAME`/`GIVN`/`SURN`
  consistency, orphan records, GEDCOM 7 rules. Exit 0 means no errors.
- `scripts/inspect_gedcom.py summary|find|show|refs|raw|diff`: read-only
  navigation and diffing so a 50 MB tree never has to be read whole.
- `scripts/gedcom_lib.py`: the shared parser and date model, importable if
  you need a custom check.

## Examples

**Example 1: sourcing an approximate birth.** The user gives an act image
for a person whose record has `BIRT DATE ABT 1795`. The agent runs `show`
on the xref, transcribes the act, replaces the date with the one the act
states (in its original calendar), adds `PLAC`, a citation with `PAGE`,
`QUAY 3`, `DATA.DATE` for the act date and `DATA.TEXT` for the
transcription, checks that the parents named in the act match the `FAMC`
family and cites the act on that link too, validates, and reports the
change with a Documented level.

**Example 2: a tree says the great-grandfather was someone else.** The
user's Geneanet match gives different parents for `@I40@`. The agent looks
for the source behind the match. Finding only "family tradition", it leaves
`@I40@`'s parents untouched, adds a dated `NOTE` stating the alternative
parentage as `HYPOTHESIS`, names the marriage act that would settle it, and
reports it under conflicts left open rather than editing a single pointer.

**Example 3: two Marie Dupont.** `find "marie dupont" --born 1820` returns
two individuals. `show` reveals one died at 2, the other married in 1845.
The agent explains the namesake pattern, declines to merge, and attaches the
new record to the one whose spouse and parents match.
