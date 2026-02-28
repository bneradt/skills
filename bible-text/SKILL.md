---
name: bible-text
description: "Lookup Bible passages from a local jburson/bible-data dataset. Use when the user asks for Bible text by reference (e.g. Romans 8:28-30, Psalm 23). Offline/local only."
metadata: { "openclaw": { "emoji": "📖", "requires": { "bins": ["python3"] } } }
---

# Bible Text Skill

Retrieve Bible passages from a local `bible-data` checkout (no API calls).

## Usage

```bash
python3 ~/openclaw/skills/bible-text/scripts/bible_text.py "Romans 8:28-30"
python3 ~/openclaw/skills/bible-text/scripts/bible_text.py "Psalm 23" --json
```

## Configuration

- `BIBLE_TEXT_DATA_DIR` (required): path to the local `bible-data` repo or `data/` directory parent
- `BIBLE_TEXT_TRANSLATION` (optional, default `KJV`)
- `BIBLE_TEXT_STRICT` (optional, default `false`)

## When to Use

- User asks for Bible passage text
- Commentary skill needs local passage text for display

## Notes

- Targets `jburson/bible-data` JSON format (`data/VERSION/VERSION.json`)
- Strips inline rendering markers (e.g. `*pn`, `*s`) from verse text output

