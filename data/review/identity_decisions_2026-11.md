# Identity decisions (2026-11)

The open identity questions from `data/review/probable_duplicates.md` and the round-2 "Augusto Mauro" merge.
Rule: merge only on positive evidence that both nodes are one person (the same person attested under
both forms, or one form shown to be a misreading of the source it came from). Plausible is not enough.

| Question | Decision |
|---|---|
| Mario Manzardo (3974) / Mario Mazzardo (3975) | **Merged** into 3974 Mario Manzardo |

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
