#!/usr/bin/env python3
"""
Review Person-to-Person Connections

Analyzes the network data to find all person-to-person connections and
identifies shared institutions between each pair. Generates an HTML report
for easy review.

Usage:
  python review_person_connections.py
  python review_person_connections.py --types type1.csv --edges singlerows.csv
"""

import argparse
import csv
import io
import re
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path

def norm(s: str) -> str:
    """Normalize whitespace in a string."""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def read_csv_rows(path, delimiter=",", has_header=True):
    """Read CSV with auto-detected encoding."""
    candidates = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "mac_roman"]

    with open(path, "rb") as fb:
        raw = fb.read()

    for enc in candidates:
        try:
            text = raw.decode(enc, errors="strict")
            stream = io.StringIO(text)
            reader = csv.reader(stream, delimiter=delimiter)
            if has_header:
                next(reader, None)
            return list(reader), enc
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(f"Could not decode '{path}' with any encoding")

def load_data(types_path, edges_path):
    """Load and process the CSV files."""
    # Read types
    rows, enc = read_csv_rows(types_path)
    print(f"[info] {types_path}: decoded as {enc}", file=sys.stderr)

    type_map = {}  # normalized name -> type
    display_name = {}  # normalized name -> display name

    for row in rows:
        if not row or len(row) < 2:
            continue
        raw_name, raw_type = row[0], row[1]
        name = norm(raw_name).lower()
        node_type = norm(raw_type).lower()

        if not name:
            continue

        display_name[name] = raw_name.strip()
        if node_type in ("person", "institution"):
            type_map[name] = node_type
        else:
            type_map[name] = "unknown"

    # Read edges
    rows, enc = read_csv_rows(edges_path)
    print(f"[info] {edges_path}: decoded as {enc}", file=sys.stderr)

    edges = []
    adjacency = defaultdict(set)  # name -> set of connected names

    for row in rows:
        if not row or len(row) < 2:
            continue
        raw_src, raw_tgt = row[0], row[1]
        src = norm(raw_src).lower()
        tgt = norm(raw_tgt).lower()

        if not src or not tgt:
            continue

        edges.append((src, tgt))
        adjacency[src].add(tgt)
        adjacency[tgt].add(src)

        # Update display names
        display_name.setdefault(src, raw_src.strip())
        display_name.setdefault(tgt, raw_tgt.strip())

    return type_map, display_name, edges, adjacency

def analyze_person_connections(type_map, display_name, edges, adjacency):
    """Find all person-to-person connections and their shared institutions."""
    results = []
    seen = set()

    for src, tgt in edges:
        # Skip if not person-to-person
        src_type = type_map.get(src, "unknown")
        tgt_type = type_map.get(tgt, "unknown")

        if src_type != "person" or tgt_type != "person":
            continue

        # Deduplicate (A-B same as B-A)
        pair_key = tuple(sorted([src, tgt]))
        if pair_key in seen:
            continue
        seen.add(pair_key)

        # Find shared institutions
        src_institutions = {n for n in adjacency[src] if type_map.get(n) == "institution"}
        tgt_institutions = {n for n in adjacency[tgt] if type_map.get(n) == "institution"}
        shared = src_institutions & tgt_institutions

        # Get connection counts
        src_count = len(adjacency[src])
        tgt_count = len(adjacency[tgt])

        results.append({
            "person_a": display_name.get(src, src),
            "person_b": display_name.get(tgt, tgt),
            "shared_institutions": [display_name.get(i, i) for i in sorted(shared)],
            "shared_count": len(shared),
            "a_connections": src_count,
            "b_connections": tgt_count,
        })

    # Sort by shared institution count (ascending, so 0 shared comes first)
    results.sort(key=lambda x: (x["shared_count"], x["person_a"].lower()))

    return results

def generate_html(results, output_path):
    """Generate an HTML report."""

    # Calculate stats
    total = len(results)
    zero_shared = sum(1 for r in results if r["shared_count"] == 0)
    one_shared = sum(1 for r in results if r["shared_count"] == 1)
    two_shared = sum(1 for r in results if r["shared_count"] == 2)
    three_plus = sum(1 for r in results if r["shared_count"] >= 3)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Person-to-Person Connection Review</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #6b8e9f;
            padding-bottom: 10px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-box.zero {{ border-left: 4px solid #e74c3c; }}
        .stat-box.one {{ border-left: 4px solid #f39c12; }}
        .stat-box.two {{ border-left: 4px solid #3498db; }}
        .stat-box.three {{ border-left: 4px solid #27ae60; }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .filters {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filters label {{
            margin-right: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #6b8e9f;
            color: white;
            padding: 12px 15px;
            text-align: left;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            background: #5a7d8e;
        }}
        th::after {{
            content: ' \\2195';
            opacity: 0.5;
        }}
        td {{
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        tr.zero-shared {{
            background: #fdf2f2;
        }}
        tr.zero-shared:hover {{
            background: #fbe8e8;
        }}
        tr.three-plus {{
            background: #f0f9f4;
        }}
        tr.three-plus:hover {{
            background: #e5f5ec;
        }}
        .institution-list {{
            font-size: 0.9em;
            color: #666;
        }}
        .institution-list span {{
            background: #e8e8e8;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 5px;
            display: inline-block;
            margin-bottom: 3px;
        }}
        .none {{
            color: #e74c3c;
            font-style: italic;
        }}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 4px;
            vertical-align: middle;
            margin-right: 5px;
        }}
        .connection-count {{
            color: #888;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <h1>Person-to-Person Connection Review</h1>

    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{total}</div>
            <div class="stat-label">Total Person-Person Connections</div>
        </div>
        <div class="stat-box zero">
            <div class="stat-number">{zero_shared}</div>
            <div class="stat-label">0 Shared Institutions<br>(Hard to convert)</div>
        </div>
        <div class="stat-box one">
            <div class="stat-number">{one_shared}</div>
            <div class="stat-label">1 Shared Institution</div>
        </div>
        <div class="stat-box two">
            <div class="stat-number">{two_shared}</div>
            <div class="stat-label">2 Shared Institutions</div>
        </div>
        <div class="stat-box three">
            <div class="stat-number">{three_plus}</div>
            <div class="stat-label">3+ Shared Institutions<br>(Easy to convert)</div>
        </div>
    </div>

    <div class="filters">
        <strong>Filter:</strong>
        <label><input type="checkbox" id="show-zero" checked> 0 shared (hard)</label>
        <label><input type="checkbox" id="show-one" checked> 1 shared</label>
        <label><input type="checkbox" id="show-two" checked> 2 shared</label>
        <label><input type="checkbox" id="show-three" checked> 3+ shared (easy)</label>
        &nbsp;&nbsp;
        <input type="text" id="search" placeholder="Search names..." style="padding: 5px; width: 200px;">
    </div>

    <table id="connections-table">
        <thead>
            <tr>
                <th data-sort="person_a">Person A</th>
                <th data-sort="person_b">Person B</th>
                <th data-sort="shared_count">Shared Institutions</th>
                <th data-sort="a_connections">A's Connections</th>
                <th data-sort="b_connections">B's Connections</th>
            </tr>
        </thead>
        <tbody>
"""

    for r in results:
        shared_count = r["shared_count"]
        row_class = ""
        if shared_count == 0:
            row_class = "zero-shared"
        elif shared_count >= 3:
            row_class = "three-plus"

        if r["shared_institutions"]:
            institutions_html = '<span>' + '</span><span>'.join(r["shared_institutions"]) + '</span>'
        else:
            institutions_html = '<span class="none">None found</span>'

        html += f"""            <tr class="{row_class}" data-shared="{shared_count}">
                <td>{r["person_a"]}</td>
                <td>{r["person_b"]}</td>
                <td class="institution-list">{institutions_html}</td>
                <td class="connection-count">{r["a_connections"]}</td>
                <td class="connection-count">{r["b_connections"]}</td>
            </tr>
"""

    html += """        </tbody>
    </table>

    <div class="legend">
        <strong>Legend:</strong>
        <div class="legend-item">
            <span class="legend-color" style="background: #fdf2f2; border: 1px solid #e74c3c;"></span>
            0 shared institutions (hard to convert - may need to keep or find institution)
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background: #f0f9f4; border: 1px solid #27ae60;"></span>
            3+ shared institutions (easy to convert - connection is already institution-mediated)
        </div>
    </div>

    <script>
        // Filtering
        function applyFilters() {
            const showZero = document.getElementById('show-zero').checked;
            const showOne = document.getElementById('show-one').checked;
            const showTwo = document.getElementById('show-two').checked;
            const showThree = document.getElementById('show-three').checked;
            const searchTerm = document.getElementById('search').value.toLowerCase();

            document.querySelectorAll('#connections-table tbody tr').forEach(row => {
                const shared = parseInt(row.dataset.shared);
                const text = row.textContent.toLowerCase();

                let showByFilter = false;
                if (shared === 0 && showZero) showByFilter = true;
                if (shared === 1 && showOne) showByFilter = true;
                if (shared === 2 && showTwo) showByFilter = true;
                if (shared >= 3 && showThree) showByFilter = true;

                const showBySearch = !searchTerm || text.includes(searchTerm);

                row.style.display = (showByFilter && showBySearch) ? '' : 'none';
            });
        }

        document.querySelectorAll('.filters input').forEach(input => {
            input.addEventListener('change', applyFilters);
            input.addEventListener('input', applyFilters);
        });

        // Sorting
        let sortColumn = null;
        let sortAsc = true;

        document.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.sort;
                if (sortColumn === column) {
                    sortAsc = !sortAsc;
                } else {
                    sortColumn = column;
                    sortAsc = true;
                }

                const tbody = document.querySelector('#connections-table tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));

                rows.sort((a, b) => {
                    let aVal, bVal;

                    if (column === 'person_a') {
                        aVal = a.cells[0].textContent.toLowerCase();
                        bVal = b.cells[0].textContent.toLowerCase();
                    } else if (column === 'person_b') {
                        aVal = a.cells[1].textContent.toLowerCase();
                        bVal = b.cells[1].textContent.toLowerCase();
                    } else if (column === 'shared_count') {
                        aVal = parseInt(a.dataset.shared);
                        bVal = parseInt(b.dataset.shared);
                    } else if (column === 'a_connections') {
                        aVal = parseInt(a.cells[3].textContent);
                        bVal = parseInt(b.cells[3].textContent);
                    } else if (column === 'b_connections') {
                        aVal = parseInt(a.cells[4].textContent);
                        bVal = parseInt(b.cells[4].textContent);
                    }

                    if (typeof aVal === 'string') {
                        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                    }
                    return sortAsc ? aVal - bVal : bVal - aVal;
                });

                rows.forEach(row => tbody.appendChild(row));
            });
        });
    </script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path

def main():
    parser = argparse.ArgumentParser(description="Review person-to-person connections")
    parser.add_argument("--types", default="type1.csv", help="Path to types CSV")
    parser.add_argument("--edges", default="singlerows.csv", help="Path to edges CSV")
    parser.add_argument("--output", default="person_person_review.html", help="Output HTML file")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    print("[info] Loading data...", file=sys.stderr)
    type_map, display_name, edges, adjacency = load_data(args.types, args.edges)

    print("[info] Analyzing person-to-person connections...", file=sys.stderr)
    results = analyze_person_connections(type_map, display_name, edges, adjacency)

    print(f"[info] Found {len(results)} person-to-person connections", file=sys.stderr)

    output_path = generate_html(results, args.output)
    print(f"[done] Generated {output_path}", file=sys.stderr)

    # Summary
    zero = sum(1 for r in results if r["shared_count"] == 0)
    one = sum(1 for r in results if r["shared_count"] == 1)
    two = sum(1 for r in results if r["shared_count"] == 2)
    three_plus = sum(1 for r in results if r["shared_count"] >= 3)

    print(f"\n[stats] Breakdown:", file=sys.stderr)
    print(f"  0 shared institutions: {zero} ({100*zero/len(results):.1f}%) - Hard to convert", file=sys.stderr)
    print(f"  1 shared institution:  {one} ({100*one/len(results):.1f}%)", file=sys.stderr)
    print(f"  2 shared institutions: {two} ({100*two/len(results):.1f}%)", file=sys.stderr)
    print(f"  3+ shared institutions: {three_plus} ({100*three_plus/len(results):.1f}%) - Easy to convert", file=sys.stderr)

    if not args.no_open:
        print(f"\n[info] Opening {output_path} in browser...", file=sys.stderr)
        webbrowser.open(f"file://{Path(output_path).resolve()}")

if __name__ == "__main__":
    main()
