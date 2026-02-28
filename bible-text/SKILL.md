---
name: bible-text
description: "Lookup Bible passages from a local jburson/bible-data dataset. Use when the user asks for Bible text by reference (e.g. Romans 8:28-30, Psalm 23). Offline/local only."
metadata: { "openclaw": { "emoji": "📖", "requires": { "bins": ["python3"] } } }
---

# Bible Text Skill

Retrieve Bible passages from a local `bible-data` checkout (no API calls).

## Usage

```bash
python3 ~/.openclaw/workspace/skills/bible-text/scripts/bible_text.py "Romans 8:28-30"
python3 ~/.openclaw/workspace/skills/bible-text/scripts/bible_text.py "Psalm 23" --json
python3 ~/.openclaw/workspace/skills/bible-text/scripts/bible_text.py --setup
```

## Configuration

- `BIBLE_TEXT_DATA_DIR` (optional): path to the local `bible-data` repo or `data/` directory parent
- `BIBLE_TEXT_TRANSLATION` (optional, default `KJV`)
- `BIBLE_TEXT_STRICT` (optional, default `false`)

If `BIBLE_TEXT_DATA_DIR` is not set, the script auto-discovers common paths including:

- `~/.openclaw/workspace/data/bible-data`
- `~/openclaw/workspace/data/bible-data`
- `~/workspace/data/bible-data`
- `~/bible-data`

## First-Time Startup

- Running with `--setup` launches an interactive setup flow.
- It asks for:
  - Bible data directory
  - preferred translation
  - strict parsing preference
- It writes these values to `~/.openclaw/openclaw.json` under `env.vars`:
  - `BIBLE_TEXT_DATA_DIR`
  - `BIBLE_TEXT_TRANSLATION`
  - `BIBLE_TEXT_STRICT`
- After writing config, the script prints a gateway restart suggestion.

### One-time setup (if dataset is missing)

```bash
mkdir -p ~/.openclaw/workspace/data
git clone https://github.com/jburson/bible-data.git ~/.openclaw/workspace/data/bible-data
```

## When to Use

- User asks for Bible passage text
- Commentary skill needs local passage text for display

## Notes

- Targets `jburson/bible-data` JSON format (`data/VERSION/VERSION.json`)
- Strips inline rendering markers (e.g. `*pn`, `*s`) from verse text output
