---
name: weather
description: "Get current weather and historical weather data via Open-Meteo. Use when: user asks about weather, temperature, forecasts, or past weather for any location. No API key needed."
homepage: https://open-meteo.com/
metadata: { "openclaw": { "emoji": "🌤️", "requires": { "bins": ["python3"] } } }
---

# Weather Skill

Get current or historical weather via the Open-Meteo API. Python 3, stdlib only — no pip dependencies.

## Usage

```bash
# Current weather for a location
python3 ~/openclaw/skills/weather/weather.py "Cape Coral, FL"

# Uses USER_LOCATION from .env if no location given
python3 ~/openclaw/skills/weather/weather.py

# Historical weather
python3 ~/openclaw/skills/weather/weather.py "Savoy, IL" --date yesterday
python3 ~/openclaw/skills/weather/weather.py "Savoy, IL" --date 2026-01-15
```

## Configuration

Copy `.env.example` to `.env` and set the openclaw's default location:

```
USER_LOCATION=Savoy, IL
```

## When to Use

- "What's the weather?"
- "Will it rain today/tomorrow?"
- "Temperature in [city]"
- "What was the weather yesterday?"

## When NOT to Use

- Severe weather alerts — check official NWS alert feeds
- Aviation/marine weather — use METAR/TAF
- Climate trend analysis — use specialized datasets
