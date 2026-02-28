import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common_passages import parse_passage


class PassageTests(unittest.TestCase):
    def test_single_verse(self):
        p = parse_passage("Romans 8:28")
        self.assertEqual(p.book_name, "Romans")
        self.assertEqual((p.chapter_start, p.verse_start, p.chapter_end, p.verse_end), (8, 28, 8, 28))

    def test_range_same_chapter(self):
        p = parse_passage("Romans 8:28-30")
        self.assertEqual((p.chapter_start, p.verse_start, p.chapter_end, p.verse_end), (8, 28, 8, 30))

    def test_chapter_only(self):
        p = parse_passage("Psalm 23")
        self.assertTrue(p.is_chapter_only)
        self.assertEqual(p.normalized_label(), "Psalms 23")


if __name__ == "__main__":
    unittest.main()

