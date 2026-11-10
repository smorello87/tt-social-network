#!/usr/bin/env python3
"""
Step 3 of the contributor pipeline: import a reviewed roster into network.db.

- Creates the periodical node (institution/periodical) if missing
- "existing" entries link to their node_id (which must be a person node, not the
  periodical itself); "new" entries create a person node and fail if a node with the
  same normalized name already exists (unless it is a person already linked to this
  periodical, so re-running an import is harmless)
- Refuses to run while any entry is "unresolved" (see build_roster.py)
- Backs up the database (data/editor/backups/) before writing
- Edges are written in canonical direction (source_id <= target_id)
- After committing, recalculates shared institutions / needs_review for all edges

Usage: python3 import_contributors.py iam [--dry-run]
"""

import json
import sqlite3
import sys
from pathlib import Path

import database
from database import backup_db, normalize_name, recalculate_all_shared_institutions

DATA_DIR = Path(__file__).resolve().parent.parent


def get_or_create_node(conn, name, node_type='person', subtype=None):
    normalized = normalize_name(name)
    row = conn.execute("SELECT id FROM nodes WHERE name_normalized = ?", (normalized,)).fetchone()
    if row:
        return row[0], False
    cursor = conn.execute(
        "INSERT INTO nodes (name, name_normalized, type, subtype) VALUES (?, ?, ?, ?)",
        (name.strip(), normalized, node_type, subtype)
    )
    return cursor.lastrowid, True


def edge_exists(conn, a_id, b_id):
    return conn.execute(
        """SELECT 1 FROM edges
           WHERE (source_id = ? AND target_id = ?) OR (source_id = ? AND target_id = ?)""",
        (a_id, b_id, b_id, a_id)
    ).fetchone() is not None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry_run = '--dry-run' in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)

    roster = json.loads((DATA_DIR / args[0] / "roster.json").read_text(encoding='utf-8'))
    people = roster['people']

    unresolved = [p['name'] for p in people if p['status'] == 'unresolved']
    if unresolved:
        sys.exit("Unresolved matches; add each to review.json 'match' or 'new' and re-run build_roster.py:\n  "
                 + "\n  ".join(unresolved))

    if not dry_run:
        print(f"Backup: {backup_db()}")

    conn = sqlite3.connect(database.DB_PATH)
    try:
        periodical_id, created = get_or_create_node(conn, roster['periodical'], 'institution', 'periodical')
        if conn.execute("SELECT type FROM nodes WHERE id = ?", (periodical_id,)).fetchone()[0] != 'institution':
            sys.exit(f"Periodical node {roster['periodical']!r} (id={periodical_id}) is not an institution; aborting")
        print(f"{'Created' if created else 'Found'} '{roster['periodical']}' node (id={periodical_id})")

        stats = {'nodes_created': 0, 'nodes_existed': 0, 'edges_created': 0, 'edges_existed': 0}
        for person in people:
            if person['status'] == 'existing':
                row = conn.execute("SELECT name FROM nodes WHERE id = ?", (person['node_id'],)).fetchone()
                if not row:
                    raise ValueError(f"node_id {person['node_id']} for {person['name']} not found")
                node_id, was_created = person['node_id'], False
                if node_id == periodical_id:
                    sys.exit(f"{person['name']!r} resolves to the periodical node itself (id={node_id}); aborting")
                if conn.execute("SELECT type FROM nodes WHERE id = ?", (node_id,)).fetchone()[0] != 'person':
                    sys.exit(f"{person['name']!r} resolves to node id={node_id}, which is not a person; aborting")
                if row[0] != person['name']:
                    print(f"  linked {person['name']!r} -> existing {row[0]!r} (id={node_id})")
            else:
                clash = conn.execute("SELECT id, type FROM nodes WHERE name_normalized = ?",
                                     (normalize_name(person['name']),)).fetchone()
                if clash and not (clash[1] == 'person' and edge_exists(conn, clash[0], periodical_id)):
                    sys.exit(f"{person['name']!r} is marked new but a node with that name already exists "
                             f"(id={clash[0]}, type={clash[1]}); add it to review.json 'match' and re-run build_roster.py")
                node_id, was_created = get_or_create_node(conn, person['name'], 'person')

            stats['nodes_created' if was_created else 'nodes_existed'] += 1
            if edge_exists(conn, node_id, periodical_id):
                stats['edges_existed'] += 1
            else:
                conn.execute("INSERT INTO edges (source_id, target_id, type) VALUES (?, ?, 'affiliation')",
                             tuple(sorted((node_id, periodical_id))))
                stats['edges_created'] += 1

        if dry_run:
            conn.rollback()
            print("\n=== Dry run (rolled back) ===")
        else:
            conn.commit()
            print("\n=== Import Complete ===")
            print(f"Recalculated shared institutions for {recalculate_all_shared_institutions()} edges")
        for k, v in stats.items():
            print(f"{k.replace('_', ' ').capitalize() + ':':<17}{v}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
