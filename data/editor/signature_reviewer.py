#!/usr/bin/env python3
"""
Review UI for build_signatures.py output (e.g. La Follia).

Shows each contributor with the scan pages they signed, and writes decisions
(merge/alias, match to a DB node, mark distinct, skip, drop one credit, resolve an
open question) to data/<slug>/review.json, then rebuilds contributors.json.
Read-only with respect to network.db. Standard library only (no Flask needed).

Usage: python3 signature_reviewer.py follia   ->  http://localhost:5003
"""

import json
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from build_roster import DATA_DIR
from build_signatures import build
from database import DB_PATH

SLUG = sys.argv[1] if len(sys.argv) > 1 else "follia"
BASE = DATA_DIR / SLUG
PAGES = BASE / "pages"  # rendered scans, gitignored (data/*/pages/)
TEMPLATE = Path(__file__).resolve().parent / "templates" / "signature_reviewer.html"
PORT = 5003


def load_review():
    return json.loads((BASE / "review.json").read_text())


def save_review(review):
    (BASE / "review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")


def apply_decision(d):
    """Record one review decision; returns an error string or None."""
    review = load_review()
    action, name = d.get("action"), d.get("name", "")
    if action == "merge":  # name -> target (another contributor or a DB node name)
        target = (d.get("target") or "").strip()
        if not target or target == name:
            return "target required"
        aliases = review.setdefault("aliases", {})
        # Re-point earlier aliases that led to the old name, so merges chain.
        for k, v in list(aliases.items()):
            if v == name:
                aliases[k] = target
        for source in d.get("source_names", []):
            if source != target:
                aliases[source] = target
    elif action == "distinct":
        if name not in review.setdefault("new", []):
            review["new"].append(name)
    elif action == "skip":
        for source in d.get("source_names", [name]):
            if source not in review.setdefault("skip", []):
                review["skip"].append(source)
    elif action == "drop":
        entry = [d["file"], d["page"], d["source_name"]]
        if entry not in review.setdefault("drop", []):
            review["drop"].append(entry)
    elif action == "resolve":
        question = review.get("open_questions", {}).pop(d["key"], None)
        if question is not None:
            review.setdefault("resolved_questions", {})[d["key"]] = {
                "question": question, "answer": (d.get("answer") or "").strip()}
    elif action == "exclude":
        review.setdefault("exclude", {})[name] = (d.get("reason") or "").strip() or "excluded in review"
    elif action == "include":
        review.get("exclude", {}).pop(name, None)
    elif action == "note":
        review.setdefault("notes", {})[name] = d.get("note", "")
    else:
        return f"unknown action {action}"
    save_review(review)
    return None


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self.send(200, TEMPLATE.read_text().replace("{{ slug }}", SLUG), "text/html; charset=utf-8")
        elif path == "/api/data":
            with sqlite3.connect(DB_PATH) as conn:
                people = [r[0] for r in conn.execute("SELECT name FROM nodes WHERE type = 'person' ORDER BY name")]
            self.send(200, {"contributors": json.loads((BASE / "contributors.json").read_text()),
                            "review": load_review(), "db_people": people})
        elif path.startswith("/scan/") and path.endswith(".png"):
            pdf, _, page = path[len("/scan/"):-len(".png")].rpartition("/")
            src = Path(load_review()["scan_dir"]) / pdf
            if "/" in pdf or src.suffix != ".pdf" or not src.is_file() or not page.isdigit():
                return self.send(404, {"error": "not found"})
            out = PAGES / f"{src.stem}-p{int(page):02d}.png"
            if not out.exists():
                PAGES.mkdir(parents=True, exist_ok=True)
                subprocess.run(["pdftoppm", "-f", page, "-l", page, "-r", "130", "-png", "-singlefile",
                                str(src), str(out.with_suffix(""))], check=True)
            self.send(200, out.read_bytes(), "image/png")
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/decision":
            return self.send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        error = apply_decision(body)
        if error:
            return self.send(400, {"error": error})
        self.send(200, {"summary": build(SLUG)})

    def log_message(self, fmt, *args):
        if not self.path.startswith("/scan/"):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    print("Precomputing network matches…", flush=True)
    print(build(SLUG), flush=True)  # warms the match cache so clicks are fast
    print(f"Reviewing {BASE}: http://localhost:{PORT}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
