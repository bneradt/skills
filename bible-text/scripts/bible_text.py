#!/usr/bin/env python3
"""Local Bible passage lookup for jburson/bible-data JSON files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMENTARY_SCRIPTS = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "bible-commentary", "scripts"))
if COMMENTARY_SCRIPTS not in sys.path:
    sys.path.insert(0, COMMENTARY_SCRIPTS)

from common_passages import parse_osis_ref, parse_passage  # type: ignore  # noqa: E402


def discover_bible_data_dir() -> str:
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".openclaw", "workspace", "data", "bible-data"),
        os.path.join(home, "openclaw", "workspace", "data", "bible-data"),
        os.path.join(home, "workspace", "data", "bible-data"),
        os.path.join(home, "bible-data"),
    ]
    for path in candidates:
        if os.path.isfile(os.path.join(path, "data", "KJV", "KJV.json")):
            return path
        if os.path.isfile(os.path.join(path, "KJV", "KJV.json")):
            return path
    return ""


def _clean_bible_data_text(text: str) -> str:
    # Remove inline feature markers used by jburson/bible-data (e.g., "Lord*s", "For*pn")
    out_words = []
    for word in text.split():
        if "*" in word:
            word = word.split("*", 1)[0]
        out_words.append(word)
    return " ".join(out_words).strip()


def find_translation_file(data_dir: str, translation: str) -> str:
    candidates = [
        os.path.join(data_dir, "data", translation, f"{translation}.json"),
        os.path.join(data_dir, "data", translation.lower(), f"{translation.lower()}.json"),
        os.path.join(data_dir, translation, f"{translation}.json"),
        os.path.join(data_dir, f"{translation}.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path

    # last resort: case-insensitive scan
    want = f"{translation.lower()}.json"
    for root, _, files in os.walk(data_dir):
        for name in files:
            if name.lower() == want:
                return os.path.join(root, name)
    raise FileNotFoundError(
        f"Could not find translation file for {translation}. Expected e.g. data/{translation}/{translation}.json under {data_dir}"
    )


def load_bible_data(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")
    return data


def verse_records_for_passage(items: List[dict], query):
    out = []
    for item in items:
        ref = item.get("r")
        text = item.get("t", "")
        if not isinstance(ref, str) or not isinstance(text, str):
            continue
        if item.get("h"):  # section heading/title rows
            continue
        try:
            verse_p = parse_osis_ref(ref)
        except Exception:
            continue
        if verse_p.book_id != query.book_id:
            continue
        if not (query.chapter_start <= verse_p.chapter_start <= query.chapter_end):
            continue
        if query.verse_start is not None and query.verse_end is not None:
            if verse_p.chapter_start == query.chapter_start == query.chapter_end:
                if not (query.verse_start <= (verse_p.verse_start or 0) <= query.verse_end):
                    continue
            elif query.chapter_start != query.chapter_end:
                # Cross-chapter request; apply per-edge filtering
                ch = verse_p.chapter_start
                vv = verse_p.verse_start or 0
                if ch == query.chapter_start and vv < query.verse_start:
                    continue
                if ch == query.chapter_end and vv > query.verse_end:
                    continue
        out.append(
            {
                "book": verse_p.book_name,
                "chapter": verse_p.chapter_start,
                "verse": verse_p.verse_start,
                "text": _clean_bible_data_text(text),
            }
        )
    out.sort(key=lambda r: (r["chapter"], r["verse"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Lookup Bible passage from local bible-data files")
    ap.add_argument("passage", help="Passage reference, e.g. 'Romans 8:28-30'")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")
    args = ap.parse_args()

    data_dir = os.path.expanduser(os.environ.get("BIBLE_TEXT_DATA_DIR", ""))
    if not data_dir:
        data_dir = discover_bible_data_dir()
    translation = os.environ.get("BIBLE_TEXT_TRANSLATION", "KJV")
    strict = os.environ.get("BIBLE_TEXT_STRICT", "false").lower() in {"1", "true", "yes", "on"}
    if not data_dir:
        print(
            "Bible data not found. Set BIBLE_TEXT_DATA_DIR or clone bible-data to "
            "~/.openclaw/workspace/data/bible-data",
            file=sys.stderr,
        )
        return 2

    try:
        query = parse_passage(args.passage, strict=strict)
        path = find_translation_file(data_dir, translation)
        items = load_bible_data(path)
        verses = verse_records_for_passage(items, query)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not verses:
        print(f"No verses found for {query.normalized_label()} in {translation}", file=sys.stderr)
        return 1

    payload = {
        "query": args.passage,
        "normalized_passage": query.normalized_label(),
        "translation": translation,
        "verses": verses,
        "text": " ".join(f"{v['verse']}. {v['text']}" for v in verses),
    }

    if args.as_json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{payload['normalized_passage']} ({translation})")
    for v in verses:
        print(f"{v['chapter']}:{v['verse']} {v['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
