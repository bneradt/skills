#!/usr/bin/env bash
set -euo pipefail

# Run a Python command in the msgraph skill venv with PYTHONPATH set.
# Usage:
#   ./scripts/py.sh -c 'import msgraph_kit; print(msgraph_kit.__file__)'
#   ./scripts/py.sh scripts/onenote_list_pages.py --section-id ...

MSGRAPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$MSGRAPH_DIR/scripts/ensure_venv.sh"

export PYTHONPATH="$MSGRAPH_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$MSGRAPH_DIR/.venv/bin/python3" "$@"
