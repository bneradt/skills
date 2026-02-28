#!/usr/bin/env python3
"""SQLite schema and query helpers for commentary indexing."""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from common_passages import BOOKS, Passage

SCHEMA_VERSION = "1"
PARSER_VERSION = "0.1"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def expand_user(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def default_data_dir() -> str:
    return expand_user(os.environ.get("BIBLE_COMMENTARY_DATA_DIR", "~/.openclaw/data/bible-commentary"))


def default_index_path() -> str:
    return expand_user(
        os.environ.get("BIBLE_COMMENTARY_INDEX_PATH", os.path.join(default_data_dir(), "index", "commentary.sqlite"))
    )


def ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    db_path = path or default_index_path()
    ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
          id INTEGER PRIMARY KEY,
          canon_order INTEGER NOT NULL,
          osis TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS book_aliases (
          alias TEXT PRIMARY KEY,
          book_id INTEGER NOT NULL REFERENCES books(id)
        );
        CREATE TABLE IF NOT EXISTS sources (
          id INTEGER PRIMARY KEY,
          commentator_key TEXT NOT NULL,
          work_title TEXT NOT NULL,
          source_url TEXT NOT NULL,
          local_raw_path TEXT NOT NULL,
          parser_name TEXT NOT NULL,
          parser_version TEXT NOT NULL,
          content_hash TEXT,
          downloaded_at TEXT NOT NULL,
          UNIQUE(commentator_key, work_title, local_raw_path)
        );
        CREATE TABLE IF NOT EXISTS entries (
          id INTEGER PRIMARY KEY,
          source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
          commentator_key TEXT NOT NULL,
          work_title TEXT NOT NULL,
          book_id INTEGER NOT NULL REFERENCES books(id),
          chapter_start INTEGER NOT NULL,
          verse_start INTEGER,
          chapter_end INTEGER NOT NULL,
          verse_end INTEGER,
          granularity TEXT NOT NULL CHECK(granularity IN ('verse','range','chapter')),
          passage_label TEXT NOT NULL,
          excerpt TEXT NOT NULL,
          sort_chapter INTEGER NOT NULL,
          sort_verse INTEGER NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS coverage (
          commentator_key TEXT NOT NULL,
          book_id INTEGER NOT NULL REFERENCES books(id),
          chapter_start INTEGER NOT NULL,
          chapter_end INTEGER NOT NULL,
          notes TEXT,
          PRIMARY KEY(commentator_key, book_id, chapter_start, chapter_end)
        );
        CREATE TABLE IF NOT EXISTS build_manifest (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_entries_passage
          ON entries(book_id, chapter_start, chapter_end, verse_start, verse_end);
        CREATE INDEX IF NOT EXISTS idx_entries_commentator
          ON entries(commentator_key, book_id, chapter_start);
        CREATE INDEX IF NOT EXISTS idx_entries_granularity ON entries(granularity);
        CREATE INDEX IF NOT EXISTS idx_sources_commentator ON sources(commentator_key);
        """
    )
    seed_books(conn)
    set_manifest(conn, "schema_version", SCHEMA_VERSION)
    conn.commit()


def seed_books(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    if count:
        return
    for idx, (osis, name, aliases) in enumerate(BOOKS, start=1):
        conn.execute(
            "INSERT INTO books(id, canon_order, osis, name) VALUES (?, ?, ?, ?)",
            (idx, idx, osis, name),
        )
        alias_values = {osis.lower(), name.lower(), *(a.lower() for a in aliases)}
        for alias in alias_values:
            conn.execute(
                "INSERT OR IGNORE INTO book_aliases(alias, book_id) VALUES (?, ?)",
                (alias, idx),
            )


def get_manifest(conn: sqlite3.Connection, key: str) -> Optional[str]:
    row = conn.execute("SELECT value FROM build_manifest WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_manifest(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO build_manifest(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def book_lookup(conn: sqlite3.Connection) -> Dict[str, int]:
    rows = conn.execute(
        "SELECT b.id, b.osis, b.name, a.alias FROM books b LEFT JOIN book_aliases a ON a.book_id = b.id"
    ).fetchall()
    mapping: Dict[str, int] = {}
    for row in rows:
        if row["osis"]:
            mapping[row["osis"].lower()] = row["id"]
        if row["name"]:
            mapping[row["name"].lower()] = row["id"]
        if row["alias"]:
            mapping[row["alias"].lower()] = row["id"]
    return mapping


def upsert_source(
    conn: sqlite3.Connection,
    commentator_key: str,
    work_title: str,
    source_url: str,
    local_raw_path: str,
    parser_name: str,
    parser_version: str,
    content_hash: Optional[str],
    downloaded_at: Optional[str] = None,
) -> int:
    downloaded_at = downloaded_at or utc_now()
    conn.execute(
        """
        INSERT INTO sources(commentator_key, work_title, source_url, local_raw_path, parser_name, parser_version, content_hash, downloaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(commentator_key, work_title, local_raw_path)
        DO UPDATE SET source_url=excluded.source_url, parser_name=excluded.parser_name,
                      parser_version=excluded.parser_version, content_hash=excluded.content_hash,
                      downloaded_at=excluded.downloaded_at
        """,
        (commentator_key, work_title, source_url, local_raw_path, parser_name, parser_version, content_hash, downloaded_at),
    )
    row = conn.execute(
        "SELECT id FROM sources WHERE commentator_key=? AND work_title=? AND local_raw_path=?",
        (commentator_key, work_title, local_raw_path),
    ).fetchone()
    return int(row["id"])


def replace_entries_for_source(conn: sqlite3.Connection, source_id: int, rows: Sequence[Mapping[str, object]]) -> None:
    existing = conn.execute("SELECT commentator_key, book_id, chapter_start, chapter_end FROM entries WHERE source_id = ?", (source_id,))
    cov_keys = {(r["commentator_key"], r["book_id"], r["chapter_start"], r["chapter_end"]) for r in existing.fetchall()}
    conn.execute("DELETE FROM entries WHERE source_id = ?", (source_id,))
    for key in cov_keys:
        conn.execute(
            "DELETE FROM coverage WHERE commentator_key=? AND book_id=? AND chapter_start=? AND chapter_end=?",
            key,
        )

    now = utc_now()
    inserted_cov = set()
    for row in rows:
        conn.execute(
            """
            INSERT INTO entries(
              source_id, commentator_key, work_title, book_id, chapter_start, verse_start,
              chapter_end, verse_end, granularity, passage_label, excerpt, sort_chapter, sort_verse, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                row["commentator_key"],
                row["work_title"],
                row["book_id"],
                row["chapter_start"],
                row.get("verse_start"),
                row["chapter_end"],
                row.get("verse_end"),
                row["granularity"],
                row["passage_label"],
                row["excerpt"],
                row["sort_chapter"],
                row["sort_verse"],
                now,
            ),
        )
        cov = (
            row["commentator_key"],
            row["book_id"],
            row["chapter_start"],
            row["chapter_end"],
        )
        if cov not in inserted_cov:
            inserted_cov.add(cov)
            conn.execute(
                "INSERT OR IGNORE INTO coverage(commentator_key, book_id, chapter_start, chapter_end, notes) VALUES (?, ?, ?, ?, ?)",
                (*cov, None),
            )


def _sql_candidates(conn: sqlite3.Connection, p: Passage) -> List[sqlite3.Row]:
    params = [p.book_id, p.chapter_end, p.chapter_start]
    sql = """
      SELECT e.*, s.source_url, s.local_raw_path
      FROM entries e
      JOIN sources s ON s.id = e.source_id
      WHERE e.book_id = ?
        AND e.chapter_start <= ?
        AND e.chapter_end >= ?
    """
    return conn.execute(sql, params).fetchall()


def _verse_overlap_score(p: Passage, row: sqlite3.Row) -> float:
    gran = row["granularity"]
    if gran == "chapter":
        return 0.2
    if p.verse_start is None or p.verse_end is None:
        return 0.35 if gran == "range" else 0.25
    if row["chapter_start"] != p.chapter_start or row["chapter_end"] != p.chapter_end:
        return 0.3
    rv1 = row["verse_start"] or 1
    rv2 = row["verse_end"] or rv1
    q1, q2 = p.verse_start, p.verse_end
    overlap = max(0, min(rv2, q2) - max(rv1, q1) + 1)
    if overlap <= 0:
        return 0.0
    qlen = max(1, q2 - q1 + 1)
    rlen = max(1, rv2 - rv1 + 1)
    ratio = overlap / qlen
    exact = 1.0 if rv1 == q1 and rv2 == q2 else 0.0
    tight = overlap / rlen
    return ratio * 0.6 + tight * 0.2 + exact * 0.2


def score_row(row: sqlite3.Row, p: Passage, commentator_priority: Mapping[str, int]) -> float:
    granularity_weight = {"verse": 1.0, "range": 0.8, "chapter": 0.45}.get(row["granularity"], 0.5)
    overlap = _verse_overlap_score(p, row)
    if overlap <= 0 and not (p.verse_start is None and row["granularity"] == "chapter"):
        return 0.0
    pref_rank = commentator_priority.get((row["commentator_key"] or "").lower(), 999)
    pref_bonus = max(0.0, 0.25 - min(pref_rank, 20) * 0.03)
    excerpt_len = len((row["excerpt"] or "").strip())
    len_bonus = 0.05 if 120 <= excerpt_len <= 1200 else (0.02 if excerpt_len > 40 else 0.0)
    return granularity_weight + overlap + pref_bonus + len_bonus


def search_entries(
    conn: sqlite3.Connection,
    passage: Passage,
    commentator_priority: Mapping[str, int],
    limit: int = 8,
) -> List[Dict[str, object]]:
    rows = _sql_candidates(conn, passage)
    scored: List[Tuple[float, sqlite3.Row]] = []
    for row in rows:
        s = score_row(row, passage, commentator_priority)
        if s > 0:
            scored.append((s, row))
    scored.sort(key=lambda x: (-x[0], x[1]["sort_chapter"], x[1]["sort_verse"], x[1]["id"]))
    result: List[Dict[str, object]] = []
    seen = set()
    for score, row in scored:
        key = (row["commentator_key"], row["passage_label"], row["excerpt"][:120])
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "id": row["id"],
                "commentator": row["commentator_key"],
                "work": row["work_title"],
                "coverage": row["passage_label"],
                "granularity": row["granularity"],
                "excerpt": row["excerpt"],
                "source_url": row["source_url"],
                "local_raw_path": row["local_raw_path"],
                "score": round(float(score), 4),
            }
        )
        if len(result) >= limit:
            break
    return result

