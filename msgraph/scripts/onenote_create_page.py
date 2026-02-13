#!/usr/bin/env python3
"""Create a new page in a OneNote section."""

import argparse
import asyncio
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

from msgraph_kit.onenote import pages


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a page in a OneNote section")
    parser.add_argument("--section-id", required=True, help="Section ID")
    parser.add_argument("--title", required=True, help="Page title")
    parser.add_argument("--content", default=None, help="Page content in Markdown")
    parser.add_argument("--stdin", action="store_true", help="Read content from stdin")
    args = parser.parse_args()

    content = args.content or ""
    if args.stdin:
        content = sys.stdin.read()

    try:
        result = await pages.create_page(args.section_id, args.title, content)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
