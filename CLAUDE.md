# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Commit Rules

- Do NOT include "Co-Authored-By: Claude" or any AI attribution in commit messages.
- Always regenerate `visualization/graph.json` from `data/editor/network.db` before committing, since the database is the source of truth.

## Project Overview

**Reti di Carta: Italian-American Print Networks (1890-1980)** — interactive network visualization mapping transnational connections in Italian-American print culture between writers, translators, scholars, and cultural institutions (4,223 nodes — 3,790 persons, 433 institutions — and 5,677 edges at the time of writing; the database is the authority, so check `python3 data/editor/validate.py` rather than trusting these numbers).

## Data Flow (Source of Truth)

```
data/editor/network.db (SQLite — authoritative data store)
       ↓
  Export button in editor UI (POST /api/export-graph)
  — OR — curl http://localhost:5001/api/graph.json > visualization/graph.json
       ↓
visualization/graph.json (static file for deployment)
       ↓
visualization/index.html (loads graph.json via D3.js)
```

The CSV files (`type1.csv`, `singlerows.csv`) are legacy inputs. The database is the current source of truth. Edits made in the editor update the database; you must click "Export" (or regenerate manually) to update the static `graph.json`.

## Commands

### Run the Data Editor (primary workflow)
```bash
cd data/editor && python3 app.py
```
- Editor UI: http://localhost:5001
- Visualization (live from DB): http://localhost:5001/visualization/
- API: http://localhost:5001/api/graph.json
- Export to static file: click "Export" button in editor header

### View standalone visualization
```bash
cd visualization && python3 serve.py
```
Starts at port 8080, auto-opens browser. Loads static `graph.json`.

### Regenerate graph.json from database (command line)
```bash
cd data/editor && python3 -c "import json, database as db; json.dump(db.get_graph_json(), open('../../visualization/graph.json','w'), indent=2)"
```
Uses the same `get_graph_json()` as the editor's Export button (includes edge `type`, which drives edge colors). Don't hand-roll the SQL.

### Validate the database and graph.json (read-only)
```bash
cd data/editor && python3 validate.py
```
Exits 1 if there are self-loops, orphan/reversed/duplicate edges, duplicate folded names, non-NFC names, or `visualization/graph.json` differs from the database export.

### Generate from CSV (legacy — do not use on `visualization/graph.json`)
`data/csv-to-json.py` builds a graph from the old CSVs only (~1,600 nodes), so writing it to `visualization/graph.json` would clobber the published graph. If you must run it, write to a scratch file:
```bash
cd data && python csv-to-json.py --types type1.csv --edges singlerows.csv --out /tmp/legacy-graph.json
```

### Omeka import workflow
```bash
cd data/editor
python3 omeka_import.py              # Fetch from Omeka API
python3 omeka_editor.py              # Review at http://localhost:5002
python3 clean_metadata.py            # Normalize metadata
```

### Import a periodical's masthead + contributors (scanned PDF → DB)
Use this pipeline for new periodicals. "The usual thing" = everyone on the masthead (editorial and business staff) plus every TOC byline/photographer, each linked to the periodical by an `affiliation` edge.
```bash
cd data/editor
# 1. Extract with Qwen3-VL on Bedrock (us-east-1); per-page JSON -> data/<slug>/extraction/
python3 extract_toc.py SCAN.pdf --slug iam --periodical "I-AM" --pages 2,4,6-10
# 2. Merge pages + review decisions, match names against the DB -> data/<slug>/roster.json
python3 build_roster.py iam
# 3. Import (refuses while any match is unresolved; backs up DB to data/editor/backups/)
python3 import_contributors.py iam --dry-run
python3 import_contributors.py iam
```
- **Review is mandatory between steps 1 and 2.** Check every TOC page against the scan (`data/<slug>/pages/`, gitignored). Qwen's main error: putting article *subjects* (names in the description line) into bylines; the byline is the LAST line of a TOC entry.
- All review decisions live in `data/<slug>/review.json` (`not_authors`, `drop`, `add`, `aliases`, `skip`, `match`, `new`, `notes`, page→issue `issues`) so `build_roster.py` is re-runnable. Field docs are in the `build_roster.py` docstring.
- `build_roster.py` flags fuzzy candidates (same surname + first initial, or Levenshtein ≥ 0.85, e.g. "John Ciardi" ~ "John Anthony Ciardi"). Resolve each with `match` (existing node id) or `new`; don't merge uncertain ones.
- `roster.json` keeps each person's roles and issues; the DB schema does not store them (deliberately — no roles in the DB for now).

### Import signed pieces read page by page (no TOC) — e.g. La Follia
For scans where contributors are found from bylines/end signatures on the pages themselves.
```bash
cd data/editor
# 1. Extraction: Claude subagents read each page image -> data/<slug>/extraction/<pdf stem>.json
#    (pages: issue per page from footer/header/masthead; signatures: name, as_printed, title, kind, confidence)
# 2. Merge + apply review.json -> data/<slug>/contributors.json and roster.json
python3 build_signatures.py follia
# 3. Review in the browser (saves to review.json, rebuilds on startup and on every click)
python3 signature_reviewer.py follia        # http://localhost:5003
# 4. Import with the shared importer
python3 import_contributors.py follia --dry-run && python3 import_contributors.py follia
```
- Extraction: Sonnet subagents match Opus on this task; Haiku credits article subjects as authors. Run few image-reading agents at once (too many trigger "[media removed: request limit]"), and never let an agent write a file from OCR or guesses. Cross-check names against the PDF text layer (`pdftotext`). Spellings in an example file get copied, so verify the example against the scan first.
- Inclusion: photo credits and composers count; letter writers only if in 2+ issues or already in the DB; initials-only names with no DB match and unidentifiable pen names are excluded (kept in the data via `exclude` / `excluded_reason`).
- `review.json` keys are documented in the `build_signatures.py` docstring (`aliases`, `skip`, `drop`, `new`, `exclude`, `notes`, `open_questions`).
- Starting the reviewer rewrites `contributors.json`/`roster.json` from the current DB, so after an import they show a diff (newly created nodes now matched). That's expected; commit it or `git checkout` it.
- The reviewer only answers requests addressed to `localhost:5003`/`127.0.0.1:5003` (403 for a LAN IP or other hostname) and only accepts JSON POSTs. This guards against CSRF and DNS rebinding; keep both checks if you change the server.

### Scripted data fixes (merge / rename / split nodes)
- Use `database.py` helpers from `data/editor/`: `backup_db()` first, then `merge_nodes(primary, secondary)`, `update_node(id, name=...)`, `create_node`, `create_edge`, `update_edge` — they keep `name_normalized` and canonical edge direction in sync, and `create_edge`, `update_edge`, `update_node` and `merge_nodes` refresh `needs_review`/shared institutions. `delete_edge`, `delete_node` and the batch deletes do not, so after scripted deletions (or any raw SQL) run `recalculate_all_shared_institutions()`. Avoid raw SQL writes.
- After a fix that touches an imported periodical, record it in that periodical's `data/<slug>/review.json` (`match`/`aliases`) so re-running `build_roster.py` doesn't undo it.
- Name conventions: generational suffixes without a period (`Luigi Barzini Jr`, `Luigi Barzini Sr`). Split homonymous father/son nodes by date (e.g. anything after Barzini Sr's death in 1947 is Jr).
- New data source → add it to both the About modal "Data Sources" list in `visualization/index.html` and the README sources list.

Legacy one-off importers (`import_carroccio_contributors.py`, `import_atlantica_contributors.py`, `import_parola_contributors.py`) parse their own text formats; keep them for reference, don't extend them.

### Ports
| Service | Port | Command |
|---------|------|---------|
| Visualization (standalone) | 8080 | `cd visualization && python3 serve.py` |
| Data Editor | 5001 | `cd data/editor && python3 app.py` |
| Omeka Staging | 5002 | `cd data/editor && python3 omeka_editor.py` |
| Signature Reviewer | 5003 | `cd data/editor && python3 signature_reviewer.py follia` (stdlib only) |

## Architecture

### Visualization (`visualization/index.html`)

Single-file HTML with inline CSS/JS. Hybrid rendering architecture:
- **SVG layer** (z-index 2): node circles + labels, handles pointer events
- **Canvas layer** (z-index 1): all edge rendering via Canvas 2D API, background gradient
- **Force simulation**: D3.js v7 forceSimulation with link, charge, collision, and optional cluster forces

Key internal structures (all inside the `NetworkViz` IIFE):
- `DPR` (const): cached `window.devicePixelRatio` for canvas scaling
- `DEGREE_THRESHOLDS` (const): `[1, 5, 10, 30, 40, 50]` for degree filter slider
- `nodesById` (Map): O(1) node lookup by ID
- `adjacencyList` (Map): pre-computed neighbor sets
- `nodeDegrees` (Map): pre-computed degree counts
- `communityCache` (Map): label propagation community assignments
- `communitySizes` (Map): node count per community
- `hiddenEdges` / `highlightedEdges` (Sets): control canvas edge drawing
- `preCommunityPositions` (Map): saved positions for toggle restore
- `explorerDisplayNodes` (Set|null): visible nodes from explorer/search/click, or null when inactive
- `explorerDisplayEdges` (Set|null): visible edges from explorer, or null
- `explorerAnchorNodes` (Set|null): searched/clicked endpoint nodes, always visible in explorer mode

Exposed API via `const NetworkViz` (script scope, not on `window`): `init`, `findPath`, `exploreConnections`, `clearPath`, `exportPNG`, `fullReset`, `toggleCommunities`, `exportSubgraph`, `expandTwoHop`, `autoFit`, `getStats`, `filterByType`, `filterBySubtype`, `setFilterMode`, `resetFilters`, `setExplorerMode`

**Filter system:**
- Multi-select enabled for both types and subtypes (uses JavaScript Sets)
- `selectedTypes` Set: active type filters ('person', 'institution')
- `selectedSubtypes` Set: active subtype filters ('magazine', 'publisher', etc.)
- `filterMode`: 'or' (default) or 'and' — controls how Person + multiple subtypes are filtered
- Subtype pills shown when: no type filter, 'institution' selected, OR subtypes already selected
- **Context-dependent filtering**: Person + subtype filters show only persons connected to institutions with those subtypes
- **AND/OR toggle**: When Person + 2+ subtypes selected, toggle appears to switch between:
  - OR (Any): persons connected to at least one selected subtype
  - AND (All selected): persons connected to ALL selected subtypes

**Composite visibility system** (`applyCompositeVisibility()`):
- Central function that computes node/edge visibility by intersecting explorer state with filter state
- Called by `highlightNode()`, `applySearchResults()`, `applyExplorerResult()`, `findSharedConnections()`, and `applyAllFilters()`
- When explorer + filters both active: anchors always visible, other nodes must be in explorer set AND pass filter
- When explorer + subtype filters active: **2-hop expansion** from anchors through `adjacencyList` to find matching institutions via intermediary persons
- Edge computation: induced subgraph (all edges between visible nodes) when subtypes active; filtered explorer edges otherwise
- Non-visible nodes always faded (`opacity: 0.1` for explorer, `0.08` for filters), never `display:none`
- `updateLabelsForExplorer(visibleNodes, anchorNodes)`: shared helper for post-visibility label styling — anchors get 36px/700, visible nodes get 12px, hidden nodes get opacity 0

**Reset functions:**
- `resetExplorerVisuals()`: resets DOM styles (nodes, edges, labels) without clearing explorer/filter state. Used by `applyExplorerResult()`
- `clearPath()`: clears all explorer state variables + resets DOM + re-applies filters on full graph. Filters persist after clearing
- `resetView()`: clears explorer state + re-applies filters if active, or resets all styles. Called when search is cleared
- `fullReset()`: calls `resetFilters()` then `clearPath()` then `resetView()` — complete state wipe

Data loading: port 5001 → `/api/graph.json` (live DB); otherwise → static `graph.json`.

**Security patterns:**
- Node details panel and explorer chips use DOM methods (createElement/textContent), not innerHTML with user data
- Event delegation on `#details-list` for connection item clicks (single listener, not per-item)
- Search input escapes regex metacharacters before `new RegExp()`

### Community Detection
- Label propagation algorithm (max 20 iterations, shuffle per iteration with a seeded mulberry32 PRNG, nodes in sorted id order, ties to the lowest label, so the result is reproducible; `node tests/community.test.js` checks it)
- Selective spatial clustering: only communities ≥ 20 nodes get centroid force (0.12 strength)
- Cross-community link strength reduced to 0.005 when active
- Cross-community edges drawn at 8% opacity on canvas
- Node positions saved/restored on toggle for deterministic behavior

### Data Editor (`data/editor/`)

Flask app with SQLite backend. CORS restricted to localhost/127.0.0.1 origins only.

**Database schema:**
```sql
nodes (id, name, name_normalized, type, subtype)
edges (id, source_id, target_id, type, needs_review)  -- UNIQUE(source_id, target_id)
shared_institutions (edge_id, institution_id)
```

Node types: `person`, `institution`
Institution subtypes: `periodical`, `publisher`, `university`, `organization`, `media`, `business`, `event`, `government`, `other`

**Edge integrity (canonical ordering):**
- All edges stored with `source_id <= target_id` — enforced by SQLite triggers (`enforce_edge_direction_insert`, `enforce_edge_direction_update`)
- `create_edge()`, `update_edge()`, `batch_create_edges()`, and `merge_nodes()` all normalize direction before writing
- `migrate_deduplicate_edges()` runs at startup: removes reverse-duplicate edges, normalizes existing edges (idempotent)
- When checking for duplicate edges, always check both directions: `(source_id=? AND target_id=?) OR (source_id=? AND target_id=?)`

**Input validation and error handling:**
- `safe_int()` helper in `app.py` validates integer query params (`page`, `per_page`), returns 400 JSON on invalid input
- `get_edges()` raises `ValueError` on invalid `min_shared`/`max_shared`; caller catches and returns 400
- Batch operations return `cursor.rowcount` (actual rows affected), not `len(input_ids)`
- Edge creation/update returns 409 on UNIQUE constraint violations (duplicate edges), not 500
- Frontend `createEdges()` distinguishes duplicate errors from other API errors in toast messages

**Editor tabs:** Nodes, Edges, Needs Review, Data Quality

**Stats API:** `GET /api/stats` returns `needs_review` (backward compat) and `unclassified_edges` (preferred) — both count edges with `type='unknown'`

**Data Quality tab** (`database.py:get_audit_report()`):
- 5 collapsible sections: unknown edges, missing subtypes, orphan nodes, needs_review edges, potential duplicates
- Duplicate detection: Levenshtein similarity >= 0.85, bucketed by first 3 chars of `name_normalized`
- Batch actions reuse existing API endpoints (batch type, subtype, reviewed, delete, merge)
- Badge count on tab updates on load and after each action

**Key API endpoints:**
- `GET/POST /api/nodes`, `GET/PUT/DELETE /api/nodes/<id>`
- `GET/POST /api/edges`, `GET/PUT/DELETE /api/edges/<id>`
- `POST /api/nodes/merge` — merge duplicates
- `POST /api/batch/nodes/type` — batch update node types
- `POST /api/batch/nodes/subtype` — batch update institution subtypes
- `POST /api/export-graph` — write graph.json to visualization/
- `GET /api/graph.json` — live graph data from DB
- `GET /api/audit` — data quality audit report (unknown edges, missing subtypes, orphans, needs_review, duplicates)

**Editor frontend files** (`data/editor/static/`):
- `js/api.js` — API client wrapper
- `js/editor.js` — main UI state and rendering
- `js/batch.js` — batch operations
- `css/editor.css` — all styles (CSS variables in `:root`)
- Templates use `?v=N` cache busting; increment when editing JS/CSS

### Folder Structure
```
├── data/
│   ├── type1.csv, singlerows.csv     # Legacy CSV sources
│   ├── contributors_list.md           # Il Carroccio contributor names
│   ├── contributors-and-board/        # Divagando TOC data (1945-1957)
│   ├── csv-to-json.py                 # CSV→JSON converter (legacy)
│   ├── iam/                           # I-AM (1976-77): extraction/, review.json, roster.json
│   ├── follia/                        # La Follia di New York (1940-75): extraction/, review.json, contributors.json, roster.json
│   ├── editor/                        # Flask editor + SQLite DB
│   └── cytoscape/                     # Archived (outdated)
├── visualization/
│   ├── index.html                     # Main visualization (production)
│   ├── graph.json                     # Generated from DB (commit this)
│   ├── magazines_network.html         # Subset: shared Divagando/Carroccio contributors
│   ├── multi_node_sidebar.html        # Multi-node connection finder
│   ├── serve.py                       # Dev server (port 8080)
│   └── experimental/                  # Test, debug, mobile prototypes
├── docs/                              # Images (figures, screenshots)
└── .gitignore                         # Ignores .DS_Store, __pycache__, backups, staging DB
```

## Key Implementation Details

### Force Simulation Parameters
- Link distance: 300px (degree-adjusted), strength: 0.15
- Charge: -2500 (degree-adjusted), distanceMax: 500, theta: 1.2
- Collision: 35px radius
- Velocity decay: 0.7, alpha: 0.5, alphaDecay: 0.04
- Auto-stop timeout: 3000ms, auto-fit after convergence

### Path Finding (`findAllConnections`)
- BFS with maxPathLength: 4, pathLengthTolerance: 1
- `findAllPathsBFS` uses `bestDepth` Map to prune: nodes only re-explored at equal or shorter depths
- Queue size capped at 50,000; returns `{ paths, overflow }` so UI can react to truncation
- `bfsShortestPathNodes` returns the actual node path array (not just distance)
- Exports include ALL edges between visible nodes (induced subgraph), not just path edges

### Explorer Modes
- **3-mode toggle**: Shortest (single BFS shortest path), Direct Only (direct edges + shared neighbors), All Paths (all paths within tolerance)
- `explorerMode` state: `'all'` (default), `'direct'`, or `'shortest'`
- When BFS overflow occurs, "All Paths" button auto-disables and mode switches to "shortest"
- `clearPath()` re-enables all mode buttons on reset

### Explorer-Filter Interaction (2-hop expansion)
- Search/click sets `explorerDisplayNodes`/`explorerDisplayEdges`/`explorerAnchorNodes`
- Type filters (Person/Institution) use simple intersection with explorer nodes
- **Subtype filters trigger 2-hop expansion**: from each anchor, traverse `adjacencyList` 2 hops to find institutions matching the subtype, including intermediary person nodes
- Example: Search "Divagando" → click "Business" → shows Divagando + intermediary persons (Erberto Landi, etc.) + business institutions (Landi Advertisement Co, etc.)
- Edges computed as induced subgraph of all visible nodes when subtypes active
- No state mutation — expansion computed inside `applyCompositeVisibility()` from existing data structures

### Subgraph Export
- Exports the induced subgraph of all visible nodes (opacity > 0.05, display ≠ none)
- Includes edges between visible nodes that aren't in `hiddenEdges`

### Visual Theme
- Person nodes: #6b8e9f (blue-gray)
- Institution nodes colored by subtype:
  - periodical: #b8860b (dark goldenrod)
  - publisher: #8b7355 (sepia)
  - university: #5d6d7e (slate blue-gray)
  - organization: #9a7b4f (warm bronze)
  - media: #a67c52 (warm copper)
  - Default/uncategorized: #8b7355 (original bronze)
- Background: radial gradient #f7f4ed → #ebe6da
- Typography: Cormorant Garamond (display), Source Sans 3 (body)
- Edge colors: affiliation #c4b5a0, personal #b09a8a

### Mobile Responsiveness
- Sidebar: hidden by default on mobile, slides in as 85vw overlay with backdrop
- All touch targets: minimum 44px
- Inputs: 16px font-size (prevents iOS zoom)
- Canvas/SVG: always full viewport on mobile
- Viewport: user-scalable=no (D3 handles pinch-zoom)

## Deployment

Production site: `reti.stefanomorello.com`
- SSH credentials stored in `.env` (gitignored)
- SSH key stored as `id_rsa` in project root (gitignored)
- Only deploy `visualization/index.html` and `visualization/graph.json`
- Always regenerate `graph.json` from the database before deploying
- `.env` is free-form notes, not `KEY=value`; the key passphrase is on the `passcode: ` line. Never `cat`/`sed`-print `.env` — read the passphrase straight into a variable.
- Deploy command (passphrase fed via `SSH_ASKPASS` from a throwaway helper; the old `expect` version hung at the passphrase prompt and exited 0 without uploading):
  ```bash
  export DEPLOY_PASS="$(sed -n 's/^passcode: //p' .env)" && A="$(mktemp)" && printf '#!/bin/sh\nprintf "%%s\\n" "$DEPLOY_PASS"\n' > "$A" && chmod 700 "$A" && \
  SSH_ASKPASS="$A" SSH_ASKPASS_REQUIRE=force DISPLAY=:0 scp -o IdentitiesOnly=yes -i id_rsa visualization/index.html visualization/graph.json stefanom@stefanomorello.com:/home/stefanom/reti.stefanomorello.com/ </dev/null; echo "scp exit: $?"; rm -f "$A"
  ```
- Always run the verify step below after deploying (check the counts changed); don't trust the upload output alone. If the server closes the connection right away, wait a minute and retry (BitNinja rate-limits repeated attempts).
- Verify live: `curl -s https://reti.stefanomorello.com/graph.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['nodes']), len(d['links']))"`

## Citation

Morello, Stefano. "Mapping Italian/American Crossings: A Network Approach." *Modern Language Notes* 140.1 (2025): 246-275. [DOI](https://doi.org/10.1353/mln.2025.a963658)
