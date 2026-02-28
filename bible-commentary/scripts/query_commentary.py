#!/usr/bin/env python3
"""Query local SQLite commentary index by Bible passage, with auto-bootstrap on first use."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from typing import Dict, List, Optional

from common_db import PARSER_VERSION, connect, default_data_dir, default_index_path, get_manifest, init_schema, search_entries
from common_passages import parse_passage, split_by_chapter
from common_progress import ProgressReporter
import build_index


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIBLE_TEXT_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "bible-text", "scripts", "bible_text.py"))


def _auto_bootstrap_needed(index_path: str, manifest: dict) -> bool:
    if not os.path.isfile(index_path):
        return True
    try:
        conn = connect(index_path)
        init_schema(conn)
        parser_version = get_manifest(conn, "parser_version")
        manifest_version = get_manifest(conn, "source_manifest_version")
        conn.close()
        if parser_version != PARSER_VERSION:
            return True
        if manifest_version not in {str(manifest.get("manifest_version", "1")), "ai_friendly_v1"}:
            return True
        if manifest_version == "ai_friendly_v1":
            return False
    except sqlite3.DatabaseError:
        return True

    data_dir = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_DATA_DIR", default_data_dir()))
    raw_root = os.path.join(data_dir, "raw")
    for src in manifest.get("sources", []):
        if src.get("required", True) and not os.path.isfile(os.path.join(raw_root, src["local_path"])):
            return True
    return False


def _run_bootstrap(progress: ProgressReporter, refresh: bool = False) -> None:
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "bootstrap_commentary.py"), "--progress"]
    if refresh:
        cmd.append("--refresh")
    progress.emit("SETUP", "first-time setup detected; downloading and indexing local commentary corpus")
    progress.emit("SETUP", "this can take several minutes")
    # stream output directly for frequent communication
    subprocess.run(cmd, check=True)


def _fetch_bible_text(passage: str) -> Optional[dict]:
    if not os.path.isfile(BIBLE_TEXT_SCRIPT):
        return None
    try:
        cp = subprocess.run(
            [sys.executable, BIBLE_TEXT_SCRIPT, passage, "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(cp.stdout)
    except Exception:
        return None


def _priority_map_from_env() -> Dict[str, int]:
    pref = os.environ.get("BIBLE_COMMENTARY_PREFERRED_COMMENTATORS", "henry,calvin,gill,jfb,spurgeon")
    order = [x.strip().lower() for x in pref.split(",") if x.strip()]
    return {k: i for i, k in enumerate(order)}


def _synthesize(results: List[dict], passage_label: str) -> str:
    if not results:
        return f"No indexed commentary excerpts were found for {passage_label}."
    names = []
    themes = []
    for r in results[:5]:
        ck = r["commentator"]
        if ck not in names:
            names.append(ck)
        excerpt = (r.get("excerpt") or "").strip()
        if excerpt:
            themes.append(excerpt[:180].rstrip())
    return (
        f"Retrieved {len(results)} local commentary excerpt(s) for {passage_label} "
        f"from {', '.join(names)}. Review the attributed excerpts for detail; summary themes: "
        + " | ".join(themes[:3])
    )


def query(passage_text: str, progress: ProgressReporter, as_json: bool = False) -> int:
    manifest = build_index.load_manifest()
    index_path = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_INDEX_PATH", default_index_path()))
    auto_bootstrap = os.environ.get("BIBLE_COMMENTARY_AUTO_BOOTSTRAP", "true").lower() in {"1", "true", "yes", "on"}
    setup_performed = False
    if _auto_bootstrap_needed(index_path, manifest):
        if not auto_bootstrap:
            print("Commentary corpus/index not ready and auto-bootstrap disabled.", file=sys.stderr)
            print("Run bootstrap_commentary.py --progress", file=sys.stderr)
            return 2
        _run_bootstrap(progress)
        setup_performed = True

    try:
        passage = parse_passage(passage_text)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    conn = connect(index_path)
    init_schema(conn)
    priority = _priority_map_from_env()
    max_excerpts = int(os.environ.get("BIBLE_COMMENTARY_MAX_EXCERPTS", "8"))

    all_results: List[dict] = []
    for ch_passage in split_by_chapter(passage):
        chunk_results = search_entries(conn, ch_passage, priority, limit=max_excerpts)
        all_results.extend(chunk_results)
    # dedupe and sort by score
    dedup = {}
    for r in all_results:
        key = (r["commentator"], r["coverage"], r["excerpt"][:120])
        prev = dedup.get(key)
        if prev is None or r["score"] > prev["score"]:
            dedup[key] = r
    results = sorted(dedup.values(), key=lambda r: (-r["score"], r["commentator"], r["coverage"]))[:max_excerpts]

    bible_text = _fetch_bible_text(passage_text)
    warnings: List[str] = []
    if not results:
        warnings.append("No direct indexed commentary excerpts found; corpus/parser coverage may be incomplete.")
    if all(r["commentator"] != "spurgeon" for r in results) and passage.book_name != "Psalms":
        warnings.append("Spurgeon coverage in this MVP is primarily Psalms (Treasury of David).")

    payload = {
        "query": passage_text,
        "normalized_passage": passage.normalized_label(),
        "setup_performed": setup_performed,
        "bible_text": bible_text,
        "results": results,
        "synthesis": _synthesize(results, passage.normalized_label()),
        "warnings": warnings,
        "provenance": [{"commentator": r["commentator"], "source_url": r["source_url"]} for r in results],
    }

    if as_json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"{payload['normalized_passage']}")
    if setup_performed:
        print("First-time setup was performed (local download + indexing).")
    if bible_text:
        print(f"\nBible Text ({bible_text.get('translation')}):")
        print(bible_text.get("text", ""))
    print("\nCommentary Summary:")
    print(payload["synthesis"])
    if warnings:
        print("\nNotes:")
        for w in warnings:
            print(f"- {w}")
    if results:
        print("\nExcerpts:")
        for r in results:
            print(f"- [{r['commentator']}] {r['work']} ({r['coverage']}, {r['granularity']}, score={r['score']})")
            print(f"  {r['excerpt']}")
            print(f"  Source: {r['source_url']}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Query local Bible commentary index")
    ap.add_argument("passage", help="Passage reference, e.g. 'Romans 8:28-30'")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")
    ap.add_argument("--progress", action="store_true", help="Emit progress messages")
    ap.add_argument("--json-progress", action="store_true", help="Emit progress as JSON lines")
    args = ap.parse_args(argv)
    reporter = ProgressReporter(enabled=args.progress or args.json_progress, json_mode=args.json_progress)
    return query(args.passage, reporter, as_json=args.as_json)


if __name__ == "__main__":
    raise SystemExit(main())
