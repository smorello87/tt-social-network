# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Commit Rules

- Do NOT include "Co-Authored-By: Claude" or any AI attribution in commit messages.
- Always regenerate `visualization/graph.json` from `data/editor/network.db` before committing, since the database is the source of truth.

## Project Overview

Network visualization project mapping relationships in a transnational Italian-American literary network (1890-1980). Visualizes connections between writers, translators, scholars, and cultural institutions (~3,100 nodes, ~4,400 edges).

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
```python
import sqlite3, json
db = sqlite3.connect('data/editor/network.db')
db.row_factory = sqlite3.Row
nodes = [dict(r) for r in db.execute('SELECT name as id, type, subtype FROM nodes')]
edges = [dict(r) for r in db.execute('SELECT n1.name as source, n2.name as target FROM edges e JOIN nodes n1 ON e.source_id=n1.id JOIN nodes n2 ON e.target_id=n2.id')]
json.dump({'nodes': nodes, 'links': edges}, open('visualization/graph.json','w'), indent=2)
```

### Generate from CSV (legacy)
```bash
cd data && python csv-to-json.py --types type1.csv --edges singlerows.csv --out ../visualization/graph.json
```

### Omeka import workflow
```bash
cd data/editor
python3 omeka_import.py              # Fetch from Omeka API
python3 omeka_editor.py              # Review at http://localhost:5002
python3 clean_metadata.py            # Normalize metadata
```

### Import contributor lists
```bash
cd data/editor
python3 import_carroccio_contributors.py    # Import Il Carroccio TOC contributors
python3 import_atlantica_contributors.py    # Import Atlantica TOC contributors
```
These scripts parse contributor files and add nodes/edges to the database. They handle name normalization and duplicate detection.

### Ports
| Service | Port | Command |
|---------|------|---------|
| Visualization (standalone) | 8080 | `cd visualization && python3 serve.py` |
| Data Editor | 5001 | `cd data/editor && python3 app.py` |
| Omeka Staging | 5002 | `cd data/editor && python3 omeka_editor.py` |

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
- Callers manage label styling (font-size, font-weight, opacity) after composite visibility returns

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
- Label propagation algorithm (max 20 iterations, shuffle per iteration)
- Selective spatial clustering: only communities ≥ 20 nodes get centroid force (0.12 strength)
- Cross-community link strength reduced to 0.005 when active
- Cross-community edges drawn at 8% opacity on canvas
- Node positions saved/restored on toggle for deterministic behavior

### Data Editor (`data/editor/`)

Flask app with SQLite backend.

**Database schema:**
```sql
nodes (id, name, name_normalized, type, subtype)
edges (id, source_id, target_id, type, needs_review)
shared_institutions (edge_id, institution_id)
```

Node types: `person`, `institution`
Institution subtypes: `periodical`, `publisher`, `university`, `organization`, `media`, `business`, `event`, `government`, `other`

**Editor tabs:** Nodes, Edges, Needs Review, Data Quality

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
- Deploy command: `scp -o IdentitiesOnly=yes -i id_rsa visualization/index.html visualization/graph.json stefanom@stefanomorello.com:/home/stefanom/reti.stefanomorello.com/`

## Citation

Morello, Stefano. "Mapping Italian/American Crossings: A Network Approach." *Modern Language Notes* 140.1 (2025): 246-275. [DOI](https://doi.org/10.1353/mln.2025.a963658)
