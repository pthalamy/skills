---
name: geneanet-researcher
description: >-
  Search Geneanet for everything public trees, collaborative indexes
  (relevés collaboratifs), association indexes and cemetery surveys say
  about given people, and record for every fact the source the tree or
  index gives, verbatim (act type, act number, cote, archive, view or image
  number, viewer link), flagging facts with no stated source. Works with a
  URL-fetch tool alone when shell network access is blocked; knows
  Geneanet's URL patterns and search parameters, which pages robots.txt
  refuses, how to phrase extraction prompts so a summarising fetcher copies
  text verbatim, and how to tell copied trees from independent evidence.
  Produces a validated findings file, a report and research-log entries.
  Use whenever the user asks what Geneanet or other researchers' trees say
  about an ancestor, wants leads or sources from Geneanet, pastes a
  gw.geneanet.org or geneanet.org link, or asks to search public trees or
  relevés for a person, couple or family.
license: MIT
metadata:
  author: Pierre Thalamy
  category: genealogy
---

# Geneanet Researcher

Harvest what Geneanet knows about a person and, above all, where each
piece came from. A public tree is not evidence: it is someone else's
conclusion. Its value lies in the source it cites, because a cited act
with its cote and view number is a record the user can open and read.
Collaborative indexes are derivative too, but they were made from real
registers one act at a time, so they usually outrank trees. The job is
therefore not "find the ancestor on Geneanet" but "list every claim,
the exact words of the source behind it, and which claims are just
copies of one another", so the user knows which records to open next.

## When to use

Any search of Geneanet's public content for named people: trees
(`gw.geneanet.org`), the search engine, relevés collaboratifs,
association indexes shown in search results, cemetery surveys. Not for
reading an archive image (hand it to record-transcriber), editing a
`.ged` file (gedcom-maintainer), or deciding which archive to search
beyond Geneanet (genealogy-research-planner); this skill feeds all three
when they are available.

## Access rules

- **Fetch tool only.** Geneanet pages are read with the agent's
  URL-fetch tool (WebFetch or its equivalent). When shell network access
  (curl, wget, Python HTTP libraries) is blocked, do not try it, and
  never route around a refusal through proxies, caches, archives or
  mirrors. The skill's script builds URLs and processes results offline;
  it makes no network calls.
- **robots.txt is binding.** The fetch tool refuses URLs that Geneanet's
  robots.txt disallows. On `gw.geneanet.org` that includes every URL
  with an `m=` parameter (ascendance `m=A`, descendance `m=D`, search
  `m=S`) except the surname and given-name indexes `m=N` and `m=P`. On
  `www.geneanet.org` it includes `/cercles/` (association indexes) and
  `/archives/ouvrages/`. Walk a tree person by person through the family
  links instead, and record association hits from the search result
  snippet. Check any URL first with `python3 scripts/geneanet_findings.py
  check URL`.
- **Login, Premium and masked people** are not visible. Say so in the
  finding (`not-visible`) instead of guessing what the page would show.
  A hit seen only in the search results, whose page was not or could not
  be read, is `snippet-only`.
- **Pace the requests.** Fetch what the question needs, not whole trees.
  If pages start returning errors or a challenge page, stop and report.

## The fetcher summarises

A URL-fetch tool usually returns a small model's answer to a prompt
about the page, not the page itself. Left to a general prompt it
paraphrases sources ("Birth and marriage records" for a line that
names a cote and a view), drops the inline sources attached to events,
and can even claim a search filter was applied when the site ignored
it. Read `references/fetch-prompts.md` before the first fetch and use its
templates. The essentials:

- One job per fetch: facts and family links in one call, the source
  text in another, never "summarise this page".
- Ask for a character-for-character copy inside a code block, in plain
  text with the page's French labels, and a sentinel answer when the
  section is absent ("NO SOURCES HEADING"). The fetcher still adds
  markdown (headings, bullets, `*italics*`); strip what it added, keep
  the words.
- Start an unfamiliar tree page with the headings prompt. Many GeneWeb
  trees put the sources inside the `Événements` block, not under a
  `Sources` heading; a page is unsourced only when neither block exists
  or the dedicated prompts for the blocks it has come back empty.
- Ask for absolute URLs, never "the link".
- Verify a search filter by the result count and the results, not by the
  page's description of itself.

## Workflow

1. **Fix the identity criteria.** For each target person: surname and its
   spellings, given names, approximate dates, places, spouse, parents,
   and the GEDCOM xref if there is one. Without criteria, a name match is
   just a name. Create the findings file:
   `python3 scripts/geneanet_findings.py init FINDINGS.json --subject "…"`
   and add the persons (see `assets/findings-example.json`).
2. **Run the search engine** for each spelling:
   `python3 scripts/geneanet_findings.py url search --nom DUBOIS --prenom
   "Jeanne Rosalie" --place Bresles --from 1850 --to 1890`. `go=1` is
   required and the script always adds it. Page through with `--page`
   (`size` up to 100). The place filter drops trees that lack that
   place (a tree with only the death elsewhere), so for a rare name run
   the search without a place too. Record every relevant hit as a lead,
   with its type label exactly as shown ("Arbre de …", "Archives : Oise,
   naissances", cemetery), and every search in `searches` with its scope
   and result, including negatives. A snippet lists places together, not
   per event, and shows one row per union: read the page before
   recording which place goes with which event. Read
   `references/geneanet-pages.md` for the parameters and page anatomy.
3. **Read the indexes first.** For each `releves-collaboratifs/view/`
   hit, copy the record fields verbatim, then the project block (title,
   period, depositor, licence) and the project page for any statement of
   what was indexed. For association hits under `/cercles/`, which cannot
   be fetched, the search snippet is the finding (`snippet-only`): record
   it as shown with the collection code from its URL. For cemetery
   surveys, record the names and dates as shown with the photo reference.
4. **Read each tree page** in up to four fetches: the section headings;
   facts and family links; the `Sources` and `Notes` sections verbatim
   when the headings show them; the text attached to each event verbatim
   (witnesses, declarants, inline sources, archive viewer links) when
   there is an `Événements` block. Follow parent, spouse and child links
   inside the same tree when the question extends to them. Use `oc=` to
   separate homonyms (`url person --oc 2`), and the tree's surname index
   (`url names`) when a constructed URL misses.
5. **Record one finding per fact per page**, never per person: the fact
   as shown, the origin (kind, URL, tree owner, access date), where on
   the page the source was found, the source verbatim, and its status:
   `record` (names an act precisely enough to open it), `repository`
   (names only an archive or collection), `derivative` (cites another
   tree, an index, a book, a person), `unsourced` (checked, nothing
   stated), `not-visible` (Premium, login, masked), `snippet-only` (seen
   in search results only). A fact with no source still goes in the
   file, flagged. Give dated facts a normalised `date` in GEDCOM form
   (`4 MAY 1861`, `1862`, `BET 1825 AND 1875`) and `place` (commune
   first) next to `as_shown`, and marriages the `spouse` as shown, so
   the report can find conflicts and say which act to open. Then run
   `python3 scripts/geneanet_findings.py refs FINDINGS.json --write` to
   pull cotes, views, act numbers, archives and URLs out of the verbatim
   text into `record_ref`, and check what it extracted.
6. **Separate copies from evidence.** GeneWeb formats every tree the
   same way, so identical layout proves nothing; identical rare
   spellings, identical errors, an identical source line, or a source
   that names another tree ("Arbre Geneanet X") mean one source copied,
   not corroboration. Mark visible copies with `copy_of`. Count distinct
   cited records, not trees. Read
   `references/source-evaluation.md` for the classification rules, the
   usual shapes of GeneWeb source lines and the QUAY each kind supports.
7. **Validate, report, hand over.**
   `python3 scripts/geneanet_findings.py validate FINDINGS.json`, then
   `report FINDINGS.json --out REPORT.md`. The report lists, per person,
   every fact with its verbatim source and status, the conflicts (dates,
   places, names), repetition and copies, the unsourced facts and the
   records to open. `log FINDINGS.json LOG.json --question Q1` appends
   the searches and one pending search per act to open to the
   genealogy-research-planner log (create the question first with
   `research_log.py question LOG.json add "…"`). Records the user then
   opens go to record-transcriber; conclusions go to gedcom-maintainer.

## Recording rules

- **Verbatim means verbatim.** Keep the tree's spelling, capitals,
  punctuation, typos and its own mistakes ("acte de naissance" as the
  source of a marriage). Flag an internal inconsistency in `remarks`;
  do not correct it. Normalised dates and places go in their own fields.
- **Source per fact.** A tree's `Sources` block is split by label
  ("Naissance:", "Union:", "Décès:", "Personne:", "Famille:"); an inline
  event source belongs to that event only. A `Personne:` source is a
  source for the person as a whole, so record it on each fact it could
  support and say so.
- **Every hit has an address.** Absolute URL, tree owner, `oc` if any,
  access date. A finding the user cannot reopen is gossip.
- **Negative results count.** "Search engine, DUBOIS Jeanne Rosalie,
  Bresles 1850-1890, 1 page, 14 hits, no relevé" is a result; record it
  with its scope in `searches`.
- **Masked and living people stay out.** Do not try to unmask a
  `Personne masquée` or copy details of people who may be alive.
- **Contributors own their work.** Record the depositor and licence of
  a relevé and the tree owner; the report cites them.

## Parallel research

When the targets are many people or branches and the agent can delegate
to sub-agents, give each one person or couple and the brief in
`assets/subagent-brief.md`, which carries the access rules, the prompt
templates and the finding format. Merge their findings into one file
and validate it; duplicates across sub-agents are resolved in step 6.

## Output

1. The findings file (`FINDINGS.json`), validated.
2. The Markdown report, whose "Records to open" section is the next
   step of the research.
3. When a research log is in use, its new entries.
4. In the reply: a short synthesis per person (what is well sourced,
   what conflicts, what is only copied) and the three to five records
   most worth opening, each with its verbatim reference.

## Scripts

`scripts/geneanet_findings.py` needs only Python 3.9+ and the standard
library, and never touches the network. Subcommands: `url` (search,
person, names, releve), `check` (robots.txt snapshot), `init`,
`validate`, `refs`, `report`, `log`.

## Examples

**Example 1: a birth with an inline source.** A tree shows Jeanne
Rosalie DUBOIS born 4 May 1861 at Bresles with no `Sources` heading but
an `Événements` block. The event-level prompt returns "Sources: …
Archives Départementales de l'Oise - Registre Bresles NMD années
1860-1870 côte archives 3E999/4 vue 52/300 - Original". The finding is
`record`, `refs` extracts cote `3E999/4` and view `52/300`, and the
report lists "birth, Bresles, Oise, 4 MAY 1861: … cote 3E999/4; view
52/300" under "Records to open". (Fictional values; the full case is
`assets/findings-example.json`.)

**Example 2: five trees, one source.** Five trees give the same parents
with the same misspelled mother's name and no source; one gives an
inline marriage source. The report shows one cited record and five
trees repeating the parents without a source, not five confirmations.

**Example 3: an association index.** The search engine lists "Archives :
Oise, naissances … Bresles" with a `/cercles/` URL. `check` confirms the
page is refused, so the snippet is recorded as a `cercle` finding with
status `snippet-only` and date `BET 1825 AND 1875`, and the plan is to
open the Bresles birth register for the years the snippet brackets.
