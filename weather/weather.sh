#!/usr/bin/env bash
set -euo pipefail

# weather.sh — Open-Meteo (primary) weather summary with optional NWS fallback.
# Usage:
#   weather.sh "Savoy, IL"
#   weather.sh "Cape Coral, FL" --days 1
#   weather.sh --lat 26.5629 --lon -81.9495
#
# Env:
#   WEATHER_DEFAULT_LOCATION  (used if no args)
#
# Notes:
# - Requires: bash, curl, python3

DAYS=1
LOCATION=""
LAT=""
LON=""

usage() {
  cat <<'EOF'
Usage:
  weather.sh "City, ST" [--days N]
  weather.sh --lat <lat> --lon <lon> [--days N]

Examples:
  weather.sh "Savoy, IL"
  weather.sh "Cape Coral, FL" --days 1
  weather.sh --lat 26.5629 --lon -81.9495
EOF
}

if [[ ${1-} == "-h" || ${1-} == "--help" ]]; then
  usage
  exit 0
fi

# First positional arg is location, unless it looks like a flag.
if [[ ${1-} != "" && ${1:0:1} != "-" ]]; then
  LOCATION="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --days)
      DAYS="$2"; shift 2 ;;
    --lat)
      LAT="$2"; shift 2 ;;
    --lon)
      LON="$2"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$LOCATION" && -z "$LAT" && -z "$LON" ]]; then
  LOCATION="${WEATHER_DEFAULT_LOCATION:-}"
fi

if [[ -z "$LAT" || -z "$LON" ]]; then
  if [[ -z "$LOCATION" ]]; then
    echo "Provide a location string or --lat/--lon" >&2
    usage >&2
    exit 2
  fi

  # Open-Meteo geocoder can be picky. Try a few variants (e.g. drop ", FL").
  CANDIDATES=(
    "$LOCATION"
    "${LOCATION//,/ }"
    "${LOCATION%%,*}"
  )
  # If the last token is a 2-letter state/country code, also try removing it.
  if [[ "$LOCATION" =~ ^(.*)[[:space:]]+[A-Za-z]{2}$ ]]; then
    CANDIDATES+=("${BASH_REMATCH[1]}")
  fi

  GEO_JSON=""
  for GEO_QUERY in "${CANDIDATES[@]}"; do
    GEO_QUERY=$(printf "%s" "$GEO_QUERY" | tr ',' ' ')
    GEO_JSON=$(curl -sS --max-time 10 --retry 0 \
      "https://geocoding-api.open-meteo.com/v1/search?name=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))' "$GEO_QUERY")&count=1&language=en&format=json" || true)

    # If it has "results", keep it.
    if python3 -c 'import json,sys
try:
  j=json.load(sys.stdin)
except Exception:
  raise SystemExit(1)
raise SystemExit(0 if j.get("results") else 1)
' <<<"$GEO_JSON"; then
      break
    fi
  done

  mapfile -t _GEO_LINES < <(
    python3 -c 'import json,sys
raw=sys.stdin.read().strip()
if not raw:
  print("\n\n")
  raise SystemExit(0)
try:
  j=json.loads(raw)
except Exception:
  print("\n\n")
  raise SystemExit(0)
res=j.get("results") or []
if not res:
  print("\n\n")
  raise SystemExit(0)
r=res[0]
name = ", ".join([x for x in [r.get("name"), r.get("admin1"), r.get("country_code")] if x])
print(r.get("latitude", ""))
print(r.get("longitude", ""))
print(name)
' <<<"$GEO_JSON"
  )
  LAT="${_GEO_LINES[0]:-}"
  LON="${_GEO_LINES[1]:-}"
  RESOLVED_NAME="${_GEO_LINES[2]:-}"

  if [[ -z "$LAT" || -z "$LON" ]]; then
    echo "Could not geocode location: $LOCATION" >&2
    exit 1
  fi
else
  RESOLVED_NAME="$LOCATION"
fi

FORECAST_JSON=$(curl -sS --max-time 10 --retry 0 \
  "https://api.open-meteo.com/v1/forecast?latitude=${LAT}&longitude=${LON}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto&forecast_days=${DAYS}" || true)

python3 "$(dirname "$0")/weather_summary.py" "$RESOLVED_NAME" <<<"$FORECAST_JSON"
