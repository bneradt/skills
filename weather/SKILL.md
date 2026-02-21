---
name: weather
description: "Get current weather conditions and forecasts via Open-Meteo (primary) with National Weather Service (weather.gov) as a fallback. Use when: user asks about weather, temperature, or forecasts for any location. NOT for: historical weather data, severe weather alerts, or detailed meteorological analysis. No API key needed."
homepage: https://open-meteo.com/
metadata: { "openclaw": { "emoji": "🌤️", "requires": { "bins": ["curl"] } } }
---

# Weather Skill

Get current weather conditions and forecasts.

## Approach

**Primary:** **Open-Meteo** (fast, no key, generally reliable)
- Geocoding: `https://geocoding-api.open-meteo.com/v1/search`
- Forecast: `https://api.open-meteo.com/v1/forecast`

**Fallback:** **US National Weather Service** (weather.gov)
- Points → forecast: `https://api.weather.gov/points/{lat},{lon}` → `forecast` URL
- Note: requires a **User-Agent** header; US-focused.

## When to Use

✅ **USE this skill when:**
- "What's the weather?"
- "Will it rain today/tomorrow?"
- "Temperature in [city]"
- Travel planning weather checks

## When NOT to Use

❌ **DON'T use this skill when:**
- Historical weather data → use weather archives/APIs
- Climate analysis/trends → use specialized datasets
- Severe weather alerts → check official NWS alert feeds directly
- Aviation/marine weather → use METAR/TAF or marine products

## Location

Always include a city/region or provide **lat/lon**.

## Commands

### Quick command (recommended)

This skill ships with a helper script:

```bash
# From this repo/host
~/openclaw/skills/weather/weather.sh "Savoy, IL"
~/openclaw/skills/weather/weather.sh "Cape Coral, FL"

# Or set a default location
export WEATHER_DEFAULT_LOCATION="Savoy, IL"
~/openclaw/skills/weather/weather.sh
```

### Open-Meteo (recommended)

#### 1) Geocode a place name → latitude/longitude

```bash
curl -s --max-time 10 \
  "https://geocoding-api.open-meteo.com/v1/search?name=Savoy%2C%20Illinois&count=1&language=en&format=json"
```

#### 2) Current weather + today’s highs/lows (example)

```bash
# Replace LAT/LON with the geocoding result.
LAT=40.06
LON=-88.25

curl -s --max-time 10 \
  "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto"
```

#### 3) Quick one-liner (JSON still; good for scripts)

```bash
curl -s --max-time 10 \
  "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,apparent_temperature,wind_speed_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto"
```

### National Weather Service fallback (US)

#### 1) Get forecast endpoint from lat/lon

```bash
LAT=40.06
LON=-88.25

curl -s --max-time 10 \
  -H "User-Agent: OpenClaw Weather Skill (contact: local)" \
  "https://api.weather.gov/points/${LAT},${LON}"
```

#### 2) Fetch forecast (human-readable periods)

```bash
FORECAST_URL="https://api.weather.gov/gridpoints/ILX/52,72/forecast"  # example

curl -s --max-time 10 \
  -H "User-Agent: OpenClaw Weather Skill (contact: local)" \
  "$FORECAST_URL"
```

## Reliability Notes (timeouts)

- Prefer `curl --max-time 10` (or similar) to avoid hanging.
- If Open-Meteo fails or returns empty results, fall back to NWS (US locations).
- If both fail, ask the user for **ZIP code or lat/lon** and try again.
