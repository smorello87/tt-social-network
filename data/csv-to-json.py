#!/usr/bin/env python3
"""
Build graph JSON from two CSVs:
- type1.csv: element,type
- singlerows.csv: source,target  (e.g., author,magazine)

Features:
- Auto-detects CSV encoding (or force via --encoding)
- Deduplicates rows in both CSVs (after trimming/collapsing whitespace)
- Normalizes names for matching, preserves first-seen display casing
- Resolves conflicting types with helpful warnings
- Emits JSON: {"nodes":[{"id":..., "type":...}], "links":[{"source":..., "target":...}]}

Usage:
  python csv-to-json.py --types type1.csv --edges singlerows.csv --out graph.json
Optional:
  --encoding auto|utf-8|utf-8-sig|cp1252|latin-1|mac_roman   (default: auto)
  --no-header-types
  --no-header-edges
  --delimiter ","
"""

import argparse, csv, json, sys, re, io
from collections import defaultdict

VALID_TYPES = {"person", "institution"}
DEFAULT_TYPE = "unknown"

def norm(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def _read_csv_rows(path, delimiter, has_header, encoding_opt="auto"):
    """
    Returns (rows:list[list[str]], used_encoding:str)
    Tries multiple encodings if encoding_opt == 'auto'.
    """
    if encoding_opt.lower() != "auto":
        used = encoding_opt
        with open(path, newline="", encoding=used, errors="strict") as f:
            text_stream = f.read()
        stream = io.StringIO(text_stream)
        reader = csv.reader(stream, delimiter=delimiter)
        if has_header:
            next(reader, None)
        return list(reader), used

    # auto-detect
    candidates = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "mac_roman"]
    raw = None
    with open(path, "rb") as fb:
        raw = fb.read()

    last_err = None
    for enc in candidates:
        try:
            text = raw.decode(enc, errors="strict")
            stream = io.StringIO(text)
            reader = csv.reader(stream, delimiter=delimiter)
            if has_header:
                next(reader, None)
            rows = list(reader)
            return rows, enc
        except UnicodeDecodeError as e:
            last_err = e
            continue

    raise UnicodeDecodeError(
        "csv-to-json", b"", 0, 0,
        f"Could not decode '{path}' with any of: {candidates}. "
        f"Last error: {last_err}"
    )

def read_types(path, delimiter, has_header=True, encoding_opt="auto"):
    rows, used_enc = _read_csv_rows(path, delimiter, has_header, encoding_opt)
    print(f"[info] {path}: decoded as {used_enc}", file=sys.stderr)

    type_map = {}           # norm_name_lower -> type
    display_name = {}       # norm_name_lower -> first-seen original casing
    seen_rows = set()       # for (element_lower, type_lower) dedupe

    for row in rows:
        if not row or len(row) < 2:
            continue
        raw_el, raw_ty = row[0], row[1]
        el = norm(raw_el)
        ty = norm(raw_ty).lower()
        if not el:
            continue

        key = (el.lower(), ty)
        if key in seen_rows:
            continue
        seen_rows.add(key)

        display_name.setdefault(el.lower(), raw_el.strip())

        if ty not in VALID_TYPES:
            print(
                f"[warn] type '{raw_ty}' for '{raw_el}' not in {VALID_TYPES}; treating as '{DEFAULT_TYPE}'",
                file=sys.stderr
            )
            ty = DEFAULT_TYPE

        prev = type_map.get(el.lower())
        if prev is None or (prev == DEFAULT_TYPE and ty in VALID_TYPES):
            type_map[el.lower()] = ty
        elif prev in VALID_TYPES and ty in VALID_TYPES and prev != ty:
            print(
                f"[warn] conflicting types for '{raw_el}': '{prev}' vs '{ty}'. Keeping '{prev}'.",
                file=sys.stderr
            )

    return type_map, display_name

def read_edges(path, delimiter, has_header=True, encoding_opt="auto"):
    rows, used_enc = _read_csv_rows(path, delimiter, has_header, encoding_opt)
    print(f"[info] {path}: decoded as {used_enc}", file=sys.stderr)

    edges = {}             # (src_lower, tgt_lower) -> edge_type
    display_names = {}     # lower_name -> first-seen original casing

    for row in rows:
        if not row or len(row) < 2:
            continue
        raw_src, raw_tgt = row[0], row[1]
        raw_type = row[2].strip() if len(row) >= 3 else ""
        src = norm(raw_src)
        tgt = norm(raw_tgt)
        if not src or not tgt:
            continue

        key = (src.lower(), tgt.lower())
        if key in edges:
            continue
        edges[key] = raw_type if raw_type else "affiliation"  # default to affiliation

        display_names.setdefault(src.lower(), raw_src.strip())
        display_names.setdefault(tgt.lower(), raw_tgt.strip())

    return edges, display_names

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", required=True)
    ap.add_argument("--edges", required=True)
    ap.add_argument("--out",   required=True)
    ap.add_argument("--delimiter", default=",")
    ap.add_argument("--encoding", default="auto",
                    help="auto|utf-8|utf-8-sig|cp1252|latin-1|mac_roman")
    ap.add_argument("--no-header-types", action="store_true")
    ap.add_argument("--no-header-edges", action="store_true")
    args = ap.parse_args()

    type_map, type_display = read_types(
        args.types, args.delimiter, has_header=not args.no_header_types, encoding_opt=args.encoding
    )
    edges, edge_display = read_edges(
        args.edges, args.delimiter, has_header=not args.no_header_edges, encoding_opt=args.encoding
    )

    # Merge display dictionaries, favoring first-seen from types file
    display = dict(edge_display)
    for k, v in type_display.items():
        display.setdefault(k, v)

    # Collect all nodes mentioned anywhere
    all_norm_names = set(display.keys()) | set(type_map.keys())
    nodes = []
    for name_l in sorted(all_norm_names):
        human_name = display.get(name_l, name_l)
        ty = type_map.get(name_l, DEFAULT_TYPE)
        nodes.append({"id": human_name, "type": ty})

    # Build links using display names for source/target
    links = []
    for (src_l, tgt_l), edge_type in sorted(edges.items()):
        links.append({
            "source": display.get(src_l, src_l),
            "target": display.get(tgt_l, tgt_l),
            "type": edge_type,
        })

    graph = {"nodes": nodes, "links": links}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"[done] wrote {args.out}", file=sys.stderr)
    print(f"[stats] nodes={len(nodes)} links={len(links)}", file=sys.stderr)

if __name__ == "__main__":
    main()
