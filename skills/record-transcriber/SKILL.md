---
name: record-transcriber
description: >-
  Transcribe and extract structured data from genealogical records: images or
  text of parish registers (baptism, marriage, burial), civil registration
  acts (birth, marriage, death), census sheets, military rolls and notarial
  deeds, mainly French but also Latin and other European forms. Produces a
  literal transcription with uncertain readings marked, a structured JSON
  extraction (persons, roles, ages, occupations, places, witnesses,
  signatures, marginal mentions) validated against a schema, and ready-to-
  paste GEDCOM citation fragments. Use whenever the user shares a scan, photo
  or PDF of an old handwritten record, asks to read, decipher, transcribe or
  translate an "acte", a register page or old handwriting, asks what a record
  says about a person, or wants a record turned into data for a family tree.
license: MIT
metadata:
  author: Pierre Thalamy
  category: data
---

# Record Transcriber

Turn a genealogical record into evidence someone else can check. The
output is three things that stay separate: what the document literally
says, what the agent extracted from it, and how sure each reading is.
Keeping them apart is what lets a later researcher, or the
gedcom-maintainer skill, weigh the record instead of inheriting a guess.
A transcription that silently corrects the scribe or fills a gap from the
family tree is worse than no transcription, because it looks like evidence.

## When to use

Any time a record has to be read: an image, a PDF page, a photo of a
register, or a pasted transcription that needs structuring. Hand the
result to the gedcom-maintainer skill (when available) to integrate into a
`.ged` file; this skill does not edit trees. For a printed index or a
typed database extract, extraction still applies but paleography does not.
Not for narrative translation of a whole letter or diary; for that,
translate and keep the uncertainty conventions below.

## Workflow

1. **Identify the document before reading it.** Type of act, period,
   language, jurisdiction, whether it is the original register or the
   duplicate (the *double* or *grosse*), and the exact reference the user
   or the viewer gives (archive, series, register, image or folio, act
   number). Read `references/record-types.md` for what an act of that type
   and period normally contains, so that you know what to look for and can
   say what is missing. If the image is too small or blurred to read, ask
   for a higher-resolution crop of the act instead of guessing.
2. **Read in passes, whole act each time.**
   - Layout: locate the act boundaries on the page, the margin (act
     number, names, later mentions), the signatures block, and any
     insertion marks or crossed-out text.
   - Literal transcription, line by line, keeping the original spelling,
     capitalisation, punctuation and line breaks. Expand abbreviations in
     square brackets: `Jne` becomes `J[ean]ne`. Use
     `references/paleography.md` for letterforms, abbreviations, formulas,
     numbers written in words and calendar conventions.
   - Uncertainty marks: `[?]` after a doubtful word, `[word|other]` for
     alternatives, `[...]` for illegible passages with an estimate of
     length, `[sic]` for an evident slip you are not correcting. Never
     resolve a doubtful reading from what the family tree says.
   - Extraction into `assets/transcription-schema.json`: persons with
     their roles, ages, occupations, residences, status (*feu*, *veuve*),
     signatures, the event date versus the act date, places as written and
     normalised separately, witnesses and godparents, marginal mentions as
     their own events, and a per-field confidence.
3. **Check the act against itself.** Dates in words against numerals in
   the margin; an age against the words *majeur* or *mineur* and against
   parental consent; the number of witnesses against what the period
   requires; the sex against the given name and the grammatical
   agreements. Disagreements inside the act go into `uncertainties`, not
   into a silent fix.
4. **Compare with the tree only to flag, never to correct.** If the user
   gives context (a name, a birth year, a GEDCOM xref), note where the
   record agrees or conflicts. The record still says what it says.
5. **Validate and convert.** Run
   `python3 scripts/transcription_to_gedcom.py validate act.json`, fix what
   it reports, then `python3 scripts/transcription_to_gedcom.py gedcom
   act.json` to produce GEDCOM 5.5.1 fragments with a `SOUR` citation on
   every fact, `QUAY` set from the source type, `DATA.DATE` for the act
   date and `DATA.TEXT` holding the literal transcription. Use `--map
   p1=@I12@` to bind persons to existing xrefs. `date` converts a French
   Republican date written in words to GEDCOM and Gregorian form.
6. **Deliver** the literal transcription, the JSON, the GEDCOM fragments,
   and a short list of open readings and questions for the user.

## Reading rules

- **Transcribe, do not translate or modernise.** A Latin act stays Latin
  in `literal`; give a translation in `expanded` if useful. Keep `Dupond`
  if the scribe wrote `Dupond`. Normalised forms live in their own fields.
- **Every person in the act is data.** Godparents, witnesses, declarants,
  the midwife, the officiant: their names, ages, occupations, residences
  and relationships stated ("oncle de l'épouse") are often the only
  evidence that links families. Record them all with their roles.
- **Ages are approximate unless a birth date is given.** "âgé de trente
  ans" yields a calculated birth year (`CAL`), "environ trente ans" an
  approximate one (`ABT`). The script derives these; do not round them to
  a nicer year.
- **Event date is not act date.** A birth "d'hier" is the day before the
  act; a burial is not a death. Record both dates when the act gives both
  and only the one it gives otherwise. Republican dates are transcribed as
  written and converted separately.
- **Places as written first.** "Saint Jean de Bournay" stays so in
  `as_written`; the current commune, department and country go in
  `normalised` only when you are sure. A hamlet or a street is part of the
  place, not noise.
- **Signatures are evidence.** Record who signed, who marked, who
  "declared not knowing how to sign", and whether a signature spells the
  name differently from the body of the act.
- **The margin is part of the act.** Later marginal mentions (marriage,
  divorce, death, recognition, rectification) each become a
  `marginal_mentions` entry with their own date and authority.
- **Say what you cannot read.** A confident wrong reading costs more than
  a `[...]`. When the whole act is unreadable, say so and stop.

## Output format

Three blocks, in this order:

1. The literal transcription, as a fenced block with line numbers.
2. The JSON extraction, validated by the script.
3. The GEDCOM fragments from the script, followed by open questions:
   readings to confirm, conflicts with the user's tree, records that would
   corroborate the act.

## Scripts

`scripts/transcription_to_gedcom.py` needs only Python 3.9+ and the
standard library. Subcommands: `validate`, `gedcom`, `date`, `summary`.

## Examples

**Example 1: a birth act of the year IV.** The user sends a photo of a
Lyon register. The agent identifies a civil birth act, Republican
calendar, transcribes it literally (`Jne` expanded, father's age "trente
ans", "accouchée hier"), extracts the child, father, mother, two witnesses
with occupations and residences, converts 13 vendémiaire IV to
`@#DFRENCH R@ 13 VEND 4` and 5 October 1795 for the act, 12 vendémiaire
for the birth, and emits `BIRT` with a `QUAY 3` citation, `CAL 1765` for
the father's birth, `OCCU` for each adult, and `ASSO` links for the
witnesses. See `assets/example-transcription.json`.

**Example 2: a Latin baptism with an ambiguous surname.** The scribe's
`Dupont` could be `Dupond`; the godfather signs `Dupond`. The agent keeps
`Dupon[t|d]` in the literal text, records both in `uncertainties` with the
signature as the reason the second reading is stronger, and lets the user
or gedcom-maintainer choose the canonical spelling.

**Example 3: a marriage act with a marginal note.** The margin says
"divorcé par jugement du … transcrit le …". The agent records the marriage
as the event, the divorce as a `marginal_mentions` entry with its date and
court, and emits `MARR` and `DIV` fragments with separate citations.
