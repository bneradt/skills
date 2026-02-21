#!/usr/bin/env bash
set -euo pipefail

# Ensure the msgraph skill virtualenv exists and has deps installed.
# Prefers `uv` if available (fast, reproducible). Falls back to venv+pip.

MSGRAPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$MSGRAPH_DIR/.venv"
PY="$VENV/bin/python3"

if [[ -x "$PY" ]]; then
  exit 0
fi

cd "$MSGRAPH_DIR"

if command -v uv >/dev/null 2>&1; then
  uv venv "$VENV"
  # Install pinned deps (requirements.txt). `uv pip` is compatible with pip args.
  uv pip install -r requirements.txt
  exit 0
fi

python3 -m venv "$VENV"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r requirements.txt
