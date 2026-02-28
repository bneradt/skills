---
name: bible-commentary
description: "Provide Bible commentary excerpts and synthesis for a passage using a local SQLite index of public-domain commentaries (Henry, Calvin, Gill, JFB, Spurgeon Treasury of David). Auto-downloads/builds local corpus on first use and emits progress updates."
metadata: { "openclaw": { "emoji": "📚", "requires": { "bins": ["python3"] } } }
---

# Bible Commentary Skill

Retrieve public-domain commentary excerpts from a local SQLite index and synthesize them for a requested passage.

## Usage

```bash
python3 ~/openclaw/skills/bible-commentary/scripts/query_commentary.py "Romans 8:28-30" --progress
python3 ~/openclaw/skills/bible-commentary/scripts/query_commentary.py "Psalm 23" --json --progress
python3 ~/openclaw/skills/bible-commentary/scripts/bootstrap_commentary.py --progress
python3 ~/openclaw/skills/bible-commentary/scripts/build_index.py --refresh --progress
```

## First-Time Setup Behavior (Important)

If the local corpus or SQLite index is missing, `query_commentary.py` will auto-bootstrap:

1. Download public-domain source pages/files locally
2. Parse them into normalized commentary entries
3. Build/update a local SQLite index
4. Continue answering the user in the same request

This can take several minutes.

### OpenClaw response behavior

When first-time setup starts, explicitly tell the user:

- setup is being performed locally
- it may take a while
- progress updates will be posted

Relay progress lines from the script while it runs. Do not wait silently.

## Configuration

- `BIBLE_COMMENTARY_DATA_DIR` (default `~/.openclaw/data/bible-commentary`)
- `BIBLE_COMMENTARY_INDEX_PATH` (optional override)
- `BIBLE_COMMENTARY_AUTO_BOOTSTRAP` (default `true`)
- `BIBLE_COMMENTARY_PREFERRED_COMMENTATORS` (default `henry,calvin,gill,jfb,spurgeon`)
- `BIBLE_COMMENTARY_MAX_EXCERPTS` (default `8`)

Also configure `BIBLE_TEXT_DATA_DIR` for passage text enrichment via the `bible-text` skill/script.

## Commentary Sources (MVP)

- Matthew Henry
- John Calvin
- John Gill
- Jamieson, Fausset, Brown
- Charles Spurgeon (`Treasury of David`, primarily Psalms)

## Notes

- Runtime queries are local/offline after bootstrap.
- Bootstrap/build is manifest-driven. Expand the manifest for broader corpus coverage.
- Parsers are heuristic and may need tuning if source HTML/layout changes.

