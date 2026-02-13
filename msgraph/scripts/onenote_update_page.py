#!/usr/bin/env python3
"""Update (patch) a OneNote page's content."""

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
    parser = argparse.ArgumentParser(description="Update a OneNote page")
    parser.add_argument("--page-id", required=True, help="Page ID")
    parser.add_argument(
        "--action",
        required=True,
        choices=["append", "replace", "insert"],
        help="Patch action",
    )
    parser.add_argument("--content", required=True, help="Content (Markdown or HTML)")
    args = parser.parse_args()

    try:
        result = await pages.update_page(args.page_id, args.action, args.content)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
