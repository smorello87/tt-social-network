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
                   "Achille Loria", "Mario Donati", "John S. White")


@pytest.mark.parametrize("query, expected", [
    ("Luigi Barzini", {"Luigi Barzini Jr", "Luigi Barzini Sr"}),
    ("Barzini, Luigi", {"Luigi Barzini Jr", "Luigi Barzini Sr"}),
    ("Prezzolini", {"Giuseppe Prezzolini"}),
    ("Joseph Tusiani", {"Giuseppe Tusiani"}),
    ("Loria Achille", {"Achille Loria"}),
    ("Maria Donati", {"Mario Donati"}),
    ("John A. White", {"John S. White"}),
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
