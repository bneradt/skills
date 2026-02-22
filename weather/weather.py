#!/usr/bin/env python3
"""Get current or historical weather from Open-Meteo."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

TIMEOUT = 10

WMO = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
}

COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def deg_to_compass(deg):
    return COMPASS[int((deg % 360 + 11.25) // 22.5) % 16]


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
    """Geocode a city/state string to (lat, lon, display_name).

    Open-Meteo's geocoder is picky — "Savoy, IL" returns nothing but "Savoy"
    works. Try the full string first, then fall back to just the city name.
    """
    # Build candidate queries: original, without comma, city name only
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


def fetch_current(lat, lon):
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m",
        ]),
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_probability_max", "wind_speed_10m_max",
            "sunrise", "sunset",
        ]),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
        "forecast_days": 1,
    })
    return fetch_json(f"https://api.open-meteo.com/v1/forecast?{params}")


def fetch_historical(lat, lon, target_date):
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": target_date,
        "end_date": target_date,
        "daily": ",".join([
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "wind_speed_10m_max",
            "weather_code",
        ]),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    })
    return fetch_json(f"https://archive-api.open-meteo.com/v1/archive?{params}")


def fmt_current(name, data):
    cur = data.get("current", {})
    daily = data.get("daily", {})

    t = cur.get("temperature_2m")
    feel = cur.get("apparent_temperature")
    code = cur.get("weather_code")
    cond = WMO.get(code, "")
    wind = cur.get("wind_speed_10m")
    wind_dir = cur.get("wind_direction_10m")
    hum = cur.get("relative_humidity_2m")
    precip = cur.get("precipitation")

    first = lambda arr: arr[0] if isinstance(arr, list) and arr else None
    hi = first(daily.get("temperature_2m_max"))
    lo = first(daily.get("temperature_2m_min"))
    pp = first(daily.get("precipitation_probability_max"))
    wind_max = first(daily.get("wind_speed_10m_max"))
    sunrise = first(daily.get("sunrise"))
    sunset = first(daily.get("sunset"))

    # Line 1: location, temp, feels like
    parts = []
    if t is not None:
        parts.append(f"{t:.0f}°F")
    if feel is not None:
        parts.append(f"feels {feel:.0f}°F")
    line1 = f"{name}: {' / '.join(parts)}" if parts else f"{name}: (temp n/a)"

    # Line 2: conditions
    extras = []
    if cond:
        extras.append(cond)
    if wind is not None:
        w = f"wind {wind:.0f} mph"
        if wind_dir is not None:
            w += f" {deg_to_compass(wind_dir)}"
        extras.append(w)
    if hum is not None:
        extras.append(f"humidity {hum:.0f}%")
    if precip is not None:
        extras.append(f"precip {precip:.2f} in")

    # Line 3: daily summary
    day_parts = []
    if hi is not None and lo is not None:
        day_parts.append(f"Today: {hi:.0f}°F / {lo:.0f}°F")
    if pp is not None:
        day_parts.append(f"precip chance {pp:.0f}%")
    if wind_max is not None:
        day_parts.append(f"max wind {wind_max:.0f} mph")

    # Line 4: sunrise/sunset
    def hhmm(iso):
        if not iso or "T" not in iso:
            return None
        return iso.split("T", 1)[1]

    sr, ss = hhmm(sunrise), hhmm(sunset)

    lines = [line1]
    if extras:
        lines.append("; ".join(extras))
    if day_parts:
        lines.append("; ".join(day_parts))
    if sr and ss:
        lines.append(f"Sunrise {sr}; Sunset {ss}")
    print("\n".join(lines))


def fmt_historical(name, target_date, data):
    daily = data.get("daily", {})

    first = lambda arr: arr[0] if isinstance(arr, list) and arr else None
    hi = first(daily.get("temperature_2m_max"))
    lo = first(daily.get("temperature_2m_min"))
    precip = first(daily.get("precipitation_sum"))
    wind_max = first(daily.get("wind_speed_10m_max"))
    code = first(daily.get("weather_code"))
    cond = WMO.get(code, "")

    lines = [f"{name} ({target_date}):"]
    if cond:
        lines[0] += f" {cond}"
    if hi is not None and lo is not None:
        lines.append(f"High: {hi:.0f}°F / Low: {lo:.0f}°F")
    parts = []
    if precip is not None:
        parts.append(f"Precipitation: {precip:.2f} in")
    if wind_max is not None:
        parts.append(f"Max wind: {wind_max:.0f} mph")
    if parts:
        lines.append("; ".join(parts))
    print("\n".join(lines))


def resolve_date(val):
    if val == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    if val == "today":
        return date.today().isoformat()
    # Validate ISO format
    date.fromisoformat(val)
    return val


def main():
    load_env()

    parser = argparse.ArgumentParser(description="Get weather from Open-Meteo")
    parser.add_argument("location", nargs="?", default=None, help="City, State (e.g. 'Cape Coral, FL')")
    parser.add_argument("--date", default=None, help="Date for historical weather: 'yesterday', 'today', or YYYY-MM-DD")
    args = parser.parse_args()

    location = args.location or os.environ.get("USER_LOCATION", "")
    if not location:
        print("No location provided. Pass a city/state or set USER_LOCATION in .env", file=sys.stderr)
        return 1

    geo = geocode(location)
    if not geo:
        print(f"Could not geocode: {location}", file=sys.stderr)
        return 1
    lat, lon, name = geo

    if args.date:
        target = resolve_date(args.date)
        data = fetch_historical(lat, lon, target)
        fmt_historical(name, target, data)
    else:
        data = fetch_current(lat, lon)
        fmt_current(name, data)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
