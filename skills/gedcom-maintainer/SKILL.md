---
name: gedcom-maintainer
description: >-
  Maintain, inspect, enrich and safely update GEDCOM (.ged) genealogy files as
  an evidence-backed graph: parse individuals, families, sources and notes;
  add or correct names, dates, places and relationships only when a cited
  source supports them; record conflicts and hypotheses in notes instead of
  overwriting; validate pointers, levels and encoding after every edit and
  report a change log. Use whenever the user mentions a GEDCOM or .ged file, a
  family tree export from genealogy software or a genealogy website, civil or
  parish register acts (birth, baptism, marriage, death, burial), ancestors or
  descendants, or asks to merge, clean, verify, source or update a family tree,
  even if they never say the word GEDCOM.
license: MIT
compatibility: Requires Python 3.9+ to run scripts/validate_gedcom.py.
metadata:
  author: Pierre Thalamy
  category: data
---

# GEDCOM Maintainer

Maintain a genealogical dataset as an evidence-backed graph. Treat the GEDCOM as a working source file, not as permission to turn plausible matches into facts.

## Core workflow

1. Locate the exact input file and make a copy before editing. Preserve the original filename and encoding in the working copy; use UTF-8 and retain a BOM only when the source uses one.
2. Parse the file into individuals, families, notes, sources, and pointers before making changes. Identify the requested target person or family by stable `@I...@` / `@F...@` identifiers, not by name alone.
3. Separate evidence into three levels:
   - **Documented**: directly supported by an act, image, archival reference, or an explicitly cited reliable source.
   - **Corroborated**: supported by multiple independent clues or a public tree whose underlying source is visible.
   - **Hypothesis**: a possible identification or relationship that still needs proof.
4. Add or change only what the evidence supports. When sources conflict, preserve the existing claim and record the conflict in a `NOTE`; do not silently choose the most convenient version.
5. Keep facts on the relevant individual or family. Put event-specific uncertainty, transcription choices, aliases, and research reasoning in notes or source records rather than altering the canonical name/date to hide ambiguity.
6. Validate pointers, uniqueness, family roles, levels, and encoding after every edit. Produce a diff or concise change log listing each changed record and its evidence.

## Genealogical rules

- Prefer exact act citations: archive/site, collection or register, commune/parish, year, page/image, permalink, and access date when available.
- A public genealogy tree is a lead by default. Treat it as corroborating evidence only when the tree exposes a source that can be checked. Never copy an unsourced ancestor chain merely because names and dates line up.
- Preserve original spellings in source/transcription notes; normalize only in a separate name form or an explicit `ALIA` entry when the software supports it.
- Use approximate dates (`ABT`, `BEF`, `AFT`, ranges, or a note) when precision is not established. Never invent a day or place from context.
- Distinguish biological, legal/adoptive, foster, step, and presumed relationships. Model legal or adoptive links with the appropriate family structure and explain unusual roles in a note.
- For a person with multiple unions, model each union as its own `FAM` record. Attach children to the family supported by the record; do not infer parentage solely from household proximity.
- Keep living-person data minimal and avoid adding sensitive details that are not needed for the tree.
- If an act image is supplied, transcribe what is legible and mark uncertain readings with `[?]` or an explanatory note. Do not "correct" handwriting by guessing.

## GEDCOM editing conventions

- Respect the source's GEDCOM 5.5/5.5.1 dialect and tag vocabulary. Do not convert the whole file to a different dialect during a targeted update.
- Keep one level-0 record per unique xref. Update both directions of every relationship: `FAMC`/`FAMS` on individuals and `HUSB`/`WIFE`/`CHIL` on families.
- Keep `NAME`, `SURN`, and `GIVN` mutually consistent with the chosen canonical spelling. Put titles, nicknames, and alternate spellings in `TITL`, `NICK`, or `ALIA` only when justified by the source format.
- Keep `DATE` and `PLAC` under the relevant event (`BIRT`, `DEAT`, `MARR`, etc.). Do not attach a date or place at the wrong level merely to preserve information.
- Reuse an existing `NOTE` or `SOUR` record when it is clearly the same evidence. Otherwise create a new unique xref and link it with `NOTE`/`SOUR`.
- Preserve source-generated identifiers and existing notes unless correcting a demonstrable structural error. Avoid wholesale reformatting because it obscures genealogical changes.

## Deliverables

When the user requests an update, provide the updated GEDCOM plus a compact summary of:

- records added, changed, or left unresolved;
- evidence and citations attached to each material claim;
- conflicts or hypotheses requiring a future check;
- validation result and any limitations.

Use `scripts/validate_gedcom.py` for deterministic structural checks. Read `references/evidence-and-gedcom.md` when evaluating source quality, uncertain readings, or relationship conflicts.
