import json
import sys

import pytest

import extract_toc


class FakeClient:
    def __init__(self, replies):
        self.replies = replies  # call order is not guaranteed with threads, so key by prompt page via image bytes

    def converse(self, **kw):
        page = kw["messages"][0]["content"][0]["image"]["source"]["bytes"]
        text, stop = self.replies[page]
        return {"stopReason": stop, "output": {"message": {"content": [{"text": text}]}}, "usage": {"in": 1}}


@pytest.mark.parametrize("data, ok", [
    ({"masthead": [], "articles": []}, True),
    ([], False),
    ("text", False),
    ({"masthead": [], "articles": "x"}, False),
    ({"masthead": None, "articles": []}, False),
    ({"articles": []}, False),
])
def test_check_result(data, ok):
    assert (extract_toc.check_result(data) is None) is ok


def test_stop_reason_must_be_end_turn(monkeypatch):
    monkeypatch.setattr(extract_toc, "halves", lambda img: [b"x"])
    client = FakeClient({b"x": ("{}", "max_tokens")})
    with pytest.raises(RuntimeError, match="max_tokens"):
        extract_toc.extract(client, None, "Mag")


def run_main(monkeypatch, tmp_path, replies, pages):
    class Doc:
        page_count = 10

    monkeypatch.setattr(extract_toc, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(extract_toc.fitz, "open", lambda p: Doc(), raising=False)
    monkeypatch.setattr(extract_toc.boto3, "client", lambda *a, **k: FakeClient(replies), raising=False)
    monkeypatch.setattr(extract_toc, "render_page", lambda doc, p, out: f"page{p}".encode())
    monkeypatch.setattr(extract_toc, "halves", lambda img: [img])
    monkeypatch.setattr(sys, "argv", ["extract_toc.py", "scan.pdf", "--slug", "t", "--periodical", "Mag", "--pages", pages])
    extract_toc.main()


def test_failed_pages_exit_nonzero_but_good_pages_are_kept(monkeypatch, tmp_path, capsys):
    good = json.dumps({"masthead": [], "articles": []})
    replies = {b"page2": (good, "end_turn"), b"page3": ("[1, 2]", "end_turn"),
               b"page4": (good, "max_tokens"), b"page5": ("not json", "end_turn")}
    with pytest.raises(SystemExit) as e:
        run_main(monkeypatch, tmp_path, replies, "2-5")
    assert "[3, 4, 5]" in str(e.value)
    ext = tmp_path / "data" / "t" / "extraction"
    assert json.loads((ext / "p-02.json").read_text())["_page"] == 2
    assert not (ext / "p-03.json").exists() and not (ext / "p-04.json").exists()
    assert json.loads((ext / "_manifest.json").read_text())["pages"] == [2, 3, 4, 5]


def test_all_good_exits_zero_and_manifest_accumulates(monkeypatch, tmp_path):
    good = json.dumps({"masthead": [], "articles": []})
    run_main(monkeypatch, tmp_path, {b"page2": (good, "end_turn")}, "2")
    run_main(monkeypatch, tmp_path, {b"page6": (good, "end_turn")}, "6")
    ext = tmp_path / "data" / "t" / "extraction"
    assert json.loads((ext / "_manifest.json").read_text())["pages"] == [2, 6]
