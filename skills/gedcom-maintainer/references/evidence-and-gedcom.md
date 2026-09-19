# Evidence, proof and genealogical reasoning

How to decide whether a claim is strong enough to enter the tree, how to
grade it, and what to do when records disagree. Read this before adding a
relationship, resolving a conflict, or merging two records.

## Contents

- [The Genealogical Proof Standard](#the-genealogical-proof-standard)
- [Classifying sources, information and evidence](#classifying-sources-information-and-evidence)
- [Source hierarchy](#source-hierarchy)
- [Mapping evidence to GEDCOM QUAY](#mapping-evidence-to-gedcom-quay)
- [Identity: is this the same person?](#identity-is-this-the-same-person)
- [Chronological plausibility](#chronological-plausibility)
- [Conflicts](#conflicts)
- [Uncertain transcriptions](#uncertain-transcriptions)
- [Names and spelling](#names-and-spelling)
- [Merging duplicate records](#merging-duplicate-records)
- [Research notes](#research-notes)
- [Living people and privacy](#living-people-and-privacy)

## The Genealogical Proof Standard

Professional genealogy measures a conclusion against five elements, known
as the Genealogical Proof Standard (GPS). A relationship or identity is
"proven" only when all five hold:

1. **Reasonably exhaustive research**: the records that could bear on the
   question have been sought, not just the first one that fits.
2. **Complete and accurate citations**: every piece of evidence can be
   found again by someone else.
3. **Analysis and correlation**: each record has been weighed for
   reliability and compared with the others.
4. **Resolution of conflicting evidence**: disagreements are explained,
   not ignored.
5. **A soundly reasoned, written conclusion**: the argument is recorded,
   not only the result.

An agent cannot do exhaustive research in one session, so most edits will
not reach "proven". That is fine. The point is to be honest about where a
claim stands. The three working levels the skill uses map onto the GPS:

| Level | Meaning | What the agent does |
| ----- | ------- | ------------------- |
| **Documented** | Directly supported by an original record cited precisely (elements 2 and 3 satisfied for that fact). | Enter the fact with its citation and `QUAY 3` (or `2` for a derivative copy). |
| **Corroborated** | Two or more independent records point the same way, or a tree exposes a checkable source; conflicts unresolved or search incomplete (elements 1 or 4 missing). | Enter the fact, cite each record, `QUAY 2` or `1`, note what is still missing. |
| **Hypothesis** | Plausible identification or link without a record that names it. | Do not create the link. Record the hypothesis and the record that would test it in a `NOTE`. |

## Classifying sources, information and evidence

Genealogists separate three things that are easy to blur. Apply all three
to every record before deciding what it proves.

**Source** (the container):

- **Original**: the first written form, or an image of it. A parish register
  page, a civil act, a census sheet, a notarial deed.
- **Derivative**: copied, abstracted, indexed or transcribed from an original.
  A published index, a tables décennales entry, a transcription on a
  website, a database extract. Each copying step can introduce error.
- **Authored**: a narrative someone compiled from other sources. A family
  history book, a genealogy site's tree, a Wikipedia article.

**Information** (each statement inside the source):

- **Primary**: from someone with first-hand knowledge, recorded close to the
  event. The midwife or father declaring a birth; the couple's ages given at
  their own marriage.
- **Secondary**: reported second-hand or long after. An informant giving a
  deceased person's birthplace and parents on a death act; a grandchild's
  recollection.
- **Indeterminable**: the informant is unknown.

A single record can carry both kinds. A death act is primary for the date
and place of death and usually secondary for the deceased's birth date and
parents' names.

**Evidence** (how the information answers the question):

- **Direct**: the record states the answer. "Son of Jean Dupont and Marie
  Martin."
- **Indirect**: the answer must be inferred from several facts. A godfather's
  name, a shared unusual surname, an heir listed in a succession.
- **Negative**: the absence of an expected record is itself informative. No
  burial in the parish where the family lived in the years the death should
  have occurred.

Indirect and negative evidence can be strong when several pieces agree, but
each piece alone is a hypothesis. Never write an indirect inference into the
tree as if it were a direct statement.

## Source hierarchy

Prefer, in descending order of evidentiary weight:

1. A contemporaneous original civil or church register act (image seen).
2. A certified or archival copy, with the repository and image/page reference.
3. A later original act that explicitly names the person or parents (a
   marriage act naming the bride's parents; a death act naming the spouse).
4. An independently created census, military, notarial, cemetery, tax or
   institutional record.
5. An index or transcription (tables décennales, online index, book).
6. A public genealogy tree with visible source references.
7. An unsourced tree, name-match search result, or user assertion.

The hierarchy is a starting point, not a verdict. An original act can concern
the wrong person; a well-sourced tree can be right. Weigh the source with
the information and evidence classification above, then check identity.

## Mapping evidence to GEDCOM QUAY

GEDCOM's `QUAY` tag on a citation stores the certainty assessment so that
software can display it. Use it on every citation the agent writes:

| QUAY | Standard meaning | Use for |
| ---- | ---------------- | ------- |
| 3 | Direct and primary evidence, or dominance of the evidence | Original act, image seen, names the person directly |
| 2 | Secondary evidence, data officially recorded sometime after the event | Certified copy, later act naming the fact second-hand, index checked against the image |
| 1 | Questionable reliability (interviews, oral genealogy, potential bias) | Unverified index, sourced tree, family paper |
| 0 | Unreliable or estimated | Unsourced tree, inference from a name match, estimate |

`QUAY` grades the citation, not the person. A person can have a `QUAY 3`
birth and a `QUAY 0` parentage.

## Identity: is this the same person?

Same-name conflation is the most common serious error in a tree. In a rural
parish there may be three Jean Dupont born within five years, and cousins
were routinely given the same names. Before linking a record to an existing
individual, check as many of these as the record allows:

- **Age or birth year** consistent within a couple of years (ages on
  marriage and death acts are often rounded or wrong by several years, so
  treat them as approximate).
- **Parents' names**, including the mother's birth surname.
- **Spouse** and marriage date.
- **Place**: parish or commune of birth, residence, and whether the move
  between them is plausible.
- **Occupation** and social status, which rarely change drastically.
- **Witnesses, godparents and declarants**: recurring names are strong
  indirect evidence; a stranger where a relative is expected is a warning.
- **Signature**: a person who signed once and marked with a cross later is
  probably two people.
- **Elimination**: has the same-name candidate been accounted for elsewhere
  (died in infancy, married someone else, buried in another parish)?

A match on name and approximate year alone is a hypothesis. Two independent
matching details beyond the name make a corroborated identification. Say
which details matched in the citation or note.

Watch for the infant-death pattern: a child dies young and the next child of
the same sex receives the same given name. The tree must then hold two
individuals, not one with a corrected birth date.

## Chronological plausibility

Rough bounds that make a link suspect and worth a second look. They are
warnings, not rules. Real exceptions exist and should be documented in a
note when confirmed.

- Mother younger than about 15 or older than about 50 at a child's birth.
- Father younger than about 15; father older than about 70 is unusual.
- Child born more than about 10 months after the father's death.
- Siblings born fewer than about 9 months apart (unless twins).
- Marriage before about 12 (canon law minimum) and rarely before 16.
- Lifespan beyond about 105 years before the 20th century.
- Baptism before birth, burial before death, a marriage after a spouse's
  death (a remarriage record probably belongs to a different person or a
  new `FAM`).
- Event dates in the future or before the record type existed (French civil
  registration begins in 1792; most parish registers do not predate the
  16th century).

`scripts/validate_gedcom.py` flags most of these mechanically.

## Conflicts

Preserve both claims when they cannot yet be resolved. Add a note that states:

- the conflicting values;
- the record supporting each value, with its classification (original or
  derivative, primary or secondary information);
- why one currently appears stronger, if applicable;
- the concrete next record or archive search that could decide it.

Rules of thumb:

- Do not overwrite a sourced value with an unsourced value.
- Do not delete the weaker claim merely because it is inconvenient.
- A single primary original outweighs several derivatives copied from it,
  but not several independent originals.
- Ages stated on marriage and death acts lose to a birth or baptism act.
- When the canonical field must hold one value, keep the currently
  best-supported one there, put the alternative in a second event with its
  own citation where the software allows (a second `BIRT` is legal GEDCOM),
  or in the note otherwise.

## Uncertain transcriptions

Transcribe legible text literally. For ambiguous handwriting, retain the
best reading and document alternatives, for example:
`Marie Louise "Lison" [Lisou?]`. Record whether the uncertainty concerns a
given name, surname, date, place, or relationship. Keep editorial
expansions separate from the literal transcription, for example
`Jne` transcribed as `J[ean]ne`.

Do not "correct" a scribe's spelling to a modern form in the transcription.
Normalise in the canonical `NAME` only, and say in the citation that the
act spells it differently.

## Names and spelling

- Before civil registration, surname spelling was fluid. `Dupont`,
  `Dupond` and `du Pont` in successive acts are not evidence of different
  people. Choose one canonical spelling for `NAME` (usually the one the
  person or their descendants signed with, or the modern form) and cite
  the variants.
- Record a woman under her birth surname throughout. A married name is a
  second `NAME` with `TYPE married` if it matters, never a replacement.
- "Dit" names, aliases and nicknames go in a second `NAME` with `TYPE aka`
  or in `NICK`, not in the canonical name.
- Do not translate given names between languages. `Giovanni` in an Italian
  act stays `Giovanni`, even if descendants used `Jean`.
- Particles and compound surnames: keep the whole surname between the
  slashes, `/de La Tour/`, and put the surname prefix in `SPFX` only when
  the software already does so.

## Merging duplicate records

Two `INDI` records are the same person only when the identity checks above
are satisfied, not when names and years line up. To merge:

1. Choose the survivor: the record with more sourced facts, or the older
   xref when equal. Never change the survivor's xref.
2. Move every `FAMS`, `FAMC`, event, `NOTE`, `SOUR`, `OBJE`, `ALIA` and custom
   tag from the duplicate onto the survivor. Deduplicate identical events;
   keep differing ones side by side with their citations.
3. Update every `FAM` that pointed to the duplicate (`HUSB`, `WIFE`, `CHIL`)
   to point to the survivor, then check that the family does not now list
   the same child twice or the same person as both spouse and child.
4. Update `ASSO` and `ALIA` pointers elsewhere.
5. Delete the duplicate record and add a `NOTE` on the survivor: "Merged
   from @I123@ on 2026-09-19; that record held … ; identity established by
   …". The old xref in the note lets the user trace it in earlier exports.
6. Run the validator. Orphaned `NOTE`/`SOUR` records left behind by the
   merge are reported as warnings.

Merging two `FAM` records follows the same pattern; the two unions must be
the same couple, not merely the same husband.

## Research notes

Use notes for provenance and reasoning, not as a substitute for a
relationship pointer. A useful note includes the record type, date, place,
archive or site, image or page, URL, access date, and what the record
proves and does not prove. Mark a proposed connection `HYPOTHESIS:` until a
source establishes it, and say what would test it. Date the note so a later
reader knows what was known when.

## Living people and privacy

- Treat anyone born within the last 100 years with no death event as
  possibly living.
- Record only what the tree needs for living people: name, relationships,
  approximate birth year if required. Leave out exact birth dates,
  addresses, occupations, health, religion and anything the person did
  not publish themselves.
- Do not import living people's details from another tree or a social
  network into a file that will be shared.
- If the software marks records private (`RESN privacy` or a custom
  `_PRIV` flag), preserve the flag and honour it when producing extracts.
