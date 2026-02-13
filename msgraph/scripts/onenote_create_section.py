#!/usr/bin/env python3
"""Create a new section in a OneNote notebook."""

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

from msgraph_kit import auth
from msgraph_kit.onenote import sections


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create a section in a OneNote notebook")
    parser.add_argument("--notebook-id", required=True, help="Notebook ID")
    parser.add_argument("--name", required=True, help="Section name")
    args = parser.parse_args()

    try:
        client = auth.get_graph_client()
        result = await sections.create_section(client, args.notebook_id, args.name)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
