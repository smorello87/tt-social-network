import json
import sqlite3

import pytest

import validate
from conftest import add_edge, add_node


def write_graph(db, path):
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as c:
        path.write_text(json.dumps(validate.export_graph(c)))


@pytest.fixture
def good(db, tmp_path):
    a, b, i = add_node(db, "Mario Rossi"), add_node(db, "Anna Verdi"), add_node(db, "Mag", "institution", "periodical")
    add_edge(db, a, i)
    add_edge(db, b, i)
    graph = tmp_path / "graph.json"
    write_graph(db, graph)
    return db, graph


def test_good_db_passes(good, capsys):
    db, graph = good
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 0
    out = capsys.readouterr().out
    assert "connected components: 1" in out and "OK" in out


def test_self_loop_fails(good, capsys):
    db, graph = good
    with sqlite3.connect(db) as c:
        c.execute("DROP TRIGGER forbid_self_loop_insert")
        c.execute("INSERT INTO edges (source_id, target_id, type) VALUES (1, 1, 'personal')")
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    assert "self-loops" in capsys.readouterr().out


def test_reversed_duplicate_orphan_and_stale_graph_fail(good, capsys):
    db, graph = good
    with sqlite3.connect(db) as c:
        c.execute("DROP TRIGGER enforce_edge_direction_insert")
        c.execute("INSERT INTO edges (source_id, target_id, type) VALUES (3, 1, 'personal')")  # reversed + duplicate pair
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    out = capsys.readouterr().out
    assert "reversed" in out and "duplicate edge pairs" in out and "differs" in out


def test_duplicate_folded_key_fails(good, capsys):
    db, graph = good
    add_node(db, "Mário Rossi")
    write_graph(db, graph)
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    assert "duplicate folded keys" in capsys.readouterr().out


def test_novella_with_year_is_not_a_duplicate(good):
    db, graph = good
    add_node(db, "Novella", "institution", "publisher")
    add_node(db, "Novella 2000", "institution", "publisher")
    write_graph(db, graph)
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 0


def test_validate_does_not_modify_db(good):
    import hashlib
    db, graph = good
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    validate.main(["--db", str(db), "--graph", str(graph)])
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


def test_non_nfc_name_fails(good, capsys):
    db, graph = good
    add_node(db, "André Martinet")  # inserted raw, bypassing create_node
    write_graph(db, graph)
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    assert "names not in NFC" in capsys.readouterr().out


def test_missing_self_loop_triggers_fail(good, capsys):
    """A DB created before the self-loop triggers existed must be flagged, not silently trusted."""
    db, graph = good
    with sqlite3.connect(db) as c:
        c.execute("DROP TRIGGER forbid_self_loop_update")
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    assert "forbid_self_loop_update" in capsys.readouterr().out


def test_stale_name_normalized_fails(good, capsys):
    db, graph = good
    with sqlite3.connect(db) as c:
        c.execute("UPDATE nodes SET name_normalized = 'something else' WHERE name = 'Mario Rossi'")
    assert validate.main(["--db", str(db), "--graph", str(graph)]) == 1
    assert "name_normalized" in capsys.readouterr().out
