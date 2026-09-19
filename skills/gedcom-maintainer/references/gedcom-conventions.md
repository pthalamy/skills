# GEDCOM conventions and worked examples

The mechanics of writing correct GEDCOM. Read this before adding a
citation, an adoption, a non-Gregorian date, or a long note, and when
the file turns out to be GEDCOM 7 or non-UTF-8.

## Contents

- [Versions and dialects](#versions-and-dialects)
- [Encoding and line endings](#encoding-and-line-endings)
- [Line syntax, continuation and length](#line-syntax-continuation-and-length)
- [Record anatomy](#record-anatomy)
- [Events: which tag](#events-which-tag)
- [Dates](#dates)
- [Places](#places)
- [Names](#names)
- [Source records and citations](#source-records-and-citations)
- [Relationships: PEDI, adoption, step and foster](#relationships-pedi-adoption-step-and-foster)
- [Custom tags](#custom-tags)
- [Worked example: adding a sourced birth](#worked-example-adding-a-sourced-birth)
- [Worked example: recording a conflict](#worked-example-recording-a-conflict)
- [Worked example: attaching a child to a family](#worked-example-attaching-a-child-to-a-family)

## Versions and dialects

Read `HEAD.GEDC.VERS` first. The bundled scripts print it.

| Version | Notes |
| ------- | ----- |
| 5.5 (1996) | Still exported by older software. No `EMAIL`, `FONE`, `ROMN`, `MAP`. |
| 5.5.1 (1999, finalised 2019) | The de facto standard. UTF-8 allowed. 255-character line limit. `CONC` and `CONT` for long text. |
| 7.0 (2021) | UTF-8 only. `CONC` removed (lines have no length limit). `@VOID@` placeholder pointer. `SNOTE` shared notes. Extension tags declared in `HEAD.SCHMA`. Enumerations are case-sensitive and upper-case (`PEDI ADOPTED`). |

Exports from Ancestry, MyHeritage, Geneanet, Heredis, Gramps, RootsMagic
and Family Tree Maker are mostly 5.5.1 with custom tags; FamilySearch and
recent Gramps and Ancestris builds can produce 7.0.

Do not convert between versions during a targeted edit. Write new lines in
the dialect the file already uses. If the user asks for a conversion, do it
as a separate whole-file step with a tool built for it, then validate.

## Encoding and line endings

`HEAD.CHAR` declares the encoding: `UTF-8`, `ANSEL`, `ANSI` (usually
Windows-1252), `ASCII` or `UNICODE` (UTF-16). The bytes must match the
declaration; the validator checks this.

- Preserve the encoding, the byte-order mark and the line-ending style
  (CRLF vs LF) of the input on a targeted edit. Many programs reject a file
  whose BOM disappeared.
- ANSEL has no standard Python codec. When editing an ANSEL file, keep
  edits ASCII-only or convert the whole file to UTF-8 deliberately (and
  change `CHAR` to `UTF-8`) with the user's agreement.
- Never mix encodings in one file. One UTF-8 accent in a Windows-1252 file
  corrupts the import.

## Line syntax, continuation and length

`LEVEL [@XREF@] TAG [VALUE]`, single spaces, no leading spaces, no tabs.
Levels increase by at most one per line. Each level-0 record other than
`HEAD` and `TRLR` has a unique xref.

Long text in 5.5.1:

- `CONT` starts a new line inside the value (a newline character).
- `CONC` continues the same line; split anywhere except immediately
  after a space, or the space is lost on import by some programs.
- Both sit one level below the tag they extend and can be repeated.
- Keep every physical line at 255 characters or fewer.

In 7.0 there is no `CONC` and no length limit; only `CONT` remains.

A literal `@` in text is written `@@` in 5.5.1 (7.0 dropped the doubling
except at the start of a value). The validator flags unescaped ones.

## Record anatomy

```
0 @I12@ INDI
1 NAME Jean Baptiste /Dupont/
2 TYPE birth
2 GIVN Jean Baptiste
2 SURN Dupont
2 NICK Baptiste
1 SEX M
1 BIRT
2 DATE 4 OCT 1795
2 PLAC Lyon, Rhône, Auvergne-Rhône-Alpes, France
2 SOUR @S3@
3 PAGE Naissances 1795, acte n° 34, vue 12/40
3 QUAY 3
1 OCCU tisseur
2 DATE 1818
1 FAMC @F5@
2 PEDI birth
1 FAMS @F9@
1 NOTE @N4@
1 CHAN
2 DATE 19 SEP 2026

0 @F9@ FAM
1 HUSB @I12@
1 WIFE @I13@
1 CHIL @I20@
1 MARR
2 DATE 15 JUN 1818
2 PLAC Lyon, Rhône, Auvergne-Rhône-Alpes, France
2 SOUR @S3@
3 PAGE Mariages 1818, acte n° 112, vue 58/210
3 QUAY 3
```

Every relationship is stored twice and both halves must agree:
`INDI.FAMS @F9@` with `FAM.HUSB`/`WIFE @I12@`, and `INDI.FAMC @F5@` with
`FAM.CHIL @I12@`. Each union is its own `FAM`; a remarriage is a new `FAM`
record, never a second `WIFE` line. Children go in the `FAM` of the couple
the record names as parents. A child of unknown father goes in a `FAM` with
only `WIFE` and `CHIL`.

Most programs update `CHAN.DATE` on the changed record. Do the same when
the file already carries `CHAN` structures.

## Events: which tag

Use the tag for the event the record actually documents. A baptism act
documents a baptism, and often states the birth date as well; enter both
when the act gives both.

| Record says | Tag | Do not use |
| ----------- | --- | ---------- |
| Born, birth act | `BIRT` | |
| Baptised (Christian) | `BAPM` (or `CHR`, which many programs treat as the same) | `BIRT` alone |
| Died, death act | `DEAT` | |
| Buried, burial act | `BURI` | `DEAT` alone |
| Married (civil or church) | `MARR` (add `TYPE civil` / `TYPE religious` if both exist) | |
| Marriage contract | `MARC` | `MARR` |
| Banns | `MARB` | `MARR` |
| Divorce | `DIV` | |
| Adopted | `ADOP` on the child, plus `FAMC`/`PEDI` | |
| Census entry | `CENS` | `RESI` |
| Occupation | `OCCU` with `DATE` and `PLAC` | a note |
| Anything else | `EVEN` with `TYPE` | a made-up tag |

A parish that records only baptisms gives you `BAPM` dated, and `BIRT`
only if the act says "né le …". When the act says "born yesterday", the
birth date is `BIRT DATE` one day earlier with the citation and a note that
it is inferred from the baptism act; do not invent a birth date from a
baptism date alone.

## Dates

Format: `[modifier] [day] MONTH year`, months as three-letter English
abbreviations, always upper-case: `4 OCT 1795`, `OCT 1795`, `1795`.

Modifiers:

| Form | Meaning |
| ---- | ------- |
| `ABT 1795` | About; the record gives an age or the date is inferred. |
| `CAL 1795` | Calculated from an age at another event. |
| `EST 1795` | Estimated by the researcher from context (children's births, etc.). |
| `BEF 1795` / `AFT 1795` | Bound from evidence (alive at a marriage, dead by a succession). |
| `BET 1795 AND 1799` | Somewhere in the range (a death between two censuses). |
| `FROM 1795 TO 1799` | A period (residence, occupation). |
| `INT 1795 (phrase)` | Interpreted from an unreadable or non-standard form. |
| `(text)` | Free text only; software cannot sort it. Last resort. |

Calendars are declared with an escape at the start of the value:

- French Republican: `@#DFRENCH R@ 12 VEND 4` (months `VEND BRUM FRIM NIVO
  PLUV VENT GERM FLOR PRAI MESS THER FRUC COMP`, year in Arabic numerals,
  not Roman). Used in France 22 Sep 1792 to 31 Dec 1805. Enter the date as
  written in the act; the scripts convert for chronology. Optionally add the
  Gregorian equivalent in a note.
- Julian: `@#DJULIAN@ 11 FEB 1699/00`. Use dual years for January to March
  dates in England and colonies before 1752, and for Julian dates in any
  country where the year began on 25 March. Most of continental Europe used
  Gregorian from 1582 to 1587; Russia until 1918; Greece until 1923.
- Hebrew: `@#DHEBREW@ 5 TSH 5555`.

Distinguish the date of the event from the date of the act. A birth act
dated 5 October recording a birth "yesterday" gives `BIRT DATE 4 OCT 1795`
and, in the citation, `DATA` / `DATE 5 OCT 1795` for when the record was
made.

Never enter a `DATE` with slashes or numeric months (`03/04/1795`) and
never guess a day or month the record does not state.

## Places

One `PLAC` string per event, comma-separated from smallest to largest
jurisdiction, matching the convention already used in the file (usually
`commune, département, région, pays` or `town, county, state, country`).
Use the name as it was at the time of the event if the file does so, or the
current name if the file does so; do not mix. Keep an unreadable or
uncertain place in a note rather than guessing a commune. `MAP` with `LATI`
and `LONG` is allowed in 5.5.1 but never required.

## Names

- `NAME Given Names /Surname/ Suffix`; the surname between slashes, empty
  slashes `//` when unknown. `GIVN` and `SURN` repeat the parts and must
  match the `NAME` line exactly.
- Several `NAME` structures are allowed. The first is the canonical one
  displayed by software. Give the others a `TYPE`: `birth`, `married`,
  `aka`, `immigrant`, `religious`.
- `NICK` for a nickname used in records ("Lison"), `NPFX`/`NSFX` for
  titles and suffixes, `SPFX` for a surname prefix only if the software
  already separates it.
- `ALIA` is a pointer to another `INDI` record that might be the same
  person, not a text alias. Do not use it for spelling variants.

## Source records and citations

Separate the source (the register or collection) from the citation (this
act on this page). One `SOUR` record per register or collection, reused by
every citation into it; one citation under each fact it supports.

```
0 @S3@ SOUR
1 TITL Lyon (Rhône). État civil, naissances, mariages, décès
1 AUTH Commune de Lyon
1 PUBL Archives municipales de Lyon, en ligne
1 REPO @R1@
1 NOTE Registers digitised; images cited by "vue" number as displayed by the viewer.

0 @R1@ REPO
1 NAME Archives municipales de Lyon
1 WWW https://www.archives-lyon.fr/
```

The citation under the event:

```
1 BIRT
2 DATE 4 OCT 1795
2 PLAC Lyon, Rhône, Auvergne-Rhône-Alpes, France
2 SOUR @S3@
3 PAGE Naissances 1795 (an IV), acte n° 34, vue 12/40, https://… (consulté le 19 sept. 2026)
3 QUAY 3
3 DATA
4 DATE 13 VEND 4
4 TEXT Le treize vendémiaire an quatre … est comparu Pierre Dupont, tisseur, … lequel a déclaré que Marie Louise Martin son épouse est accouchée hier d'un enfant mâle …
3 NOTE Age of the father given as 30, consistent with baptism 1765 (@S7@).
3 OBJE @O2@
```

- `PAGE` holds everything needed to find the act again: register, year,
  act number, image or folio, permalink, access date. Be generous; this is
  what the Genealogical Proof Standard means by a complete citation.
- `QUAY` grades the citation (see `evidence-and-gedcom.md`).
- `DATA.DATE` is the date the record was made; `DATA.TEXT` is the literal
  transcription, uncertain readings in `[?]`.
- `OBJE` links an image file if the file already manages media.
- An inline citation (`2 SOUR Some text`) with no record is legal but
  invisible to most reports. Prefer a `SOUR` record.
- A public tree cited as corroboration is a `SOUR` record whose `TITL`
  names the site and tree owner, cited with `QUAY 1` or `0`, and whose
  `PAGE` says which underlying record the tree shows.

## Relationships: PEDI, adoption, step and foster

`FAMC` links a child to a family. `PEDI` under it says what kind of link:

```
1 FAMC @F5@
2 PEDI birth
1 FAMC @F8@
2 PEDI adopted
1 ADOP
2 DATE 12 MAR 1825
2 FAMC @F8@
3 ADOP BOTH
2 SOUR @S9@
```

Values in 5.5.1: `birth`, `adopted`, `foster`, `sealing`; in 7.0 the same
words upper-case plus `OTHER`. A child with two `FAMC` links where one is
`birth` and the other `adopted` is the correct way to record an adoption;
two `birth` links is a conflict the validator flags.

Step-relationships need no explicit link: the step-parent's `FAM` with the
biological parent exists, and the child is `CHIL` only of the biological
family. Explain in a `NOTE` if the child was raised in the other household.

A presumed but unproven father is not a `HUSB`. Leave the `FAM` with `WIFE`
and `CHIL` only and record the hypothesis in a note on the child.

Godparents, witnesses and declarants that matter to identity go in `ASSO`
with a `RELA` (5.5.1) or `ROLE` (7.0), pointing to their `INDI` record, or
in the citation's `NOTE` if they have no record.

## Custom tags

Tags starting with `_` are vendor extensions: `_UID`, `_FREL`/`_MREL`
(relationship to father/mother in some programs), `_MILT`, `_SHAR`,
`_PRIV`, `_FSFTID`, `_APID`. Preserve them exactly. Do not invent new ones;
use `EVEN`/`TYPE` or a `NOTE` instead. `scripts/inspect_gedcom.py summary`
lists the custom tags present.

## Worked example: adding a sourced birth

The user supplies a birth act image for @I12@ Jean Baptiste Dupont, whose
record shows `BIRT DATE ABT 1795` with no source. The act (Lyon, 13
vendémiaire IV, acte 34) says he was born the previous day to Pierre Dupont,
tisseur, and Marie Louise Martin.

Before:

```
0 @I12@ INDI
1 NAME Jean Baptiste /Dupont/
1 SEX M
1 BIRT
2 DATE ABT 1795
1 FAMC @F5@
```

After (5.5.1 file, existing `@S3@` register record reused):

```
0 @I12@ INDI
1 NAME Jean Baptiste /Dupont/
1 SEX M
1 BIRT
2 DATE @#DFRENCH R@ 12 VEND 4
2 PLAC Lyon, Rhône, Auvergne-Rhône-Alpes, France
2 SOUR @S3@
3 PAGE Naissances an IV, acte n° 34, vue 12/40, https://… (consulté le 19 sept. 2026)
3 QUAY 3
3 DATA
4 DATE @#DFRENCH R@ 13 VEND 4
4 TEXT … est comparu Pierre Dupont, tisseur, âgé de trente ans, … Marie Louise Martin son épouse … accouchée hier …
1 FAMC @F5@
```

Also check that `@F5@` has `HUSB` Pierre Dupont and `WIFE` Marie Louise
Martin. If it does, the act corroborates the existing parentage; add the
same citation with `QUAY 3` to the `FAM` (or to the `FAMC` link) so the
relationship, not only the birth, is sourced. If the parents in `@F5@`
differ from the act, that is a conflict: see the next example.

## Worked example: recording a conflict

The tree has `@I12@ BIRT DATE 2 OCT 1795` sourced to an online index. The
act image says 12 vendémiaire IV, which is 4 October 1795. The index is a
derivative; the act is an original. Update the canonical date and keep the
trail:

```
1 BIRT
2 DATE @#DFRENCH R@ 12 VEND 4
2 SOUR @S3@
3 PAGE Naissances an IV, acte n° 34, vue 12/40
3 QUAY 3
2 SOUR @S11@
3 PAGE Index entry "DUPONT Jean Baptiste, 02/10/1795"
3 QUAY 1
2 NOTE Conflict: index @S11@ gives 2 OCT 1795; original act @S3@ gives 12 vendémiaire IV
3 CONC  (= 4 OCT 1795). Original preferred; index date probably a conversion error.
3 CONT Checked 2026-09-19.
```

When the two claims are of equal weight (two originals disagreeing), keep
the existing canonical value, add the second as a second `BIRT` event with
its own citation if the software tolerates it, and write the note with the
next record that could decide it (for example the marriage act, which
states an age).

## Worked example: attaching a child to a family

A marriage act for @I20@ Louise Dupont names her parents as Jean Baptiste
Dupont and Marie Louise Martin, who are `@I12@` and `@I13@`, spouses in
`@F9@`. Louise currently has no `FAMC`.

```
0 @I20@ INDI
…
1 FAMC @F9@
2 PEDI birth
2 SOUR @S3@
3 PAGE Mariages 1842, acte n° 57, vue 30/98
3 QUAY 2
3 NOTE Parents named on the bride's marriage act; secondary information for the parentage, primary for the marriage.

0 @F9@ FAM
1 HUSB @I12@
1 WIFE @I13@
1 CHIL @I20@
```

Both halves are written: `FAMC` on the child and `CHIL` on the family. The
citation says the parentage comes from a later act (`QUAY 2`); when her
birth act is found, add it with `QUAY 3`. If `@F9@` already had a daughter
named Louise born about the same year, do not add a second one: check
whether it is the same person (identity checklist) or an infant death
followed by a namesake.
