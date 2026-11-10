import pytest

from build_signatures import is_initials


@pytest.mark.parametrize("name, expected", [
    ("B. Z.", True), ("Dott. D. S.", True), ("GA.", True), ("e. d. g.", True), ("E.", True), ("BZ", True),
    ("Ugo Foa", False), ("Ugo Rè", False), ("Mario Rossi", False),
])
def test_is_initials(name, expected):
    assert is_initials(name) is expected
