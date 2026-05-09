#!/usr/bin/env python3
"""
Batch import La Parola del Popolo contributors.
- Renames existing "La Parola" node to "La Parola del Popolo" (sets subtype=periodical)
- Creates person nodes for each contributor and links them via affiliation edges
- Reuses existing nodes by case-insensitive normalized-name match
- Hand-coded canonicalization map handles known spelling variants
- Edges are written in canonical direction (source_id <= target_id)
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "network.db"
CONTRIBUTORS_FILE = Path("/Users/veritas44/Downloads/Caroccio/parola_contributors_list.md")

PERIODICAL_NAME = "La Parola del Popolo"

NAME_CANONICAL_MAP = {
    "Giuseppe D Procopio": "Giuseppe D. Procopio",
}


def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name.lower()


def get_or_create_node(conn, name, node_type='person', subtype=None):
    if not name or not name.strip():
        return None, False

    name = name.strip()
    normalized = normalize_name(name)

    row = conn.execute(
        "SELECT id FROM nodes WHERE name_normalized = ?",
        (normalized,)
    ).fetchone()

    if row:
        return row[0], False

    if subtype is not None:
        cursor = conn.execute(
            "INSERT INTO nodes (name, name_normalized, type, subtype) VALUES (?, ?, ?, ?)",
            (name, normalized, node_type, subtype)
        )
    else:
        cursor = conn.execute(
            "INSERT INTO nodes (name, name_normalized, type) VALUES (?, ?, ?)",
            (name, normalized, node_type)
        )
    return cursor.lastrowid, True


def edge_exists(conn, source_id, target_id):
    row = conn.execute(
        """SELECT id FROM edges
           WHERE (source_id = ? AND target_id = ?)
              OR (source_id = ? AND target_id = ?)""",
        (source_id, target_id, target_id, source_id)
    ).fetchone()
    return row is not None


def create_edge(conn, a_id, b_id, edge_type='affiliation'):
    src, tgt = sorted((a_id, b_id))
    conn.execute(
        "INSERT INTO edges (source_id, target_id, type) VALUES (?, ?, ?)",
        (src, tgt, edge_type)
    )


def resolve_periodical(conn):
    """Rename existing 'La Parola' to 'La Parola del Popolo' (or create if missing)."""
    target_norm = normalize_name(PERIODICAL_NAME)

    row = conn.execute(
        "SELECT id, name FROM nodes WHERE name_normalized = ?",
        (target_norm,)
    ).fetchone()
    if row:
        # Already exists with the canonical name; ensure subtype
        conn.execute(
            "UPDATE nodes SET type='institution', subtype='periodical' WHERE id = ?",
            (row[0],)
        )
        return row[0], False

    legacy = conn.execute(
        "SELECT id, name FROM nodes WHERE name_normalized = ?",
        ("la parola",)
    ).fetchone()
    if legacy:
        conn.execute(
            "UPDATE nodes SET name=?, name_normalized=?, type='institution', subtype='periodical' WHERE id=?",
            (PERIODICAL_NAME, target_norm, legacy[0])
        )
        return legacy[0], False

    node_id, _ = get_or_create_node(conn, PERIODICAL_NAME, 'institution', 'periodical')
    return node_id, True


def main():
    with open(CONTRIBUTORS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    contributors = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('**'):
            continue
        # Skip prose lines (commas, sentence-ending periods, parentheses) — names don't have these
        if ',' in line or '(' in line or line.endswith('.'):
            continue
        contributors.append(line)

    print(f"Found {len(contributors)} contributors to import")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        periodical_id, created = resolve_periodical(conn)
        action = "Created" if created else "Resolved (renamed if needed)"
        print(f"{action} '{PERIODICAL_NAME}' node (id={periodical_id})")

        stats = {
            'nodes_created': 0,
            'nodes_existed': 0,
            'edges_created': 0,
            'edges_existed': 0,
            'canonicalized': 0,
            'skipped': 0,
        }

        for raw in contributors:
            name = NAME_CANONICAL_MAP.get(raw, raw)
            if name != raw:
                stats['canonicalized'] += 1

            node_id, was_created = get_or_create_node(conn, name, 'person')
            if node_id is None:
                stats['skipped'] += 1
                continue

            if was_created:
                stats['nodes_created'] += 1
            else:
                stats['nodes_existed'] += 1

            if edge_exists(conn, node_id, periodical_id):
                stats['edges_existed'] += 1
            else:
                create_edge(conn, node_id, periodical_id, 'affiliation')
                stats['edges_created'] += 1

        conn.commit()

        print("\n=== Import Complete ===")
        print(f"Nodes created:    {stats['nodes_created']}")
        print(f"Nodes existed:    {stats['nodes_existed']}")
        print(f"Edges created:    {stats['edges_created']}")
        print(f"Edges existed:    {stats['edges_existed']}")
        print(f"Canonicalized:    {stats['canonicalized']}")
        print(f"Skipped:          {stats['skipped']}")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
