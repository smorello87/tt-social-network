# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a network visualization project for mapping relationships in a transnational Italian-American literary network. It visualizes connections between writers, translators, scholars, and cultural institutions.

### Folder Structure
- `data/`: Contains CSV source files and Python processing script
  - `csv-to-json.py`: Converts CSV data to JSON format
  - `type1.csv`: Node definitions (persons/institutions)
  - `singlerows.csv`: Edge definitions (relationships)
- `visualization/`: Contains all HTML visualization files
  - `diva_optimized.html`: Main visualization (performance-optimized)
  - `graph.json`: Generated network data
  - `serve.py`: Custom Python server with CORS headers
  - Test files for debugging

## Commands

### Generate graph data from CSV files
```bash
cd data
python csv-to-json.py --types type1.csv --edges singlerows.csv --out ../visualization/graph.json
```

Options:
- `--encoding auto|utf-8|utf-8-sig|cp1252|latin-1|mac_roman` (default: auto-detect)
- `--no-header-types` if type1.csv has no header
- `--no-header-edges` if singlerows.csv has no header
- `--delimiter ","` to specify a different delimiter

### View the visualization

1. **Start a local web server** (required for loading local JSON data):
```bash
cd visualization
python3 -m http.server 8080
```
Then navigate to `http://localhost:8080/diva_optimized.html`

2. **Alternative - using custom Python server** (includes CORS headers):
```bash
cd visualization
python3 serve.py
```

3. **Other server options**:
- Node.js: `npx http-server`
- PHP: `php -S localhost:8080`

The visualization requires:
- `graph.json` to be present in the same directory
- Internet connection for loading D3.js and other libraries from CDNs

## Architecture

### Data Pipeline (`csv-to-json.py`)
- **Input**: Two CSV files
  - `type1.csv`: Maps entities to types (person/institution)
  - `singlerows.csv`: Defines edges/relationships between entities
- **Processing**:
  - Auto-detects file encoding
  - Deduplicates rows
  - Normalizes names for matching while preserving display casing
  - Resolves type conflicts with warnings
- **Output**: `graph.json` with nodes and links for D3.js visualization

### Visualization Files

#### `diva_optimized.html` (Primary Visualization)
- **Force-directed graph** using D3.js v7 with modular NetworkViz architecture
- **Performance features**:
  - Map-based data structures for O(1) lookups
  - Pre-computed node degrees and adjacency lists
  - Debounced search (300ms) and throttled zoom (16ms)
  - RequestAnimationFrame for 60fps animations
  - Loading indicator with progress tracking
  - Circular pre-positioning to reduce initial chaos

- **User Interface**:
  - Search with autocomplete (triggers after 1 character, highlights nodes AND edges)
  - Connection Explorer: finds all relevant paths between two nodes
  - Network Density Filter: discrete stops at 1+, 5+, 10+, 30+, 40+, 50+ connections
  - Auto-fit view button
  - Export to PNG functionality
  - About modal with data source information
  - Compact sidebar layout optimized for screen space

- **Visual design** (Literary theme):
  - Person/Actor nodes: muted blue-gray (#6b8e9f)
  - Institution nodes: bronze (#8b7355)
  - Background: warm ivory gradient (#f5f1e8 to #faf8f3)
  - Typography: Crimson Text (serif) and Inter (sans-serif)
  - Path highlighting: green (start), red (end), golden borders (intermediate)

#### Mobile Versions (Beta - Require Further Development)
- `diva_optimized_mobile.html`: Basic mobile UI optimizations (sidebar, touch controls)
- `diva_optimized_mobile_d3.html`: Enhanced with D3 touch gestures (pinch-zoom, tap-select)
- **Note**: These are experimental and need refinement. Use `diva_optimized.html` for production.

#### `diva.html` (Original Version)
- Basic force-directed visualization
- Original punk aesthetic (red/black color scheme)
- Similar features but without performance optimizations

## Key Implementation Details

### Force Simulation Parameters (`diva_optimized.html`)
- **Link distance**: 300px base (dynamically adjusts with zoom)
- **Charge strength**: -2500 (stronger repulsion for better spacing)
- **Collision radius**: 35px (prevents node overlap)
- **Velocity decay**: 0.6 (higher damping for stability)
- **AlphaTarget during drag**: 0.05 (reduced from 0.3 to minimize wobbling)

### Path Finding Algorithm (`findAllConnections`)
- Uses BFS to find paths between nodes with configurable parameters:
  - `maxPathLength`: 4 (maximum path length to consider)
  - `pathLengthTolerance`: 1 (how many hops longer than shortest to include)
- Shows shortest paths plus alternative paths within tolerance
- Includes triangles (common neighbors that connect to both start and end)
- Completely hides non-connected nodes (`display: none` and `opacity: 0`)
- Visual indicators: green for start node, red for end node, golden borders for intermediate
- Displays path information: distance, number of paths, shared contacts

### Performance Considerations
- Zoom scale extent: [0.05, 10] (allows bird's eye view to detailed inspection)
- Auto-fit after 5 seconds of initial simulation
- Simulation auto-stops when stable to save CPU
- Maximum 10 autocomplete suggestions for performance

## Data Format

### type1.csv
```csv
entry,type
Name,person|institution
```
Valid types: `person`, `institution`. Others default to `unknown`.
Contains ~1500+ entries representing actors and institutions in the literary network.

### singlerows.csv
```csv
entry,Merged
Source Name,Target Name
```
Represents bidirectional connections between entities.
Contains ~2300+ relationships (publications, collaborations, affiliations).

### graph.json
```json
{
  "nodes": [{"id": "Name", "type": "person|institution|unknown"}],
  "links": [{"source": "Name1", "target": "Name2"}]
}
```
Generated automatically from CSV files using `csv-to-json.py`.

## Troubleshooting

### Visualization stuck on "Initializing..."
- Check browser console for errors (F12)
- Ensure `graph.json` exists in same directory
- Verify local server is running (CORS errors if opened directly)
- Check for JavaScript syntax errors

### Common Issues
- **Autocomplete not working**: Wait for data to load completely (5+ seconds)
- **Nodes overlapping**: Allow simulation to settle, use auto-fit button
- **Path finder shows no results**: Ensure exact node names or use autocomplete