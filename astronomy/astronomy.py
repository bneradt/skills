#!/usr/bin/env python3
"""Moon phase, illumination, and sunrise/sunset from Open-Meteo."""

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

TIMEOUT = 10

# Known new moon epoch and synodic period
NEW_MOON_EPOCH = date(2000, 1, 6)  # known new moon
SYNODIC_PERIOD = 29.53058867

PHASE_NAMES = [
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
]


def load_env():
    """Load .env from the script's directory."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if not os.environ.get(key):
                os.environ[key] = val


def fetch_json(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def geocode(location):
    """Geocode a city/state string to (lat, lon, display_name)."""
    candidates = [location, location.replace(",", " ")]
    city = location.split(",")[0].strip()
    if city != location:
        candidates.append(city)

    for query in candidates:
        encoded = urllib.parse.quote(query.strip())
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
        data = fetch_json(url)
        results = data.get("results")
        if results:
            r = results[0]
            name = ", ".join(
                x for x in [r.get("name"), r.get("admin1"), r.get("country_code")] if x
            )
            return r["latitude"], r["longitude"], name
    return None


def resolve_date(val):
    if val == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    if val == "today":
        return date.today().isoformat()
    date.fromisoformat(val)
    return val


def moon_phase_fraction(date_str):
    """Return phase as a fraction of the synodic cycle (0.0 = new moon, 0.5 = full)."""
    d = date.fromisoformat(date_str)
    days_since = (d - NEW_MOON_EPOCH).days
    return (days_since % SYNODIC_PERIOD) / SYNODIC_PERIOD


def moon_phase_name(date_str):
    """Return the 8-point phase name."""
    frac = moon_phase_fraction(date_str)
    index = int((frac * 8 + 0.5) % 8)
    return PHASE_NAMES[index]


def moon_illumination_percent(date_str):
    """Return illumination percentage (0–100)."""
    frac = moon_phase_fraction(date_str)
    return (1 - math.cos(2 * math.pi * frac)) / 2 * 100


def fetch_sun_times(lat, lon, target_date):
    """Fetch sunrise/sunset from Open-Meteo for a given date."""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "daily": "sunrise,sunset",
        "timezone": "auto",
        "start_date": target_date,
        "end_date": target_date,
    })
    return fetch_json(f"https://api.open-meteo.com/v1/forecast?{params}")


def main():
    load_env()

    parser = argparse.ArgumentParser(description="Moon phase and astronomical info")
    parser.add_argument("location", nargs="?", default=None,
                        help="City, State (e.g. 'Cape Coral, FL')")
    parser.add_argument("--date", default=None,
                        help="'yesterday', 'today', or YYYY-MM-DD")
    args = parser.parse_args()

    target = resolve_date(args.date) if args.date else date.today().isoformat()

    phase = moon_phase_name(target)
    illum = moon_illumination_percent(target)
    print(f"Moon ({target}): {phase}, {illum:.0f}% illuminated")

    location = args.location or os.environ.get("USER_LOCATION", "")
    if location:
        geo = geocode(location)
        if not geo:
            print(f"Could not geocode: {location}", file=sys.stderr)
            return 1
        lat, lon, name = geo

        data = fetch_sun_times(lat, lon, target)
        daily = data.get("daily", {})
        sunrise = daily.get("sunrise", [None])[0]
        sunset = daily.get("sunset", [None])[0]

        def hhmm(iso):
            if not iso or "T" not in iso:
                return None
            return iso.split("T", 1)[1]

        sr, ss = hhmm(sunrise), hhmm(sunset)
        if sr and ss:
            print(f"{name} — Sunrise {sr}; Sunset {ss}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
