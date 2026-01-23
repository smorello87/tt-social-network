# Italian-American Literary Network Visualization

An interactive network visualization mapping transnational connections in Italian-American literary culture, revealing relationships between writers, translators, scholars, and cultural institutions.

## Overview

This project visualizes a network of individuals and institutions connected by relationships including publications, collaborations, translations, and institutional affiliations. The visualization helps identify patterns of cultural exchange, influential brokers, and community formations within the Italian-American literary ecosystem.

## Quick Start

```bash
git clone https://github.com/smorello87/tt-social-network.git
cd tt-social-network/visualization
python3 serve.py
```

This starts a local server and opens the visualization at `http://localhost:8080`.

## Features

### Main Visualization (`visualization/index.html`)
- **Interactive Force-Directed Graph**: D3.js v7 with hybrid SVG + Canvas rendering
- **Search with Autocomplete**: Find individuals or institutions (triggers after 1 character)
- **Connection Explorer**: Discover all paths between any two nodes (BFS with configurable depth)
- **Node Details Panel**: Click any node for a slide-in panel showing all connections grouped by type
- **Community Detection**: Label propagation algorithm with spatial clustering for major communities
- **Network Density Filter**: Filter by connection count (1+, 5+, 10+, 30+, 40+, 50+)
- **2-Hop Neighborhood**: Explore the local neighborhood around any selected node
- **Export to PNG**: Composites canvas links + SVG nodes into a downloadable image

### Data Editor (`data/editor/`)
- Browser-based CRUD interface for managing network data
- SQLite-backed with REST API
- Node/edge creation, editing, deletion, and merging
- Batch operations and review workflow for unclassified edges
- Omeka API integration for importing external collections

### Multi-Node Analysis (`visualization/multi_node_sidebar.html`)
- Select up to 10 nodes to analyze their connections
- **Direct Connections Mode**: Shows only direct edges between selected nodes
- **Steiner Tree Mode**: Minimal connecting subgraph with intermediate nodes
- Connection matrix visualization and density statistics

## Project Structure

```
tt-social-network/
├── README.md
├── CLAUDE.md                          # Development instructions
├── .gitignore
├── docs/                              # Images and documentation assets
│   ├── divagando.png
│   ├── Morello_figure1.png
│   └── Morello_figure2.png
├── data/
│   ├── type1.csv                      # Node definitions (persons/institutions)
│   ├── singlerows.csv                 # Edge definitions (relationships)
│   ├── contributors_list.md           # Il Carroccio contributors list
│   ├── contributors-and-board/        # Divagando TOC and board data (1945-1957)
│   ├── csv-to-json.py                 # CSV → JSON converter for D3.js
│   ├── check_single_connections.py    # Peripheral node analysis
│   ├── add_type_column.py             # Utility: add type column to CSV
│   ├── import_csv.py                  # Utility: CSV import to SQLite
│   ├── review_person_connections.py   # Utility: review person-person edges
│   ├── editor/                        # Flask data editor application
│   │   ├── app.py                     # Main editor server (port 5001)
│   │   ├── database.py                # SQLite operations
│   │   ├── network.db                 # Network database
│   │   ├── omeka_import.py            # Omeka API importer
│   │   ├── omeka_editor.py            # Staging review UI (port 5002)
│   │   ├── import_carroccio_contributors.py
│   │   ├── import_atlantica_contributors.py
│   │   ├── clean_metadata.py          # Metadata normalization
│   │   ├── static/                    # Frontend assets (CSS, JS)
│   │   └── templates/                 # Jinja2 templates
│   └── cytoscape/                     # Archived legacy workflow
├── visualization/
│   ├── index.html            # Main visualization (production)
│   ├── magazines_network.html         # Subset: Divagando & Il Carroccio contributors
│   ├── multi_node_sidebar.html        # Multi-node connection finder
│   ├── multi_node_sidebar.js          # Multi-node algorithms
│   ├── multi_node_sidebar.css         # Multi-node styles
│   ├── multi_node_direct_connections.js
│   ├── graph.json                     # Generated network data
│   ├── graph_magazines.json           # Subset graph data
│   ├── serve.py                       # Dev server (port 8080, CORS, auto-open)
│   └── experimental/                  # Test, debug, and prototype files
│       ├── diva.html                  # Original visualization
│       ├── diva_optimized_mobile*.html
│       └── test_*.html, debug_*.html
└── LICENSE                            # CC BY-NC 4.0
```

## Data Sources

- [Transatlantic Transfers Atlas](https://transatlantictransfers.polimi.it/atlas)
- Digitized tables of contents from 103 issues of *Divagando* (1945-1957)
- Tables of contents of *Il Carroccio* (1915-1930)
- Tables of contents of *Atlantica* (1923-1930)
- [The Periconi Collection of Italian American Imprints](https://italianamericanimprints.omeka.net/)
- Wikipedia biographical data
- Metadata from the Italian Sistema Bibliotecario Nazionale (SBN)

## Usage

### Generating Graph Data

```bash
cd data
python csv-to-json.py --types type1.csv --edges singlerows.csv --out ../visualization/graph.json
```

Options: `--encoding auto|utf-8|utf-8-sig|cp1252|latin-1|mac_roman`

### Running the Data Editor

```bash
cd data/editor
python3 app.py          # Editor at http://localhost:5001
python3 omeka_editor.py # Omeka staging at http://localhost:5002
```

### Analyzing the Network

```bash
cd data
python check_single_connections.py singlerows.csv
```

## Navigation

- **Zoom**: Scroll or pinch
- **Pan**: Click and drag empty space
- **Move Nodes**: Click and drag individual nodes
- **Node Details**: Click any node for connection info
- **Connection Explorer**: Enter two names in the sidebar, click "Find"
- **Community Detection**: Click "Color by Community" to identify clusters
- **Auto-Fit**: Reset the viewport to show all nodes

## Technical Notes

### Performance
- Hybrid SVG (nodes/labels) + Canvas (edges) rendering
- ~2,885 nodes and ~3,895 edges with 60fps interaction
- Zoom-dependent label visibility (hub labels only at low zoom)
- Map-based O(1) lookups, pre-computed adjacency lists
- Debounced search, throttled zoom, RequestAnimationFrame

### Visual Design
- **Theme**: Archival/literary (warm ivory, sepia tones)
- **Persons**: Muted blue-gray (#6b8e9f)
- **Institutions**: Bronze (#8b7355)
- **Typography**: Cormorant Garamond (display), Source Sans 3 (body)

## Citation

Morello, Stefano. "Mapping Italian/American Crossings: A Network Approach." *Modern Language Notes* 140.1 (2025): 246-275. [DOI](https://doi.org/10.1353/mln.2025.a963658)

```
Morello, Stefano. (2025). Italian-American Literary Network Visualization.
GitHub repository: https://github.com/smorello87/tt-social-network
```

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). See [LICENSE](LICENSE).

## Contact

Created by Stefano Morello - [stefanomorello.com](https://stefanomorello.com)
