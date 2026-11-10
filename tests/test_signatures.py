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


def test_recurring_title_needs_reviewer_confirmation_to_merge_month_into_day():
    """'Plausi e consensi' runs in every issue: a month label and a day label are not evidence of one issue."""
    from build_signatures import recurring_titles
    letters = rec(("a.pdf", "1947-01", "Plausi e consensi"), ("b.pdf", "1947-01-15", "Plausi e consensi"))
    other = rec(("c.pdf", "1947-03-01", "Plausi e consensi"))
    recurring = recurring_titles([letters, other])
    assert recurring == {"Plausi e consensi"}
    dedupe_appearances(letters, recurring)
    assert len(letters["appearances"]) == 2 and letters["issues"] == {"1947-01", "1947-01-15"}
    confirmed = rec(("a.pdf", "1947-01", "Plausi e consensi"), ("b.pdf", "1947-01-15", "Plausi e consensi"))
    dedupe_appearances(confirmed, recurring, {("1947-01", "1947-01-15")})
    assert len(confirmed["appearances"]) == 1 and confirmed["issues"] == {"1947-01-15"}


def test_one_off_title_still_merges_month_into_day():
    from build_signatures import recurring_titles
    r = rec(("a.pdf", "1947-01", "Ode a Garibaldi"), ("b.pdf", "1947-01-15", "Ode a Garibaldi"))
    dedupe_appearances(r, recurring_titles([r]))
    assert r["issues"] == {"1947-01-15"}
