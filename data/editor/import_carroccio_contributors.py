#!/usr/bin/env python3
"""
Batch import Il Carroccio contributors.
Creates person nodes for each contributor and links them to Il Carroccio.
Skips existing nodes/edges.
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).parent / "network.db"
CONTRIBUTORS_FILE = Path("/Users/veritas44/Downloads/github/tt-social-network/data/contributors_list.md")


def normalize_name(name: str) -> str:
    """Normalize name for matching."""
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name.lower()


def get_or_create_node(conn, name, node_type='person'):
    """Get existing node or create new one. Returns (node_id, was_created)."""
    if not name or not name.strip():
        return None, False

    name = name.strip()
    normalized = normalize_name(name)

    # Check if exists
    row = conn.execute(
        "SELECT id FROM nodes WHERE name_normalized = ?",
        (normalized,)
    ).fetchone()

    if row:
        return row[0], False

    # Create new node
    cursor = conn.execute(
        "INSERT INTO nodes (name, name_normalized, type) VALUES (?, ?, ?)",
        (name, normalized, node_type)
    )
    return cursor.lastrowid, True


def edge_exists(conn, source_id, target_id):
    """Check if edge exists in either direction."""
    row = conn.execute(
        """SELECT id FROM edges
           WHERE (source_id = ? AND target_id = ?)
              OR (source_id = ? AND target_id = ?)""",
        (source_id, target_id, target_id, source_id)
    ).fetchone()
    return row is not None


def create_edge(conn, source_id, target_id, edge_type='affiliation'):
    """Create edge between two nodes."""
    conn.execute(
        "INSERT INTO edges (source_id, target_id, type) VALUES (?, ?, ?)",
        (source_id, target_id, edge_type)
    )


def main():
    # Read contributors
    with open(CONTRIBUTORS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Parse contributors (skip header and blank lines)
    contributors = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, header, and markdown formatting
        if not line or line.startswith('#'):
            continue
        contributors.append(line)

    print(f"Found {len(contributors)} contributors to import")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Get or create Il Carroccio
        carroccio_id, carroccio_created = get_or_create_node(conn, "Il Carroccio", "institution")
        if carroccio_created:
            print("Created 'Il Carroccio' node")
        else:
            print(f"Found existing 'Il Carroccio' node (id={carroccio_id})")

        stats = {
            'nodes_created': 0,
            'nodes_existed': 0,
            'edges_created': 0,
            'edges_existed': 0,
            'skipped': 0
        }

        for contributor in contributors:
            # Get or create contributor node
            contributor_id, was_created = get_or_create_node(conn, contributor, 'person')

            if contributor_id is None:
                stats['skipped'] += 1
                continue

            if was_created:
                stats['nodes_created'] += 1
            else:
                stats['nodes_existed'] += 1

            # Check if edge exists
            if edge_exists(conn, contributor_id, carroccio_id):
                stats['edges_existed'] += 1
            else:
                create_edge(conn, contributor_id, carroccio_id, 'affiliation')
                stats['edges_created'] += 1

        conn.commit()

        print("\n=== Import Complete ===")
        print(f"Nodes created:  {stats['nodes_created']}")
        print(f"Nodes existed:  {stats['nodes_existed']}")
        print(f"Edges created:  {stats['edges_created']}")
        print(f"Edges existed:  {stats['edges_existed']}")
        print(f"Skipped:        {stats['skipped']}")

    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
