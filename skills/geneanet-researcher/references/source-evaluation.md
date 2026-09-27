# Weighing what Geneanet says

How to classify the source statement behind each fact, how to spot
copies, what each kind of finding can support in a tree, and how to turn
a reference into a record the user can open.

## Contents

- [Source status](#source-status)
- [Reading a tree's source line](#reading-a-trees-source-line)
- [Indexes are derivative, and still worth more](#indexes-are-derivative-and-still-worth-more)
- [Copies are not corroboration](#copies-are-not-corroboration)
- [Conflicts](#conflicts)
- [What a finding can support](#what-a-finding-can-support)
- [From reference to record](#from-reference-to-record)

## Source status

Every finding gets exactly one status, describing what the page says
about where the fact comes from, not whether the fact is true.

| Status | The page… | Example |
| ------ | --------- | ------- |
| `record` | names one act precisely enough to open it: act type with place and date, or a cote, register, view, folio or act number, or a viewer URL | "Registre Bresles NMD années 1860-1870 côte archives 3E999/4 vue 52/300"; a relevé entry with commune, act type and date |
| `repository` | names only an archive, a series or a record type, with nothing that locates the act | "Archives départementales du Pas-de-Calais"; "état civil"; "AD62" |
| `derivative` | cites another tree, an index, a book, a website, a cousin or "Geneanet" | "arbre de X"; "relevé du cercle"; "Filae"; "d'après M. Y" |
| `unsourced` | states no source, established by the dedicated sources prompt and the event-level prompt | a fact line with neither |
| `not-visible` | was read but hides it: Premium, login, masked person | a padlocked field; `Personne masquée` |
| `snippet-only` | was not read: the fact comes from a search result line only, because the page is refused (robots.txt) or was not opened | a `/cercles/` hit; a tree seen only in the result list |

Borderline cases:

- "Archives Oise, image 37" names a repository and an image but not the
  register; with the date and place of the event it usually locates the
  act, so `record`, with the missing register noted in `remarks`.
- "Archives départementales du Pas-de-Calais" on a birth given with its
  full date and commune is `repository`: the line itself locates
  nothing, but the event does. The report lists such findings under
  "act to find by its date and place", after the cited records, and
  `log` adds them as pending searches; give them `date` and `place`.
- "5h00-acte 44 Sources: Archives départementales du Pas-de-Calais"
  inside an event is `record`: the act number with the event's date and
  commune locates the act.
- A viewer URL alone in `Notes` ("Naissance: https://…/registre.html?id=…")
  is `record`: it opens the register, even if not at the right page.
- "Original", "Copie intégrale", "Extrait" at the end of a GeneWeb
  source line is the owner's statement of what they saw. Record it; do
  not rely on it.
- A `Personne:` source supports the person generally. Attach it to each
  fact it could cover and say in `remarks` that it is not event-specific.

## Reading a tree's source line

GeneWeb source lines are free text, so their shapes vary. Pull these
elements out (the script's `refs` does most of it) and check them:

| Element | Shapes seen |
| ------- | ----------- |
| Archive | "Archives Départementales de l'Oise", "AD 60", "AD60", "Archives Oise", "Mairie de Clermont", "Archives municipales de …" |
| Register | "Registre Bresles NMD années 1860-1870", "BMS 1740-1760", "tables décennales 1853-1862" |
| Cote | "côte archives 3E999/4", "cote 5 MI 1234", "3E 999/4", "5 MIR 048/5", "EDEPOT 12/GG3" |
| View | "vue 37/310", "vues 163-164-165/253", "image 37", "images 163, 164 et 165", "p. 12" |
| Act number | "acte n° 23", "n°23", "acte 52" |
| Link | archive viewer URLs, often in `Notes`; the archive's home page is not a link to the act |
| Nature | "Original", "Copie intégrale", "Extrait", "Relevé", "Transcription" |

Check the line against the fact: a marriage whose only source reads
"… acte de naissance" is a template left unchanged or a slip; the view
number may still be right. Flag it in `remarks`; the report lists these
as inconsistencies. Do not fix the tree's text.

## Indexes are derivative, and still worth more

A relevé collaboratif or an association index was made by someone
reading the register, act by act, for a whole commune and period. That
makes it derivative (an index, not the act) and usually incomplete in
its fields (often only date and names), but systematic: the entry
exists because the act exists, and the absence of an entry in a covered
period is meaningful. A tree, by contrast, is a conclusion that may have
been built on a name match.

So, for the same fact: an index entry beats an unsourced tree; a tree
citing the act with cote and view beats an index entry for precision,
because it tells where to look. Both point to the same next step: open
the act.

Cemetery surveys and stones are derivative too, and dates on stones are
often wrong by a year or reduced to years. They locate a death, they do
not date it.

## Copies are not corroboration

Trees copy one another, including their mistakes. GeneWeb renders
every tree with the same templates, so identical layout ("Née le 4 mai
1861 (samedi) - Bresles, Oise, …") only means identical data. Signs of a
copy:

- a source that names another tree ("Arbre Geneanet X", a
  `gw.geneanet.org` link): `refs` puts it in `record_ref.cites`;
- identical rare spellings, the same misspelling, the same wrong code
  (an INSEE number, a postcode) or the same unusual place format;
- the same `Sources` text, or the same inline source line with the same
  typo;
- a date given only as a year in several trees that all derive from one
  that had the full date, or the reverse;
- hits that appear with several `oc` values in the same tree.

Mark the later or less complete one with `copy_of` pointing to the
fuller one when the direction is clear; when it is not, mark all but one
and say so in `remarks`. The report counts distinct cited records, not
trees, and lists facts that several trees give without a source as
repetition, not as evidence. Five trees without a source and one
tree citing the act are one piece of evidence, the act, plus five
opinions.

Parents given by many unsourced trees are the classic trap: the first
tree may have picked the wrong same-name couple, and everyone after
copied it.

## Conflicts

Record every value as it is shown, each in its own finding. Two trees
giving 1863 and 1864 for a birth are a conflict even if one looks like a
rounding; the report lists them. Common causes worth naming in
`remarks`: a baptism date given as a birth, a birth year computed from
an age at death, two homonyms merged, a Republican date converted
wrongly. The resolution is the act, not a vote.

## What a finding can support

Following gedcom-maintainer's scale, a Geneanet finding supports at
most:

| Finding | QUAY | Use in the tree |
| ------- | ---- | --------------- |
| Tree, `unsourced` or `derivative`; any `snippet-only` or `not-visible` finding | 0 | A lead or a hypothesis in a note; not a link |
| Tree, `record` or `repository` | 1 | A lead with a checkable source; open the record before entering the fact as documented |
| Relevé or association index entry, unverified | 1 | A located act to open; enough to plan, not to conclude |
| Index entry checked against the act image | 2 | Derivative confirmed by the original |
| The act itself, read by the user | 3 | Through record-transcriber, not this skill |

The script prints the suggested QUAY per finding in the report. None of
these justify creating a parent-child link on their own.

## From reference to record

For each `record` finding the next step is to open the act:

1. The archive: from the source line or the place (the archives
   départementales of the commune's département, or the city archives
   for large cities).
2. The register: from the cote and the year range, or from the act type
   and the year in the archive's online viewer for the commune.
3. The page: from the view or image number, remembering that numbering
   can differ between the archive's viewer and another site's copy.
4. A viewer URL in the tree's notes often opens the register directly.

State in the report exactly what the user should open ("AD Oise, Bresles
NMD 1860-1870, cote 3E999/4, vue 52"), and log it as a pending search.
The act, once read with record-transcriber, replaces the Geneanet finding
as the citation.
