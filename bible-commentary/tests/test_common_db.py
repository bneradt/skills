import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common_db import connect, init_schema, replace_entries_for_source, search_entries, upsert_source
from common_passages import parse_passage


class DbQueryTests(unittest.TestCase):
    def test_search_prefers_verse_over_chapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "c.sqlite")
            conn = connect(db)
            init_schema(conn)
            sid = upsert_source(conn, "henry", "Henry", "https://example.com", "/tmp/raw", "test", "1", None)
            replace_entries_for_source(
                conn,
                sid,
                [
                    {
                        "commentator_key": "henry",
                        "work_title": "Henry",
                        "book_id": 45,  # Romans
                        "chapter_start": 8,
                        "verse_start": None,
                        "chapter_end": 8,
                        "verse_end": None,
                        "granularity": "chapter",
                        "passage_label": "Romans 8",
                        "excerpt": "Chapter summary",
                        "sort_chapter": 8,
                        "sort_verse": 0,
                    },
                    {
                        "commentator_key": "henry",
                        "work_title": "Henry",
                        "book_id": 45,
                        "chapter_start": 8,
                        "verse_start": 28,
                        "chapter_end": 8,
                        "verse_end": 28,
                        "granularity": "verse",
                        "passage_label": "Romans 8:28",
                        "excerpt": "Verse summary",
                        "sort_chapter": 8,
                        "sort_verse": 28,
                    },
                ],
            )
            conn.commit()
            res = search_entries(conn, parse_passage("Romans 8:28"), {"henry": 0}, limit=5)
            self.assertGreaterEqual(len(res), 2)
            self.assertEqual(res[0]["granularity"], "verse")


if __name__ == "__main__":
    unittest.main()

