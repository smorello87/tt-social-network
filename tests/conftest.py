"""Shared fixtures: every test works on a temporary SQLite file, never data/editor/network.db."""

import sqlite3
import sys
import types
from pathlib import Path

import pytest

EDITOR = Path(__file__).resolve().parent.parent / "data" / "editor"
sys.path.insert(0, str(EDITOR))

# extract_toc imports these at module level; the tests never call Bedrock or render PDFs.
for _mod in ("boto3", "fitz", "PIL", "PIL.Image"):
    if _mod not in sys.modules:
        try:
            __import__(_mod)
        except ImportError:
            sys.modules[_mod] = types.ModuleType(_mod)
sys.modules["PIL"].Image = sys.modules["PIL.Image"]

import database  # noqa: E402  (importing no longer touches the DB)


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Empty temporary database with the real schema; database.DB_PATH points at it."""
    path = tmp_path / "network.db"
    monkeypatch.setattr(database, "DB_PATH", path)
    monkeypatch.setattr(database, "BACKUP_DIR", tmp_path / "backups")
    database.init_db()
    return path


def add_node(path, name, ntype="person", subtype=None):
    with sqlite3.connect(path) as c:
        return c.execute("INSERT INTO nodes (name, name_normalized, type, subtype) VALUES (?, ?, ?, ?)",
                         (name, database.normalize_name(name), ntype, subtype)).lastrowid


def add_edge(path, a, b, etype="affiliation"):
    with sqlite3.connect(path) as c:
        return c.execute("INSERT INTO edges (source_id, target_id, type) VALUES (?, ?, ?)",
                         (min(a, b), max(a, b), etype)).lastrowid


def query(path, sql, params=()):
    with sqlite3.connect(path) as c:
        return c.execute(sql, params).fetchall()
