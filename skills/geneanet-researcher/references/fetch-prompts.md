# Fetch prompts that return evidence, not summaries

A URL-fetch tool that answers a prompt about a page is a second, smaller
model standing between the page and the agent. It rewrites, shortens,
translates and occasionally invents. These templates were tested on
Geneanet in September 2026 and are built to keep it copying.

## Contents

- [Rules](#rules)
- [Failures seen in testing](#failures-seen-in-testing)
- [Templates](#templates)
  - [Section headings](#section-headings)
  - [Person facts and family links](#person-facts-and-family-links)
  - [Sources and notes sections](#sources-and-notes-sections)
  - [Event-level text](#event-level-text)
  - [Photos and documents](#photos-and-documents)
  - [Search results page](#search-results-page)
  - [Relevé entry](#relevé-entry)
  - [Relevé project page](#relevé-project-page)
  - [Relevés for a commune](#relevés-for-a-commune)
  - [Tree surname index](#tree-surname-index)
  - [Cemetery page](#cemetery-page)

## Rules

1. **One job per fetch.** A prompt that asks for facts, links and
   sources at once gets a summary of all three. Split them.
2. **Say "character for character inside a code block".** Code blocks
   are the fetcher's cue to copy rather than rewrite. Add "no paraphrase,
   no translation, no merging of lines". It still often answers in
   markdown with headings of its own, bullets and `*italics*` around
   copied lines: remove what the fetcher added before storing a
   verbatim, and keep every word, spelling and punctuation mark of the
   page.
3. **Start with the headings** on an unfamiliar tree page. They tell
   which of the sources and event prompts are worth a call.
4. **Give it a sentinel.** "If there is no such heading, answer exactly
   NO SOURCES HEADING." Without one, an absent section and a skipped
   section look the same.
5. **Ask for absolute URLs.** Otherwise it shortens them to an owner
   name or a collection code.
6. **Never accept an absence from a general prompt.** A section that a
   summary did not mention may still be there. Only a dedicated prompt
   with a sentinel establishes that a page has no source.
7. **Check the counts.** For a search, ask for the total number of
   results and the active filters, then compare with the unfiltered
   count. A filter the site ignored can still be reported as applied.
8. **Re-fetch to confirm anything surprising**, with a narrower prompt.
   A date, a cote or a name that matters to the conclusion is worth a
   second call that asks for that line only.
9. **Expect caching.** Fetch tools often cache a URL for some minutes;
   a re-fetch with a new prompt is cheap, but the page will not have
   changed.

## Failures seen in testing

- A tree's `Sources` line "Naissance, union: Archives départementales du
  Pas-de-Calais" came back from a general prompt as "Archives
  départementales du Pas-de-Calais (Birth and marriage records)".
- A tree with no `Sources` heading but an inline source on every event
  ("… côte archives 3E…/11 vue 37/310 - Original") came back from a
  general prompt with no source at all. The event-level template below
  recovered all three.
- A search with an unsupported spouse parameter returned 661,649
  results, unfiltered; the fetcher still listed "Spouse/Conjoint: <the
  surname>" among the active filters.
- The facts template came back five times out of five as reformatted
  markdown with English headings ("Events:", "Links:") instead of a code
  block; the dates, places and links were right, the layout was not the
  page's. The sources template kept its code block but wrapped a line in
  `*…*` with a bullet.
- In an unfiltered search result list, the fetcher attached the places
  listed at the end of a snippet to the wrong events.
- A profession line was returned as "Sans profession en 1789" for a
  woman born in 1863. Anything odd is re-fetched before it is recorded.

## Templates

Replace the parts in angle brackets. Keep the wording otherwise; small
changes ("summarise", "list the key facts") bring the paraphrasing back.

### Section headings

Use first on an unfamiliar tree, to know which of the next prompts
apply.

```
List, in page order, every section heading in the main content of this
page, exactly as written (for example "Parents", "Union(s) et enfant(s)",
"Frères et sœurs", "Événements", "Notes", "Sources"). Nothing else.
```

### Person facts and family links

```
Copy inside a code block, in plain text, character for character and
in page order, keeping the page's French labels and adding no headings,
bullets or translations of your own: the person header, each event line
(naissance, baptême, mariage, décès, inhumation, profession) with its
date and place exactly as shown, the Parents block, the Union(s) block
with children, and the siblings. Then list as "role | name as shown |
dates | absolute URL" the links to the father, the mother, each spouse,
each child and each sibling. Write "Personne masquée" where the page
does.
```

### Sources and notes sections

```
Copy ONLY the section of the page headed "Sources" and any section or
sub-section headed "Notes", character for character, inside a code
block. Do not paraphrase, translate, summarise or merge lines. Keep
every URL in full. If a heading exists but is empty, say so. If there
is no "Sources" heading, answer exactly NO SOURCES HEADING, and if there
is no "Notes" heading, answer exactly NO NOTES HEADING.
```

### Event-level text

```
For each event of this person (naissance, baptême, mariage, décès,
inhumation, recensement and any other), copy character for character
inside a code block the full text attached to that event, including any
source citation, note, declarant, witness list with ages, occupations
and residences, archive name, cote, vue or image number and URL
embedded in it. Also give the heading of the section where these event
details appear. If the page has no event details beyond the short
summary lines, answer exactly NO EVENT DETAILS. No paraphrase, no
translation.
```

### Photos and documents

Only when the headings show `Photos et documents d'archives`.

```
Copy inside a code block the section headed "Photos et documents
d'archives": the title, date and type of each document and any URL. If
the section shows only template placeholders such as {{ ... }} and no
actual document titles, answer exactly JS TEMPLATE ONLY.
```

### Search results page

```
1) The total number of results and the active filter chips, quoted
exactly. 2) For EVERY result on this page, one line:
name as shown | spouse or parents as shown | source type label exactly
as shown (e.g. "Arbre de X", "Archives : …") | events with dates and
places exactly as shown | the full absolute URL of the result link.
3) Whether there is a next page. Do not skip results and do not shorten
URLs.
```

For long result lists, ask for results 1 to 25 and 26 to 50 in two
fetches of the same URL.

### Relevé entry

```
Copy the main record content of this page character for character
inside a code block: the heading with the act type and place, every
field label and value exactly as displayed (Jour, Mois, Année, names,
parents, ages, professions, remarks, cote, vue, and any other), then the
project block (title, Période, Mise en ligne, Déposé par, Licence).
Then list the main-content links as "text -> absolute URL". Say which
fields are hidden behind Premium or login, if any. No paraphrase.
```

### Relevé project page

```
Copy inside a code block, character for character, the project
description: title, type, commune, period, number of acts, depositor,
licence, and ANY text that states what source was indexed (archive,
registers, cote, collection communale or greffe, tables décennales,
microfilm, website). If no source is described, answer exactly
NO SOURCE DESCRIPTION.
```

### Relevés for a commune

```
List every collaborative index (relevé) available for this commune:
title, type (naissances, mariages, décès, recensement…), period
covered, number of entries, depositor, and the absolute URL.
```

### Tree surname index

```
List every person shown on this page as "name | dates as shown |
absolute URL", in page order, without skipping any. Say if the page is
an error or empty.
```

### Cemetery page

```
Copy the main content character for character inside a code block:
cemetery name and place, each person listed with dates exactly as
shown, the photo reference, the contributor, and every link as
"text -> absolute URL". Say whether anything is hidden behind login or
Premium.
```
