#!/usr/bin/env python3
"""List all pages in a OneNote section."""

import argparse
import json
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_script_dir)
_venv_python = os.path.join(_repo_root, ".venv", "bin", "python3")
if os.path.exists(_venv_python) and sys.executable != _venv_python:
    os.execv(_venv_python, [_venv_python] + sys.argv)

sys.path.insert(0, os.path.join(_repo_root, "src"))

from msgraph_kit.onenote import pages


def main() -> None:
    parser = argparse.ArgumentParser(description="List pages in a section")
    parser.add_argument("--section-id", required=True, help="Section ID")
    args = parser.parse_args()

    try:
        result = pages.list_pages(args.section_id)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
