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


def test_names_are_stored_in_nfc(db):
    decomposed = "André Martinet"
    nid = database.create_node(decomposed, "person")
    assert query(db, "SELECT name FROM nodes WHERE id = ?", (nid,)) == [("André Martinet",)]
    assert database.normalize_name(decomposed) == database.normalize_name("André Martinet")
    database.update_node(nid, name="Cantù Cesare")
    assert query(db, "SELECT name, name_normalized FROM nodes WHERE id = ?", (nid,)) == [
        ("Cantù Cesare", "cantù cesare")]


def test_bulk_recalculation_never_reflags_reviewed_edges(db):
    """needs_review = 0 on a personal edge can be the owner's "reviewed"; recalculations must keep it."""
    a, b = add_node(db, "Person A"), add_node(db, "Person B")
    ab = add_edge(db, a, b, "personal")
    with database.get_db() as conn:
        database.compute_shared_for_edge(conn, ab)  # a new edge: flagged
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(1,)]
    database.batch_mark_reviewed([ab])
    database.recalculate_all_shared_institutions()
    database.update_node(a, name="Person A Renamed")
    c = add_node(db, "Person C")
    add_edge(db, a, c, "personal")
    database.merge_nodes(a, c)
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(0,)]


def test_bulk_recalculation_still_clears_flags(db):
    a, b, i = add_node(db, "Person A"), add_node(db, "Person B"), add_node(db, "Inst", "institution", "other")
    ab = database.create_edge(a, b, "personal")
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(1,)]
    add_edge(db, a, i)
    add_edge(db, b, i)
    database.recalculate_all_shared_institutions()
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (ab,)) == [(0,)]


def test_update_edge_rejects_self_loop(db):
    a, b = add_node(db, "Person A"), add_node(db, "Person B")
    e = add_edge(db, a, b, "personal")
    with pytest.raises(ValueError):
        database.update_edge(e, target_id=a)
    assert query(db, "SELECT source_id, target_id FROM edges WHERE id = ?", (e,)) == [(a, b)]


def test_put_api_edge_self_loop_is_400_not_409(db):
    pytest.importorskip("flask_cors")
    import app
    a, b = add_node(db, "Person A"), add_node(db, "Person B")
    e = add_edge(db, a, b, "personal")
    r = app.app.test_client().put(f"/api/edges/{e}", json={"source_id": b, "target_id": b})
    assert r.status_code == 400
    assert "itself" in r.get_json()["error"]


def test_batch_create_skips_self_loop(db):
    a, b = add_node(db, "Person A"), add_node(db, "Inst", "institution", "other")
    created = database.batch_create_edges([a, b], b, "affiliation")
    assert len(created) == 1
    assert query(db, "SELECT source_id, target_id FROM edges") == [(a, b)]


def test_node_routes_reject_unknown_subtype(db):
    """subtype is rendered into the editor's HTML; only the known values may be stored."""
    pytest.importorskip("flask_cors")
    import app
    client = app.app.test_client()
    bad = '<img src=x onerror=alert(1)>'
    assert client.post("/api/nodes", json={"name": "Some Press", "type": "institution", "subtype": bad}).status_code == 400
    r = client.post("/api/nodes", json={"name": "Some Press", "type": "institution", "subtype": "publisher"})
    assert r.status_code == 201
    nid = r.get_json()["id"]
    assert client.put(f"/api/nodes/{nid}", json={"subtype": bad}).status_code == 400
    assert client.put(f"/api/nodes/{nid}", json={"subtype": ""}).status_code == 200
    assert query(db, "SELECT subtype FROM nodes WHERE id = ?", (nid,)) == [(None,)]
