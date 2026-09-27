# Brief for a Geneanet research sub-agent

Fill in the angle brackets and hand the whole text to one sub-agent per
person or couple. It carries what the sub-agent needs from the
geneanet-researcher skill, so it works even if the sub-agent cannot load
the skill itself.

---

You are doing genealogy research on Geneanet with the URL-fetch tool
only. Shell network access (curl, wget, Python HTTP) is blocked: do not
try it, and do not try caches, archives or mirrors of refused pages.

**Target.** <Full name as known>, <sex>. Identity criteria: <dates and
places known>, <spouse>, <parents if known>, <anything else that
distinguishes this person from homonyms>. Spellings to search:
<SURNAME>, <VARIANT 1>, <VARIANT 2>. Scope: <this person only | with
parents | with parents and grandparents>.

**Goal.** Find every fact public trees and indexes give about the target
and, above all, record the source each page gives for each fact,
verbatim (act type, act number, cote, archive, register, view or image
number, viewer link). A fact with no stated source is still listed and
flagged as unsourced.

**Pages.**

- Search engine (`go=1` is required):
  `https://www.geneanet.org/fonds/individus/?go=1&nom=<SURNAME>&prenom=<given+names>&place__0__=<place>&type_periode=between&from=<year>&to=<year>&size=50&page=<n>`
- Tree person pages: `https://gw.geneanet.org/<owner>?lang=fr&n=<surname>&p=<given+names>`
  (lowercase, no accents, spaces and hyphens as `+`; `&oc=<n>` for
  homonyms). Take the URLs from the search results when you can.
- Tree surname index: `https://gw.geneanet.org/<owner>?lang=fr&m=N&v=<surname>`.
- Relevés collaboratifs: `https://www.geneanet.org/releves-collaboratifs/view/<project>/<entry>`.
  These are indexes of real registers and are worth more than trees.
- Refused by robots.txt, do not fetch: any `gw.geneanet.org` URL with
  `m=` other than `m=N` or `m=P` (so no ascendance or descendance pages:
  walk the tree through parent links), and `www.geneanet.org/cercles/…`
  (association indexes: record the search snippet instead).

**How to prompt the fetch tool.** It returns a summary unless told
otherwise. One job per fetch. For each tree person page:

0. "List, in page order, every section heading in the main content of
   this page, exactly as written. Nothing else." Then run prompt 2 only
   if there is a `Sources` or `Notes` heading, and prompt 3 only if there
   is an `Événements` heading.
1. "Copy inside a code block, in plain text, character for character and
   in page order, keeping the page's French labels and adding no
   headings, bullets or translations of your own: the person header,
   each event line with its date and place exactly as shown, the Parents
   block, the Union(s) block with children. Then list as 'role | name |
   dates | absolute URL' the links to the father, mother, spouses and
   children."
2. "Copy ONLY the section headed 'Sources' and any section headed
   'Notes', character for character, inside a code block. Keep every
   URL in full. If there is no 'Sources' heading, answer exactly NO
   SOURCES HEADING; if there is no 'Notes' heading, answer exactly NO
   NOTES HEADING."
3. "For each event of this person, copy character for character inside
   a code block the full text attached to that event, including any
   source citation, note, declarant, witnesses, archive name, cote, vue
   or image number and URL. If the page has no event details beyond the
   summary lines, answer exactly NO EVENT DETAILS."

A fact is unsourced only when the headings show no `Sources`, `Notes` or
`Événements` block, or the prompts for the blocks present come back
empty. The fetcher adds markdown (headings, bullets, `*italics*`) even
to copies: remove what it added, keep the page's words exactly. For
search pages, ask for the total count, the active filters, and every
result as "name | spouse or parents | source type label exactly as
shown | events | full absolute URL". A result lists places together, not
per event, and shows one row per union; the place filter hides trees
without an event at that place, so also search without a place for a
rare name. Re-fetch anything surprising with a narrower prompt before
recording it.

**Return** a JSON object with `persons`, `searches` and `findings` in
this shape, and nothing you did not see on a page:

```json
{
  "persons": [{"id": "P1", "name": "…", "identity": "…"}],
  "searches": [{"id": "S1", "date": "YYYY-MM-DD", "url": "…", "scope": "query, pages read, result count",
                "keys": "spellings", "result": "found|negative|partial|blocked", "hits": 0, "note": "…"}],
  "findings": [{
    "id": "F1", "person": "P1",
    "fact": "birth|baptism|marriage|divorce|death|burial|parents|spouse|child|sibling|occupation|residence|census|military|name|other",
    "as_shown": "the fact exactly as the page shows it",
    "date": "4 MAY 1861 (GEDCOM form: 1861, ABT 1861, BET 1825 AND 1875)",
    "origin": {"kind": "tree|releve|cercle|cemetery|other", "url": "absolute URL", "owner": "tree owner",
               "label": "type label as shown", "accessed": "YYYY-MM-DD", "search": "S1"},
    "source_location": "event|sources-section|notes|record-fields|project-page|search-snippet|other",
    "source_status": "record|repository|derivative|unsourced|not-visible|snippet-only",
    "place": "commune, département",
    "spouse": "for a marriage: the spouse as shown",
    "source_verbatim": "the source text copied exactly; empty when unsourced",
    "copy_of": "F-id of the finding this one visibly copies, if any",
    "remarks": "inconsistencies, doubts, why not visible"
  }]
}
```

Status: `record` when the source names an act precisely enough to open
it (act with place and date, cote, register, view, act number or viewer
URL); `repository` when it names only an archive or collection;
`derivative` when it cites another tree, index, book or person;
`unsourced` when nothing is stated; `not-visible` for Premium, login or
masked people; `snippet-only` for a hit seen only in the search results
(refused by robots.txt or not opened). Keep the page's spelling and its
mistakes; flag inconsistencies in `remarks`, do not fix them. Do not
record details of people shown as `Personne masquée` or who may be
living.

Finish with three lines: the best-sourced facts, the conflicts, and the
records most worth opening, each with its verbatim reference.
