import hashlib
import shutil
import sqlite3
import subprocess
import sys

import pytest

import database
from conftest import EDITOR, add_edge, add_node, query


def test_self_loop_rejected_at_all_levels(db):
    n = add_node(db, "Mario Rossi")
    with pytest.raises(ValueError):
        database.create_edge(n, n, "affiliation")
    with pytest.raises(sqlite3.IntegrityError):
        add_edge(db, n, n)
    other = add_node(db, "Anna Verdi")
    e = add_edge(db, n, other)
    with pytest.raises(sqlite3.IntegrityError):
        with sqlite3.connect(db) as c:
            c.execute("UPDATE edges SET target_id = source_id WHERE id = ?", (e,))
    assert query(db, "SELECT COUNT(*) FROM edges") == [(1,)]


def test_post_api_edges_self_loop_is_400(db):
    pytest.importorskip("flask_cors")
    import app
    n = add_node(db, "Mario Rossi")
    client = app.app.test_client()
    r = client.post("/api/edges", json={"source_id": n, "target_id": n, "type": "personal"})
    assert r.status_code == 400
    other = add_node(db, "Anna Verdi")
    assert client.post("/api/edges", json={"source_id": n, "target_id": other}).status_code == 201


def test_import_database_does_not_write(tmp_path):
    """Importing database.py must not run init_db / migrations (it used to)."""
    shutil.copy(EDITOR / "database.py", tmp_path / "database.py")
    path = tmp_path / "network.db"
    with sqlite3.connect(path) as c:  # legacy-looking DB: no triggers, reverse-duplicate edges
        c.executescript("""
            CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT, name_normalized TEXT, type TEXT, subtype TEXT);
            CREATE TABLE edges (id INTEGER PRIMARY KEY, source_id INT, target_id INT, type TEXT, needs_review BOOLEAN DEFAULT 0);
            INSERT INTO edges (source_id, target_id, type) VALUES (2, 1, 'personal'), (1, 2, 'personal');
        """)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    subprocess.run([sys.executable, "-c", "import database"], cwd=tmp_path, check=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_app_initialises_schema_on_start(tmp_path, monkeypatch):
    pytest.importorskip("flask_cors")
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "fresh.db")
    sys.modules.pop("app", None)
    import app  # noqa: F401
    assert query(tmp_path / "fresh.db", "SELECT name FROM sqlite_master WHERE name = 'edges'")
    sys.modules.pop("app", None)


def test_merge_keeps_classified_type_over_unknown(db):
    a, b, x = add_node(db, "A One"), add_node(db, "A Two"), add_node(db, "Neighbour")
    add_edge(db, a, x, "unknown")
    add_edge(db, b, x, "personal")
    database.merge_nodes(a, b)
    assert query(db, "SELECT type FROM edges") == [("personal",)]


def test_merge_keeps_existing_classified_type(db):
    a, b, x = add_node(db, "A One"), add_node(db, "A Two"), add_node(db, "Neighbour")
    add_edge(db, a, x, "affiliation")
    add_edge(db, b, x, "unknown")
    database.merge_nodes(a, b)
    assert query(db, "SELECT type FROM edges") == [("affiliation",)]


def test_merge_refuses_different_types(db):
    p, i = add_node(db, "Somebody"), add_node(db, "Somewhere", "institution", "other")
    with pytest.raises(ValueError):
        database.merge_nodes(p, i)
    assert query(db, "SELECT COUNT(*) FROM nodes") == [(2,)]


def test_merge_recomputes_needs_review(db):
    a, b = add_node(db, "Person A"), add_node(db, "Person B")
    i1, i2 = add_node(db, "Inst One", "institution", "other"), add_node(db, "Inst One Dup", "institution", "other")
    ab = add_edge(db, a, b, "personal")
    add_edge(db, a, i1)
    add_edge(db, b, i2)
    with database.get_db() as conn:
        database.compute_shared_for_edge(conn, ab)
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(1,)]
    database.merge_nodes(i1, i2)  # now A and B share Inst One
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(0,)]
    assert query(db, "SELECT COUNT(*) FROM shared_institutions WHERE edge_id = ?", (ab,)) == [(1,)]
