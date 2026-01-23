#!/usr/bin/env python3
"""
Omeka API Import Script
Fetches items from Italian American Imprints collection into staging SQLite database.

Usage:
    python omeka_import.py              # Import all items
    python omeka_import.py --collection 2  # Import specific collection
    python omeka_import.py --resume     # Skip already-imported items
"""

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


def strip_html(text):
    """Remove HTML tags from text."""
    if not text:
        return text
    return re.sub(r'<[^>]+>', '', text)

# Configuration
API_BASE = "https://italianamericanimprints.omeka.net/api"
DB_PATH = Path(__file__).parent / "omeka_staging.db"
PER_PAGE = 50  # Omeka default


def init_db():
    """Initialize the staging database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS omeka_items (
            id INTEGER PRIMARY KEY,
            title TEXT,
            creator TEXT,
            publisher TEXT,
            date TEXT,
            description TEXT,
            collection_id INTEGER,
            collection_name TEXT,
            tags TEXT,
            raw_json TEXT,
            imported_at TIMESTAMP,
            skip BOOLEAN DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS omeka_collections (
            id INTEGER PRIMARY KEY,
            title TEXT,
            item_count INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_items_collection ON omeka_items(collection_id);
        CREATE INDEX IF NOT EXISTS idx_items_skip ON omeka_items(skip);
    """)
    conn.commit()
    return conn


def api_get(endpoint, params=None):
    """Make a GET request to the Omeka API."""
    url = f"{API_BASE}/{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except URLError as e:
        print(f"URL Error: {e.reason}")
        return None


def extract_element_text(item, element_name):
    """Extract a specific element text from item's element_texts array."""
    element_texts = item.get("element_texts", [])
    for et in element_texts:
        element = et.get("element", {})
        if element.get("name") == element_name:
            return et.get("text", "")
    return ""


def fetch_collections(conn):
    """Fetch all collections and store them."""
    print("Fetching collections...")
    data = api_get("collections")
    if not data:
        print("Failed to fetch collections")
        return []

    collections = []
    for coll in data:
        coll_id = coll.get("id")
        # Get collection title from element_texts
        title = strip_html(extract_element_text(coll, "Title")) or f"Collection {coll_id}"
        item_count = coll.get("items", {}).get("count", 0)

        conn.execute("""
            INSERT OR REPLACE INTO omeka_collections (id, title, item_count)
            VALUES (?, ?, ?)
        """, (coll_id, title, item_count))

        collections.append({"id": coll_id, "title": title, "count": item_count})
        print(f"  Collection {coll_id}: {title} ({item_count} items)")

    conn.commit()
    return collections


def get_existing_ids(conn):
    """Get set of already-imported item IDs."""
    cursor = conn.execute("SELECT id FROM omeka_items")
    return set(row[0] for row in cursor.fetchall())


def fetch_items(conn, collection_id=None, resume=False):
    """Fetch all items (optionally filtered by collection)."""
    existing_ids = get_existing_ids(conn) if resume else set()
    if resume and existing_ids:
        print(f"Resume mode: {len(existing_ids)} items already imported")

    # Build collection name lookup
    coll_names = {}
    for row in conn.execute("SELECT id, title FROM omeka_collections"):
        coll_names[row[0]] = row[1]

    page = 1
    total_imported = 0
    total_skipped = 0

    while True:
        params = {"page": page, "per_page": PER_PAGE}
        if collection_id:
            params["collection"] = collection_id

        print(f"Fetching page {page}...", end=" ", flush=True)
        data = api_get("items", params)

        if not data:
            print("No data returned")
            break

        if len(data) == 0:
            print("No more items")
            break

        imported_this_page = 0
        for item in data:
            item_id = item.get("id")

            # Skip if already imported (resume mode)
            if item_id in existing_ids:
                total_skipped += 1
                continue

            # Extract metadata (strip HTML tags)
            title = strip_html(extract_element_text(item, "Title"))
            creator = strip_html(extract_element_text(item, "Creator"))
            publisher = strip_html(extract_element_text(item, "Publisher"))
            date = strip_html(extract_element_text(item, "Date"))
            description = extract_element_text(item, "Description")  # Keep HTML in description

            # Get collection info
            coll = item.get("collection")
            coll_id = coll.get("id") if coll else None
            coll_name = strip_html(coll_names.get(coll_id, "")) if coll_id else ""

            # Get tags
            tags_data = item.get("tags", [])
            tags = json.dumps([t.get("name", "") for t in tags_data])

            # Store item
            conn.execute("""
                INSERT OR REPLACE INTO omeka_items
                (id, title, creator, publisher, date, description,
                 collection_id, collection_name, tags, raw_json, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, title, creator, publisher, date, description,
                coll_id, coll_name, tags, json.dumps(item), datetime.now().isoformat()
            ))

            imported_this_page += 1
            total_imported += 1

        conn.commit()
        print(f"imported {imported_this_page} items")

        # Check if we've reached the end
        if len(data) < PER_PAGE:
            break

        page += 1
        time.sleep(0.5)  # Be nice to the API

    return total_imported, total_skipped


def show_stats(conn):
    """Show database statistics."""
    total = conn.execute("SELECT COUNT(*) FROM omeka_items").fetchone()[0]
    skipped = conn.execute("SELECT COUNT(*) FROM omeka_items WHERE skip = 1").fetchone()[0]

    print(f"\n{'='*50}")
    print("Database Statistics")
    print(f"{'='*50}")
    print(f"Total items: {total}")
    print(f"Marked to skip: {skipped}")
    print(f"Available for import: {total - skipped}")

    print("\nBy collection:")
    for row in conn.execute("""
        SELECT collection_name, COUNT(*) as count
        FROM omeka_items
        GROUP BY collection_id
        ORDER BY count DESC
    """):
        name = row[0] or "(No collection)"
        print(f"  {name}: {row[1]}")


def main():
    parser = argparse.ArgumentParser(description="Import items from Omeka API")
    parser.add_argument("--collection", "-c", type=int, help="Import only this collection ID")
    parser.add_argument("--resume", "-r", action="store_true", help="Skip already-imported items")
    parser.add_argument("--stats", "-s", action="store_true", help="Show database stats only")
    args = parser.parse_args()

    print(f"Database: {DB_PATH}")
    conn = init_db()

    if args.stats:
        show_stats(conn)
        return

    # Fetch collections first
    collections = fetch_collections(conn)
    if not collections:
        print("Warning: No collections found")

    # Calculate expected total
    if args.collection:
        expected = next((c["count"] for c in collections if c["id"] == args.collection), 0)
        print(f"\nImporting collection {args.collection} ({expected} items)...")
    else:
        expected = sum(c["count"] for c in collections)
        print(f"\nImporting all items (~{expected} expected)...")

    # Fetch items
    imported, skipped = fetch_items(conn, args.collection, args.resume)

    print(f"\n{'='*50}")
    print(f"Import complete!")
    print(f"  Imported: {imported}")
    if skipped:
        print(f"  Skipped (already imported): {skipped}")
    print(f"{'='*50}")

    show_stats(conn)
    conn.close()


if __name__ == "__main__":
    main()
