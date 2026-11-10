import pytest

from build_roster import candidates_for, fold, flip_comma


def make_nodes(*names, ntype="person"):
    return [(i, n, ntype, fold(n), " ".join(fold(n))) for i, n in enumerate(names, 1)]


def test_fold_basics():
    assert fold("Jean-Paul D’Amico") == ["jean", "paul", "damico"]
    assert fold("***") == []
    assert fold("Novella") != fold("Novella 2000")  # digits are kept


def test_dannunzio_straight_and_curly_apostrophe_fold_alike():
    assert fold("Gabriele D'Annunzio") == fold("Gabriele D’Annunzio") == ["gabriele", "dannunzio"]
    nodes = make_nodes("Gabriele D’Annunzio")
    assert [c["id"] for c in candidates_for("Gabriele D'Annunzio", nodes)] == [1]


def test_flip_comma():
    assert flip_comma("Barzini, Luigi") == "Luigi Barzini"
    assert flip_comma("Luigi Barzini") == "Luigi Barzini"


NODES = make_nodes("Luigi Barzini Jr", "Luigi Barzini Sr", "Giuseppe Prezzolini", "Giuseppe Tusiani",
                   "Achille Loria", "Gilberto Altichieri", "Mario Donati", "John S. White")


@pytest.mark.parametrize("query, expected", [
    ("Luigi Barzini", {"Luigi Barzini Jr", "Luigi Barzini Sr"}),
    ("Barzini, Luigi", {"Luigi Barzini Jr", "Luigi Barzini Sr"}),
    ("Prezzolini", {"Giuseppe Prezzolini"}),
    ("Joseph Tusiani", {"Giuseppe Tusiani"}),
    ("Loria Achille", {"Achille Loria"}),
    ("Maria Donati", {"Mario Donati"}),
    ("John A. White", {"John S. White"}),
    ("Giberto Altichieri", {"Gilberto Altichieri"}),
    ("Nobody Atall", set()),
    ("***", set()),
    ("E.", set()),
])
def test_candidates(query, expected):
    assert {c["name"] for c in candidates_for(query, NODES)} == expected


def test_given_name_equivalents():
    pairs = [("Giuseppe", "Joseph"), ("Giovanni", "John"), ("Francesco", "Frank"), ("Maria", "Mary"),
             ("Giuseppina", "Josephine"), ("Salvatore", "Sam")]
    for it, en in pairs:
        assert candidates_for(f"{en} Zanardi", make_nodes(f"{it} Zanardi")), (it, en)


def test_flip_comma_leaves_generational_suffix_alone():
    assert flip_comma("Lowry Nelson, Jr") == "Lowry Nelson, Jr"
    assert flip_comma("Barzini, Luigi") == "Luigi Barzini"


@pytest.mark.parametrize("query, node, flagged", [
    ("Giberto Altichieri", "Gilberto Altichieri", True),   # distance 1
    ("Erberto Landi", "Roberto Landi", True),             # distance 2, both 6+ letters
    ("Renzo Giusso", "Lorenzo Giusso", True),             # hypocoristic ending
    ("Marco Sforza", "Carlo Sforza", False),              # distance 2, short: different names
    ("Aldo Romano", "Elmo Romano", False),
    ("Karl Stephenson", "Mary L. Stephenson", False),
])
def test_near_given_name_rule(query, node, flagged):
    assert bool(candidates_for(query, make_nodes(node))) is flagged


def test_rule_based_candidates_are_not_capped_at_five():
    rossi = [f"{g} Rossi" for g in ("Adolfo", "Alice", "Ernesto", "Filippo", "Luigi", "Nando", "Ugo", "Carla")]
    found = {c["name"] for c in candidates_for("Rossi", make_nodes(*rossi))}
    assert found == set(rossi)


@pytest.mark.parametrize("query, node", [
    ("Guareschi, Nino", "Giovanni Guareschi"), ("Gino Calza", "Luigi Calza"), ("Beppe Rossi", "Giuseppe Rossi"),
    ("Totò Russo", "Salvatore Russo"), ("Mimmo Greco", "Domenico Greco"), ("Sandro Penna", "Alessandro Penna"),
    ("Lello Conti", "Raffaele Conti"), ("Ciccio Leo", "Francesco Leo"), ("Gigi Negri", "Luigi Negri"),
    ("Vanni Scheiwiller", "Giovanni Scheiwiller"), ("Gianni Rodari", "Nino Rodari"),  # both from Giovanni
])
def test_diminutives_flag(query, node):
    assert [c["name"] for c in candidates_for(query, make_nodes(node))] == [node]


def test_diminutives_never_link(db, tmp_path, monkeypatch):
    """A diminutive match is a candidate (unresolved), never an 'existing' link."""
    import json, sys
    import build_roster
    from conftest import add_node
    add_node(db, "I-AM", "institution", "periodical")
    add_node(db, "Giovanni Guareschi")
    base = tmp_path / "data" / "x"
    (base / "extraction").mkdir(parents=True)
    (base / "extraction" / "p-02.json").write_text(json.dumps(
        {"_page": 2, "issue": "March 1976", "masthead": [], "articles": [{"byline": ["Guareschi, Nino"]}]}))
    (base / "extraction" / "_manifest.json").write_text(json.dumps({"pages": [2]}))
    (base / "review.json").write_text(json.dumps({"periodical": "I-AM"}))
    monkeypatch.setattr(build_roster, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(sys, "argv", ["build_roster.py", "x"])
    build_roster.main()
    people = {p["name"]: p for p in json.loads((base / "roster.json").read_text())["people"]}
    assert people["Nino Guareschi"]["status"] == "unresolved"
    assert [c["name"] for c in people["Nino Guareschi"]["candidates"]] == ["Giovanni Guareschi"]
