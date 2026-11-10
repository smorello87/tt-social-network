#!/usr/bin/env python3
"""
Step 2 of the contributor pipeline: merge per-page extractions into a roster,
apply hand-review decisions, and match every name against network.db.

Inputs (in data/<slug>/):
  extraction/p-NN.json   output of extract_toc.py
  review.json            hand-review decisions (created empty on first run):
    periodical     node name for the periodical
    source/method  provenance, copied into the roster
    issues         {"6": "1977-01"}  page -> issue override when not printed
    not_authors    names Qwen put in bylines that are article subjects
    drop           [[page, name, role?]] credits to discard; optional role prefix
                   limits it, e.g. [8, "Richard Gambino", "cover"]
    add            [[page, name, role]] credits Qwen missed
    aliases        {"Mike Iachetta": "Michael Iachetta"} variants -> canonical
    skip           names never imported (organizations, unresolvable credits)
    match          {"John Ciardi": 43} link to an existing node id
    new            names confirmed distinct from their fuzzy candidates
    notes          {"name": "free-text note"} kept in the roster

Output: data/<slug>/roster.json, one entry per person with status
  existing    linked to a node (exact match or review "match")
  new         no plausible match in the database (or confirmed via "new")
  unresolved  fuzzy candidates found; add the name to "match" or "new"
import_contributors.py refuses to run while any entry is unresolved.

Usage: python3 build_roster.py iam
"""

import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from database import _similarity, connect_readonly

DATA_DIR = Path(__file__).resolve().parent.parent

REVIEW_TEMPLATE = {
    "periodical": "", "source": "", "method": "", "issues": {}, "not_authors": [],
    "drop": [], "add": [], "aliases": {}, "skip": [], "match": {}, "new": [], "notes": {},
}


def fold(name):
    """Accent/punctuation-insensitive token list: 'Jean-Paul D’Amico' -> ['jean', 'paul', 'damico']."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[-.]", " ", s)
    return re.sub(r"[^a-z ]", "", s).split()


def parse_issue(text):
    if not text:
        return None
    for fmt in ("%B %Y", "%b %Y"):
        try:
            return datetime.strptime(re.sub(r"[,.]", "", text).strip().title(), fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return None


def collect(base, review):
    clean = lambda n: re.sub(r"\s+", " ", n.replace("’", "'")).strip()
    aliases = {clean(k): v for k, v in review["aliases"].items()}
    not_authors = {clean(n) for n in review["not_authors"]}
    drop = [(d[0], clean(d[1]), d[2] if len(d) > 2 else "") for d in review["drop"]]
    skip = {clean(n) for n in review["skip"]}

    roster = {}

    def add(page, issue, raw, role, reviewed=False):
        name = clean(raw)
        if not reviewed and any(page == dp and name == dn and role.startswith(dr) for dp, dn, dr in drop):
            return
        name = aliases.get(name, name)
        if not name or name in skip:
            return
        entry = roster.setdefault(name, {"roles": set(), "issues": set()})
        entry["roles"].add(role)
        if issue:
            entry["issues"].add(issue)

    page_issue = {}
    for f in sorted((base / "extraction").glob("p-*.json")):
        d = json.loads(f.read_text())
        p = d["_page"]
        issue = review["issues"].get(str(p)) or parse_issue(d.get("issue"))
        page_issue[p] = issue
        for m in d.get("masthead", []):
            for n in m["names"]:
                add(p, issue, n, "masthead: " + m["role"].title())
        for c in d.get("fine_print") or []:
            add(p, issue, c["name"], "officer: " + c["role"].title())
        for c in d.get("cover_credit") or []:
            add(p, issue, c["name"], "cover " + c["role"].lower())
        for a in d.get("articles", []):
            for n in a.get("byline") or []:
                if clean(n) not in not_authors:
                    add(p, issue, n, "author")
            for n in a.get("photo_or_art") or []:
                add(p, issue, n, "photographer/illustrator")
    for p, n, role in review["add"]:
        add(p, review["issues"].get(str(p)) or page_issue.get(p), n, role, reviewed=True)

    missing = sorted(p for p, i in page_issue.items() if not i)
    if missing:
        print(f"warning: no issue date for pages {missing}; add them to review.json 'issues'")
    return roster


SUFFIXES = {"jr", "sr", "ii", "iii"}

# Italian <-> English given names that denote the same first name.
_GIVEN_GROUPS = [
    {"giuseppe", "joseph"}, {"giovanni", "john"}, {"luigi", "louis"}, {"antonio", "anthony"},
    {"francesco", "frank", "francis"}, {"vincenzo", "vincent"}, {"salvatore", "sam"},
    {"pietro", "peter"}, {"paolo", "paul"}, {"michele", "michael"}, {"domenico", "dominic"},
    {"giacomo", "james"}, {"guglielmo", "william"}, {"carlo", "charles"}, {"enrico", "henry"},
    {"edoardo", "edward"}, {"roberto", "robert"}, {"riccardo", "richard"}, {"tommaso", "thomas"},
    {"stefano", "stephen"}, {"maria", "mary"}, {"giuseppina", "josephine"},
]
_GIVEN_GROUP = {n: i for i, g in enumerate(_GIVEN_GROUPS) for n in g}


def flip_comma(name):
    """'Barzini, Luigi' -> 'Luigi Barzini' (only the single-comma 'Surname, First' form)."""
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and parts[0] and parts[1]:
        return parts[1] + " " + parts[0]
    return name


def _strip_suffix(toks):
    return [t for t in toks if t not in SUFFIXES]


def candidates_for(name, nodes):
    toks = fold(flip_comma(name))
    if not toks:
        return []
    key = " ".join(toks)
    base = _strip_suffix(toks)
    found = []
    for nid, nm, ntype, toks2, key2 in nodes:
        if not toks2:
            continue
        # "John Ciardi" ~ "John Anthony Ciardi", "Domenico Bartoli" ~ "D Bartoli"
        same_person_shape = toks2[-1] == toks[-1] and toks2[0][0] == toks[0][0] and len(toks[-1]) > 3
        base2 = _strip_suffix(toks2)
        flagged = same_person_shape
        if not flagged and len(toks) > 1 and sorted(toks) == sorted(toks2):
            flagged = True  # same tokens in any order: "Loria Achille" ~ "Achille Loria"
        if not flagged and len(toks) == 1 and len(toks[0]) > 1 and len(toks2) > 1 and toks[0] == toks2[-1]:
            flagged = True  # bare surname: "Prezzolini" ~ "Giuseppe Prezzolini"
        if not flagged and base and base2 and len(base) > 1 and base == base2 and (toks != toks2):
            flagged = True  # generational suffix: "Luigi Barzini" ~ "Luigi Barzini Jr"
        if not flagged and len(base) > 1 and len(base2) > 1 and base[-1] == base2[-1]:
            g1, g2 = _GIVEN_GROUP.get(base[0]), _GIVEN_GROUP.get(base2[0])
            flagged = g1 is not None and g1 == g2  # "Joseph Tusiani" ~ "Giuseppe Tusiani"
        # Edit distance >= length difference, so a >15% length gap can't reach 0.85; skip the costly DP.
        if not flagged and abs(len(key) - len(key2)) > 0.15 * max(len(key), len(key2)):
            continue
        score = _similarity(key, key2)
        if score >= 0.85 or flagged:
            found.append({"id": nid, "name": nm, "type": ntype, "score": round(score, 2)})
    return sorted(found, key=lambda c: -c["score"])[:5]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    base = DATA_DIR / sys.argv[1]
    review_path = base / "review.json"
    if not review_path.exists():
        review_path.write_text(json.dumps(REVIEW_TEMPLATE, indent=2) + "\n")
        print(f"created {review_path}; fill in 'periodical' and re-run")
    review = {**REVIEW_TEMPLATE, **json.loads(review_path.read_text())}
    if not review["periodical"]:
        sys.exit("review.json: 'periodical' is required")

    roster = collect(base, review)

    conn = connect_readonly()
    degree = dict(conn.execute(
        "SELECT id, COUNT(*) FROM (SELECT source_id AS id FROM edges UNION ALL SELECT target_id FROM edges) GROUP BY id"))
    nodes = [(nid, nm, t, fold(nm), " ".join(fold(nm)))
             for nid, nm, t in conn.execute("SELECT id, name, type FROM nodes")]
    by_key = {}
    for n in nodes:
        by_key.setdefault(n[4], []).append(n)

    people = []
    for name in sorted(roster, key=lambda n: (fold(n)[-1:], fold(n))):
        e = roster[name]
        entry = {"name": name, "roles": sorted(e["roles"]), "issues": sorted(e["issues"])}
        exact = by_key.get(" ".join(fold(name)), []) if fold(name) else []
        if name in review["match"]:
            entry.update(status="existing", node_id=review["match"][name])
        elif len(exact) == 1:
            entry.update(status="existing", node_id=exact[0][0])
        elif name in review["new"]:
            entry["status"] = "new"
        else:
            cands = [{"id": n[0], "name": n[1], "type": n[2], "score": 1.0} for n in exact] or candidates_for(name, nodes)
            if cands or not fold(name):  # a name that folds to nothing ("***") needs a human
                for c in cands:
                    c["degree"] = degree.get(c["id"], 0)
                entry.update(status="unresolved", candidates=cands)
            else:
                entry["status"] = "new"
        if name in review["notes"]:
            entry["note"] = review["notes"][name]
        people.append(entry)

    for name in list(review["match"]) + review["new"]:
        if name not in roster:
            print(f"warning: review.json names {name!r}, which is not in the roster")

    out = {k: review[k] for k in ("periodical", "source", "method")}
    out["people"] = people
    (base / "roster.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    counts = {s: sum(p["status"] == s for p in people) for s in ("existing", "new", "unresolved")}
    print(f"{len(people)} people -> {base / 'roster.json'}: {counts}")
    for p in people:
        if p["status"] == "unresolved":
            print(f"  UNRESOLVED {p['name']}: " + "; ".join(
                f"{c['name']} (id {c['id']}, {c['degree']} edges, {c['score']})" for c in p["candidates"]))


if __name__ == "__main__":
    main()
