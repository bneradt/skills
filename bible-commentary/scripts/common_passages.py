#!/usr/bin/env python3
"""Shared Bible passage parsing utilities for commentary scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


BOOKS = [
    ("Gen", "Genesis", ["gen", "ge", "gn", "genesis"]),
    ("Exod", "Exodus", ["exod", "ex", "exo", "exodus"]),
    ("Lev", "Leviticus", ["lev", "le", "lv", "leviticus"]),
    ("Num", "Numbers", ["num", "nu", "nm", "numbers"]),
    ("Deut", "Deuteronomy", ["deut", "dt", "deuteronomy"]),
    ("Josh", "Joshua", ["josh", "jos", "joshua"]),
    ("Judg", "Judges", ["judg", "jg", "jdg", "judges"]),
    ("Ruth", "Ruth", ["ruth", "ru"]),
    ("1Sam", "1 Samuel", ["1 samuel", "1 sam", "1sa", "i samuel", "first samuel"]),
    ("2Sam", "2 Samuel", ["2 samuel", "2 sam", "2sa", "ii samuel", "second samuel"]),
    ("1Kgs", "1 Kings", ["1 kings", "1 kgs", "1ki", "i kings", "first kings"]),
    ("2Kgs", "2 Kings", ["2 kings", "2 kgs", "2ki", "ii kings", "second kings"]),
    ("1Chr", "1 Chronicles", ["1 chronicles", "1 chr", "1ch", "i chronicles", "first chronicles"]),
    ("2Chr", "2 Chronicles", ["2 chronicles", "2 chr", "2ch", "ii chronicles", "second chronicles"]),
    ("Ezra", "Ezra", ["ezra", "ezr"]),
    ("Neh", "Nehemiah", ["neh", "nehemiah"]),
    ("Esth", "Esther", ["esth", "est", "esther"]),
    ("Job", "Job", ["job"]),
    ("Ps", "Psalms", ["ps", "psalm", "psalms", "psa"]),
    ("Prov", "Proverbs", ["prov", "pr", "proverbs"]),
    ("Eccl", "Ecclesiastes", ["eccl", "ecc", "ecclesiastes"]),
    ("Song", "Song of Solomon", ["song", "song of solomon", "songs", "canticles"]),
    ("Isa", "Isaiah", ["isa", "isaiah"]),
    ("Jer", "Jeremiah", ["jer", "jeremiah"]),
    ("Lam", "Lamentations", ["lam", "lamentations"]),
    ("Ezek", "Ezekiel", ["ezek", "eze", "ezekiel"]),
    ("Dan", "Daniel", ["dan", "daniel"]),
    ("Hos", "Hosea", ["hos", "hosea"]),
    ("Joel", "Joel", ["joel", "jl"]),
    ("Amos", "Amos", ["amos", "am"]),
    ("Obad", "Obadiah", ["obad", "ob", "obadiah"]),
    ("Jonah", "Jonah", ["jonah", "jon"]),
    ("Mic", "Micah", ["mic", "micah"]),
    ("Nah", "Nahum", ["nah", "nahum"]),
    ("Hab", "Habakkuk", ["hab", "habakkuk"]),
    ("Zeph", "Zephaniah", ["zeph", "zep", "zephaniah"]),
    ("Hag", "Haggai", ["hag", "haggai"]),
    ("Zech", "Zechariah", ["zech", "zec", "zechariah"]),
    ("Mal", "Malachi", ["mal", "malachi"]),
    ("Matt", "Matthew", ["matt", "mt", "matthew"]),
    ("Mark", "Mark", ["mark", "mk", "mrk"]),
    ("Luke", "Luke", ["luke", "lk", "luk"]),
    ("John", "John", ["john", "jn", "jhn"]),
    ("Acts", "Acts", ["acts", "act"]),
    ("Rom", "Romans", ["rom", "ro", "romans"]),
    ("1Cor", "1 Corinthians", ["1 corinthians", "1 cor", "1co", "i corinthians", "first corinthians"]),
    ("2Cor", "2 Corinthians", ["2 corinthians", "2 cor", "2co", "ii corinthians", "second corinthians"]),
    ("Gal", "Galatians", ["gal", "ga", "galatians"]),
    ("Eph", "Ephesians", ["eph", "ephesians"]),
    ("Phil", "Philippians", ["phil", "php", "philippians"]),
    ("Col", "Colossians", ["col", "colossians"]),
    ("1Thess", "1 Thessalonians", ["1 thessalonians", "1 thess", "1th", "i thessalonians", "first thessalonians"]),
    ("2Thess", "2 Thessalonians", ["2 thessalonians", "2 thess", "2th", "ii thessalonians", "second thessalonians"]),
    ("1Tim", "1 Timothy", ["1 timothy", "1 tim", "1ti", "i timothy", "first timothy"]),
    ("2Tim", "2 Timothy", ["2 timothy", "2 tim", "2ti", "ii timothy", "second timothy"]),
    ("Titus", "Titus", ["titus", "tit"]),
    ("Phlm", "Philemon", ["philemon", "phm", "phlm"]),
    ("Heb", "Hebrews", ["heb", "hebrews"]),
    ("Jas", "James", ["james", "jas", "jm"]),
    ("1Pet", "1 Peter", ["1 peter", "1 pet", "1pe", "i peter", "first peter"]),
    ("2Pet", "2 Peter", ["2 peter", "2 pet", "2pe", "ii peter", "second peter"]),
    ("1John", "1 John", ["1 john", "1 jn", "1jo", "i john", "first john"]),
    ("2John", "2 John", ["2 john", "2 jn", "2jo", "ii john", "second john"]),
    ("3John", "3 John", ["3 john", "3 jn", "3jo", "iii john", "third john"]),
    ("Jude", "Jude", ["jude", "jud"]),
    ("Rev", "Revelation", ["rev", "re", "revelation", "apocalypse"]),
]

BOOK_BY_ALIAS: Dict[str, Tuple[int, str, str]] = {}
for idx, (osis, name, aliases) in enumerate(BOOKS, start=1):
    BOOK_BY_ALIAS[name.lower()] = (idx, osis, name)
    BOOK_BY_ALIAS[osis.lower()] = (idx, osis, name)
    for alias in aliases:
        BOOK_BY_ALIAS[alias.lower()] = (idx, osis, name)


def _normalize_book_phrase(s: str) -> str:
    s = s.strip().lower().replace(".", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.replace("iii ", "3 ").replace("ii ", "2 ").replace("i ", "1 ")
    return s


def match_book(book_str: str) -> Optional[Tuple[int, str, str]]:
    return BOOK_BY_ALIAS.get(_normalize_book_phrase(book_str))


@dataclass(frozen=True)
class Passage:
    book_id: int
    osis: str
    book_name: str
    chapter_start: int
    verse_start: Optional[int]
    chapter_end: int
    verse_end: Optional[int]

    @property
    def is_chapter_only(self) -> bool:
        return self.verse_start is None and self.verse_end is None

    def normalized_label(self) -> str:
        if self.is_chapter_only:
            if self.chapter_start == self.chapter_end:
                return f"{self.book_name} {self.chapter_start}"
            return f"{self.book_name} {self.chapter_start}-{self.chapter_end}"
        if self.chapter_start == self.chapter_end:
            if self.verse_start == self.verse_end:
                return f"{self.book_name} {self.chapter_start}:{self.verse_start}"
            return f"{self.book_name} {self.chapter_start}:{self.verse_start}-{self.verse_end}"
        return (
            f"{self.book_name} {self.chapter_start}:{self.verse_start}-"
            f"{self.chapter_end}:{self.verse_end}"
        )


PASSAGE_RE = re.compile(
    r"^\s*(?P<book>[1-3]?\s*[A-Za-z][A-Za-z .]+?)\s+"
    r"(?P<c1>\d+)"
    r"(?:\:(?P<v1>\d+))?"
    r"(?:\s*-\s*(?:(?P<c2>\d+)\:)?(?P<v2>\d+)? )?\s*$",
    re.X,
)


def parse_passage(text: str, strict: bool = False) -> Passage:
    raw = text.strip()
    m = PASSAGE_RE.match(raw)
    if not m:
        # try chapter range without verses, e.g. "Romans 8-9"
        m2 = re.match(r"^\s*(?P<book>[1-3]?\s*[A-Za-z][A-Za-z .]+?)\s+(?P<c1>\d+)\s*-\s*(?P<c2>\d+)\s*$", raw)
        if not m2:
            raise ValueError(f"Could not parse passage reference: {text!r}")
        b = match_book(m2.group("book"))
        if not b:
            raise ValueError(f"Unknown Bible book: {m2.group('book')!r}")
        book_id, osis, book_name = b
        c1 = int(m2.group("c1"))
        c2 = int(m2.group("c2"))
        if c2 < c1:
            raise ValueError("Ending chapter is before starting chapter")
        return Passage(book_id, osis, book_name, c1, None, c2, None)

    b = match_book(m.group("book"))
    if not b:
        raise ValueError(f"Unknown Bible book: {m.group('book')!r}")
    book_id, osis, book_name = b
    c1 = int(m.group("c1"))
    v1 = int(m.group("v1")) if m.group("v1") else None
    c2 = int(m.group("c2")) if m.group("c2") else c1
    if m.group("v2"):
        v2 = int(m.group("v2"))
    elif m.group(0).find("-") != -1 and v1 is not None and m.group("c2") is None:
        # "Rom 8:28-30"
        v2 = int(re.search(r"-\s*(\d+)\s*$", raw).group(1))
    else:
        v2 = v1

    if v1 is None and m.group(0).find("-") != -1 and m.group("v2"):
        # malformed like "John 3-16"
        if strict:
            raise ValueError("Ambiguous chapter/verse range; use John 3:16 or John 3-4")

    if v1 is None and v2 is not None:
        # normalize chapter-only range case
        if m.group("c2"):
            return Passage(book_id, osis, book_name, c1, None, c2, None)
        return Passage(book_id, osis, book_name, c1, None, c1, None)

    if v1 is not None and v2 is None:
        v2 = v1
    if c2 < c1:
        raise ValueError("Ending chapter is before starting chapter")
    if c1 == c2 and v1 is not None and v2 is not None and v2 < v1:
        raise ValueError("Ending verse is before starting verse")

    return Passage(book_id, osis, book_name, c1, v1, c2, v2)


def parse_osis_ref(ref: str) -> Passage:
    # Expected: "kjv:Genesis:1:1"
    parts = ref.split(":")
    if len(parts) < 4:
        raise ValueError(f"Unsupported verse ref format: {ref}")
    _, book_raw, chap_raw, verse_raw = parts[:4]
    b = match_book(book_raw)
    if not b:
        raise ValueError(f"Unknown book in OSIS ref: {book_raw}")
    book_id, osis, book_name = b
    ch = int(chap_raw)
    vs = int(verse_raw)
    return Passage(book_id, osis, book_name, ch, vs, ch, vs)


def overlaps(a: Passage, b: Passage) -> bool:
    if a.book_id != b.book_id:
        return False
    if a.chapter_end < b.chapter_start or b.chapter_end < a.chapter_start:
        return False
    if a.is_chapter_only or b.is_chapter_only:
        return True
    if a.chapter_start == a.chapter_end == b.chapter_start == b.chapter_end:
        return not (a.verse_end < b.verse_start or b.verse_end < a.verse_start)
    return True


def split_by_chapter(p: Passage) -> List[Passage]:
    if p.chapter_start == p.chapter_end:
        return [p]
    out: List[Passage] = []
    for ch in range(p.chapter_start, p.chapter_end + 1):
        if p.is_chapter_only:
            out.append(Passage(p.book_id, p.osis, p.book_name, ch, None, ch, None))
            continue
        start_v = p.verse_start if ch == p.chapter_start else 1
        end_v = p.verse_end if ch == p.chapter_end else 999
        out.append(Passage(p.book_id, p.osis, p.book_name, ch, start_v, ch, end_v))
    return out


VERSE_REF_SCAN_RE = re.compile(
    r"\b(?:(?P<book>[1-3]?\s*[A-Za-z][A-Za-z .]+?)\s+)?(?P<ch>\d{1,3})\:(?P<v1>\d{1,3})(?:-(?:(?P<ch2>\d{1,3})\:)?(?P<v2>\d{1,3}))?\b"
)


def scan_passages_in_text(text: str, default_book: Optional[str] = None) -> List[Passage]:
    passages: List[Passage] = []
    for m in VERSE_REF_SCAN_RE.finditer(text):
        book_part = m.group("book") or default_book
        if not book_part:
            continue
        b = match_book(book_part)
        if not b:
            continue
        book_id, osis, book_name = b
        c1 = int(m.group("ch"))
        v1 = int(m.group("v1"))
        c2 = int(m.group("ch2")) if m.group("ch2") else c1
        v2 = int(m.group("v2")) if m.group("v2") else v1
        try:
            passages.append(Passage(book_id, osis, book_name, c1, v1, c2, v2))
        except ValueError:
            continue
    return passages

