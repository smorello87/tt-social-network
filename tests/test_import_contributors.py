import hashlib
import json
import sys

import pytest

import database
import import_contributors
from conftest import add_edge, add_node, query


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def setup(db, tmp_path, monkeypatch):
    ids = {"person": add_node(db, "Mario Rossi"), "inst": add_node(db, "Some Press", "institution", "publisher")}
    monkeypatch.setattr(import_contributors, "DATA_DIR", tmp_path / "data")

    def run(people, periodical="Test Mag", *extra):
        d = tmp_path / "data" / "t"
        d.mkdir(parents=True, exist_ok=True)
        (d / "roster.json").write_text(json.dumps({"periodical": periodical, "people": people}))
        monkeypatch.setattr(sys, "argv", ["import_contributors.py", "t", *extra])
        import_contributors.main()
    return ids, run


def person(name, status, **kw):
    return {"name": name, "roles": [], "issues": [], "status": status, **kw}


def counts(db):
    return query(db, "SELECT (SELECT COUNT(*) FROM nodes), (SELECT COUNT(*) FROM edges)")[0]


def test_import_is_idempotent_and_canonical(setup, db, capsys):
    ids, run = setup
    people = [person("Mario Rossi", "existing", node_id=ids["person"]), person("Fresh Name", "new")]
    run(people)
    after_first = counts(db)
    assert after_first == (4, 2)  # + periodical + Fresh Name; two affiliation edges
    assert all(s <= t for s, t in query(db, "SELECT source_id, target_id FROM edges"))
    capsys.readouterr()
    run(people)  # second run: nothing new
    assert counts(db) == after_first
    out = capsys.readouterr().out
    assert "Nodes created:   0" in out and "Edges created:   0" in out


def test_refuses_unresolved(setup, db):
    ids, run = setup
    with pytest.raises(SystemExit) as e:
        run([person("Mario Rossi", "unresolved", candidates=[])])
    assert e.value.code
    assert counts(db) == (2, 0)


def test_refuses_periodical_itself_as_contributor(setup, db):
    ids, run = setup
    run([], "Test Mag")  # creates the periodical node
    pid = query(db, "SELECT id FROM nodes WHERE name = 'Test Mag'")[0][0]
    with pytest.raises(SystemExit) as e:
        run([person("Test Mag", "existing", node_id=pid)], "Test Mag")
    assert e.value.code


def test_refuses_non_person_target(setup, db):
    ids, run = setup
    with pytest.raises(SystemExit) as e:
        run([person("Some Press", "existing", node_id=ids["inst"])])
    assert e.value.code
    assert counts(db) == (2, 0)  # rolled back, periodical not left behind


def test_refuses_periodical_that_is_not_an_institution(setup, db):
    ids, run = setup
    with pytest.raises(SystemExit) as e:
        run([], "Mario Rossi")
    assert e.value.code


def test_new_entry_clashing_with_existing_node_fails(setup, db):
    ids, run = setup
    with pytest.raises(SystemExit) as e:
        run([person("Mario Rossi", "new")])
    assert e.value.code
    assert counts(db) == (2, 0)


def test_dry_run_leaves_file_unchanged(setup, db):
    ids, run = setup
    before = sha(db)
    run([person("Mario Rossi", "existing", node_id=ids["person"]), person("Fresh Name", "new")], "Test Mag", "--dry-run")
    assert sha(db) == before


def test_import_refreshes_needs_review(setup, db):
    ids, run = setup
    other = add_node(db, "Anna Verdi")
    edge = add_edge(db, ids["person"], other, "personal")
    with database.get_db() as conn:
        database.compute_shared_for_edge(conn, edge)
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (edge,)) == [(1,)]  # no shared institution
    run([person("Mario Rossi", "existing", node_id=ids["person"]), person("Anna Verdi", "existing", node_id=other)])
    assert query(db, "SELECT needs_review FROM edges WHERE id = ?", (edge,)) == [(0,)]
