#!/usr/bin/env python3
"""
Step 1 of the contributor pipeline: extract masthead + table-of-contents
names from a scanned periodical PDF with Qwen3-VL on AWS Bedrock.

- Renders each requested page to data/<slug>/pages/p-NN.jpg (gitignored)
- Sends the left and right halves of the page to Qwen (masthead column and
  TOC column read much better at half-page resolution)
- Writes one JSON per page to data/<slug>/extraction/p-NN.json
- Pages already extracted are skipped unless --force

Usage:
  python3 extract_toc.py SCAN.pdf --slug iam --periodical "I-AM" --pages 2,4,6-10
Then review the output (see build_roster.py).
"""

import argparse
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
import fitz  # PyMuPDF
from PIL import Image

DATA_DIR = Path(__file__).resolve().parent.parent
MODEL = "qwen.qwen3-vl-235b-a22b"
REGION = "us-east-1"
LONG_SIDE_PX = 3200

PROMPT = """These two images are the left and right halves of one masthead / table-of-contents page from the periodical {periodical}.

Transcribe EVERY person named on the page, exactly as printed (keep accents, initials, hyphens, capitalization). Return ONLY a JSON object with this shape:

{{
  "issue": "Month Year as printed, e.g. November 1976 (null if not visible)",
  "volume": "volume/number as printed or null",
  "masthead": [ {{"role": "EDITOR", "names": ["..."]}} ],
  "fine_print": [ {{"role": "e.g. Chairman / President / Treasurer", "name": "..."}} ],
  "cover_credit": [ {{"role": "photographer / illustrator / other", "name": "..."}} ],
  "articles": [
    {{"page": 28, "section": "feature or department", "title": "...", "byline": ["authors"], "photo_or_art": ["photographers/illustrators"], "subjects": ["people the article is ABOUT"]}}
  ],
  "organizations": ["companies or institutions named"],
  "uncertain": ["names you could not read confidently, with your best reading and why"]
}}

Rules:
- Masthead: the column with role headings (EDITOR, CONTRIBUTING EDITORS, PUBLISHER, etc.). One entry per role heading; split comma-separated name lists into separate names. Strip parenthetical notes like "(photography)" from names but keep them in the role.
- The small-print legal paragraph under the masthead often names officers (Chairman, President, Treasurer, Secretary) — put those in fine_print.
- Table of contents entries are: page number, bold title, then a description line, then (optionally) a final line with ONLY the author name(s). The byline is ALWAYS the LAST line of the entry and contains nothing but names joined by commas or "and". The line directly under the title is the description and is NEVER the byline, even if it starts with a person's name (e.g. "Paul Sorvino, superstar" or "Gerald Ford and Jimmy Carter parlano italiano" are descriptions; those people are subjects). An entry with only title + description has an empty byline.
- "Photographed by X" / "Illustrated by X" / "X (photography)" go in photo_or_art, not byline.
- A cover note naming a book or a person pictured is not a cover credit; only photographers/illustrators of the cover are.
- subjects: only real people's names.
- Output raw JSON only, no markdown fences, no commentary."""


def parse_pages(spec, page_count):
    if not spec:
        return list(range(1, page_count + 1))
    pages = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages.extend(range(int(a), int(b) + 1))
        else:
            pages.append(int(part))
    return pages


def render_page(doc, page_no, out_path):
    page = doc[page_no - 1]
    zoom = LONG_SIDE_PX / max(page.rect.width, page.rect.height)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img.save(out_path, "JPEG", quality=88)
    return img


def halves(img):
    w, h = img.size
    overlap = w // 30
    out = []
    for box in ((0, 0, w // 2 + overlap, h), (w // 2 - overlap, 0, w, h)):
        buf = io.BytesIO()
        img.crop(box).save(buf, "JPEG", quality=90)
        out.append(buf.getvalue())
    return out


def extract(client, img, periodical):
    content = [{"image": {"format": "jpeg", "source": {"bytes": b}}} for b in halves(img)]
    content.append({"text": PROMPT.format(periodical=periodical)})
    resp = client.converse(
        modelId=MODEL,
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 8000, "temperature": 0},
    )
    text = resp["output"]["message"]["content"][0]["text"].strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    return text, resp["usage"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--slug", required=True, help="folder name under data/, e.g. iam")
    ap.add_argument("--periodical", required=True, help="periodical name, used in the prompt")
    ap.add_argument("--pages", help="1-based pages, e.g. 2,4,6-10 (default: all)")
    ap.add_argument("--force", action="store_true", help="re-extract pages that already have JSON")
    args = ap.parse_args()

    base = DATA_DIR / args.slug
    (base / "pages").mkdir(parents=True, exist_ok=True)
    (base / "extraction").mkdir(parents=True, exist_ok=True)

    doc = fitz.open(args.pdf)
    pages = parse_pages(args.pages, doc.page_count)
    client = boto3.client("bedrock-runtime", region_name=REGION)

    todo = []
    for p in pages:
        out = base / "extraction" / f"p-{p:02d}.json"
        if out.exists() and not args.force:
            print(f"p{p:02d}: already extracted, skipping")
            continue
        todo.append((p, render_page(doc, p, base / "pages" / f"p-{p:02d}.jpg")))

    def run(item):
        p, img = item
        try:
            text, usage = extract(client, img, args.periodical)
        except Exception as e:
            return p, f"ERROR: {e}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            (base / "extraction" / f"p-{p:02d}.raw.txt").write_text(text)
            return p, "ERROR: invalid JSON (raw output saved)"
        data["_page"] = p
        (base / "extraction" / f"p-{p:02d}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return p, usage

    with ThreadPoolExecutor(max_workers=4) as ex:
        for p, result in ex.map(run, todo):
            print(f"p{p:02d}: {result}")


if __name__ == "__main__":
    main()
