import pytest

from build_signatures import is_initials


@pytest.mark.parametrize("name, expected", [
    ("B. Z.", True), ("Dott. D. S.", True), ("GA.", True), ("e. d. g.", True), ("E.", True), ("BZ", True),
    ("Ugo Foa", False), ("Ugo Rè", False), ("Mario Rossi", False),
])
def test_is_initials(name, expected):
    assert is_initials(name) is expected


from build_signatures import dedupe_appearances


def rec(*apps):
    return {"appearances": [dict(file=f, page=1, issue=i, **({"title": t} if t else {})) for f, i, t in apps], "issues": set()}


def test_same_issue_title_in_two_files_counts_once():
    r = rec(("1965.pdf", "1965-03", "Ode"), ("ScanPro0514.pdf", "1965-03", "Ode"), ("1965.pdf", "1965-03", "Other"))
    dedupe_appearances(r)
    assert [(a["file"], a["title"]) for a in r["appearances"]] == [("1965.pdf", "Ode"), ("1965.pdf", "Other")]
    assert r["issues"] == {"1965-03"}


def test_month_and_day_labels_merge_only_with_same_title():
    r = rec(("a.pdf", "1947-01", "Poem"), ("b.pdf", "1947-01-01", "Poem"))
    dedupe_appearances(r)
    assert len(r["appearances"]) == 1 and r["issues"] == {"1947-01-01"}
    r = rec(("a.pdf", "1947-01", "Poem"), ("b.pdf", "1947-01-01", "Other poem"))
    dedupe_appearances(r)
    assert len(r["appearances"]) == 2 and r["issues"] == {"1947-01", "1947-01-01"}
    r = rec(("a.pdf", "1947-01", None), ("b.pdf", "1947-01-01", None))
    dedupe_appearances(r)
    assert len(r["issues"]) == 2


def test_undated_appearances_are_kept_and_count_zero_issues():
    r = rec(("a.pdf", None, "Poem"), ("b.pdf", None, "Poem"))
    dedupe_appearances(r)
    assert len(r["appearances"]) == 2 and r["issues"] == set()
