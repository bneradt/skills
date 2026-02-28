#!/usr/bin/env python3
"""Normalize local commentary corpora into AI-friendly JSONL with provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from html import unescape
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from common_passages import BOOKS, match_book, parse_passage, scan_passages_in_text


COMMENTARIES_ROOT = Path("~/OneDrive/Documents/development/myopenclaw/commentaries").expanduser()
OUTPUT_ROOT_DEFAULT = COMMENTARIES_ROOT / "ai_friendly"
README_PATH_DEFAULT = (
    Path("~/Library/CloudStorage/OneDrive-Personal/Documents/development/myopenclaw/skills/bible-commentary/README.md")
    .expanduser()
)


SOURCE_DEFAULTS: Dict[str, dict] = {
    "mh": {
        "commentator": "matthew_henry",
        "work": "Matthew Henry Complete Commentary",
        "source_retrieval_method": "download_zip",
        "source_retrieval_url": "https://www.biblesnet.com/matthew_henry.zip",
        "source_canonical_url": None,
        "source_canonical_label": "Matthew Henry commentary corpus package",
        "source_archive_name": "matthew_henry.zip",
        "source_base_record_url": None,
    },
    "jfb": {
        "commentator": "jamieson_fausset_brown",
        "work": "Jamieson-Fausset-Brown Commentary",
        "source_retrieval_method": "download_zip",
        "source_retrieval_url": "https://www.biblesnet.com/jfb_commentary.zip",
        "source_canonical_url": None,
        "source_canonical_label": "Jamieson-Fausset-Brown commentary corpus package",
        "source_archive_name": "jfb_commentary.zip",
        "source_base_record_url": None,
    },
    "jg": {
        "commentator": "john_gill",
        "work": "Exposition of the Old and New Testament",
        "source_retrieval_method": "scrape",
        "source_retrieval_url": "https://www.sacred-texts.com/bib/cmt/gill/index.htm",
        "source_canonical_url": "https://www.sacred-texts.com/bib/cmt/gill/index.htm",
        "source_canonical_label": "Internet Sacred Text Archive - John Gill",
        "source_archive_name": "jg.zip",
        "source_base_record_url": "https://www.sacred-texts.com/bib/cmt/gill/",
    },
    "jc": {
        "commentator": "john_calvin",
        "work": "Calvin Commentaries Collection",
        "source_retrieval_method": "download_zip",
        "source_retrieval_url": "https://nycphantom.com/store/downloads/John_Calvin.zip",
        "source_canonical_url": None,
        "source_canonical_label": "John Calvin commentary PDF package",
        "source_archive_name": "John_Calvin.zip",
        "source_base_record_url": None,
    },
    "ac": {
        "commentator": "adam_clarke",
        "work": "Adam Clarke's Commentary and critical notes on the Bible",
        "source_retrieval_method": "download_zip",
        "source_retrieval_url": "https://en.wikisource.org/wiki/Commentary_and_critical_notes_on_the_Bible",
        "source_canonical_url": "https://en.wikisource.org/wiki/Commentary_and_critical_notes_on_the_Bible",
        "source_canonical_label": "Wikisource text referenced by SWORD Clarke module",
        "source_archive_name": "Clarke.zip",
        "source_base_record_url": None,
    },
}


JG_PREFIX_BOOK = {
    "act": "Acts",
    "amo": "Amos",
    "ch1": "1 Chronicles",
    "ch2": "2 Chronicles",
    "col": "Colossians",
    "co1": "1 Corinthians",
    "co2": "2 Corinthians",
    "dan": "Daniel",
    "deu": "Deuteronomy",
    "ecc": "Ecclesiastes",
    "eph": "Ephesians",
    "est": "Esther",
    "exo": "Exodus",
    "eze": "Ezekiel",
    "ezr": "Ezra",
    "gal": "Galatians",
    "gen": "Genesis",
    "hab": "Habakkuk",
    "hag": "Haggai",
    "heb": "Hebrews",
    "hos": "Hosea",
    "int": None,
    "isa": "Isaiah",
    "jam": "James",
    "jde": "Jude",
    "jdg": "Judges",
    "jer": "Jeremiah",
    "job": "Job",
    "joe": "Joel",
    "jo1": "1 John",
    "jo2": "2 John",
    "jo3": "3 John",
    "joh": "John",
    "jon": "Jonah",
    "jos": "Joshua",
    "kg1": "1 Kings",
    "kg2": "2 Kings",
    "lam": "Lamentations",
    "lev": "Leviticus",
    "luk": "Luke",
    "mal": "Malachi",
    "mar": "Mark",
    "mat": "Matthew",
    "mic": "Micah",
    "nah": "Nahum",
    "neh": "Nehemiah",
    "num": "Numbers",
    "oba": "Obadiah",
    "pe1": "1 Peter",
    "pe2": "2 Peter",
    "phi": "Philippians",
    "plm": "Philemon",
    "pro": "Proverbs",
    "psa": "Psalms",
    "rev": "Revelation",
    "rom": "Romans",
    "rut": "Ruth",
    "sa1": "1 Samuel",
    "sa2": "2 Samuel",
    "sol": "Song of Solomon",
    "th1": "1 Thessalonians",
    "th2": "2 Thessalonians",
    "ti1": "1 Timothy",
    "ti2": "2 Timothy",
    "tit": "Titus",
    "zac": "Zechariah",
    "zep": "Zephaniah",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"(?i)</div>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def norm_excerpt(text: str, max_len: int = 1400) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


def passage_fields(p) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[int], Optional[int], str]:
    granularity = "chapter" if p.is_chapter_only else ("verse" if p.chapter_start == p.chapter_end and p.verse_start == p.verse_end else "range")
    return p.book_name, p.chapter_start, p.verse_start, p.chapter_end, p.verse_end, granularity


def record_id(commentator: str, source_file: str, coverage: str, text: str) -> str:
    h = hashlib.sha1(f"{commentator}|{source_file}|{coverage}|{text[:200]}".encode("utf-8", "ignore")).hexdigest()
    return f"{commentator}:{h[:16]}"


def make_record(
    src_key: str,
    source_path: Path,
    text: str,
    coverage: str,
    p=None,
    confidence: float = 0.5,
    source_record_url: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    defaults = SOURCE_DEFAULTS[src_key]
    book = chapter_start = verse_start = chapter_end = verse_end = None
    granularity = "document"
    if p is not None:
        book, chapter_start, verse_start, chapter_end, verse_end, granularity = passage_fields(p)
    rec = {
        "id": record_id(defaults["commentator"], source_path.name, coverage, text),
        "commentator": defaults["commentator"],
        "work": defaults["work"],
        "source_type": source_path.suffix.lower().lstrip("."),
        "source_file": source_path.name,
        "source_local_path": str(source_path),
        "source_archive_name": defaults["source_archive_name"],
        "source_retrieval_url": defaults["source_retrieval_url"],
        "source_retrieval_method": defaults["source_retrieval_method"],
        "source_canonical_url": defaults["source_canonical_url"],
        "source_canonical_label": defaults["source_canonical_label"],
        "source_record_url": source_record_url,
        "provenance_notes": notes,
        "book": book,
        "chapter_start": chapter_start,
        "verse_start": verse_start,
        "chapter_end": chapter_end,
        "verse_end": verse_end,
        "coverage_label": coverage,
        "granularity": granularity,
        "text": norm_excerpt(text),
        "parser": "ai_friendly_normalize_v1",
        "parser_version": "1.0.0",
        "mapping_confidence": round(float(confidence), 3),
        "created_at": utc_now(),
    }
    return rec


def infer_mh_book_chapter(path: Path) -> Tuple[Optional[str], Optional[int]]:
    m = re.match(r"MHC(\d{2})(\d{3})\.HTM$", path.name, re.I)
    if not m:
        return None, None
    bno = int(m.group(1))
    ch = int(m.group(2))
    if bno < 1 or bno > len(BOOKS):
        return None, None
    _, book_name, _ = BOOKS[bno - 1]
    return book_name, (ch if ch > 0 else None)


def infer_jfb_book(path: Path) -> Optional[str]:
    m = re.match(r"JFB(\d{2})\.HTM$", path.name, re.I)
    if not m:
        return None
    idx = int(m.group(1))
    if idx <= 0 or idx > len(BOOKS):
        return None
    _, book_name, _ = BOOKS[idx - 1]
    return book_name


def infer_jg_book_chapter(path: Path) -> Tuple[Optional[str], Optional[int]]:
    name = path.stem.lower()
    m = re.match(r"([a-z]{2,3}\d?|[a-z]{3})(\d{3})$", name)
    if m:
        pref = m.group(1)
        ch = int(m.group(2))
        return JG_PREFIX_BOOK.get(pref), ch if ch > 0 else None
    m2 = re.match(r"([a-z]{2,3}\d?|[a-z]{3})$", name)
    if m2:
        return JG_PREFIX_BOOK.get(m2.group(1)), None
    return None, None


def _chunk_text(lines: List[str], start: int, max_lines: int = 8) -> str:
    out = [lines[start]]
    for j in range(start + 1, min(len(lines), start + max_lines)):
        if scan_passages_in_text(lines[j]):
            break
        out.append(lines[j])
    return " ".join(out)


def extract_records_from_html(src_key: str, source_path: Path, default_book: Optional[str], default_chapter: Optional[int]) -> List[dict]:
    raw = source_path.read_text("utf-8", errors="ignore")
    text = strip_html(raw)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    base_url = SOURCE_DEFAULTS[src_key].get("source_base_record_url")
    source_record_url = (base_url + source_path.name) if base_url else None
    records: List[dict] = []

    # Reference-based extraction
    for i, line in enumerate(lines):
        found = scan_passages_in_text(line, default_book=default_book)
        if not found and default_book and default_chapter:
            m = re.search(r"\bVerse\s+(\d{1,3})\b", line, re.I)
            if m:
                try:
                    found = [parse_passage(f"{default_book} {default_chapter}:{int(m.group(1))}")]
                except Exception:
                    found = []
        if not found:
            continue
        excerpt = _chunk_text(lines, i)
        for p in found[:3]:
            records.append(
                make_record(
                    src_key=src_key,
                    source_path=source_path,
                    text=excerpt,
                    coverage=p.normalized_label(),
                    p=p,
                    confidence=0.95 if default_book else 0.9,
                    source_record_url=source_record_url,
                )
            )

    if records:
        return records

    # Chapter fallback from filename inference
    if default_book and default_chapter:
        p = parse_passage(f"{default_book} {default_chapter}")
        excerpt = " ".join(lines[:20]) if lines else text[:1200]
        return [
            make_record(
                src_key=src_key,
                source_path=source_path,
                text=excerpt,
                coverage=p.normalized_label(),
                p=p,
                confidence=0.6,
                source_record_url=source_record_url,
                notes="No explicit verse refs detected; chapter-level inference from filename.",
            )
        ]

    # Document-level fallback
    excerpt = " ".join(lines[:20]) if lines else text[:1200]
    coverage = default_book or source_path.stem
    return [
        make_record(
            src_key=src_key,
            source_path=source_path,
            text=excerpt,
            coverage=coverage,
            p=None,
            confidence=0.2,
            source_record_url=source_record_url,
            notes="Document-level fallback: no passage mapping detected.",
        )
    ]


def extract_records_from_calvin_pdf(source_path: Path) -> List[dict]:
    def _is_toc_like(line: str) -> bool:
        # Examples: "Acts 1:1-2 . . . . . . . p. 16"
        if re.search(r"\.{3,}\s*p\.\s*\d+\s*$", line, re.I):
            return True
        if line.count(".") >= 8 and re.search(r"\bp\.\s*\d+\b", line, re.I):
            return True
        if re.search(r"\btable of contents\b", line, re.I):
            return True
        if re.search(r"\bindexes?\b|\bindex of scripture\b", line, re.I):
            return True
        return False

    def _run_pdftotext(pdf_path: Path) -> str:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            cp = subprocess.run(
                ["pdftotext", "-layout", "-nopgbrk", str(pdf_path), tmp_path],
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                err = (cp.stderr or cp.stdout or "").strip()
                raise RuntimeError(err or "pdftotext failed")
            return Path(tmp_path).read_text("utf-8", errors="ignore")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _default_books_from_filename(name: str) -> List[str]:
        base = name.lower().replace(".pdf", "")
        if "commentary on " in base:
            base = base.split("commentary on ", 1)[1]
        base = re.sub(r"\bvol\s*\d+\b", " ", base)
        base = base.replace(" and ", " ").replace(",", " ")
        tokens = [t.strip() for t in base.split() if t.strip()]
        out: List[str] = []
        i = 0
        while i < len(tokens):
            # capture up to 3-word book names, e.g., "song of solomon"
            matched = None
            for span in (3, 2, 1):
                if i + span > len(tokens):
                    continue
                phrase = " ".join(tokens[i : i + span])
                b = match_book(phrase)
                if b:
                    matched = b[2]
                    i += span
                    break
            if matched:
                out.append(matched)
            else:
                i += 1
        dedup: List[str] = []
        seen = set()
        for b in out:
            if b not in seen:
                seen.add(b)
                dedup.append(b)
        return dedup

    try:
        txt = _run_pdftotext(source_path)
    except Exception as exc:
        return [
            make_record(
                src_key="jc",
                source_path=source_path,
                text=f"Calvin PDF source file: {source_path.name}",
                coverage=source_path.stem,
                p=None,
                confidence=0.05,
                source_record_url=None,
                notes=f"PDF text extraction failed: {exc}",
            )
        ]

    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    if not lines:
        return [
            make_record(
                src_key="jc",
                source_path=source_path,
                text=f"Calvin PDF source file: {source_path.name}",
                coverage=source_path.stem,
                p=None,
                confidence=0.05,
                source_record_url=None,
                notes="PDF text extracted but produced no usable lines.",
            )
        ]

    default_books = _default_books_from_filename(source_path.name)
    default_book = default_books[0] if len(default_books) == 1 else None

    records: List[dict] = []
    for i, line in enumerate(lines):
        if _is_toc_like(line):
            continue
        found = scan_passages_in_text(line, default_book=default_book)
        if not found:
            continue
        chunk = [line]
        for j in range(i + 1, min(i + 18, len(lines))):
            if scan_passages_in_text(lines[j], default_book=default_book) and not _is_toc_like(lines[j]):
                break
            if _is_toc_like(lines[j]):
                continue
            chunk.append(lines[j])
        excerpt = " ".join(chunk)
        if len(re.sub(r"[^A-Za-z]+", "", excerpt)) < 80:
            # Skip likely heading/index fragments with no meaningful commentary text.
            continue
        for p in found[:3]:
            records.append(
                make_record(
                    src_key="jc",
                    source_path=source_path,
                    text=excerpt,
                    coverage=p.normalized_label(),
                    p=p,
                    confidence=0.82 if default_book else 0.75,
                    source_record_url=None,
                    notes="Extracted via pdftotext -layout.",
                )
            )

    if records:
        return records

    # Fallback: chunk text into coarse segments with document-level coverage.
    chunk_size = 80
    for start in range(0, min(len(lines), 800), chunk_size):
        snippet = " ".join(lines[start : start + chunk_size])
        if not snippet.strip():
            continue
        records.append(
            make_record(
                src_key="jc",
                source_path=source_path,
                text=snippet,
                coverage=source_path.stem,
                p=None,
                confidence=0.25,
                source_record_url=None,
                notes="No explicit passage refs detected; document chunk fallback.",
            )
        )
    return records or [
        make_record(
            src_key="jc",
            source_path=source_path,
            text=f"Calvin PDF source file: {source_path.name}",
            coverage=source_path.stem,
            p=None,
            confidence=0.05,
            source_record_url=None,
            notes="No extractable content found.",
        )
    ]


def extract_records_from_ac_sword(ac_root: Path) -> List[dict]:
    diatheke = os.environ.get("DIATHEKE_BIN", "diatheke")
    sword_path = str(ac_root)

    def _clean_osis_text(s: str) -> str:
        # Strip simple XML/OSIS tags from diatheke output.
        s = re.sub(r"(?is)<[^>]+>", " ", s)
        s = unescape(s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # canonical book names from common_passages.BOOKS
    canonical_books = [name for _, name, _ in BOOKS]
    records: List[dict] = []
    for book_name in canonical_books:
        cp = subprocess.run(
            [diatheke, "-b", "Clarke", "-k", book_name],
            env={**os.environ, "SWORD_PATH": sword_path},
            capture_output=True,
            text=True,
        )
        if cp.returncode != 0:
            continue
        raw = cp.stdout or ""
        for line in raw.splitlines():
            line = line.strip()
            if not line or line == "(Clarke)":
                continue
            m = re.match(r"^([1-3]?\s*[A-Za-z][A-Za-z ]+?)\s+(\d+):(\d+):\s*(.*)$", line)
            if not m:
                continue
            ref_book = m.group(1).strip()
            ch = int(m.group(2))
            vs = int(m.group(3))
            body = _clean_osis_text(m.group(4))
            if not body:
                continue
            try:
                p = parse_passage(f"{ref_book} {ch}:{vs}")
            except Exception:
                continue
            source_path = ac_root / "mods.d" / "clarke.conf"
            records.append(
                make_record(
                    src_key="ac",
                    source_path=source_path,
                    text=body,
                    coverage=p.normalized_label(),
                    p=p,
                    confidence=0.95,
                    source_record_url=None,
                    notes="Extracted from local SWORD module via diatheke.",
                )
            )
    return records


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_schema(path: Path) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CommentaryRecord",
        "type": "object",
        "required": [
            "id",
            "commentator",
            "work",
            "source_file",
            "source_local_path",
            "source_retrieval_url",
            "source_retrieval_method",
            "source_canonical_url",
            "source_canonical_label",
            "source_record_url",
            "book",
            "chapter_start",
            "verse_start",
            "chapter_end",
            "verse_end",
            "coverage_label",
            "granularity",
            "text",
            "mapping_confidence",
            "created_at",
        ],
        "properties": {
            "id": {"type": "string"},
            "commentator": {"type": "string"},
            "work": {"type": "string"},
            "source_type": {"type": "string"},
            "source_file": {"type": "string"},
            "source_local_path": {"type": "string"},
            "source_archive_name": {"type": ["string", "null"]},
            "source_retrieval_url": {"type": "string"},
            "source_retrieval_method": {"type": "string"},
            "source_canonical_url": {"type": ["string", "null"]},
            "source_canonical_label": {"type": ["string", "null"]},
            "source_record_url": {"type": ["string", "null"]},
            "provenance_notes": {"type": ["string", "null"]},
            "book": {"type": ["string", "null"]},
            "chapter_start": {"type": ["integer", "null"]},
            "verse_start": {"type": ["integer", "null"]},
            "chapter_end": {"type": ["integer", "null"]},
            "verse_end": {"type": ["integer", "null"]},
            "coverage_label": {"type": "string"},
            "granularity": {"type": "string"},
            "text": {"type": "string"},
            "parser": {"type": "string"},
            "parser_version": {"type": "string"},
            "mapping_confidence": {"type": "number"},
            "created_at": {"type": "string"},
        },
        "additionalProperties": True,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


def write_manifest(path: Path, key: str, source_dir: Path, record_count: int) -> None:
    payload = {
        "dataset": key,
        "generated_at": utc_now(),
        "record_count": record_count,
        "source_dir": str(source_dir),
        "source": SOURCE_DEFAULTS[key],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def read_readme_sources(readme: Path) -> Dict[str, str]:
    if not readme.exists():
        return {}
    txt = readme.read_text("utf-8", errors="ignore")
    out = {}
    patterns = {
        "mh": r"Matthew Henry:\s*(https?://\S+)",
        "jfb": r"Jamieson, Fausset, Brown:\s*(https?://\S+)",
        "jg": r"John Gill:\s*Scraped from\s*(https?://\S+)",
        "jc": r"John Calvin:\s*(https?://\S+)",
        "ac": r"Adam Clarke:\s*(https?://\S+)",
    }
    for k, pat in patterns.items():
        m = re.search(pat, txt, re.I)
        if m:
            out[k] = m.group(1).rstrip(".")
    return out


def apply_readme_overrides(readme_sources: Dict[str, str]) -> None:
    for key, url in readme_sources.items():
        if key in SOURCE_DEFAULTS and url:
            SOURCE_DEFAULTS[key]["source_retrieval_url"] = url


def export_all(output_root: Path, readme: Path, only: Optional[Sequence[str]] = None) -> Dict[str, int]:
    apply_readme_overrides(read_readme_sources(readme))
    selected = set(only or ("mh", "jg", "jfb", "jc", "ac"))

    ensure_dir(output_root)
    ensure_dir(output_root / "schemas")
    ensure_dir(output_root / "manifests")
    for d in selected:
        ensure_dir(output_root / d)

    counts: Dict[str, int] = {}

    # Matthew Henry
    if "mh" in selected:
        mh_dir = COMMENTARIES_ROOT / "mh"
        mh_records: List[dict] = []
        for p in sorted(mh_dir.glob("*.HTM")):
            book, ch = infer_mh_book_chapter(p)
            mh_records.extend(extract_records_from_html("mh", p, book, ch))
        counts["mh"] = write_jsonl(output_root / "mh" / "records.jsonl", mh_records)
        write_manifest(output_root / "manifests" / "mh.json", "mh", mh_dir, counts["mh"])

    # John Gill
    if "jg" in selected:
        jg_dir = COMMENTARIES_ROOT / "jg"
        jg_records: List[dict] = []
        for p in sorted(jg_dir.glob("*.html")):
            book, ch = infer_jg_book_chapter(p)
            jg_records.extend(extract_records_from_html("jg", p, book, ch))
        counts["jg"] = write_jsonl(output_root / "jg" / "records.jsonl", jg_records)
        write_manifest(output_root / "manifests" / "jg.json", "jg", jg_dir, counts["jg"])

    # JFB
    if "jfb" in selected:
        jfb_dir = COMMENTARIES_ROOT / "jfb"
        jfb_records: List[dict] = []
        for p in sorted(jfb_dir.glob("*.htm")) + sorted(jfb_dir.glob("*.HTM")):
            book = infer_jfb_book(p)
            jfb_records.extend(extract_records_from_html("jfb", p, book, None))
        counts["jfb"] = write_jsonl(output_root / "jfb" / "records.jsonl", jfb_records)
        write_manifest(output_root / "manifests" / "jfb.json", "jfb", jfb_dir, counts["jfb"])

    # John Calvin
    if "jc" in selected:
        jc_dir = COMMENTARIES_ROOT / "jc" / "jc_commentaries"
        jc_records: List[dict] = []
        for p in sorted(jc_dir.glob("*.pdf")) + sorted(jc_dir.glob("*.PDF")):
            jc_records.extend(extract_records_from_calvin_pdf(p))
        counts["jc"] = write_jsonl(output_root / "jc" / "records.jsonl", jc_records)
        write_manifest(output_root / "manifests" / "jc.json", "jc", jc_dir, counts["jc"])

    # Adam Clarke (SWORD module)
    if "ac" in selected:
        ac_dir = COMMENTARIES_ROOT / "ac"
        ac_records = extract_records_from_ac_sword(ac_dir)
        counts["ac"] = write_jsonl(output_root / "ac" / "records.jsonl", ac_records)
        write_manifest(output_root / "manifests" / "ac.json", "ac", ac_dir, counts["ac"])

    write_schema(output_root / "schemas" / "commentary_record.schema.json")
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize commentary corpora into AI-friendly JSONL")
    ap.add_argument("--output-root", default=str(OUTPUT_ROOT_DEFAULT), help="Output root (default: ~/.../commentaries/ai_friendly)")
    ap.add_argument("--readme-path", default=str(README_PATH_DEFAULT), help="README containing retrieval source URLs")
    ap.add_argument(
        "--only",
        default="mh,jg,jfb,jc,ac",
        help="Comma-separated corpora to build: mh,jg,jfb,jc,ac (default all)",
    )
    args = ap.parse_args()

    output_root = Path(os.path.expanduser(args.output_root)).resolve()
    readme = Path(os.path.expanduser(args.readme_path)).resolve()
    only = [x.strip() for x in args.only.split(",") if x.strip()]
    valid = {"mh", "jg", "jfb", "jc", "ac"}
    bad = [x for x in only if x not in valid]
    if bad:
        raise SystemExit(f"Invalid --only values: {', '.join(bad)}")
    counts = export_all(output_root, readme, only=only)
    print(json.dumps({"output_root": str(output_root), "counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
