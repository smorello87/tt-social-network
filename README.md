# Italian-American Literary Network Visualization

An interactive network visualization mapping transnational connections in Italian-American literary culture, revealing relationships between writers, translators, scholars, and cultural institutions.

## Overview

This project visualizes a network of over 1,500 nodes (individuals and institutions) connected by nearly 3,000 edges representing various relationships including publications, collaborations, translations, and institutional affiliations. The visualization helps identify patterns of cultural exchange, influential brokers, and community formations within the Italian-American literary ecosystem.

## Live Demo

The current stable version is `diva_optimized.html`. Mobile versions are in beta and require further refinement.

## Features

- **Interactive Force-Directed Graph**: Dynamic D3.js visualization with real-time physics simulation
- **Search with Autocomplete**: Find specific individuals or institutions quickly
- **Connection Explorer**: Discover paths and relationships between any two nodes
- **Network Density Filter**: Filter nodes by their number of connections (1+, 5+, 10+, 30+, 40+, 50+)
- **Export to PNG**: Save the current view as an image
- **About Modal**: Detailed information about data sources and methodology

## Installation & Usage

### Prerequisites
- Python 3.x (for local server and data processing)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection (for loading D3.js libraries from CDN)

### Quick Start

1. **Clone the repository**
```bash
git clone [repository-url]
cd divagando-updated
```

2. **Start the visualization**
```bash
cd visualization
python3 -m http.server 8080
```

3. **Open in browser**
Navigate to: `http://localhost:8080/diva_optimized.html`

### Generating New Data

If you need to regenerate the network from updated CSV files:

```bash
cd data
python csv-to-json.py --types type1.csv --edges singlerows.csv --out ../visualization/graph.json
```

## Project Structure

```
divagando-updated/
├── README.md                    # This file
├── CLAUDE.md                    # Documentation for AI assistants
├── data/                        # Data processing
│   ├── csv-to-json.py          # Convert CSV to JSON
│   ├── type1.csv               # Node definitions (persons/institutions)
│   └── singlerows.csv          # Edge definitions (relationships)
└── visualization/              # Visualization files
    ├── diva_optimized.html     # Main visualization (stable)
    ├── diva_optimized_mobile.html    # Mobile version (beta)
    ├── diva_optimized_mobile_d3.html # Enhanced mobile (beta)
    ├── diva.html               # Original version
    ├── graph.json              # Network data
    └── serve.py                # Python server with CORS
```

## Data Format

### Nodes (type1.csv)
- **Persons**: Writers, translators, scholars, editors, cultural mediators
- **Institutions**: Publishing houses, magazines, universities, cultural organizations

### Edges (singlerows.csv)
- Bidirectional connections representing various relationships
- Examples: authored by, published in, affiliated with, collaborated with

## Technical Details

### Performance Optimizations
- Map-based data structures for O(1) lookups
- Pre-computed node degrees and adjacency lists
- Debounced search (300ms) and throttled zoom (16ms)
- RequestAnimationFrame for 60fps animations
- Circular pre-positioning to reduce initial chaos

### Visual Design
- **Literary Theme**: Warm ivory backgrounds with bronze/sepia accents
- **Node Colors**:
  - Persons: Muted blue-gray (#6b8e9f)
  - Institutions: Bronze (#8b7355)
- **Typography**: Crimson Text (serif) and Inter (sans-serif)

## Usage Guide

### Navigation
- **Zoom**: Scroll or pinch to zoom
- **Pan**: Click and drag on empty space
- **Move Nodes**: Click and drag individual nodes
- **Auto-Fit**: Click "Auto-Fit View" to center the network

### Finding Connections
1. Use the Connection Explorer in the left sidebar
2. Enter two names (use autocomplete for accuracy)
3. Click "Trace Connection" to see all paths between them
4. Green = start node, Red = end node, Golden borders = intermediate nodes

### Filtering
- Use the Network Density Filter slider to show only well-connected nodes
- Settings: 1+ (all), 5+, 10+, 30+, 40+, 50+ connections

## Mobile Versions (Beta)

Two experimental mobile versions are included but require further development:
- `diva_optimized_mobile.html` - Basic mobile optimizations
- `diva_optimized_mobile_d3.html` - Enhanced touch gestures

**Note**: These mobile versions are in beta and may have performance issues or bugs. The stable, tested version is `diva_optimized.html`, which works on both desktop and mobile browsers but is optimized for desktop viewing.

## Data Sources

The network data was collected from:
- Transatlantic Transfers Atlas (Italian-American cultural exchanges database)
- *Divagando* magazine tables of contents (103 issues, 1945-1957)
- Wikipedia entries for individuals and institutions
- Italian Sistema Bibliotecario Nazionale (SBN) metadata

For detailed methodology, see the About section within the visualization.

## Browser Compatibility

- **Desktop**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: Best viewed on desktop; mobile versions in beta

## Troubleshooting

### Visualization won't load
- Ensure you're running a local server (not opening HTML directly)
- Check that `graph.json` exists in the visualization folder
- Open browser console (F12) for error messages

### Performance issues
- Allow the initial simulation to settle (5-8 seconds)
- Use the Network Density Filter to reduce visible nodes
- Try the Auto-Fit View button to reset the viewport

### Autocomplete not working
- Wait for the data to fully load (loading indicator disappears)
- Start typing at least one character
- Check browser console for errors

## Citation

If you use this visualization in academic work, please cite:
[Citation information to be added]

## License

[License information to be added]

## Contact

Created by Stefano Morello - [stefanomorello.com](https://stefanomorello.com)

## Acknowledgments

This visualization was developed as part of research into transnational Italian-American literary networks. Special thanks to all contributors and data sources that made this project possible.