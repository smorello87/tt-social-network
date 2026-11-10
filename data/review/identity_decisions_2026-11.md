# Identity decisions (2026-11)

The open identity questions from `data/review/probable_duplicates.md` and the round-2 "Augusto Mauro" merge.
Rule: merge only on positive evidence that both nodes are one person (the same person attested under
both forms, or one form shown to be a misreading of the source it came from). Plausible is not enough.

| Question | Decision |
|---|---|
| Mario Manzardo (3974) / Mario Mazzardo (3975) | **Merged** into 3974 Mario Manzardo |
| Salvatore Mario Castagna (1025) / Salvatore Castagna (1454) | **Merged** into 1025 Salvatore Mario Castagna |
| Erberto Landi (1257) / Roberto Landi (1326) | Left separate: undetermined |
| Domenico Chiaramello (3652) / Domenico Chiarello (3653) | Left separate: undetermined |
| Antonino Pais (1795) / Antonino Palisi (1796) | Left separate: evidence of two people |
| Vincenzo Janni (2571) / Vincenzo Jannuzzi (2572) | Left separate: evidence of two people |
| Giovanni Alifano (3243) / John J. Alifano (4492) | Left separate: plausible, not shown |
| "Augusto Mauro" (4281): which token is the surname | Name left as is: undetermined |

Sources checked beyond the web: the La Parola del Popolo TOC photos and extraction JSON, and the Il Carroccio
TOC images and per-TOC extraction, all in the owner's `~/Downloads/Caroccio/` working folder; the
WorldCat harvest (`~/Downloads/github/worldcat/`); the Divagando staff and contributor transcriptions
(`data/contributors-and-board/`); S. Morello, "Networks of Influence: Divagando's Italian (and) American
Literary Infrastructure", *MLN* 140.1 (2025): 113–137 (`~/Downloads/divagando.pdf`); and a Tesseract OCR
pass over the 867 Divagando photographs on `/Volumes/DataMacMini/Dropbox/Books digitized/Firenze It Am/`.
Those photographs are article pages: none names Landi or Castagna, and none is the 1957 contributors page.

## Mario Manzardo / Mario Mazzardo — merged

- Both nodes come from the La Parola del Popolo import (`import_parola_contributors.py`), each with one
  edge to La Parola del Popolo.
- The extraction (`parola_per_issue.json`, issue 131, November–December 1975, `131 - TOC.jpg`) reads the
  byline of "Labor Looks at the Bicentennial" (p. 79) as "Mario Mazzardo".
- The scan of that page prints **"Mario Manzardo"** for p. 79, and also for p. 77 ("Dante — The Comedy and
  my mother"). "Mario Manzardo" is in the same issue's COLLABORATORI list and in the collaboratori lists of
  issues 125, 127, 128, 130 and 137 (6 listings in all, 1974–77).
- "Mazzardo" is a misreading of the extraction; no source prints it. Merged 3975 into 3974 with
  `database.merge_nodes`. The duplicate Parola edge (5402) collapsed into 5401.

## Domenico Chiaramello (3652) / Domenico Chiarello (3653): left separate

- Both come from the La Parola del Popolo import, one Parola edge each.
- The no. 9 TOC (January–March 1953, `parola-del-popolo_january-march-1953_3_9_sommario.jpg`) prints
  "Le tragiche ore del Settembre 1943 ... **Domenico Chiaramello**" (p. 36).
- The no. 126 TOC (November–December 1974, `126 - TOC.jpg`) prints "Stampa italiana all'estero: sue lacune
  e necessità ... **Domenico Chiarello**" (p. 24).
- Each node is spelled as its own source prints it, so neither is a transcription error.
- Domenico Chiaramello (Cavallermaggiore 1897 – 1986) was a PSI, then PSDI, deputy and Treasury
  undersecretary (https://it.wikipedia.org/wiki/Domenico_Chiaramello). That fits a 1953 piece on September
  1943, and he would have been 77 in 1974.
- No "Domenico Chiarello" journalist turned up (web search; Wikipedia lists only a WWI veteran,
  Francesco Domenico Chiarello).
- A misprint of Chiaramello in 1974 is possible, but nothing shows it.
- **To settle:** the signature on p. 24 of no. 126, or another Parola index or masthead that names him.

## Antonino Pais (1795) / Antonino Palisi (1796): left separate (evidence points to two people)

- Both come from the Il Carroccio list (`data/contributors_list.md`).
- The per-TOC extraction (`contributors_per_toc.json`, owner's Carroccio working folder) has:
  - "**Dott.** Antonino Pais": "Il metodo Pais debellatore della malaria" (TOC image
    `mdp.39015073737408-seq_8.jpg`). The article title repeats the surname, so "Pais" is not an OCR slip.
  - "**Prof.** Antonino Palisi": three verse contributions ("Paesaggio di Primavera — Dieci sonetti",
    "La Grande Conquista — Versi", "La mia musa", the last as "Antonio Palisi").
- Different honorific, field and genre. Nothing links them.
- `Ettore Pais` (2010) is a third, unrelated person (senator and historian).

## Vincenzo Janni (2571) / Vincenzo Jannuzzi (2572): left separate (evidence points to two people)

- Both come from the Il Carroccio list.
- The 1927 TOC (`mdp.39015073737309-seq_12.jpg`, May) prints "Quadri di Sartorio negli Stati Uniti —
  **Col. Vincenzo Janni**" (p. 540). It also lists a portrait "Vincenzo Janni" among the illustrations.
  I checked the scan: the spelling is Janni.
- Vincenzo Jannuzzi appears as "Rev. Vincenzo Jannuzzi" ("La Chiesa-Scuola di San Giuseppe"), "Dr. cav.
  Vincenzo Jannuzzi" ("Sull'Oceano col 'Conte Rosso'") and as an illustrator credit.
- A colonel and a priest: no evidence of one person.

## Giovanni Alifano (3243) / John J. Alifano (4492): left separate (plausible, not shown)

- **Giovanni Alifano** came from the WorldCat publisher harvest (`github/worldcat/export/Gastaldi
  Editore.md`): *Verso l'aurora: [versi]* (Milan: Gastaldi, 1954, OCLC 1045898930; also catalogued at HSP,
  https://discover.hsp.org/Record/marc-12034). A later *L'Ateo e il credente* (Salerno: Moriniello, 1964) is
  inscribed by "Giovanni Alifano" to Pasquale Spataro
  (https://www.commoncrowbooks.com/pages/books/0063465/giovanni-alifano/lateo-e-il-credente).
- **John J. Alifano** signs as "DR. JOHN J. ALIFANO, Springfield, Mass." in La Follia: an Italian poem
  "Buona Pasqua (a Rodolfo Pucelli)" in 1947-04, and "What Is Love?" on 1949-10-01. He also reviewed Mary
  Vecchione's "Bits of Stars" in La Parola del Popolo no. 131 (1975, p. 78). That Parola appearance is
  not an edge in the DB.
- **For one person:** Giovanni is the Italian form of John. Gastaldi's paid "Poeti d'oggi" series also
  published La Follia poets (Vincenzo Foti, Giuseppe Luongo).
- **Against, or unknown:** the 1964 book was printed in Salerno. No source names "Giovanni Alifano" with
  Springfield or a medical title, or gives John J. Alifano an Italian title.
- **To settle:** the title page or colophon of *Verso l'aurora* (author's residence or title), or a La Follia
  or Parola notice of the book.

## "Augusto Mauro" (4281, the round-2 merge of 4227 "Mauro Augusto"): order left as is, undetermined

- Both forms were created in commit 5d6bbb3 (2026-10-10):
  - 4227 "Mauro Augusto", created together with "Secolo XIX" (4228) and "Le Lettere (Rome)" (4229),
    and linked to those two and to Corriere d'America.
  - 4281 "Augusto Mauro", linked to Corriere d'America only.
- That commit added the *Italian American Who's Who* (Vigo Press, 1935) as a source. Its entries are
  alphabetised surname first, so "MAURO, Augusto" read without the comma would give "Mauro Augusto",
  which would make **Mauro** the surname. This is an inference from the node pattern, not evidence.
- No repository file contains the entry. Web searches found no journalist under either order with Secolo
  XIX, Le Lettere or Corriere d'America. The 1935 *Who's Who* is not digitised in full view.
- Merging the two forms stays justified: same two name tokens, and both nodes were linked to Corriere
  d'America.
- Which token is the surname is not established, so the node keeps the name round 2 gave it.
- **To settle:** the *Italian American Who's Who* (1935) entry, or a Corriere d'America byline or masthead.

## Salvatore Castagna / Salvatore Mario Castagna: merged

- **1025 "Salvatore Mario Castagna":** from the Divagando staff lists, every year transcribed
  (`data/contributors-and-board/1948-board.txt` ... `1957-board.txt`). He sits beside the magazine's other
  designers, Frank V. Liotta and Nando Rossi.
- **1454 "Salvatore Castagna":** a hand-entered legacy node (`data/cytoscape/singlerows.csv`) with edges
  to Divagando and The Bishop Lito Co.
- **Morello, *MLN* 2025:**
  - p. 114 names "Salvatore Castagna, one of its graphic designers", who reports on the fair in
    Divagando's July 9 issue.
  - p. 127 counts Castagna among Divagando's four designers (Liotta, Castagna, Giovanni Abys, Nando
    Rossi). It notes "his training under Bob Fawcett and his later role as director of L'Episcopo's Bishop
    Litho", citing "Art Association to Hear Talk by Art Director", *The Standard Star*, 22 February 1963,
    p. 19.
- So the designer Castagna is attested in Divagando both on the masthead (with the middle name) and in a
  byline (without it). Each node holds one half of that record: the masthead form, and the designer with
  the Bishop Litho edge. No other Castagna appears in any Divagando source.
- Merged 1454 into 1025, keeping the fuller masthead form. The duplicate Divagando edge (1660) collapsed
  into 1666, and the Bishop Lito edge (1661) moved to 1025.
- If the owner prefers the byline form used in the article, rename 1025 to "Salvatore Castagna".

## Erberto Landi / Roberto Landi: left separate, undetermined

- **1257 Erberto Landi:** 19 edges. Born Giacobbe Erberto Minetto Levi (Savigliano 1908 – New York 1971);
  he took the name Erberto Landi in 1946 (https://transatlantictransfers.polimi.it/en/atlas/789/erberto-landi).
  That biography records no "Roberto" form. He is in the 1952 Divagando contributor list
  (`data/contributors-and-board/1952.txt`), and Morello (*MLN* 2025, p. 123) names him among Divagando's
  contributors after 1952.
- **1326 Roberto Landi:** a single Divagando edge, from the 1957 contributor list
  (`data/contributors-and-board/1957.txt`, line 86).
- "Roberto" could be a misreading of "Erberto", or a different contributor. The 1957 page is not among
  the scans I could reach.
- **To settle:** the 1957 Divagando contents page or article that the "Roberto Landi" line was
  transcribed from.
