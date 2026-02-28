#!/usr/bin/env python3
"""Build/update SQLite commentary index from locally downloaded corpus files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from html import unescape
from typing import Dict, Iterable, List, Optional

from common_db import PARSER_VERSION, connect, default_data_dir, init_schema, replace_entries_for_source, set_manifest, upsert_source
from common_passages import Passage, parse_passage, scan_passages_in_text
from common_progress import ProgressReporter


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_MANIFEST = os.path.join(os.path.dirname(SCRIPT_DIR), "references", "sources-manifest.yaml")


def load_manifest(path: str = REF_MANIFEST) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?i)</div>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _infer_default_book(source: dict, text: str) -> Optional[str]:
    if source.get("default_book"):
        return source["default_book"]
    for token in (source.get("work_title", ""), source.get("commentator_key", "")):
        if "psalm" in token.lower():
            return "Psalms"
    m = re.search(r"\b(Commentary on|Exposition of)\s+([1-3]?\s*[A-Za-z ]+)\b", text[:1000], re.I)
    if m:
        return m.group(2).strip()
    return None


def _chapter_from_filename(path: str) -> Optional[int]:
    base = os.path.basename(path)
    m = re.search(r"(?:psalm|ps|chapter|ch)[-_ ]?(\d{1,3})", base, re.I)
    if m:
        return int(m.group(1))
    return None


def _normalize_excerpt(text: str, max_len: int = 900) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def _make_entry(source: dict, p: Passage, excerpt: str, source_id: int) -> dict:
    gran = "chapter" if p.is_chapter_only else ("verse" if p.chapter_start == p.chapter_end and p.verse_start == p.verse_end else "range")
    return {
        "source_id": source_id,
        "commentator_key": source["commentator_key"],
        "work_title": source["work_title"],
        "book_id": p.book_id,
        "chapter_start": p.chapter_start,
        "verse_start": p.verse_start,
        "chapter_end": p.chapter_end,
        "verse_end": p.verse_end,
        "granularity": gran,
        "passage_label": p.normalized_label(),
        "excerpt": _normalize_excerpt(excerpt),
        "sort_chapter": p.chapter_start,
        "sort_verse": p.verse_start or 0,
    }


def parse_source_file(source: dict, local_path: str, source_id: int) -> List[dict]:
    with open(local_path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    text = _strip_html(raw) if local_path.lower().endswith((".html", ".htm")) else raw
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    default_book = _infer_default_book(source, text)
    parser = source.get("parser", "generic_refscan")
    entries: List[dict] = []

    if parser == "psalm_chapter_fallback":
        ch = source.get("default_chapter") or _chapter_from_filename(local_path)
        if default_book and ch:
            p = parse_passage(f"{default_book} {ch}")
            excerpt = "\n".join(lines[:8]) or text[:700]
            entries.append(_make_entry(source, p, excerpt, source_id))
            return entries

    # Generic line-based reference scan: capture nearby content following detected reference.
    for i, line in enumerate(lines):
        found = scan_passages_in_text(line, default_book=default_book)
        if not found and default_book:
            # Handle headings like "Verse 3" when current source has a known default book/chapter.
            m_verse = re.search(r"\bVerse\s+(\d{1,3})\b", line, re.I)
            m_ch = re.search(r"\b(Psalm|Chapter)\s+(\d{1,3})\b", line, re.I)
            if m_ch:
                try:
                    found = [parse_passage(f"{default_book} {int(m_ch.group(2))}")]
                except Exception:
                    found = []
            elif m_verse and source.get("default_chapter"):
                try:
                    found = [parse_passage(f"{default_book} {int(source['default_chapter'])}:{int(m_verse.group(1))}")]
                except Exception:
                    found = []
        if not found:
            continue
        snippet_lines = [line]
        for j in range(i + 1, min(i + 8, len(lines))):
            # stop if next heading with another ref appears
            if scan_passages_in_text(lines[j], default_book=default_book):
                break
            snippet_lines.append(lines[j])
        excerpt = " ".join(snippet_lines)
        for p in found[:3]:
            entries.append(_make_entry(source, p, excerpt, source_id))

    if entries:
        return entries

    # Fallback: create chapter-level entry if manifest supplies default scope.
    if source.get("default_book") and source.get("default_chapter"):
        p = parse_passage(f"{source['default_book']} {int(source['default_chapter'])}")
        entries.append(_make_entry(source, p, "\n".join(lines[:12]) or text[:800], source_id))
    elif source.get("default_book"):
        p = parse_passage(f"{source['default_book']} 1")
        entries.append(_make_entry(source, p, "\n".join(lines[:12]) or text[:800], source_id))
    return entries


def build_index(manifest: dict, refresh: bool = False, progress: Optional[ProgressReporter] = None) -> int:
    progress = progress or ProgressReporter(enabled=False)
    data_dir = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_DATA_DIR", default_data_dir()))
    raw_root = os.path.join(data_dir, "raw")
    index_path = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_INDEX_PATH", os.path.join(data_dir, "index", "commentary.sqlite")))
    conn = connect(index_path)
    init_schema(conn)

    sources = manifest.get("sources", [])
    total_inserted = 0
    progress.emit("INDEX", "starting index build", sources=len(sources), db=index_path)
    for idx, source in enumerate(sources, start=1):
        local_rel = source["local_path"]
        local_path = os.path.join(raw_root, local_rel)
        if not os.path.isfile(local_path):
            progress.emit("WARN", "raw source file missing; skipping", source=local_rel)
            continue
        content_hash = _file_hash(local_path)
        source_id = upsert_source(
            conn,
            source["commentator_key"],
            source["work_title"],
            source["source_url"],
            local_path,
            source.get("parser", "generic_refscan"),
            PARSER_VERSION,
            content_hash,
        )
        try:
            parsed_entries = parse_source_file(source, local_path, source_id)
        except Exception as exc:
            progress.emit("WARN", "parse failed; retaining prior entries if present", source=local_rel, error=str(exc))
            continue

        replace_entries_for_source(conn, source_id, parsed_entries)
        conn.commit()
        total_inserted += len(parsed_entries)
        progress.emit("INDEX", "processed source", current=idx, total=len(sources), entries=len(parsed_entries), source=local_rel)

    set_manifest(conn, "parser_version", PARSER_VERSION)
    set_manifest(conn, "source_manifest_version", str(manifest.get("manifest_version", "1")))
    conn.commit()
    conn.close()
    progress.emit("DONE", "index build complete", inserted=total_inserted, db=index_path)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build SQLite commentary index")
    ap.add_argument("--refresh", action="store_true", help="Rebuild index from downloaded raw files")
    ap.add_argument("--progress", action="store_true", help="Emit progress messages")
    ap.add_argument("--json-progress", action="store_true", help="Emit progress as JSON lines")
    args = ap.parse_args(argv)
    manifest = load_manifest()
    reporter = ProgressReporter(enabled=args.progress or args.json_progress, json_mode=args.json_progress)
    return build_index(manifest, refresh=args.refresh, progress=reporter)


if __name__ == "__main__":
    raise SystemExit(main())

