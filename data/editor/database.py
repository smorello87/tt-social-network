"""
SQLite database operations for the network data editor.
Handles nodes, edges, and shared institution caching.
"""

import sqlite3
import re
import shutil
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

DB_PATH = Path(__file__).parent / "network.db"
BACKUP_DIR = Path(__file__).parent / "backups"

def normalize_name(name: str) -> str:
    """Normalize name for matching: strip whitespace, collapse spaces, lowercase."""
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name.lower()

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database schema."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                name_normalized TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('person', 'institution', 'unknown')),
                subtype TEXT
            );

            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                target_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ('personal', 'affiliation', 'unknown')),
                needs_review BOOLEAN DEFAULT 0,
                UNIQUE(source_id, target_id)
            );

            CREATE TABLE IF NOT EXISTS shared_institutions (
                edge_id INTEGER NOT NULL REFERENCES edges(id) ON DELETE CASCADE,
                institution_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
                PRIMARY KEY (edge_id, institution_id)
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_normalized ON nodes(name_normalized);
            CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
            CREATE INDEX IF NOT EXISTS idx_edges_review ON edges(needs_review);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        """)

def backup_db():
    """Create a timestamped backup of the database. Keeps last 10 backups."""
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f"network.db.{timestamp}"
    shutil.copy2(DB_PATH, backup_path)
    # Remove old backups, keep last 10
    backups = sorted(BACKUP_DIR.glob("network.db.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[10:]:
        old.unlink()
    return backup_path

# =============================================================================
# Node Operations
# =============================================================================

def get_nodes(type_filter=None, subtype_filter=None, search=None, page=1, per_page=50, sort_by=None, sort_dir='desc'):
    """Get paginated list of nodes with optional filters and sorting."""
    with get_db() as conn:
        query = """
            SELECT n.*,
                   (SELECT COUNT(*) FROM edges e WHERE e.source_id = n.id OR e.target_id = n.id) as connection_count
            FROM nodes n
            WHERE 1=1
        """
        params = []

        if type_filter:
            query += " AND n.type = ?"
            params.append(type_filter)

        if subtype_filter:
            if subtype_filter == 'uncategorized':
                query += " AND n.subtype IS NULL"
            else:
                query += " AND n.subtype = ?"
                params.append(subtype_filter)

        if search:
            query += " AND n.name_normalized LIKE ?"
            params.append(f"%{normalize_name(search)}%")

        # Get total count - build count query with same filters
        count_query = "SELECT COUNT(*) as count FROM nodes n WHERE 1=1"
        count_params = []
        if type_filter:
            count_query += " AND n.type = ?"
            count_params.append(type_filter)
        if subtype_filter:
            if subtype_filter == 'uncategorized':
                count_query += " AND n.subtype IS NULL"
            else:
                count_query += " AND n.subtype = ?"
                count_params.append(subtype_filter)
        if search:
            count_query += " AND n.name_normalized LIKE ?"
            count_params.append(f"%{normalize_name(search)}%")

        total = conn.execute(count_query, count_params).fetchone()["count"]

        # Add ordering
        sort_direction = 'DESC' if sort_dir == 'desc' else 'ASC'
        if sort_by == 'name':
            query += f" ORDER BY n.name {sort_direction}"
        elif sort_by == 'type':
            query += f" ORDER BY n.type {sort_direction}"
        elif sort_by == 'connections':
            query += f" ORDER BY connection_count {sort_direction}"
        else:
            query += " ORDER BY n.name ASC"

        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])

        rows = conn.execute(query, params).fetchall()

        return {
            "nodes": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

def get_node(node_id):
    """Get single node by ID."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT n.*,
                   (SELECT COUNT(*) FROM edges e WHERE e.source_id = n.id OR e.target_id = n.id) as connection_count
            FROM nodes n WHERE n.id = ?
        """, (node_id,)).fetchone()
        return dict(row) if row else None

def get_node_by_name(name):
    """Get node by exact name."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM nodes WHERE name_normalized = ?",
            (normalize_name(name),)
        ).fetchone()
        return dict(row) if row else None

def create_node(name, node_type, subtype=None):
    """Create a new node."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO nodes (name, name_normalized, type, subtype) VALUES (?, ?, ?, ?)",
            (name.strip(), normalize_name(name), node_type, subtype)
        )
        return cursor.lastrowid

def update_node(node_id, name=None, node_type=None, subtype=None):
    """Update a node."""
    with get_db() as conn:
        # Build dynamic update
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name.strip())
            updates.append("name_normalized = ?")
            params.append(normalize_name(name))
        if node_type is not None:
            updates.append("type = ?")
            params.append(node_type)
        if subtype is not None:
            # Allow setting to NULL with empty string
            updates.append("subtype = ?")
            params.append(subtype if subtype else None)

        if updates:
            params.append(node_id)
            conn.execute(f"UPDATE nodes SET {', '.join(updates)} WHERE id = ?", params)

        # Recalculate needs_review for affected edges
        recalculate_needs_review_for_node(conn, node_id)

def delete_node(node_id):
    """Delete a node (cascades to edges)."""
    with get_db() as conn:
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))

def merge_nodes(primary_id, secondary_id):
    """
    Merge two nodes: transfer all edges from secondary to primary, then delete secondary.
    Returns count of edges transferred.
    """
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Get node info for validation
        primary = conn.execute("SELECT * FROM nodes WHERE id = ?", (primary_id,)).fetchone()
        secondary = conn.execute("SELECT * FROM nodes WHERE id = ?", (secondary_id,)).fetchone()

        if not primary or not secondary:
            raise ValueError("One or both nodes not found")

        if primary_id == secondary_id:
            raise ValueError("Cannot merge a node with itself")

        edges_transferred = 0

        # Transfer edges where secondary is the source
        edges_as_source = conn.execute(
            "SELECT id, target_id, type FROM edges WHERE source_id = ?",
            (secondary_id,)
        ).fetchall()

        for edge in edges_as_source:
            target_id = edge["target_id"]
            # Skip if this would create a self-loop
            if target_id == primary_id:
                conn.execute("DELETE FROM edges WHERE id = ?", (edge["id"],))
                continue
            # Check if edge already exists
            existing = conn.execute(
                "SELECT id FROM edges WHERE source_id = ? AND target_id = ?",
                (primary_id, target_id)
            ).fetchone()
            if existing:
                # Edge already exists, just delete the duplicate
                conn.execute("DELETE FROM edges WHERE id = ?", (edge["id"],))
            else:
                # Transfer edge to primary
                conn.execute(
                    "UPDATE edges SET source_id = ? WHERE id = ?",
                    (primary_id, edge["id"])
                )
                edges_transferred += 1

        # Transfer edges where secondary is the target
        edges_as_target = conn.execute(
            "SELECT id, source_id, type FROM edges WHERE target_id = ?",
            (secondary_id,)
        ).fetchall()

        for edge in edges_as_target:
            source_id = edge["source_id"]
            # Skip if this would create a self-loop
            if source_id == primary_id:
                conn.execute("DELETE FROM edges WHERE id = ?", (edge["id"],))
                continue
            # Check if edge already exists
            existing = conn.execute(
                "SELECT id FROM edges WHERE source_id = ? AND target_id = ?",
                (source_id, primary_id)
            ).fetchone()
            if existing:
                # Edge already exists, just delete the duplicate
                conn.execute("DELETE FROM edges WHERE id = ?", (edge["id"],))
            else:
                # Transfer edge to primary
                conn.execute(
                    "UPDATE edges SET target_id = ? WHERE id = ?",
                    (primary_id, edge["id"])
                )
                edges_transferred += 1

        # Delete the secondary node (any remaining edges will cascade delete)
        conn.execute("DELETE FROM nodes WHERE id = ?", (secondary_id,))

        return {
            "primary_name": primary["name"],
            "secondary_name": secondary["name"],
            "edges_transferred": edges_transferred
        }

def get_all_nodes_for_dropdown():
    """Get all nodes for autocomplete/dropdown (lightweight)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, type FROM nodes ORDER BY name"
        ).fetchall()
        return [dict(row) for row in rows]

def get_node_connections(node_id):
    """Get all nodes connected to a given node, including their connection counts."""
    with get_db() as conn:
        # Get connections where this node is the source
        as_source = conn.execute("""
            SELECT n.id, n.name, n.type, e.type as edge_type,
                   (SELECT COUNT(*) FROM edges e2 WHERE e2.source_id = n.id OR e2.target_id = n.id) as connection_count
            FROM nodes n
            JOIN edges e ON e.target_id = n.id
            WHERE e.source_id = ?
            ORDER BY n.name
        """, (node_id,)).fetchall()

        # Get connections where this node is the target
        as_target = conn.execute("""
            SELECT n.id, n.name, n.type, e.type as edge_type,
                   (SELECT COUNT(*) FROM edges e2 WHERE e2.source_id = n.id OR e2.target_id = n.id) as connection_count
            FROM nodes n
            JOIN edges e ON e.source_id = n.id
            WHERE e.target_id = ?
            ORDER BY n.name
        """, (node_id,)).fetchall()

        # Combine and dedupe
        connections = {}
        for row in as_source:
            connections[row['id']] = dict(row)
        for row in as_target:
            connections[row['id']] = dict(row)

        return list(connections.values())

# =============================================================================
# Edge Operations
# =============================================================================

def get_edges(type_filter=None, needs_review=None, source_type=None, target_type=None,
              min_shared=None, max_shared=None, search=None, page=1, per_page=50,
              sort_by=None, sort_dir='desc'):
    """Get paginated list of edges with optional filters and sorting."""
    with get_db() as conn:
        query = """
            SELECT e.id, e.type, e.needs_review,
                   ns.id as source_id, ns.name as source_name, ns.type as source_type,
                   nt.id as target_id, nt.name as target_name, nt.type as target_type,
                   (SELECT COUNT(*) FROM shared_institutions si WHERE si.edge_id = e.id) as shared_count
            FROM edges e
            JOIN nodes ns ON e.source_id = ns.id
            JOIN nodes nt ON e.target_id = nt.id
            WHERE 1=1
        """
        params = []

        if type_filter:
            query += " AND e.type = ?"
            params.append(type_filter)

        if needs_review is not None:
            query += " AND e.needs_review = ?"
            params.append(1 if needs_review else 0)

        if source_type:
            query += " AND ns.type = ?"
            params.append(source_type)

        if target_type:
            query += " AND nt.type = ?"
            params.append(target_type)

        if search:
            search_norm = f"%{normalize_name(search)}%"
            query += " AND (ns.name_normalized LIKE ? OR nt.name_normalized LIKE ?)"
            params.extend([search_norm, search_norm])

        # Subquery for shared count filtering
        if min_shared is not None or max_shared is not None:
            having_clauses = []
            if min_shared is not None:
                having_clauses.append(f"shared_count >= {int(min_shared)}")
            if max_shared is not None:
                having_clauses.append(f"shared_count <= {int(max_shared)}")
            # We need to restructure for HAVING - use a subquery
            base_query = query
            query = f"""
                SELECT * FROM ({base_query}) sub
                WHERE {' AND '.join(having_clauses)}
            """

        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM ({query}) counted"
        total = conn.execute(count_query, params).fetchone()["count"]

        # Add ordering
        sort_direction = 'DESC' if sort_dir == 'desc' else 'ASC'
        if sort_by == 'source':
            query += f" ORDER BY source_name {sort_direction}"
        elif sort_by == 'target':
            query += f" ORDER BY target_name {sort_direction}"
        elif sort_by == 'type':
            query += f" ORDER BY type {sort_direction}"
        elif sort_by == 'shared':
            query += f" ORDER BY shared_count {sort_direction}"
        elif sort_by == 'review':
            query += f" ORDER BY needs_review {sort_direction}"
        else:
            query += " ORDER BY source_name ASC, target_name ASC"

        # Add pagination
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])

        rows = conn.execute(query, params).fetchall()

        return {
            "edges": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

def get_edge(edge_id):
    """Get single edge with details."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT e.id, e.type, e.needs_review,
                   ns.id as source_id, ns.name as source_name, ns.type as source_type,
                   nt.id as target_id, nt.name as target_name, nt.type as target_type
            FROM edges e
            JOIN nodes ns ON e.source_id = ns.id
            JOIN nodes nt ON e.target_id = nt.id
            WHERE e.id = ?
        """, (edge_id,)).fetchone()

        if not row:
            return None

        result = dict(row)

        # Get shared institutions
        shared = conn.execute("""
            SELECT n.id, n.name FROM nodes n
            JOIN shared_institutions si ON si.institution_id = n.id
            WHERE si.edge_id = ?
        """, (edge_id,)).fetchall()
        result["shared_institutions"] = [dict(s) for s in shared]

        return result

def create_edge(source_id, target_id, edge_type):
    """Create a new edge."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO edges (source_id, target_id, type, needs_review) VALUES (?, ?, ?, 0)",
            (source_id, target_id, edge_type)
        )
        edge_id = cursor.lastrowid

        # Compute shared institutions and needs_review
        compute_shared_for_edge(conn, edge_id)

        return edge_id

def update_edge(edge_id, source_id=None, target_id=None, edge_type=None, needs_review=None):
    """Update an edge. Setting a non-unknown type automatically clears needs_review."""
    with get_db() as conn:
        updates = []
        params = []

        # Track if we need to recompute shared institutions
        recompute_shared = False

        if source_id is not None:
            updates.append("source_id = ?")
            params.append(source_id)
            recompute_shared = True

        if target_id is not None:
            updates.append("target_id = ?")
            params.append(target_id)
            recompute_shared = True

        if edge_type is not None:
            updates.append("type = ?")
            params.append(edge_type)
            # When assigning a definite type (personal/affiliation), mark as reviewed
            if edge_type in ('personal', 'affiliation'):
                updates.append("needs_review = 0")

        if needs_review is not None and edge_type not in ('personal', 'affiliation'):
            updates.append("needs_review = ?")
            params.append(1 if needs_review else 0)

        if updates:
            params.append(edge_id)
            query = f"UPDATE edges SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)

        # Recompute shared institutions if source or target changed
        if recompute_shared:
            compute_shared_for_edge(conn, edge_id)

def delete_edge(edge_id):
    """Delete an edge."""
    with get_db() as conn:
        conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))

# =============================================================================
# Batch Operations
# =============================================================================

def batch_update_node_subtype(node_ids, subtype):
    """Set subtype for multiple nodes (institutions)."""
    with get_db() as conn:
        placeholders = ",".join("?" * len(node_ids))
        # Only update institution nodes
        conn.execute(
            f"UPDATE nodes SET subtype = ? WHERE id IN ({placeholders}) AND type = 'institution'",
            [subtype if subtype else None] + list(node_ids)
        )
        return len(node_ids)

def batch_update_edge_type(edge_ids, edge_type):
    """Set type for multiple edges. Setting personal/affiliation clears needs_review."""
    with get_db() as conn:
        placeholders = ",".join("?" * len(edge_ids))
        if edge_type in ('personal', 'affiliation'):
            # Clear needs_review when assigning a definite type
            conn.execute(
                f"UPDATE edges SET type = ?, needs_review = 0 WHERE id IN ({placeholders})",
                [edge_type] + list(edge_ids)
            )
        else:
            conn.execute(
                f"UPDATE edges SET type = ? WHERE id IN ({placeholders})",
                [edge_type] + list(edge_ids)
            )
        return len(edge_ids)

def batch_mark_reviewed(edge_ids, reviewed=True):
    """Mark multiple edges as reviewed (clears needs_review flag)."""
    with get_db() as conn:
        placeholders = ",".join("?" * len(edge_ids))
        conn.execute(
            f"UPDATE edges SET needs_review = ? WHERE id IN ({placeholders})",
            [0 if reviewed else 1] + list(edge_ids)
        )
        return len(edge_ids)

def batch_create_edges(source_ids, target_id, edge_type):
    """Create edges from multiple sources to one target."""
    created = []
    with get_db() as conn:
        for source_id in source_ids:
            try:
                cursor = conn.execute(
                    "INSERT INTO edges (source_id, target_id, type, needs_review) VALUES (?, ?, ?, 0)",
                    (source_id, target_id, edge_type)
                )
                edge_id = cursor.lastrowid
                created.append(edge_id)
            except sqlite3.IntegrityError:
                # Edge already exists, skip
                pass

        # Compute shared institutions for new edges
        for edge_id in created:
            compute_shared_for_edge(conn, edge_id)

    return created

def batch_delete_edges(edge_ids):
    """Delete multiple edges."""
    with get_db() as conn:
        placeholders = ",".join("?" * len(edge_ids))
        conn.execute(f"DELETE FROM edges WHERE id IN ({placeholders})", list(edge_ids))
        return len(edge_ids)

# =============================================================================
# Shared Institutions Computation
# =============================================================================

def compute_shared_for_edge(conn, edge_id):
    """Compute shared institutions for a single edge and update needs_review."""
    # Clear existing shared institutions for this edge
    conn.execute("DELETE FROM shared_institutions WHERE edge_id = ?", (edge_id,))

    # Get edge details
    edge = conn.execute("""
        SELECT e.id, e.type, ns.id as source_id, ns.type as source_type,
               nt.id as target_id, nt.type as target_type
        FROM edges e
        JOIN nodes ns ON e.source_id = ns.id
        JOIN nodes nt ON e.target_id = nt.id
        WHERE e.id = ?
    """, (edge_id,)).fetchone()

    if not edge:
        return

    # Only compute for person-to-person edges
    if edge["source_type"] != "person" or edge["target_type"] != "person":
        conn.execute("UPDATE edges SET needs_review = 0 WHERE id = ?", (edge_id,))
        return

    source_id = edge["source_id"]
    target_id = edge["target_id"]

    # Get institutions connected to source
    source_insts = set(row[0] for row in conn.execute("""
        SELECT DISTINCT n.id FROM nodes n
        JOIN edges e ON (e.source_id = n.id OR e.target_id = n.id)
        WHERE n.type = 'institution'
        AND ((e.source_id = ? AND e.target_id = n.id) OR (e.target_id = ? AND e.source_id = n.id))
    """, (source_id, source_id)).fetchall())

    # Get institutions connected to target
    target_insts = set(row[0] for row in conn.execute("""
        SELECT DISTINCT n.id FROM nodes n
        JOIN edges e ON (e.source_id = n.id OR e.target_id = n.id)
        WHERE n.type = 'institution'
        AND ((e.source_id = ? AND e.target_id = n.id) OR (e.target_id = ? AND e.source_id = n.id))
    """, (target_id, target_id)).fetchall())

    # Find shared
    shared = source_insts & target_insts

    # Insert shared institutions
    for inst_id in shared:
        conn.execute(
            "INSERT INTO shared_institutions (edge_id, institution_id) VALUES (?, ?)",
            (edge_id, inst_id)
        )

    # Update needs_review: personal edge with 0 shared institutions
    needs_review = edge["type"] == "personal" and len(shared) == 0
    conn.execute(
        "UPDATE edges SET needs_review = ? WHERE id = ?",
        (1 if needs_review else 0, edge_id)
    )

def recalculate_needs_review_for_node(conn, node_id):
    """Recalculate needs_review for all edges involving a node."""
    edges = conn.execute(
        "SELECT id FROM edges WHERE source_id = ? OR target_id = ?",
        (node_id, node_id)
    ).fetchall()

    for edge in edges:
        compute_shared_for_edge(conn, edge["id"])

def recalculate_all_shared_institutions():
    """Recalculate all shared institutions and needs_review flags."""
    with get_db() as conn:
        # Clear all shared institutions
        conn.execute("DELETE FROM shared_institutions")

        # Get all edges
        edges = conn.execute("SELECT id FROM edges").fetchall()

        for edge in edges:
            compute_shared_for_edge(conn, edge["id"])

        return len(edges)

# =============================================================================
# Graph JSON Export (for visualization)
# =============================================================================

def get_graph_json():
    """Export database as graph JSON for visualization."""
    with get_db() as conn:
        # Get nodes (include subtype for institutions)
        nodes = conn.execute("SELECT name as id, type, subtype FROM nodes ORDER BY name").fetchall()

        # Get edges with names
        links = conn.execute("""
            SELECT ns.name as source, nt.name as target, e.type
            FROM edges e
            JOIN nodes ns ON e.source_id = ns.id
            JOIN nodes nt ON e.target_id = nt.id
            ORDER BY ns.name, nt.name
        """).fetchall()

        return {
            "nodes": [dict(n) for n in nodes],
            "links": [dict(l) for l in links]
        }

# =============================================================================
# Statistics
# =============================================================================

def get_stats():
    """Get network statistics."""
    with get_db() as conn:
        stats = {}

        # Node counts by type
        node_counts = conn.execute("""
            SELECT type, COUNT(*) as count FROM nodes GROUP BY type
        """).fetchall()
        stats["nodes"] = {row["type"]: row["count"] for row in node_counts}
        stats["nodes"]["total"] = sum(stats["nodes"].values())

        # Edge counts by type
        edge_counts = conn.execute("""
            SELECT type, COUNT(*) as count FROM edges GROUP BY type
        """).fetchall()
        stats["edges"] = {row["type"]: row["count"] for row in edge_counts}
        stats["edges"]["total"] = sum(stats["edges"].values())

        # Needs review count (edges with type 'unknown' need classification)
        needs_review = conn.execute(
            "SELECT COUNT(*) as count FROM edges WHERE type = 'unknown'"
        ).fetchone()
        stats["needs_review"] = needs_review["count"]

        # Shared institution distribution for person-to-person edges
        shared_dist = conn.execute("""
            SELECT
                CASE
                    WHEN shared_count = 0 THEN '0'
                    WHEN shared_count BETWEEN 1 AND 2 THEN '1-2'
                    ELSE '3+'
                END as bucket,
                COUNT(*) as count
            FROM (
                SELECT e.id,
                       (SELECT COUNT(*) FROM shared_institutions si WHERE si.edge_id = e.id) as shared_count
                FROM edges e
                JOIN nodes ns ON e.source_id = ns.id
                JOIN nodes nt ON e.target_id = nt.id
                WHERE ns.type = 'person' AND nt.type = 'person'
            ) sub
            GROUP BY bucket
        """).fetchall()
        stats["shared_distribution"] = {row["bucket"]: row["count"] for row in shared_dist}

        return stats

def _similarity(s1, s2):
    """Normalized Levenshtein similarity (0-1), pure Python two-row DP."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if not len1 or not len2:
        return 0.0
    prev = list(range(len2 + 1))
    for i in range(1, len1 + 1):
        curr = [i] + [0] * len2
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return 1.0 - prev[len2] / max(len1, len2)

def get_audit_report():
    """Return data quality audit with 5 issue categories."""
    with get_db() as conn:
        # 1. Unknown edges
        unknown_edges = [dict(r) for r in conn.execute("""
            SELECT e.id, e.source_id, e.target_id,
                   ns.name as source_name, ns.type as source_type,
                   nt.name as target_name, nt.type as target_type
            FROM edges e
            JOIN nodes ns ON e.source_id = ns.id
            JOIN nodes nt ON e.target_id = nt.id
            WHERE e.type = 'unknown'
            ORDER BY ns.name, nt.name
        """).fetchall()]

        # 2. Missing subtypes (institutions with NULL subtype)
        missing_subtypes = [dict(r) for r in conn.execute("""
            SELECT id, name, type
            FROM nodes
            WHERE type = 'institution' AND (subtype IS NULL OR subtype = '')
            ORDER BY name
        """).fetchall()]

        # 3. Orphan nodes (no edges at all)
        orphan_nodes = [dict(r) for r in conn.execute("""
            SELECT n.id, n.name, n.type, n.subtype
            FROM nodes n
            WHERE NOT EXISTS (
                SELECT 1 FROM edges e WHERE e.source_id = n.id OR e.target_id = n.id
            )
            ORDER BY n.name
        """).fetchall()]

        # 4. Needs review edges
        needs_review = [dict(r) for r in conn.execute("""
            SELECT e.id, e.type, e.needs_review,
                   ns.name as source_name, ns.type as source_type,
                   nt.name as target_name, nt.type as target_type,
                   (SELECT COUNT(*) FROM shared_institutions si WHERE si.edge_id = e.id) as shared_count
            FROM edges e
            JOIN nodes ns ON e.source_id = ns.id
            JOIN nodes nt ON e.target_id = nt.id
            WHERE e.needs_review = 1
            ORDER BY ns.name, nt.name
        """).fetchall()]

        # 5. Potential duplicates - bucket by first 3 chars of name_normalized
        all_nodes = conn.execute("""
            SELECT id, name, name_normalized, type, subtype
            FROM nodes
            ORDER BY name_normalized
        """).fetchall()

        buckets = {}
        for node in all_nodes:
            key = (node['name_normalized'] or '')[:3].lower()
            if len(key) < 2:
                continue
            buckets.setdefault(key, []).append(dict(node))

        potential_duplicates = []
        seen_pairs = set()
        for bucket_nodes in buckets.values():
            if len(bucket_nodes) < 2:
                continue
            for i in range(len(bucket_nodes)):
                for j in range(i + 1, len(bucket_nodes)):
                    a, b = bucket_nodes[i], bucket_nodes[j]
                    norm_a = (a['name_normalized'] or '').lower()
                    norm_b = (b['name_normalized'] or '').lower()
                    sim = _similarity(norm_a, norm_b)
                    if sim >= 0.85:
                        pair_key = (min(a['id'], b['id']), max(a['id'], b['id']))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            potential_duplicates.append({
                                'node_a': a,
                                'node_b': b,
                                'similarity': round(sim, 3),
                            })

        potential_duplicates.sort(key=lambda x: -x['similarity'])

        return {
            'unknown_edges': unknown_edges,
            'missing_subtypes': missing_subtypes,
            'orphan_nodes': orphan_nodes,
            'needs_review': needs_review,
            'potential_duplicates': potential_duplicates,
            'total_issues': (
                len(unknown_edges) + len(missing_subtypes) +
                len(orphan_nodes) + len(needs_review) + len(potential_duplicates)
            ),
        }

def get_subtypes():
    """Get list of available institution subtypes with counts."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT subtype, COUNT(*) as count
            FROM nodes
            WHERE type = 'institution'
            GROUP BY subtype
            ORDER BY count DESC
        """).fetchall()
        result = []
        for row in rows:
            subtype = row['subtype']
            result.append({
                'value': subtype if subtype else 'uncategorized',
                'label': (subtype or 'uncategorized').title(),
                'count': row['count']
            })
        return result

# Initialize database on import
init_db()
