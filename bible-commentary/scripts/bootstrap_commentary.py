#!/usr/bin/env python3
"""Download public-domain commentary sources locally and build the SQLite index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from common_db import default_data_dir
from common_progress import ProgressReporter
import build_index

TIMEOUT = 30


def load_manifest() -> dict:
    return build_index.load_manifest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "openclaw-bible-commentary/0.1"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def ensure_dirs(data_dir: str) -> None:
    os.makedirs(os.path.join(data_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "index"), exist_ok=True)


def bootstrap(manifest: dict, refresh: bool, progress: ProgressReporter, skip_build: bool = False) -> int:
    data_dir = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_DATA_DIR", default_data_dir()))
    ensure_dirs(data_dir)
    raw_root = os.path.join(data_dir, "raw")
    progress.emit("SETUP", "first-time/local corpus setup may take several minutes", data_dir=data_dir)

    sources = manifest.get("sources", [])
    warnings: List[str] = []
    for idx, src in enumerate(sources, start=1):
        local_path = os.path.join(raw_root, src["local_path"])
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        if os.path.exists(local_path) and not refresh:
            progress.emit("DOWNLOAD", "using cached source", current=idx, total=len(sources), source=src["local_path"])
            continue
        try:
            progress.emit("DOWNLOAD", "fetching source", current=idx, total=len(sources), source=src["local_path"])
            body = _download(src["source_url"])
            with open(local_path, "wb") as f:
                f.write(body)
            progress.emit("DOWNLOAD", "saved source", source=src["local_path"], bytes=len(body), sha256=_sha256_bytes(body)[:12])
        except urllib.error.URLError as exc:
            msg = f"{src['local_path']}: {exc}"
            warnings.append(msg)
            progress.emit("WARN", "download failed", source=src["local_path"], error=str(exc))

    if warnings:
        progress.emit("WARN", "some downloads failed; continuing with available files", count=len(warnings))

    if skip_build:
        progress.emit("DONE", "download stage complete (build skipped)")
        return 0

    progress.emit("PARSE", "starting index build")
    return build_index.build_index(manifest, refresh=refresh, progress=progress)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Bootstrap local public-domain commentary corpus")
    ap.add_argument("--refresh", action="store_true", help="Redownload sources and rebuild index")
    ap.add_argument("--skip-build", action="store_true", help="Only download sources")
    ap.add_argument("--progress", action="store_true", help="Emit progress messages")
    ap.add_argument("--json-progress", action="store_true", help="Emit progress as JSON lines")
    args = ap.parse_args(argv)

    progress = ProgressReporter(enabled=args.progress or args.json_progress, json_mode=args.json_progress)
    manifest = load_manifest()
    return bootstrap(manifest, refresh=args.refresh, progress=progress, skip_build=args.skip_build)


if __name__ == "__main__":
    raise SystemExit(main())

