#!/usr/bin/env python3
"""Import WorldCat publisher data from markdown files."""

import sqlite3
import os
import re
from pathlib import Path

EXPORT_DIR = "/Users/veritas44/Downloads/github/worldcat/export"
DB_PATH = "/Users/veritas44/Downloads/github/tt-social-network/data/editor/network.db"

# Manual mapping of file names (without .md) to existing institution names in DB
# None means create new with the file name
INSTITUTION_MAPPING = {
    "Bagnasco Press": "Bagnasco Press",
    "Bruce Humphries": "Bruce Humphries, Inc.",
    "Coccè Press": "Coccè Press",
    "Colamco Press": None,  # new
    "Creative Printing": None,  # new
    "Divagando Corp": "Divagando Corp.",
    "Division Typesetting Co": None,  # new
    "Division Typesetting": "Division Typesetting Co",  # merge with above
    "Edizioni Rivista Omnia,": "Edizioni Rivista Omnia",  # clean up trailing comma
    "Eloquent Press": "Eloquent Press Corp.",
    "Eugene Printing": None,  # new
    "Europe America Press": None,  # new
    "Fairmount Publishing Co": None,  # new
    "Follia di New York": "La Follia di New York",
    "Francesco Tocci": None,  # new (publisher, not person)
    "Frugone": "Frugone & Balletto",
    "Gastaldi Editore": "Gastaldi Editore",
    "Grassi": None,  # new (different from V. Grassi)
    "Il Carroccio": "Il Carroccio",
    "Il fauno": "Il fauno",  # new (Fauno Film is different)
    "Il Pungolo Verde": None,  # new
    "Italian Book Company": "Italian Book Company",
    "La nuova Italia letteraria": None,  # new
    "La Procellaria": None,  # new
    "Linotipografia B. Moriniello": None,  # new
    "Nicoletti": "Nicoletti Bros Press",
    "Romualdi Levitas": None,  # new
    "S.F. Vanni": "SF Vanni Publishers and Booksellers",
    "Susmel & C": "Susmel & C.",
    "The Emporium Press": None,  # new
    "V. Grassi": None,  # new
    "Vigo Press": "The Vigo Press",
}

def normalize_name(name):
    """Normalize name for matching."""
    return re.sub(r'\s+', ' ', name.strip().lower())

def get_or_create_node(cursor, name, node_type):
    """Get existing node ID or create new one."""
    name = name.strip()
    if not name:
        return None

    # Check for exact match first
    cursor.execute("SELECT id FROM nodes WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Check for normalized match
    normalized = normalize_name(name)
    cursor.execute("SELECT id, name FROM nodes WHERE name_normalized = ?", (normalized,))
    row = cursor.fetchone()
    if row:
        return row[0]

    # Create new node
    cursor.execute(
        "INSERT INTO nodes (name, name_normalized, type) VALUES (?, ?, ?)",
        (name, normalized, node_type)
    )
    return cursor.lastrowid

def edge_exists(cursor, source_id, target_id):
    """Check if edge already exists (in either direction)."""
    cursor.execute(
        """SELECT id FROM edges
           WHERE (source_id = ? AND target_id = ?)
              OR (source_id = ? AND target_id = ?)""",
        (source_id, target_id, target_id, source_id)
    )
    return cursor.fetchone() is not None

def parse_md_file(filepath):
    """Parse markdown file and return list of names."""
    names = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                names.append(line)
    return names

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stats = {
        'institutions_created': 0,
        'institutions_found': 0,
        'persons_created': 0,
        'persons_found': 0,
        'edges_created': 0,
        'edges_skipped': 0,
    }

    # Process each markdown file
    for md_file in Path(EXPORT_DIR).glob("*.md"):
        file_stem = md_file.stem

        # Skip if not in mapping
        if file_stem not in INSTITUTION_MAPPING:
            print(f"SKIP: {file_stem} (not in mapping)")
            continue

        # Determine institution name
        mapped_name = INSTITUTION_MAPPING[file_stem]
        if mapped_name is None:
            institution_name = file_stem
        else:
            institution_name = mapped_name

        # Get or create institution
        cursor.execute("SELECT id FROM nodes WHERE name = ? AND type = 'institution'", (institution_name,))
        row = cursor.fetchone()
        if row:
            institution_id = row[0]
            stats['institutions_found'] += 1
            print(f"FOUND institution: {institution_name} (id={institution_id})")
        else:
            institution_id = get_or_create_node(cursor, institution_name, 'institution')
            stats['institutions_created'] += 1
            print(f"CREATED institution: {institution_name} (id={institution_id})")

        # Parse names from file
        names = parse_md_file(md_file)
        print(f"  Processing {len(names)} entries from {md_file.name}")

        for name in names:
            # Some entries are institutions (like "Order Sons of Italy in America")
            # Check if it already exists as institution
            cursor.execute("SELECT id, type FROM nodes WHERE name = ?", (name,))
            row = cursor.fetchone()

            if row:
                person_id = row[0]
                node_type = row[1]
                stats['persons_found'] += 1
            else:
                # Default to person type for new entries
                person_id = get_or_create_node(cursor, name, 'person')
                node_type = 'person'
                stats['persons_created'] += 1

            # Create edge if not exists
            if not edge_exists(cursor, person_id, institution_id):
                cursor.execute(
                    "INSERT INTO edges (source_id, target_id, type, needs_review) VALUES (?, ?, 'affiliation', 0)",
                    (person_id, institution_id)
                )
                stats['edges_created'] += 1
            else:
                stats['edges_skipped'] += 1

    conn.commit()
    conn.close()

    print("\n=== Import Summary ===")
    print(f"Institutions found: {stats['institutions_found']}")
    print(f"Institutions created: {stats['institutions_created']}")
    print(f"Persons found: {stats['persons_found']}")
    print(f"Persons created: {stats['persons_created']}")
    print(f"Edges created: {stats['edges_created']}")
    print(f"Edges skipped (already exist): {stats['edges_skipped']}")

if __name__ == "__main__":
    main()
