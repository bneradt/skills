#!/usr/bin/env python3
"""Check current Microsoft Graph authentication status."""

import json
import os
import sys

# Auto-detect venv and re-exec if needed
_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
_venv_python = os.path.join(_repo_root, ".venv", "bin", "python3")
if os.path.exists(_venv_python) and sys.executable != _venv_python:
    os.execv(_venv_python, [_venv_python] + sys.argv)

sys.path.insert(0, os.path.join(_repo_root, "src"))

from msgraph_kit import auth


def main() -> None:
    try:
        status = auth.check_auth_status()
        print(json.dumps(status, indent=2))
    except Exception as exc:
        error = {"error": str(exc)}
        print(json.dumps(error, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
