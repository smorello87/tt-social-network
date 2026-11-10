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
  existing    linked to a node (exact match to a single person node, or review "match")
  new         no plausible match in the database (or confirmed via "new", which wins over an exact match)
  unresolved  fuzzy candidates found (in the database, or another name in this roster with
              type "roster", including names already confirmed "new"); add the name to "match"
              or "new", or alias one spelling to the other.
              Spellings that differ only in case/whitespace collapse into one entry.
Names printed "Surname, First" become "First Surname" after aliases/skip are applied, so
"match", "new" and "notes" use the "First Surname" form ("Lowry Nelson, Jr" is not flipped).
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

from database import _similarity, connect_readonly, normalize_name

DATA_DIR = Path(__file__).resolve().parent.parent

REVIEW_TEMPLATE = {
    "periodical": "", "source": "", "method": "", "issues": {}, "not_authors": [],
    "drop": [], "add": [], "aliases": {}, "skip": [], "match": {}, "new": [], "notes": {},
}


def fold(name):
    """Accent/punctuation-insensitive token list: 'Jean-Paul D’Amico' -> ['jean', 'paul', 'damico'].
    Digits are kept, so 'Novella' and 'Novella 2000' stay distinct."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[-.]", " ", s)
    return re.sub(r"[^a-z0-9 ]", "", s).split()


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
    variants = {}

    def add(page, issue, raw, role, reviewed=False):
        name = clean(raw)
        if not reviewed and any(page == dp and name == dn and role.startswith(dr) for dp, dn, dr in drop):
            return
        name = aliases.get(name, name)
        if not name or name in skip:
            return
        name = flip_comma(name)  # "Banti, Anna" -> "Anna Banti", the DB's order (match/new/notes use this form)
        # "Del vita" / "Del Vita" (case, NFC and whitespace variants) are one person: keep the first spelling
        name = variants.setdefault(unicodedata.normalize("NFC", name).casefold(), name)
        entry = roster.setdefault(name, {"roles": set(), "issues": set()})
        entry["roles"].add(role)
        if issue:
            entry["issues"].add(issue)

    manifest = base / "extraction" / "_manifest.json"
    if manifest.exists():
        gone = [p for p in json.loads(manifest.read_text()).get("pages", [])
                if not (base / "extraction" / f"p-{p:02d}.json").exists()]
        if gone:
            sys.exit(f"extraction/_manifest.json lists pages {gone} with no p-NN.json; re-run extract_toc.py")
    else:
        print("warning: no extraction/_manifest.json, so missing pages can't be detected "
              "(extract_toc.py writes it)")

    uncertain = []
    page_issue = {}
    for f in sorted((base / "extraction").glob("p-*.json")):
        d = json.loads(f.read_text())
        p = d["_page"]
        uncertain += [(p, str(u)) for u in d.get("uncertain") or []]
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

    for p, u in uncertain:
        hit = [n for n in roster if n.lower() in u.lower()]
        if hit:
            print(f"warning: model was unsure about {hit} on page {p}: {u}")

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

# Italian diminutives / hypocoristics -> the full names they can stand for (keys and values are
# folded: no accents, so "Totò" is "toto"). Used only to flag a
# candidate for review ("Nino Guareschi" ~ "Giovanni Guareschi"), never to link: one diminutive can
# stand for several names (Nino: Giovanni or Antonino), so it can't identify anyone on its own.
_HYPOCORISTICS = {
    "nino": {"giovanni", "giovannino", "antonino", "antonio"},
    "gianni": {"giovanni"}, "vanni": {"giovanni"}, "nanni": {"giovanni"},
    "gino": {"luigi", "luigino", "giorgio"}, "gigi": {"luigi"},
    "beppe": {"giuseppe"}, "peppe": {"giuseppe"}, "peppino": {"giuseppe"}, "pino": {"giuseppe", "giuseppino"},
    "pippo": {"giuseppe", "filippo"},
    "toto": {"salvatore", "antonio"}, "turi": {"salvatore"}, "tore": {"salvatore"},
    "tonino": {"antonio"}, "tonio": {"antonio"}, "totonno": {"antonio"},
    "mimmo": {"domenico"}, "mimi": {"domenico"}, "memmo": {"domenico", "guglielmo"},
    "sandro": {"alessandro"}, "renzo": {"lorenzo"}, "enzo": {"vincenzo", "lorenzo"},
    "lello": {"raffaele", "raffaello"}, "ciccio": {"francesco"}, "cecco": {"francesco"},
    "checco": {"francesco"}, "franco": {"francesco"}, "nando": {"ferdinando", "fernando"},
    "dino": {"bernardino", "corradino", "leopoldo"}, "pina": {"giuseppina"}, "peppina": {"giuseppina"},
    "nella": {"antonella", "giovanna"}, "bice": {"beatrice"}, "titta": {"battista", "giambattista", "giovanbattista"},
    "gege": {"gennaro"}, "rino": {"salvatore", "gennaro"},
}


def _hypocoristic_pair(a, b):
    """True if a and b can be the same given name via a diminutive (both ways, or a shared full name)."""
    if a == b:
        return False
    ea, eb = {a} | _HYPOCORISTICS.get(a, set()), {b} | _HYPOCORISTICS.get(b, set())
    return bool(ea & eb)


def flip_comma(name):
    """'Barzini, Luigi' -> 'Luigi Barzini' (only the single-comma 'Surname, First' form).
    'Lowry Nelson, Jr' is left alone: a generational suffix after the comma is not a given name."""
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and parts[0] and parts[1] and not (fold(parts[1]) and set(fold(parts[1])) <= SUFFIXES):
        return parts[1] + " " + parts[0]
    return name


def _strip_suffix(toks):
    return [t for t in toks if t not in SUFFIXES]


def _edit_distance(a, b):
    return round((1 - _similarity(a, b)) * max(len(a), len(b)))


def _near_given(a, b):
    """Given names close enough to be one name misread or shortened: edit distance 1
    ("Giberto" ~ "Gilberto"), distance 2 only when both have 6+ letters ("Erberto" ~ "Roberto";
    short pairs at distance 2 are mostly different names: Mario/Carlo, Aldo/Elmo, Karl/Mary),
    or a 4+ letter hypocoristic ending of the other ("Renzo" ~ "Lorenzo", "Nino" ~ "Antonino")."""
    if len(a) < 4 or len(b) < 4:
        return False
    d = _edit_distance(a, b)
    short, long_ = sorted((a, b), key=len)
    return d <= 1 or (d == 2 and len(short) >= 6) or (short != long_ and long_.endswith(short))


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
        if not flagged and len(base) > 1 and len(base2) > 1 and base[-1] == base2[-1] and len(base[-1]) > 3 \
                and _near_given(base[0], base2[0]):
            flagged = True  # same surname, near-identical given name: "Giberto Altichieri" ~ "Gilberto Altichieri"
        if not flagged and len(base) > 1 and len(base2) > 1 and base[-1] == base2[-1] \
                and _hypocoristic_pair(base[0], base2[0]):
            flagged = True  # diminutive: "Nino Guareschi" ~ "Giovanni Guareschi" (flag only, never a link)
        # Edit distance >= length difference, so a >15% length gap can't reach 0.85; skip the costly DP.
        if not flagged and abs(len(key) - len(key2)) > 0.15 * max(len(key), len(key2)):
            continue
        score = _similarity(key, key2)
        if score >= 0.85 or flagged:
            found.append(({"id": nid, "name": nm, "type": ntype, "score": round(score, 2)}, flagged))
    # Every rule-based candidate is kept (a bare "Rossi" must show all eight Rossis, not the first
    # five); only candidates found by string similarity alone are capped at five.
    found.sort(key=lambda c: -c[0]["score"])
    similar_only = [c for c, flagged in found if not flagged][:5]
    return [c for c, flagged in found if flagged or c in similar_only]


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

    # Nodes already linked to this periodical (i.e. imported by an earlier run).
    pid = conn.execute("SELECT id FROM nodes WHERE name_normalized = ? AND type = 'institution'",
                       (normalize_name(review["periodical"]),)).fetchone()
    imported = set()
    if pid:
        imported = {r[0] for r in conn.execute(
            "SELECT target_id FROM edges WHERE source_id = ? UNION SELECT source_id FROM edges WHERE target_id = ?",
            (pid[0], pid[0]))}

    people = []
    for name in sorted(roster, key=lambda n: (fold(n)[-1:], fold(n))):
        e = roster[name]
        entry = {"name": name, "roles": sorted(e["roles"]), "issues": sorted(e["issues"])}
        exact = by_key.get(" ".join(fold(name)), []) if fold(name) else []
        if name in review["match"]:
            entry.update(status="existing", node_id=review["match"][name])
        elif name in review["new"] and not (len(exact) == 1 and exact[0][0] in imported):
            # Checked before exact matches so a reviewer can declare a homonym distinct. Once the
            # name has been imported (its node is linked to the periodical), re-runs keep it "existing".
            entry["status"] = "new"
        elif len(exact) == 1 and exact[0][2] == "person":
            entry.update(status="existing", node_id=exact[0][0])
        else:  # no match, several nodes with the same key, or the only match isn't a person
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

    # Compare the roster's own unmatched names with each other so one person can't become two nodes.
    # Names in review "new" are confirmed distinct; alias one spelling to the other to merge them.
    # A name confirmed "new" is still a comparison target: confirming one spelling must not silently
    # wave through a second, unreviewed spelling of the same person.
    unmatched = [p for p in people if p["status"] in ("new", "unresolved") and fold(p["name"])]
    pending = [p for p in unmatched if p["name"] not in review["new"]]
    peers = [(p["name"], p["name"], "roster", fold(p["name"]), " ".join(fold(p["name"]))) for p in unmatched]
    for p in pending:
        found = candidates_for(p["name"], [n for n in peers if n[0] != p["name"]])
        if found:
            p["status"] = "unresolved"
            p["candidates"] = p.get("candidates", []) + [
                {"id": None, "name": c["name"], "type": "roster", "score": c["score"], "degree": 0} for c in found]

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
