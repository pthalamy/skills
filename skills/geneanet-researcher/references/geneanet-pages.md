# Geneanet pages: URLs, parameters and anatomy

What each kind of Geneanet page looks like through a URL-fetch tool, how
to build its URL, and what it can and cannot tell you. Observed in
September 2026; Geneanet changes its site, so when a pattern stops
working, fall back on the links the pages themselves give.

## Contents

- [robots.txt: what cannot be fetched](#robotstxt-what-cannot-be-fetched)
- [Search engine](#search-engine)
- [Tree person pages (GeneWeb)](#tree-person-pages-geneweb)
- [Tree indexes](#tree-indexes)
- [Relevés collaboratifs](#relevés-collaboratifs)
- [Association indexes (cercles)](#association-indexes-cercles)
- [Cemetery surveys](#cemetery-surveys)
- [Login, Premium, masked people](#login-premium-masked-people)

## robots.txt: what cannot be fetched

A fetch tool that honours robots.txt returns an error such as
`ROBOTS_DISALLOWED` for these; do not retry them under another form.
`scripts/geneanet_findings.py check URL` applies the same rules from a
snapshot.

`gw.geneanet.org` (the trees):

| Rule | Consequence |
| ---- | ----------- |
| `Disallow: /*m=` | Any URL with an `m=` parameter: ascendance `m=A`, descendance `m=D`, in-tree search `m=S`, relationship `m=R`… |
| `Allow: /*m=N`, `Allow: /*m=P` | Surname index `m=N&v=<surname>` and given-name index `m=P&v=<given>` stay readable |
| `Disallow: /*m=NG` | The tree-wide name search is refused |
| `Disallow: /*type=graph`, `links`, `carto`, `stats` | Graph, link, map and statistics views |
| `Disallow: /*templ=`, `/*color=`, `/*carto=`, `/*ei=`, `/*&dag=`, `/*&s1=`… | Display variants |
| `Disallow: /pdf/`, `/treeprint/` | Printable exports |

`www.geneanet.org`: `/cercles/` (association indexes), `/archives/ouvrages/`
and `/archives/livres/` (library), `/fonds/individus/niveaux/`,
`/fonds/redirect/`, `/sys/sources/`, `/variantes/noms/`, `/compare/`,
`/mon_compte/`, among others. The search engine (`/fonds/individus/`),
relevés collaboratifs and cemetery pages are readable.

Consequence for trees: there is no way to fetch an ascendance in one
page. Walk it person by person through the parent links of each person
page; each link is an ordinary `?lang=fr&n=…&p=…` URL.

## Search engine

```
https://www.geneanet.org/fonds/individus/?go=1&nom=<SURNAME>&prenom=<given names>&place__0__=<place>&type_periode=between&from=<year>&to=<year>&size=50&page=<n>
```

| Parameter | Meaning | Notes |
| --------- | ------- | ----- |
| `go=1` | Run the search | Required; without it the page is an empty form |
| `nom` | Surname | Case-insensitive |
| `prenom` | Given names | Matches any of the person's given names: `Rosalie` finds "Jeanne Rosalie" |
| `place__0__` | Place | Commune name; filters on any event place |
| `type_periode=between`, `from`, `to` | Period | Years; applied to any event |
| `with_variantes_nom=1` | Surname variants | Geneanet's variant list is incomplete; search each spelling separately as well |
| `size` | Results per page | 10, 20, 30, 40, 50 or 100 |
| `page` | Page number | 1-based |

Other parameters exist in the site's forms but were not verified; a
spouse-name parameter tried in testing was silently ignored while the
fetcher reported it as applied. Check any new parameter by the total
result count and the results themselves.

Each result shows the name, the spouse or parents, a type label and the
events with dates and places, then links to the page. The type label is
the most important field; copy it exactly:

| Label as shown | Target URL | Nature |
| -------------- | ---------- | ------ |
| `Arbre de <owner>` | `https://gw.geneanet.org/<owner>?lang=fr&n=…&p=…[&oc=…]` | A user tree |
| `Archives : Mariages (Oise, France)` and similar, linking to `releves-collaboratifs/view/` | `https://www.geneanet.org/releves-collaboratifs/view/<project>/<entry>` | Relevé collaboratif (readable) |
| `Archives : Oise, naissances`, `Archives : Recensements …`, linking to `/cercles/view/` | `https://www.geneanet.org/cercles/view/<collection>/<entry>` | Association index (refused by robots.txt) |
| Cemetery name | `https://www.geneanet.org/cimetieres/view/<photo>/persons/…` | Cemetery survey |

Facets shown on the page: type of source (Arbres en ligne, Archives,
État civil, Recensements et élections, Archives notariales et fiscales,
Cimetières), events, filiation, images, "Masquer les données Premium".
Their links are not exposed reliably through a fetcher; narrow with
place and period instead.

Reading the result list:

- **Places are listed together, not per event.** An unfiltered snippet
  shows the events, then all the places of the person ("… Décès: 06
  Janvier 1940 Bresles, Oise, France & Beauvais, Oise, France"), and the
  fetcher then pins them to events, often wrongly. Record snippet places
  only as a whole, or read the page.
- **The place filter hides trees without that place.** `place__0__`
  keeps only people with an event at that place; a tree holding only
  the death at another commune disappears. For a rare name, run the
  search without a place as well.
- **One row per union.** A person married twice appears twice, with the
  same URL, once with each spouse. Count trees, not rows.
- **Identical tree hits are normal**: trees copy one another. They are
  one claim until shown otherwise.

Other result types seen: `Archives : Tables de successions et absences
(…)` and similar labels linking to `/registres/view/<id>/<page>?individu_filter=…`
are Geneanet's own indexed register images (origin kind `register`).
They are allowed by robots.txt but were not tested; images are often
reserved to Premium members.

## Tree person pages (GeneWeb)

```
https://gw.geneanet.org/<owner>?lang=fr&n=<surname>&p=<given+names>[&oc=<n>]
```

- `n` and `p` are lowercased, accents removed, spaces and hyphens
  written `+`: "Marie-Thérèse Joseph" is `p=marie+therese+joseph`. The
  script's `url person` does this. Apostrophes and particles are
  unpredictable; when a built URL gives "Personne inconnue" or the wrong
  person, open the tree's surname index and take the link from there.
- `oc` is the occurrence number that separates homonyms in one tree
  (`oc=0` is implied). The same person can appear twice in one tree
  under two `oc` values; treat them as one tree, not two.
- `lang=fr` gives French labels, which the prompts expect.

Page anatomy, in order (sections may be absent):

1. Header: sex, full name, sometimes a title or nickname.
2. Events in short form: `Née le 4 mai 1861 (samedi) - Bresles,
   Oise, …`, `Décédée le …, à l'âge de 85 ans`, profession.
3. `Parents`: two links, or `Personne masquée`.
4. `Union(s) et enfant(s)`: marriage date and place, spouse link,
   children links.
5. `Frères et sœurs`, `Grands parents paternels, oncles et tantes`,
   `Grands parents maternels, oncles et tantes`: more links to walk.
6. `Présences lors d'événements`: acts where the person was a witness,
   godparent or declarant; useful for the cluster.
7. `Événements`: each event with its full text: declarants, witnesses
   with ages, occupations and residences, and in many trees an inline
   `Sources:` line for that event. This is where the most precise
   references usually are.
8. `Notes`, with sub-headings such as `Naissance` or `Notes concernant
   l'union`: free text, often an archive viewer URL.
   `Photos et documents d'archives` may appear here or higher: through a
   fetcher it is usually an unrendered JavaScript template
   (`{{ media.doc_title }}`, "Rechercher les actes correspondants"). Say
   so in `remarks` rather than reading it as empty; the images it would
   show are not reachable this way.
9. `Sources`: one line per label, `Naissance: …`, `Union: …`,
   `Décès: …`, `Personne: …`, `Famille: …`.
10. `Arbre généalogique (aperçu)` or `(jusqu'aux grands-parents)`: a
    small chart; its links are ordinary person URLs.

A tree has either an `Événements` block with inline sources, a
`Sources` block, both, or neither. Ask for the section headings first
when unsure which layout a tree uses.

Shapes of what trees write, with the names, dates and numbers changed:

```
Sources
- Naissance: Archives Oise, image 52
- Union: Archives Oise, images 210, 211 et 212
- Décès: Archives Oise, image 52, acte de naissance

Notes
Naissance: https://ressources.archives.oise.fr/v2/ad60/visualiseur/registre.html?id=600000000
```

```
Sources: JEANNE X COPIE INTEGRALE ACTE DE NAISSANCE - … - 4 MAY 1861 -
<http://archives.oise.fr> - Archives Départementales de l'Oise - Registre Bresles
NMD années 1860-1870 côte archives 3E999/4 vue 52/300 - Original
```

```
5h00-acte 44 Sources: Archives départementales du Pas-de-Calais
```

```
Sources
- Naissance, union: Archives départementales du Pas-de-Calais
```

The first two locate the act, the third names only a repository, and
the fourth gives an act number (and the hour) inside the event text.
Note the first block's death source naming a birth act: trees reuse
templates, and the slip is recorded as written.

## Tree indexes

```
https://gw.geneanet.org/<owner>?lang=fr&m=N&v=<surname>     surname index of one tree
https://gw.geneanet.org/<owner>?lang=fr&m=P&v=<given name>  given-name index
```

Both are allowed by robots.txt. The surname index lists every bearer in
the tree with dates and the exact person URL (with `oc` when needed). Use
it to find the right homonym and to check what else the tree holds on
the family before walking it.

## Relevés collaboratifs

```
https://www.geneanet.org/releves-collaboratifs/view/<project>/<entry>   one indexed act
https://www.geneanet.org/releves-collaboratifs/view/<project>           the project page (paged: ?page=2)
https://www.geneanet.org/releves-collaboratifs/geo/FRA/<dept code>/<Commune>/<slug>   all projects for a commune
```

An entry page shows the act type and place in its heading (`État civil
(Mariages) - Bresles, Oise, France`), then labelled fields: `Jour`,
`Mois`, `Année`, `Nom époux`, `Prénoms époux`, `Nom épouse`, `Prénoms
épouse`, and in richer projects parents, ages, occupations, remarks.
Below: the project block with `Période`, `Mise en ligne`, `Déposé par`,
`Licence`. Many projects index only the date and the names; that is
still enough to go to the right act in the register.

The project page usually has no statement of which register series was
indexed (greffe or communal copy, tables décennales). Say so rather than
assuming. The geo page lists all projects for a commune with their
period and act count: use it to state a negative ("relevé des mariages
1802-1902 exists, no entry for the couple"). Take its URL from the
"Tous les relevés de <commune>" link of an entry page: the trailing slug
(`france-oise-bresles`) is required, and a URL built without it returns
an empty template. With no entry page to start from, a negative can only
say that the search engine returned no relevé.

## Association indexes (cercles)

Search results labelled `Archives : <département>, naissances`,
`… décès`, `… Recensements` with URLs under `/cercles/view/<collection>/<id>`
come from genealogical associations' indexes (collection codes such as
`colgnecac60n`). The detail page is refused by robots.txt. The snippet in
the result list is all that can be read: name, sometimes parents or
spouse, the commune and a date or bracket ("entre 1825 et 1875"). Record
it as shown, with the collection code, and point the user to the
association's own access route or to the register itself.

## Cemetery surveys

```
https://www.geneanet.org/cimetieres/view/<photo id>/persons/?individu_filter=<SURNAME>%2B<given>
https://www.geneanet.org/cimetieres/collection/<id>-<slug>
```

The page gives the cemetery, the names read on the stone with the years
or dates, and the contributor. Dates on a stone are derivative and often
only years; they locate a death register, they do not replace it.

## Login, Premium, masked people

- `Personne masquée` replaces people the tree owner hides, typically the
  living or recently deceased. Do not try to unmask them.
- Some search results and index fields are reserved to Premium members;
  the page says so or shows a padlock. Record `not-visible` with the
  reason.
- Pages occasionally show a JavaScript or consent notice above the
  content; the content is usually still there, so ask for it explicitly.
