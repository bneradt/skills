---
name: astronomy
description: "Moon phase, illumination, and astronomical info. Use when: user asks about the moon, moon phase, or lunar information."
metadata: { "openclaw": { "emoji": "🌙", "requires": { "bins": ["python3"] } } }
---

# Astronomy Skill

Moon phase, illumination percentage, and sunrise/sunset times. Python 3, stdlib only — no pip dependencies.

## Usage

```bash
# Moon phase for today, no location needed
python3 ~/openclaw/skills/astronomy/astronomy.py

# Specific date
python3 ~/openclaw/skills/astronomy/astronomy.py --date 2026-02-21
python3 ~/openclaw/skills/astronomy/astronomy.py --date yesterday

# With location — adds sunrise/sunset times
python3 ~/openclaw/skills/astronomy/astronomy.py "Cape Coral, FL"
python3 ~/openclaw/skills/astronomy/astronomy.py "Savoy, IL" --date yesterday
```

## Configuration

If a location is provided (as an argument or via the `USER_LOCATION` environment variable), sunrise and sunset times are included. Moon phase and illumination work without a location. `USER_LOCATION` is set in `~/.openclaw/openclaw.json` under `env.vars` — see the `set-user-location` skill.

## When to Use

- "What phase is the moon?"
- "How full is the moon tonight?"
- "When is the next full moon?"
- "Moon phase on [date]"
- "What time is sunrise/sunset?"

## When NOT to Use

- Weather forecasts — use the weather skill
- Star charts or detailed planet positions — use a planetarium app
- Eclipse predictions — use NASA eclipse data
