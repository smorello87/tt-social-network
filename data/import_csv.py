#!/usr/bin/env python3
"""
Import CSV data into the SQLite database.

Usage:
    python import_csv.py
    python import_csv.py --types type1.csv --edges singlerows.csv
    python import_csv.py --clear  # Clear database before import
"""

import argparse
import csv
import io
import os
import re
import sys

# Add editor directory to path for database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'editor'))

import database as db

def normalize_name(name: str) -> str:
    """Normalize name for matching."""
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name.lower()

def read_csv(path, encoding_opt="auto"):
    """Read CSV file with encoding detection."""
    if encoding_opt.lower() != "auto":
        with open(path, newline="", encoding=encoding_opt) as f:
            return list(csv.reader(f))

    candidates = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "mac_roman"]
    with open(path, "rb") as fb:
        raw = fb.read()

    for enc in candidates:
        try:
            text = raw.decode(enc, errors="strict")
            return list(csv.reader(io.StringIO(text)))
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not decode {path}")

def import_data(types_path, edges_path, clear=False):
    """Import CSV data into database."""
    print(f"[info] Loading types from: {types_path}")
    print(f"[info] Loading edges from: {edges_path}")

    # Clear database if requested
    if clear:
        print("[info] Clearing existing database...")
        db_path = db.DB_PATH
        if db_path.exists():
            db_path.unlink()
        db.init_db()

    # Read CSVs
    types_rows = read_csv(types_path)
    edges_rows = read_csv(edges_path)

    print(f"[info] Found {len(types_rows)-1} type definitions")
    print(f"[info] Found {len(edges_rows)-1} edge definitions")

    # Track stats
    nodes_created = 0
    nodes_skipped = 0
    edges_created = 0
    edges_skipped = 0
    name_to_id = {}

    # Import nodes from types file
    print("\n[step 1/3] Importing nodes...")
    for i, row in enumerate(types_rows[1:], start=2):  # Skip header
        if len(row) < 2:
            continue

        name = row[0].strip()
        node_type = row[1].strip().lower()

        if not name:
            continue

        if node_type not in ("person", "institution"):
            node_type = "unknown"

        # Check if already exists
        existing = db.get_node_by_name(name)
        if existing:
            name_to_id[normalize_name(name)] = existing["id"]
            nodes_skipped += 1
            continue

        try:
            node_id = db.create_node(name, node_type)
            name_to_id[normalize_name(name)] = node_id
            nodes_created += 1
        except Exception as e:
            print(f"[warn] Line {i}: Could not create node '{name}': {e}")

    print(f"       Created: {nodes_created}, Skipped (existing): {nodes_skipped}")

    # Import edges
    print("\n[step 2/3] Importing edges...")
    for i, row in enumerate(edges_rows[1:], start=2):  # Skip header
        if len(row) < 2:
            continue

        source = row[0].strip()
        target = row[1].strip()
        edge_type = row[2].strip() if len(row) >= 3 else "affiliation"

        if not source or not target:
            continue

        if edge_type not in ("personal", "affiliation"):
            edge_type = "affiliation"

        source_norm = normalize_name(source)
        target_norm = normalize_name(target)

        # Get or create source node
        if source_norm not in name_to_id:
            existing = db.get_node_by_name(source)
            if existing:
                name_to_id[source_norm] = existing["id"]
            else:
                node_id = db.create_node(source, "unknown")
                name_to_id[source_norm] = node_id
                nodes_created += 1

        # Get or create target node
        if target_norm not in name_to_id:
            existing = db.get_node_by_name(target)
            if existing:
                name_to_id[target_norm] = existing["id"]
            else:
                node_id = db.create_node(target, "unknown")
                name_to_id[target_norm] = node_id
                nodes_created += 1

        # Create edge
        try:
            db.create_edge(name_to_id[source_norm], name_to_id[target_norm], edge_type)
            edges_created += 1
        except Exception:
            edges_skipped += 1  # Edge already exists

    print(f"       Created: {edges_created}, Skipped (existing): {edges_skipped}")

    # Recalculate shared institutions
    print("\n[step 3/3] Computing shared institutions...")
    count = db.recalculate_all_shared_institutions()
    print(f"       Processed: {count} edges")

    # Summary
    print("\n" + "="*50)
    print("Import Complete!")
    print("="*50)

    stats = db.get_stats()
    print(f"\nDatabase now contains:")
    print(f"  Nodes: {stats['nodes']['total']}")
    print(f"    - Persons: {stats['nodes'].get('person', 0)}")
    print(f"    - Institutions: {stats['nodes'].get('institution', 0)}")
    print(f"    - Unknown: {stats['nodes'].get('unknown', 0)}")
    print(f"  Edges: {stats['edges']['total']}")
    print(f"    - Personal: {stats['edges'].get('personal', 0)}")
    print(f"    - Affiliation: {stats['edges'].get('affiliation', 0)}")
    print(f"  Needs Review: {stats['needs_review']}")

    print(f"\nDatabase saved to: {db.DB_PATH}")

def main():
    parser = argparse.ArgumentParser(description="Import CSV data into SQLite database")
    parser.add_argument("--types", default="type1.csv", help="Path to types CSV")
    parser.add_argument("--edges", default="singlerows.csv", help="Path to edges CSV")
    parser.add_argument("--clear", action="store_true", help="Clear database before import")

    args = parser.parse_args()

    # Resolve paths relative to data directory
    data_dir = os.path.dirname(os.path.abspath(__file__))
    types_path = os.path.join(data_dir, args.types) if not os.path.isabs(args.types) else args.types
    edges_path = os.path.join(data_dir, args.edges) if not os.path.isabs(args.edges) else args.edges

    if not os.path.exists(types_path):
        print(f"[error] Types file not found: {types_path}")
        sys.exit(1)

    if not os.path.exists(edges_path):
        print(f"[error] Edges file not found: {edges_path}")
        sys.exit(1)

    import_data(types_path, edges_path, args.clear)

if __name__ == "__main__":
    main()
