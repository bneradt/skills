# Parsing Rules (MVP)

The current parsers are intentionally conservative and heuristic:

- HTML is stripped to plain text
- Lines are scanned for explicit verse references (`Rom 8:28`, `John 3:16-18`)
- Nearby lines are grouped into excerpts
- If no explicit references are found, parsers may fall back to chapter-level entries when the manifest provides defaults

## Parser names in manifest

- `generic_refscan`: line-based reference scanner
- `psalm_chapter_fallback`: chapter-level fallback for Psalm-focused pages/files

## Improving coverage

- Add more source entries in `sources-manifest.yaml`
- Add per-source `default_book`/`default_chapter`
- Extend `build_index.py` with source-specific adapters when a source layout is consistent

