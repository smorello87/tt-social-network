# Probable duplicates (NOT merged)

Generated read-only from `data/editor/network.db` for the owner to decide. Each pair is a candidate; nothing here has been merged.

## Landi

- id 1257: Erberto Landi (person), 19 edge(s): Cantagiro [affiliation]; Divagando [affiliation]; Epoca [affiliation]; Erberto Landi Enterprises [affiliation]; Italclub Inc [affiliation]; Landi Advertisement Co [affiliation]; NBC [affiliation]; Neapolitan Song Festival [affiliation]; Office of War Information [affiliation]; Pettinella Advertising Company [affiliation]; Sanremo Festival [affiliation]; Voice of America [affiliation]; WABC [affiliation]; WATV [affiliation]; WBNX [affiliation]; WHOM [affiliation]; WNCW [affiliation]; WOR [affiliation]; WOV [affiliation]
- id 1326: Roberto Landi (person), 1 edge(s): Divagando [affiliation]
- shared neighbours: Divagando

## Alifano

- id 3243: Giovanni Alifano (person), 1 edge(s): Gastaldi Editore [affiliation]
- id 4492: John J. Alifano (person), 1 edge(s): La Follia di New York [affiliation]
- shared neighbours: none

## Castagna

- id 1454: Salvatore Castagna (person), 2 edge(s): Divagando [affiliation]; The Bishop Lito Co. [affiliation]
- id 1025: Salvatore Mario Castagna (person), 1 edge(s): Divagando [affiliation]
- shared neighbours: Divagando

## Manzardo/Mazzardo

- id 3974: Mario Manzardo (person), 1 edge(s): La Parola del Popolo [affiliation]
- id 3975: Mario Mazzardo (person), 1 edge(s): La Parola del Popolo [affiliation]
- shared neighbours: La Parola del Popolo

## Chiaramello/Chiarello

- id 3652: Domenico Chiaramello (person), 1 edge(s): La Parola del Popolo [affiliation]
- id 3653: Domenico Chiarello (person), 1 edge(s): La Parola del Popolo [affiliation]
- shared neighbours: La Parola del Popolo

## Pais/Palisi

- id 1795: Antonino Pais (person), 1 edge(s): Il Carroccio [affiliation]
- id 1796: Antonino Palisi (person), 1 edge(s): Il Carroccio [affiliation]
- shared neighbours: Il Carroccio

## Janni/Jannuzzi

- id 2571: Vincenzo Janni (person), 1 edge(s): Il Carroccio [affiliation]
- id 2572: Vincenzo Jannuzzi (person), 1 edge(s): Il Carroccio [affiliation]
- shared neighbours: Il Carroccio

Notes: the Landi pair is Erberto/Roberto Landi, which may be two different people or an OCR/transcription variant; `Erberto Landi Enterprises` (1555) and `Landi Advertisement Co` (1556) are institutions and `Lando Landi` (4288) is a separate node. `Ettore Pais` (2010) is a different person from `Antonino Pais`.

## Merged in round 2 (for the record)

- `Achille Loria` (1703) <- `Loria Achille` (3410): same name in reversed order, both linked to Italian Book Company; kept "Achille Loria" (the form in `data/contributors_list.md`).
- `Augusto Mauro` (4281) <- `Mauro Augusto` (4227): kept given-name-first "Augusto Mauro". No source list in the repo contains either form; the choice rests on the Italian-American convention used everywhere else in the DB (given name first) and on the edges (Secolo XIX, Le Lettere (Rome), Corriere d'America, a Genoa/Rome journalist context). Please correct if you know otherwise.
- Neither name appears in any `review.json` (iam, follia), so there was no alias to record; the merges came from legacy importers and hand edits.
