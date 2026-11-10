#!/usr/bin/env python3
"""
Merge per-PDF signature extractions into one contributors file keyed by person.

Used for periodicals read page by page for signed pieces (bylines, end signatures,
photo credits, letters) rather than from a table of contents — e.g. La Follia.

Inputs (in data/<slug>/):
  extraction/<pdf stem>.json   {"file", "pages": [{page, issue, footer}],
                                "signatures": [{page, issue, name, as_printed, title,
                                                position, kind, confidence, note?}]}
  review.json                  hand-review decisions:
    aliases        {"G. Incalicchio": "Giuseppe Incalicchio"} variants -> canonical
    skip           names that aren't contributors (collective signatures, quoted officials)
    drop           [[file, page, name]] single credits to discard (e.g. article subjects)
    new            names confirmed distinct from their fuzzy DB candidates
    exclude        {"Vice-Simili": "reason"} kept in the data but left out of the network
    notes          {"name": "free-text note"} copied into the output
    letter_rule    letter writers are kept only if in 2+ issues or already in network.db
    same_issue     [["1947-01", "1947-01-15"]] a month-only label confirmed to be that day's
                   issue, needed before a recurring title (letters page, column) is de-duplicated
  Signatures seen twice because an issue was scanned in two PDFs are counted once (see
  dedupe_appearances).
  Excluded automatically (see `excluded_reason`): one-off letter writers, and names that are
  only initials ("B. Z.") with no network match — merge one into a full name to bring it back.

Output: data/<slug>/roster.json (included people, for import_contributors.py) and
data/<slug>/contributors.json, one entry per person with issues, appearances,
`include`, and either `network_node` (exact match) or fuzzy `network_candidates`.

Usage: python3 build_signatures.py follia
"""

import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from build_roster import DATA_DIR, candidates_for, fold
from database import connect_readonly

# Per-process caches: the reviewer rebuilds after every click, and fuzzy matching against
# every node is the slow part. network.db doesn't change during review (restart if it does).
_nodes = None
_candidates = {}


def db_nodes():
    global _nodes
    if _nodes is None:
        with connect_readonly() as conn:
            _nodes = [(nid, nm, nt, fold(nm), " ".join(fold(nm)))
                      for nid, nm, nt in conn.execute("SELECT id, name, type FROM nodes")]
    return _nodes


def cached_candidates(name):
    if name not in _candidates:
        _candidates[name] = candidates_for(name, db_nodes())
    return _candidates[name]


TITLES = {"dott", "dr", "avv", "prof", "mons", "cav", "sig", "sigra", "comm", "on"}


def is_initials(name):
    """'B. Z.', 'Dott. D. S.', 'GA.', 'BZ' -> True; ignores honorifics.
    Short real names ("Ugo Foa") don't count: needs a period in the name, or every token <= 2 letters."""
    toks = [t for t in fold(name) if t not in TITLES]
    return bool(toks) and (all(len(t) <= 2 for t in toks) or ("." in name and all(len(t) <= 3 for t in toks)))


def recurring_titles(people):
    """Titles printed in two or more different months (letters pages, recurring columns:
    "Plausi e consensi", "Pro Domo Nostra"). A shared title says nothing about the issue for these."""
    months = defaultdict(set)
    for rec in people:
        for a in rec["appearances"]:
            if a.get("issue") and a.get("title"):
                months[a["title"]].add(a["issue"][:7])
    return {t for t, ms in months.items() if len(ms) > 1}


def dedupe_appearances(rec, recurring=frozenset(), same_issue=frozenset()):
    """Drop signatures counted twice because an issue was scanned in two PDFs.

    Two appearances are the same when (issue, title) match for this person; only the copy from the
    first file (in name order) is kept. A month-only label ("1947-01") and a day-level label
    ("1947-01-01") in the same month are the same issue only when this person has the same title under
    both, and, for a title in `recurring` (see recurring_titles), only when the reviewer confirmed the
    pair in review.json `same_issue` ([["1947-01", "1947-01-15"]]): a semi-monthly letters page has the
    same title in both issues of a month. Otherwise they stay distinct. Untitled signatures never merge
    month with day labels, and undated appearances are never merged (they count as zero issues).
    Recomputes rec["issues"].
    """
    apps = rec["appearances"]
    labels = defaultdict(set)  # title -> issue labels
    for a in apps:
        if a.get("issue") and a.get("title"):
            labels[a["title"]].add(a["issue"])
    to_day = {}  # (title, "YYYY-MM") -> lowest "YYYY-MM-DD" seen with that title
    for title, ls in labels.items():
        for m in (l for l in ls if len(l) == 7):
            days = sorted(l for l in ls if len(l) == 10 and l[:7] == m
                          and (title not in recurring or (m, l) in same_issue))
            if days:
                to_day[(title, m)] = days[0]
    for a in apps:
        if a.get("issue") and a.get("title"):
            a["issue"] = to_day.get((a["title"], a["issue"]), a["issue"])

    first_file = {}
    for a in sorted(apps, key=lambda a: a["file"]):
        if a.get("issue"):
            first_file.setdefault((a["issue"], a.get("title")), a["file"])
    rec["appearances"] = [a for a in apps if not a.get("issue") or first_file[(a["issue"], a.get("title"))] == a["file"]]
    rec["issues"] = {a["issue"] for a in rec["appearances"] if a.get("issue")}


def build(slug):
    base = DATA_DIR / slug
    review = json.loads((base / "review.json").read_text())
    aliases = review.get("aliases", {})
    skip = set(review.get("skip", []))
    drop = {(f, p, n) for f, p, n in review.get("drop", [])}
    distinct = set(review.get("new", []))
    exclude = review.get("exclude", {})
    notes = review.get("notes", {})

    people = defaultdict(lambda: {"source_names": set(), "as_printed": set(), "issues": set(), "kinds": set(), "appearances": []})
    undated, files, pages, skipped = [], 0, 0, 0
    for f in sorted((base / "extraction").glob("*.json")):
        data = json.loads(f.read_text())
        files += 1
        pages += len(data["pages"])
        undated += [{"file": data["file"], "page": p["page"], "footer": p.get("footer")}
                    for p in data["pages"] if not p.get("issue")]
        for s in data["signatures"]:
            if s["name"] in skip or (data["file"], s["page"], s["name"]) in drop:
                skipped += 1
                continue
            name = aliases.get(s["name"], s["name"])
            rec = people[" ".join(fold(name))]
            rec.setdefault("name", name)
            rec["source_names"].add(s["name"])
            rec["as_printed"].add(s.get("as_printed") or s["name"])
            if s.get("issue"):
                rec["issues"].add(s["issue"])
            rec["kinds"].add(s.get("kind", "other"))
            rec["appearances"].append(
                {"file": data["file"], "page": s["page"], "source_name": s["name"]}
                | {k: s[k] for k in ("issue", "title", "kind", "position", "confidence", "note") if s.get(k)})

    recurring = recurring_titles(people.values())
    same_issue = {tuple(p) for p in review.get("same_issue", [])}
    for rec in people.values():
        dedupe_appearances(rec, recurring, same_issue)

    # Person nodes only; a key shared by several nodes is ambiguous and never auto-linked.
    by_key = defaultdict(list)
    for nid, nm, nt, _, key in db_nodes():
        if nt == "person":
            by_key[key].append((nid, nm))

    contributors = []
    for key, rec in people.items():
        matches = by_key.get(key, [])
        exact = matches[0] if len(matches) == 1 else None
        if len(matches) > 1:
            candidates = [{"id": nid, "name": nm, "type": "person", "score": 1.0} for nid, nm in matches]
        else:
            candidates = [] if exact or rec["name"] in distinct else cached_candidates(rec["name"])
        letters_only = rec["kinds"] == {"letter"}
        if rec["name"] in exclude:
            excluded = exclude[rec["name"]] or "excluded in review"
        elif letters_only and len(rec["issues"]) < 2 and not exact:
            excluded = "one-off letter writer"
        elif is_initials(rec["name"]) and not exact and not candidates:
            excluded = "initials only, no match"  # merge into a full name to bring back
        else:
            excluded = None
        rec["appearances"].sort(key=lambda a: (a.get("issue") or "9999", a["file"], a["page"]))
        contributors.append({
            "name": rec["name"],
            "source_names": sorted(rec["source_names"]),
            "names_as_printed": sorted(rec["as_printed"]),
            "kinds": sorted(rec["kinds"]),
            "letters_only": letters_only,
            "include": excluded is None,
            **({"excluded_reason": excluded} if excluded else {}),
            "network_node": {"id": exact[0], "name": exact[1]} if exact else None,
            "network_candidates": candidates,
            "issue_count": len(rec["issues"]),
            "issues": sorted(rec["issues"]),
            **({"note": notes[rec["name"]]} if rec["name"] in notes else {}),
            "appearances": rec["appearances"],
        })
    contributors.sort(key=lambda c: (-c["issue_count"], c["name"]))

    included = [c for c in contributors if c["include"]]
    out = {
        "periodical": review.get("periodical"),
        "source": review.get("source"),
        "method": review.get("method"),
        "files": files,
        "pages": pages,
        "signature_count": sum(len(c["appearances"]) for c in contributors),
        "contributor_count": len(contributors),
        "included_count": len(included),
        "issues": sorted({i for c in included for i in c["issues"]}),
        "undated_pages": undated,
        "contributors": contributors,
    }
    (base / "contributors.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    # Same shape build_roster.py writes, so import_contributors.py can import it unchanged.
    roster = {
        "periodical": review.get("periodical"), "source": review.get("source"), "method": review.get("method"),
        "people": sorted(({"name": c["network_node"]["name"] if c["network_node"] else c["name"],
                           "roles": c["kinds"], "issues": c["issues"],
                           "status": "existing" if c["network_node"] else "unresolved" if c["network_candidates"] else "new",
                           **({"node_id": c["network_node"]["id"]} if c["network_node"] else {}),
                           **({"note": c["note"]} if c.get("note") else {})}
                          for c in included), key=lambda p: p["name"]),
    }
    (base / "roster.json").write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n")
    return (f"{files} files, {pages} pages ({len(undated)} undated), {out['signature_count']} signatures "
            f"({skipped} skipped by review), {len(contributors)} people: {len(included)} included, "
            f"excluded: {sum(c.get('excluded_reason') == 'one-off letter writer' for c in contributors)} one-off letter writers, "
            f"{sum(c.get('excluded_reason') == 'initials only, no match' for c in contributors)} initials-only, "
            f"{sum(c['name'] in exclude for c in contributors)} by review; "
            f"{sum(c['network_node'] is not None for c in included)} already in network, "
            f"{sum(bool(c['network_candidates']) for c in included)} with fuzzy candidates")


if __name__ == "__main__":
    print(build(sys.argv[1]))
