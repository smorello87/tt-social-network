#!/usr/bin/env python3
"""
Omeka Staging Editor
Simple Flask app to review and clean imported Omeka data before parsing to network.

Usage:
    python omeka_editor.py   # Opens at http://localhost:5002
"""

import json
import re
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS


def extract_year(date_str):
    """Extract first 4-digit year from date string."""
    if not date_str:
        return None
    match = re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', str(date_str))
    return int(match.group(1)) if match else None

app = Flask(__name__)
CORS(app)

DB_PATH = Path(__file__).parent / "omeka_staging.db"
NETWORK_DB_PATH = Path(__file__).parent / "network.db"


def normalize_name(name):
    """Normalize name for matching (lowercase, strip extra whitespace)."""
    if not name:
        return ""
    return " ".join(name.lower().split())


def get_or_create_node(conn, name, node_type):
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
        return row[0], False  # Existing node

    # Create new node
    cursor = conn.execute(
        "INSERT INTO nodes (name, name_normalized, type) VALUES (?, ?, ?)",
        (name, normalized, node_type)
    )
    return cursor.lastrowid, True  # New node


def create_edge_if_not_exists(conn, source_id, target_id, edge_type='affiliation'):
    """Create edge if it doesn't exist. Returns True if created."""
    if not source_id or not target_id or source_id == target_id:
        return False

    # Check if exists (in either direction)
    row = conn.execute(
        """SELECT id FROM edges
           WHERE (source_id = ? AND target_id = ?)
              OR (source_id = ? AND target_id = ?)""",
        (source_id, target_id, target_id, source_id)
    ).fetchone()

    if row:
        return False

    conn.execute(
        "INSERT INTO edges (source_id, target_id, type) VALUES (?, ?, ?)",
        (source_id, target_id, edge_type)
    )
    return True


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# Frontend Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the editor UI."""
    return render_template('omeka_editor.html')


# =============================================================================
# API Routes
# =============================================================================

@app.route('/api/stats')
def get_stats():
    """Get database statistics."""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM omeka_items").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM omeka_items WHERE skip = 1").fetchone()[0]
        imported = conn.execute("SELECT COUNT(*) FROM omeka_items WHERE imported = 1").fetchone()[0]

        # Collection counts
        collections = []
        for row in conn.execute("""
            SELECT collection_id, collection_name, COUNT(*) as count
            FROM omeka_items
            GROUP BY collection_id
            ORDER BY count DESC
        """):
            collections.append({
                "id": row[0],
                "name": row[1] or "(No collection)",
                "count": row[2]
            })

        # Extract all unique tags with counts
        tags = {}
        for row in conn.execute("SELECT tags FROM omeka_items WHERE tags IS NOT NULL"):
            try:
                tag_list = json.loads(row[0])
                for tag in tag_list:
                    tags[tag] = tags.get(tag, 0) + 1
            except:
                pass

        # Sort tags by count
        sorted_tags = sorted(tags.items(), key=lambda x: -x[1])

        return jsonify({
            "total": total,
            "skipped": skipped,
            "imported": imported,
            "available": total - skipped,
            "collections": collections,
            "tags": [{"name": t[0], "count": t[1]} for t in sorted_tags]
        })
    finally:
        conn.close()


@app.route('/api/items')
def get_items():
    """Get paginated list of items with filtering."""
    conn = get_db()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '')
        collection_id = request.args.get('collection')
        tag = request.args.get('tag', '')
        show_skipped = request.args.get('show_skipped', 'true') == 'true'
        show_imported = request.args.get('show_imported', 'true') == 'true'
        sort_by = request.args.get('sort_by', 'id')
        sort_order = request.args.get('sort_order', 'asc')

        # Validate sort parameters
        allowed_sort_fields = ['id', 'title', 'creator', 'publisher', 'date', 'collection_name']
        if sort_by not in allowed_sort_fields:
            sort_by = 'id'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'asc'

        query = "SELECT * FROM omeka_items WHERE 1=1"
        params = []

        if not show_skipped:
            query += " AND skip = 0"

        if not show_imported:
            query += " AND (imported = 0 OR imported IS NULL)"

        if collection_id:
            query += " AND collection_id = ?"
            params.append(collection_id)

        if tag:
            # Filter by tag (stored as JSON array)
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        if search:
            query += " AND (title LIKE ? OR creator LIKE ? OR publisher LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_query, params).fetchone()[0]

        # For date sorting, we need to fetch all and sort in Python (complex date formats)
        if sort_by == 'date':
            rows = conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item['_sort_year'] = extract_year(item.get('date'))
                if item.get('tags'):
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except:
                        item['tags'] = []
                else:
                    item['tags'] = []
                item.pop('raw_json', None)
                items.append(item)

            # Sort by extracted year (None values always go to end)
            if sort_order == 'desc':
                items.sort(key=lambda x: (x['_sort_year'] is None, -(x['_sort_year'] or 0)))
            else:
                items.sort(key=lambda x: (x['_sort_year'] is None, x['_sort_year'] or 0))

            # Remove sort helper and paginate
            for item in items:
                item.pop('_sort_year', None)
            items = items[(page - 1) * per_page : page * per_page]
        else:
            # Regular SQL sorting and pagination
            query += f" ORDER BY {sort_by} {sort_order.upper()} LIMIT ? OFFSET ?"
            params.extend([per_page, (page - 1) * per_page])
            rows = conn.execute(query, params).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                if item.get('tags'):
                    try:
                        item['tags'] = json.loads(item['tags'])
                    except:
                        item['tags'] = []
                else:
                    item['tags'] = []
                item.pop('raw_json', None)
                items.append(item)

        return jsonify({
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 1
        })
    finally:
        conn.close()


@app.route('/api/items/<int:item_id>')
def get_item(item_id):
    """Get single item with full details including raw JSON."""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM omeka_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return jsonify({"error": "Item not found"}), 404

        item = dict(row)
        if item.get('tags'):
            try:
                item['tags'] = json.loads(item['tags'])
            except:
                item['tags'] = []
        if item.get('raw_json'):
            try:
                item['raw_json'] = json.loads(item['raw_json'])
            except:
                pass

        return jsonify(item)
    finally:
        conn.close()


@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an item."""
    conn = get_db()
    try:
        data = request.json

        updates = []
        params = []

        for field in ['title', 'creator', 'publisher', 'date', 'notes']:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])

        if 'skip' in data:
            updates.append("skip = ?")
            params.append(1 if data['skip'] else 0)

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        params.append(item_id)
        query = f"UPDATE omeka_items SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()

        return jsonify({"success": True})
    finally:
        conn.close()


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM omeka_items WHERE id = ?", (item_id,))
        conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()


@app.route('/api/batch/skip', methods=['POST'])
def batch_skip():
    """Mark multiple items as skip/not skip."""
    conn = get_db()
    try:
        data = request.json
        item_ids = data.get('item_ids', [])
        skip = data.get('skip', True)

        if not item_ids:
            return jsonify({"error": "No items specified"}), 400

        placeholders = ",".join("?" * len(item_ids))
        conn.execute(
            f"UPDATE omeka_items SET skip = ? WHERE id IN ({placeholders})",
            [1 if skip else 0] + item_ids
        )
        conn.commit()

        return jsonify({"success": True, "updated": len(item_ids)})
    finally:
        conn.close()


@app.route('/api/batch/delete', methods=['POST'])
def batch_delete():
    """Delete multiple items."""
    conn = get_db()
    try:
        data = request.json
        item_ids = data.get('item_ids', [])

        if not item_ids:
            return jsonify({"error": "No items specified"}), 400

        placeholders = ",".join("?" * len(item_ids))
        conn.execute(f"DELETE FROM omeka_items WHERE id IN ({placeholders})", item_ids)
        conn.commit()

        return jsonify({"success": True, "deleted": len(item_ids)})
    finally:
        conn.close()


# =============================================================================
# Import to Network
# =============================================================================

@app.route('/api/import', methods=['POST'])
def import_to_network():
    """Import selected items to network database."""
    data = request.json
    item_ids = data.get('item_ids', [])
    import_all = data.get('import_all', False)

    staging_conn = get_db()
    network_conn = sqlite3.connect(NETWORK_DB_PATH)
    network_conn.row_factory = sqlite3.Row

    try:
        # Get items to import
        if import_all:
            rows = staging_conn.execute(
                "SELECT id, creator, publisher FROM omeka_items WHERE skip = 0"
            ).fetchall()
        elif item_ids:
            placeholders = ",".join("?" * len(item_ids))
            rows = staging_conn.execute(
                f"SELECT id, creator, publisher FROM omeka_items WHERE id IN ({placeholders})",
                item_ids
            ).fetchall()
        else:
            return jsonify({"error": "No items specified"}), 400

        stats = {
            "items_processed": 0,
            "nodes_created": 0,
            "edges_created": 0,
            "skipped_no_creator": 0,
            "skipped_no_publisher": 0
        }

        for row in rows:
            creator = row['creator']
            publisher = row['publisher']

            if not creator or not creator.strip():
                stats["skipped_no_creator"] += 1
                continue
            if not publisher or not publisher.strip():
                stats["skipped_no_publisher"] += 1
                continue

            # Handle multiple creators (comma or "and" separated)
            creators = re.split(r',\s*|\s+and\s+', creator)

            for c in creators:
                c = c.strip()
                if not c:
                    continue

                # Create/get creator node (person)
                creator_id, creator_created = get_or_create_node(network_conn, c, 'person')
                if creator_created:
                    stats["nodes_created"] += 1

                # Create/get publisher node (institution)
                publisher_id, publisher_created = get_or_create_node(network_conn, publisher, 'institution')
                if publisher_created:
                    stats["nodes_created"] += 1

                # Create edge
                if creator_id and publisher_id:
                    if create_edge_if_not_exists(network_conn, creator_id, publisher_id, 'affiliation'):
                        stats["edges_created"] += 1

            stats["items_processed"] += 1

            # Mark item as imported in staging db
            staging_conn.execute(
                "UPDATE omeka_items SET imported = 1 WHERE id = ?",
                (row['id'],)
            )

        network_conn.commit()
        staging_conn.commit()

        return jsonify({
            "success": True,
            "stats": stats
        })

    finally:
        staging_conn.close()
        network_conn.close()


@app.route('/api/network/stats')
def network_stats():
    """Get current network database statistics."""
    if not NETWORK_DB_PATH.exists():
        return jsonify({"error": "Network database not found"}), 404

    conn = sqlite3.connect(NETWORK_DB_PATH)
    try:
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        persons = conn.execute("SELECT COUNT(*) FROM nodes WHERE type = 'person'").fetchone()[0]
        institutions = conn.execute("SELECT COUNT(*) FROM nodes WHERE type = 'institution'").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

        return jsonify({
            "nodes": nodes,
            "persons": persons,
            "institutions": institutions,
            "edges": edges
        })
    finally:
        conn.close()


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Run omeka_import.py first to import data.")
        exit(1)

    print(f"\n{'='*50}")
    print("Omeka Staging Editor")
    print(f"{'='*50}")
    print(f"\nDatabase: {DB_PATH}")
    print(f"Editor:   http://localhost:5002")
    print(f"\n{'='*50}\n")
    app.run(debug=False, port=5002, threaded=True)
