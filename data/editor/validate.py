#!/usr/bin/env python3
"""
Read-only consistency check of network.db and visualization/graph.json.

Fails (exit 1) if any of these invariants is broken:
  - an edge joins a node to itself
  - an edge points at a node that doesn't exist
  - an edge is stored reversed (source_id > target_id)
  - two edges join the same pair of nodes (either direction)
  - two nodes fold to the same key (case/accent/punctuation-insensitive name)
  - a node name is not in Unicode NFC
  - visualization/graph.json differs from the export of the database

Only reports (never fails on): 'unknown' edges,
person-person 'affiliation' edges, isolated nodes, connected components.

Usage: python3 validate.py [--db network.db] [--graph ../../visualization/graph.json]
Opens the database read-only (SQLite URI mode=ro).
"""

import argparse
import json
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from build_roster import fold
from database import DB_PATH

DEFAULT_GRAPH = Path(__file__).resolve().parent.parent.parent / "visualization" / "graph.json"


def export_graph(conn):
    """Same content and ordering as database.get_graph_json(), via a read-only connection."""
    nodes = [{"id": n, "type": t, "subtype": s}
             for n, t, s in conn.execute("SELECT name, type, subtype FROM nodes ORDER BY name")]
    links = [{"source": s, "target": t, "type": ty} for s, t, ty in conn.execute("""
        SELECT ns.name, nt.name, e.type FROM edges e
        JOIN nodes ns ON e.source_id = ns.id JOIN nodes nt ON e.target_id = nt.id
        ORDER BY ns.name, nt.name""")]
    return {"nodes": nodes, "links": links}


def components(node_ids, edges):
    parent = {n: n for n in node_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        if a in parent and b in parent:
            parent[find(a)] = find(b)
    return len({find(n) for n in node_ids})


def validate(db_path, graph_path):
    """Returns (failures, report) where both are lists of strings."""
    conn = sqlite3.connect(f"file:{quote(str(db_path))}?mode=ro", uri=True)
    failures, report = [], []
    try:
        nodes = conn.execute("SELECT id, name, type FROM nodes").fetchall()
        edges = conn.execute("SELECT id, source_id, target_id, type FROM edges").fetchall()
        types = {n[0]: n[2] for n in nodes}

        def check(label, rows):
            if rows:
                failures.append(f"{label}: {len(rows)} (e.g. {rows[:3]})")

        check("self-loops", [e[0] for e in edges if e[1] == e[2]])
        check("orphan edges", [e[0] for e in edges if e[1] not in types or e[2] not in types])
        check("reversed edges (source_id > target_id)", [e[0] for e in edges if e[1] > e[2]])
        pairs = defaultdict(list)
        for eid, s, t, _ in edges:
            pairs[(min(s, t), max(s, t))].append(eid)
        check("duplicate edge pairs", [ids for ids in pairs.values() if len(ids) > 1])
        check("names not in NFC", [n[1] for n in nodes if unicodedata.normalize("NFC", n[1]) != n[1]])
        keys = defaultdict(list)
        for nid, name, _ in nodes:
            keys[" ".join(fold(name))].append(name)
        check("duplicate folded keys", [v for v in keys.values() if len(v) > 1])

        graph_file = Path(graph_path)
        if not graph_file.exists():
            failures.append(f"graph.json not found at {graph_file}")
        else:
            on_disk, exported = json.loads(graph_file.read_text(encoding="utf-8")), export_graph(conn)
            if on_disk != exported:
                failures.append(
                    f"graph.json differs from the database export (nodes {len(on_disk.get('nodes', []))} vs "
                    f"{len(exported['nodes'])}, links {len(on_disk.get('links', []))} vs {len(exported['links'])})")

        degree = defaultdict(int)
        for _, s, t, _ in edges:
            degree[s] += 1
            degree[t] += 1
        report.append(f"nodes: {len(nodes)}, edges: {len(edges)}")
        report.append(f"'unknown' edges: {sum(e[3] == 'unknown' for e in edges)}")
        report.append("person-person 'affiliation' edges: "
                      f"{sum(e[3] == 'affiliation' and types.get(e[1]) == 'person' and types.get(e[2]) == 'person' for e in edges)}")
        report.append(f"isolated nodes: {sum(n[0] not in degree for n in nodes)}")
        report.append(f"connected components: {components([n[0] for n in nodes], [(e[1], e[2]) for e in edges])}")
    finally:
        conn.close()
    return failures, report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    args = ap.parse_args(argv)
    failures, report = validate(args.db, args.graph)
    print("Report:")
    for line in report:
        print("  " + line)
    if failures:
        print("FAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("OK: all invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
