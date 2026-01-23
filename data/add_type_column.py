#!/usr/bin/env python3
"""
Add a 'type' column to singlerows.csv for edge classification.

Leaves values empty for manual tagging, but can optionally pre-fill
based on node types (person-person = 'personal', otherwise = 'affiliation').

Usage:
  python add_type_column.py                    # Add empty type column
  python add_type_column.py --prefill          # Pre-fill based on node types
  python add_type_column.py --dry-run          # Preview without modifying
"""

import argparse
import csv
import io
import re
import sys
import shutil
from datetime import datetime

def norm(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def read_csv_rows(path, delimiter=","):
    candidates = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "mac_roman"]
    with open(path, "rb") as fb:
        raw = fb.read()
    for enc in candidates:
        try:
            text = raw.decode(enc, errors="strict")
            stream = io.StringIO(text)
            reader = csv.reader(stream, delimiter=delimiter)
            return list(reader), enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path}")

def load_types(path):
    rows, _ = read_csv_rows(path)
    type_map = {}
    for row in rows[1:]:  # skip header
        if len(row) >= 2:
            name = norm(row[0]).lower()
            node_type = norm(row[1]).lower()
            if node_type in ("person", "institution"):
                type_map[name] = node_type
    return type_map

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", default="singlerows.csv")
    parser.add_argument("--types", default="type1.csv")
    parser.add_argument("--prefill", action="store_true",
                        help="Pre-fill types based on node types")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without modifying file")
    args = parser.parse_args()

    # Load type information if prefilling
    type_map = {}
    if args.prefill:
        print(f"[info] Loading node types from {args.types}...", file=sys.stderr)
        type_map = load_types(args.types)

    # Read edges
    print(f"[info] Reading {args.edges}...", file=sys.stderr)
    rows, encoding = read_csv_rows(args.edges)

    if not rows:
        print("[error] No data found", file=sys.stderr)
        return

    # Check if type column already exists
    header = rows[0]
    if len(header) >= 3 and header[2].lower().strip() == "type":
        print("[info] 'type' column already exists. No changes needed.", file=sys.stderr)
        return

    # Add type column
    new_rows = []
    new_header = header[:2] + ["type"]
    new_rows.append(new_header)

    stats = {"personal": 0, "affiliation": 0, "empty": 0}

    for row in rows[1:]:
        if len(row) < 2:
            continue

        src = norm(row[0]).lower()
        tgt = norm(row[1]).lower()

        edge_type = ""
        if args.prefill:
            src_type = type_map.get(src, "unknown")
            tgt_type = type_map.get(tgt, "unknown")

            if src_type == "person" and tgt_type == "person":
                edge_type = "personal"
                stats["personal"] += 1
            else:
                edge_type = "affiliation"
                stats["affiliation"] += 1
        else:
            stats["empty"] += 1

        new_rows.append([row[0], row[1], edge_type])

    # Preview or write
    if args.dry_run:
        print("\n[preview] First 10 rows with new type column:", file=sys.stderr)
        for row in new_rows[:11]:
            print(f"  {row}", file=sys.stderr)
        print(f"\n[stats] Would add:", file=sys.stderr)
        if args.prefill:
            print(f"  personal: {stats['personal']}", file=sys.stderr)
            print(f"  affiliation: {stats['affiliation']}", file=sys.stderr)
        else:
            print(f"  empty type fields: {stats['empty']}", file=sys.stderr)
    else:
        # Backup original
        backup = f"{args.edges}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(args.edges, backup)
        print(f"[info] Backed up to {backup}", file=sys.stderr)

        # Write new file
        with open(args.edges, "w", newline="", encoding=encoding) as f:
            writer = csv.writer(f)
            writer.writerows(new_rows)

        print(f"[done] Updated {args.edges} with 'type' column", file=sys.stderr)
        if args.prefill:
            print(f"[stats] Pre-filled: {stats['personal']} personal, {stats['affiliation']} affiliation", file=sys.stderr)
        else:
            print(f"[stats] Added {stats['empty']} empty type fields for manual tagging", file=sys.stderr)

if __name__ == "__main__":
    main()
