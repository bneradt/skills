#!/usr/bin/env python3
"""Render a small human-readable weather summary from Open-Meteo forecast JSON."""

import json
import sys


def first(arr):
    if isinstance(arr, list) and arr:
        return arr[0]
    return None


WMO = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
}


def deg_to_compass(deg: float) -> str:
    # 16-point compass
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    deg = deg % 360.0
    idx = int((deg + 11.25) // 22.5) % 16
    return dirs[idx]


def _moon_phase_fraction(date_yyyy_mm_dd: str) -> float | None:
    """Approx moon phase fraction in [0,1).

    0.0 = New Moon, 0.25 = First Quarter, 0.5 = Full Moon, 0.75 = Last Quarter.
    """
    try:
        y, m, d = (int(x) for x in date_yyyy_mm_dd.split("-"))
    except Exception:
        return None

    if m <= 2:
        y -= 1
        m += 12

    # Julian day (at noon)
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5

    # Days since known new moon (2000-01-06 18:14 UT) ~ JD 2451550.1
    days_since = jd - 2451550.1
    synodic = 29.53058867
    return (days_since % synodic) / synodic


def moon_illumination_percent(date_yyyy_mm_dd: str) -> int | None:
    """Approx moon illumination percent for a given date (UTC-ish), no external API."""
    phase = _moon_phase_fraction(date_yyyy_mm_dd)
    if phase is None:
        return None

    # Illumination fraction: (1 - cos(2pi*phase)) / 2
    import math

    illum = (1 - math.cos(2 * math.pi * phase)) / 2
    return int(round(illum * 100))


def moon_phase_name(date_yyyy_mm_dd: str) -> str | None:
    """Return an 8-phase name (New, Waxing Crescent, ...)."""
    phase = _moon_phase_fraction(date_yyyy_mm_dd)
    if phase is None:
        return None

    names = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]

    # Pick nearest of 8 bins.
    idx = int((phase * 8) + 0.5) % 8
    return names[idx]


def main() -> int:
    name = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    raw = sys.stdin.read().strip()
    if not raw:
        print("Weather: (no data)")
        return 1

    try:
        j = json.loads(raw)
    except Exception:
        print("Weather: (bad data)")
        return 1

    cur = j.get("current") or {}
    daily = j.get("daily") or {}

    code = cur.get("weather_code")
    cond = WMO.get(code, f"WMO {code}" if code is not None else "")

    t = cur.get("temperature_2m")
    feel = cur.get("apparent_temperature")
    hum = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")
    wind_dir = cur.get("wind_direction_10m")
    precip = cur.get("precipitation")

    hi = first(daily.get("temperature_2m_max"))
    lo = first(daily.get("temperature_2m_min"))
    pp = first(daily.get("precipitation_probability_max"))
    wind_max = first(daily.get("wind_speed_10m_max"))
    sunrise = first(daily.get("sunrise"))
    sunset = first(daily.get("sunset"))
    day = first(daily.get("time"))

    loc = name or (j.get("timezone", "").replace("_", " ") if isinstance(j.get("timezone"), str) else "")

    parts = []
    if t is not None:
        parts.append(f"{t:.0f}°F")
    if feel is not None:
        parts.append(f"feels {feel:.0f}°F")
    line1 = " / ".join(parts) if parts else "(temp n/a)"

    extras = []
    if cond:
        extras.append(cond)
    if wind is not None:
        if wind_dir is not None:
            extras.append(f"wind {wind:.0f} mph {deg_to_compass(float(wind_dir))}")
        else:
            extras.append(f"wind {wind:.0f} mph")
    if hum is not None:
        extras.append(f"humidity {hum:.0f}%")
    if precip is not None:
        extras.append(f"precip {precip:.2f} in")

    line2 = "; ".join(extras)

    line3_parts = []
    if hi is not None and lo is not None:
        line3_parts.append(f"Today: {hi:.0f}°F / {lo:.0f}°F")
    elif hi is not None:
        line3_parts.append(f"Today high: {hi:.0f}°F")
    elif lo is not None:
        line3_parts.append(f"Today low: {lo:.0f}°F")

    if pp is not None:
        line3_parts.append(f"precip chance {pp:.0f}%")
    if wind_max is not None:
        line3_parts.append(f"max wind {wind_max:.0f} mph")

    # Sunrise/sunset (Open-Meteo returns ISO strings like 2026-02-20T06:55)
    def hhmm(iso: str | None) -> str | None:
        if not iso or "T" not in iso:
            return None
        return iso.split("T", 1)[1]

    sr = hhmm(sunrise)
    ss = hhmm(sunset)
    if sr and ss:
        line3_parts.append(f"sunrise {sr}; sunset {ss}")

    moon_pct = moon_illumination_percent(day) if isinstance(day, str) else None
    moon_name = moon_phase_name(day) if isinstance(day, str) else None
    if moon_pct is not None or moon_name:
        if moon_name and moon_pct is not None:
            line3_parts.append(f"moon: {moon_name}, {moon_pct}% illuminated")
        elif moon_name:
            line3_parts.append(f"moon: {moon_name}")
        else:
            line3_parts.append(f"moon {moon_pct}%")

    line3 = "; ".join(line3_parts)

    print(f"{loc}: {line1}")
    if line2:
        print(line2)
    if line3:
        print(line3)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
