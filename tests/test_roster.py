import json
import sys

import pytest

import build_roster
import database
from conftest import add_edge, add_node


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


@pytest.fixture
def world(db, tmp_path, monkeypatch):
    ids = {
        "periodical": add_node(db, "I-AM", "institution", "periodical"),
        "rossi": add_node(db, "Mario Rossi"),
        "verdi": add_node(db, "Anna Verdi"),
        "jr": add_node(db, "Luigi Barzini Jr"),
        "sr": add_node(db, "Luigi Barzini Sr"),
        "ciardi": add_node(db, "John Anthony Ciardi"),
        "homonym": add_node(db, "Pat Homonym"),
        "novella": add_node(db, "Novella", "institution", "publisher"),
        "novella2000": add_node(db, "Novella 2000", "institution", "publisher"),
    }
    add_edge(db, ids["verdi"], ids["periodical"])  # Anna Verdi was imported by an earlier run
    data = tmp_path / "data"
    monkeypatch.setattr(build_roster, "DATA_DIR", data)
    base = data / "iam"
    write(base / "extraction" / "p-02.json", {
        "_page": 2, "issue": "March 1976",
        "masthead": [{"role": "editor", "names": ["Mario Rossi", "Anna Verdi"]}],
        "articles": [{"byline": ["Luigi Barzini", "Pat Homonym", "Subject Person", "M. Rossi", "Drop Me", "Skip Org"],
                      "photo_or_art": ["Pia Photo"]}],
        "uncertain": ["Pia Photo might be Pia Foto"],
    })
    write(base / "extraction" / "p-04.json", {
        "_page": 4, "issue": None,
        "masthead": [], "fine_print": [{"role": "treasurer", "name": "Johnny Ciardi"}],
        "articles": [{"byline": ["Novella", "Brand New Name"]}],
    })
    write(base / "review.json", {
        "periodical": "I-AM", "issues": {"4": "1976-04"},
        "not_authors": ["Subject Person"], "drop": [[2, "Drop Me"]], "add": [[4, "Added Person", "photographer"]],
        "aliases": {"M. Rossi": "Mario Rossi"}, "skip": ["Skip Org"],
        "match": {"Johnny Ciardi": ids["ciardi"]}, "new": ["Pat Homonym", "Anna Verdi"],
    })
    write(base / "extraction" / "_manifest.json", {"pages": [2, 4]})
    return ids, base


def run(base, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["build_roster.py", base.name])
    build_roster.main()
    return {p["name"]: p for p in json.loads((base / "roster.json").read_text())["people"]}


def test_statuses(world, monkeypatch):
    ids, base = world
    people = run(base, monkeypatch)
    assert {n: p["status"] for n, p in people.items()} == {
        "Mario Rossi": "existing",       # exact match; alias "M. Rossi" folded into it
        "Anna Verdi": "existing",        # in review "new" but already imported for this periodical
        "Luigi Barzini": "unresolved",   # suffix homonyms
        "Pat Homonym": "new",            # review "new" beats the exact match
        "Pia Photo": "new",
        "Johnny Ciardi": "existing",     # review "match"
        "Novella": "unresolved",         # only match is an institution; Novella 2000 stays distinct
        "Brand New Name": "new",
        "Added Person": "new",           # review "add"
    }
    assert people["Pat Homonym"].get("node_id") is None
    assert people["Johnny Ciardi"]["node_id"] == ids["ciardi"]
    assert {c["id"] for c in people["Luigi Barzini"]["candidates"]} == {ids["jr"], ids["sr"]}
    assert [c["id"] for c in people["Novella"]["candidates"]] == [ids["novella"]]
    assert people["Mario Rossi"]["roles"] == ["author", "masthead: Editor"]
    assert people["Mario Rossi"]["issues"] == ["1976-03"]
    assert people["Added Person"]["issues"] == ["1976-04"]
    assert "Drop Me" not in people and "Skip Org" not in people and "Subject Person" not in people


def test_homonym_match_by_type_and_multiple(db, world, monkeypatch):
    ids, base = world
    add_node(db, "Mário Rossi")  # folds to the same key as "Mario Rossi": ambiguous
    people = run(base, monkeypatch)
    assert people["Mario Rossi"]["status"] == "unresolved"
    assert len(people["Mario Rossi"]["candidates"]) == 2


def test_uncertain_entries_naming_a_roster_person_are_printed(world, monkeypatch, capsys):
    run(world[1], monkeypatch)
    assert "Pia Photo" in capsys.readouterr().out


def test_missing_manifest_page_fails(world, monkeypatch):
    _, base = world
    write(base / "extraction" / "_manifest.json", {"pages": [2, 4, 6]})
    monkeypatch.setattr(sys, "argv", ["build_roster.py", "iam"])
    with pytest.raises(SystemExit) as e:
        build_roster.main()
    assert "[6]" in str(e.value)
    (base / "extraction" / "p-04.json").unlink()
    write(base / "extraction" / "_manifest.json", {"pages": [2, 4]})
    with pytest.raises(SystemExit):
        build_roster.main()


def test_no_manifest_warns_but_works(world, monkeypatch, capsys):
    _, base = world
    (base / "extraction" / "_manifest.json").unlink()
    run(base, monkeypatch)
    assert "no extraction/_manifest.json" in capsys.readouterr().out


def test_nameless_entry_is_unresolved_not_a_crash(world, monkeypatch):
    _, base = world
    review = json.loads((base / "review.json").read_text())
    review["add"].append([2, "***", "author"])
    write(base / "review.json", review)
    assert run(base, monkeypatch)["***"]["status"] == "unresolved"


def test_roster_does_not_write_the_database(world, monkeypatch):
    import hashlib
    h = lambda: hashlib.sha256(database.DB_PATH.read_bytes()).hexdigest()
    before = h()
    run(world[1], monkeypatch)
    assert h() == before


def add_bylines(base, *names):
    page = json.loads((base / "extraction" / "p-02.json").read_text())
    page["articles"].append({"byline": list(names)})
    write(base / "extraction" / "p-02.json", page)


def test_case_and_whitespace_variants_collapse(world, monkeypatch):
    _, base = world
    add_bylines(base, "Del Vita, Alessandro", "Del  Vita, Alessandro", "Flaiano, ennio", "Flaiano, Ennio")
    people = run(base, monkeypatch)
    assert sum(n.endswith(("Flaiano", "flaiano")) for n in people) == 1
    assert sum("Vita" in n for n in people) == 1
    assert people["ennio Flaiano"]["status"] == "new"
    assert not any("," in n for n in people)  # "Surname, First" is stored as "First Surname"


def test_near_duplicate_names_in_the_roster_are_flagged(world, monkeypatch):
    _, base = world
    add_bylines(base, "Altichieri, Giberto", "Altichieri, Gilberto", "Zanardi, Joseph", "Zanardi, Giuseppe")
    people = run(base, monkeypatch)
    for a, b in [("Giberto Altichieri", "Gilberto Altichieri"), ("Joseph Zanardi", "Giuseppe Zanardi")]:
        assert people[a]["status"] == people[b]["status"] == "unresolved"
        assert [c["name"] for c in people[a]["candidates"]] == [b]
        assert people[a]["candidates"][0]["type"] == "roster"


def test_confirming_distinct_in_review_new_clears_the_flag(world, monkeypatch):
    _, base = world
    add_bylines(base, "Altichieri, Giberto", "Altichieri, Gilberto")
    review = json.loads((base / "review.json").read_text())
    review["new"] += ["Giberto Altichieri", "Gilberto Altichieri"]
    write(base / "review.json", review)
    people = run(base, monkeypatch)
    assert people["Giberto Altichieri"]["status"] == people["Gilberto Altichieri"]["status"] == "new"


def test_unrelated_roster_names_stay_new(world, monkeypatch):
    _, base = world
    add_bylines(base, "Pratolini, Vasco", "Moravia, Alberto")
    people = run(base, monkeypatch)
    assert people["Vasco Pratolini"]["status"] == people["Alberto Moravia"]["status"] == "new"


def test_comma_name_exact_match_links_and_is_not_imported_inverted(world, monkeypatch):
    nodes, base = world
    add_bylines(base, "Ciardi, John Anthony", "Nelson, Lowry")
    people = run(base, monkeypatch)
    assert "Ciardi, John Anthony" not in people
    assert people["John Anthony Ciardi"]["status"] == "existing"
    assert people["John Anthony Ciardi"]["node_id"] == nodes["ciardi"]
    assert people["Lowry Nelson"]["status"] == "new"


def test_confirming_one_spelling_new_keeps_the_other_flagged(world, monkeypatch):
    """Putting one of two near-identical roster names in "new" must not silently pass the other."""
    _, base = world
    add_bylines(base, "Giberto Altichieri", "Gilberto Altichieri")
    review = json.loads((base / "review.json").read_text())
    review["new"].append("Giberto Altichieri")
    write(base / "review.json", review)
    people = run(base, monkeypatch)
    assert people["Giberto Altichieri"]["status"] == "new"
    assert people["Gilberto Altichieri"]["status"] == "unresolved"
    assert [c["name"] for c in people["Gilberto Altichieri"]["candidates"]] == ["Giberto Altichieri"]
