---
name: genealogy-research-planner
description: >-
  Plan, prioritise and log genealogical research. From a person, couple or
  question (in a GEDCOM file, notes or a description), states the research
  question precisely, inventories what is already proven, determines which
  records exist for that place and period and where they are held or online,
  orders the searches by what each would prove, applies brick-wall strategies
  (name variants, collateral lines, neighbours and witnesses, substitute
  records for lost registers), and keeps a research log that records negative
  results so searches are not repeated. Use whenever the user asks where to
  look next, what archives or records to search, how to get past a brick wall
  or a missing ancestor, what a record would prove, how to organise or
  document their genealogy research, or wants a research plan, log or report.
license: MIT
metadata:
  author: Pierre Thalamy
  category: data
---

# Genealogy Research Planner

Make research deliberate. The first element of the Genealogical Proof
Standard is a reasonably exhaustive search, and it is the one that agents
handle worst: they stop at the first record that fits, they do not know
which records exist for a place and period, and they lose negative results
when the session ends. This skill turns a question into an ordered list of
searches, each with what a hit would prove and what a miss would mean, and
keeps a log that outlives the session. It plans and records; it does not
read images (record-transcriber) or edit trees (gedcom-maintainer).

## When to use

The user is stuck, is starting on a new person or branch, asks which
archive or website to try, or wants to know what to do next. Also when a
GEDCOM has to be audited for weak spots before deciding where to spend
time. Not for transcribing a record or updating a `.ged` file; hand those
to the neighbouring skills when available.

## Workflow

1. **State the question.** One person or couple, one fact or
   relationship, in a sentence that names the identity criteria: "Find the
   parents of Jean Dupont, tisseur, married at Lyon in 1818, aged about 23,
   said to be born at Saint-Jean-de-Bournay." Use
   `assets/research-question-template.md`. A question that does not name
   who the person must be cannot be answered by a record.
2. **Inventory what is known and how well.** Every fact with its source
   and certainty. From a GEDCOM, run
   `python3 scripts/research_log.py gaps FILE.ged --xref @I12@` (or
   without `--xref` for the whole file) to list unsourced or missing vital
   facts and generate candidate questions. Distinguish proven facts from
   inherited assumptions; the brick wall is often a wrong assumption
   upstream, not a missing record.
3. **Map the record universe.** Read `references/records-by-period.md`
   for what was being created at that place and time and what each record
   type proves, then `references/where-to-search.md` for who holds it and
   how to reach it. Check the jurisdiction history: the parish before 1792,
   the commune after, mergers and département boundaries, the diocese for
   dispensations, the notarial *étude* and *bureau d'enregistrement*, the
   recruitment office for military registers.
4. **Build the plan.** An ordered list of searches, each with: record
   type; repository and access route; the exact scope (place, years,
   register or image range); search keys including spelling variants; what
   a hit would prove and at what evidentiary level; what a miss would mean;
   priority and effort. Order from known to unknown, cheapest decisive
   record first, and pair each direct-evidence search with an indirect one
   (a marriage contract next to a marriage act, a succession table next to
   a death). Use `references/brick-wall-strategies.md` when the direct
   records are exhausted or lost.
5. **Execute and log everything.** Record each search with
   `python3 scripts/research_log.py add LOG.json ...` the moment it is
   done, including negatives with their exact scope ("naissances Lyon
   1794-1797, tables décennales et actes, vues 1-120: rien"). A negative
   without its scope is worthless; with it, it is evidence and it prevents
   the same search from being redone next month.
6. **Review and hand over.** Update the question's status (open,
   probable, proven, abandoned with reason), list conflicts, name the next
   two or three searches, and produce the report with
   `research_log.py report LOG.json`. Records found go to
   record-transcriber, conclusions to gedcom-maintainer with their
   citations and QUAY.

## Planning rules

- **Known to unknown.** Start from the best-documented event and move one
  generation or one event at a time. Jumping two generations on a name
  match is how wrong ancestors enter a tree.
- **Prove identity, not just existence.** A record with the right name is
  a candidate. The plan must include the search that would exclude the
  other candidates: siblings' baptisms, same-name burials, the tables
  décennales for the whole commune.
- **Every search has a scope and a meaning.** Before opening a register,
  write what years and places will be covered and what finding nothing
  would mean. If a miss would mean nothing, the search is badly framed.
- **Prefer the record that names the link.** A marriage act naming
  parents beats ten baptisms of possible siblings. Marriage acts,
  marriage contracts, successions and military registers are the
  link-bearing records; plan them early.
- **Widen in rings, not at random.** Adjacent communes and parishes,
  then the canton, then the routes people actually took (market town,
  seasonal migration, the spouse's parish). Distance alone is not a
  reason to search a place.
- **Research the cluster.** Godparents, witnesses, neighbours, employers
  and the spouse's family recur. When the direct line is silent, their
  records name it.
- **Spell every way it was spelled.** List the phonetic and dialectal
  variants of each surname and given name before searching an index;
  indexes fail on the variant the researcher did not type.
- **Lost registers are not dead ends.** Registres de catholicité, notarial
  records, enregistrement tables, censuses, military registers and the
  1871 Paris reconstitution replace destroyed civil records.
- **Respect access rules.** Births and marriages under 75 years and
  recent deaths' causes are closed; plan around what is open and say so.
- **Cost the plan.** Say which searches are minutes online and which
  require a reading room, an email or a fee. The user decides where to
  spend effort; the plan makes the trade-off visible.

## Deliverables

1. The research question in the template form.
2. The known-facts inventory with sources and certainty.
3. The ordered plan as a table: priority, record, repository and access,
   scope, search keys, proves, if negative, effort.
4. The research log file, updated after every search, and its report
   when the session's work is done.

## Scripts

`scripts/research_log.py` needs only Python 3.9+ and the standard library.
Subcommands: `init`, `add`, `done`, `list`, `next`, `report`, `gaps`.
The log is a JSON file the user keeps next to the GEDCOM; the report is
Markdown.

## Examples

**Example 1: parents unknown.** Jean Dupont marries at Lyon in 1818 aged
"about 23", birthplace not stated. Plan: (1) the marriage act itself for
parents, consent and witnesses; (2) the marriage contract in the
enregistrement table of the Lyon bureau, 1818; (3) if a birthplace
appears, its baptisms 1793-1797, then the parish registers, with
Dupont/Dupond/Du Pont variants; (4) the 1836 census for household
composition and any elder relative living with the couple; (5) the
military register class of 1815 for a description and birthplace. Each
step logged with scope; step 3 skipped and logged as "blocked: no
birthplace yet" if step 1 and 2 give none.

**Example 2: registers destroyed.** The commune's registers burned in
1944. Plan: registres de catholicité at the diocesan archives; the greffe
duplicate at the archives départementales, which survives independently;
tables décennales (kept at the tribunal); notarial minutes; censuses;
matricules. The user learns that the greffe copy exists before assuming
the ancestor is lost.

**Example 3: the same name twice.** Two Marie Martin baptised 1820 and
1822 in the same parish. Plan: burials 1820-1845 for either, marriages of
each, godparents compared with the known family's cluster, the 1836 and
1841 censuses for households. The plan states which finding excludes
which candidate.
