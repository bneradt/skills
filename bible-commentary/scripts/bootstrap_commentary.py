#!/usr/bin/env python3
"""Download public-domain commentary sources locally and build the SQLite index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional

from common_db import default_data_dir
from common_progress import ProgressReporter
import build_index

TIMEOUT = 30
DEFAULT_ARCHIVE_URL = "https://files.brianneradt.com/api/public/dl/xhCdAE8Z?inline=true"
DEFAULT_ARCHIVE_NAME = "commentaries_ai_friendly.tar.gz"


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
    os.makedirs(os.path.join(data_dir, "downloads"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "ai_friendly"), exist_ok=True)


def _safe_extract_tar(archive_path: str, out_dir: str) -> None:
    out_abs = os.path.abspath(out_dir)
    with tarfile.open(archive_path, "r:gz") as tf:
        members = tf.getmembers()
        for member in members:
            target = os.path.abspath(os.path.join(out_abs, member.name))
            if not target.startswith(out_abs + os.sep) and target != out_abs:
                raise ValueError(f"Unsafe archive path: {member.name}")
        try:
            tf.extractall(path=out_abs, members=members, filter="data")
        except TypeError:
            tf.extractall(path=out_abs, members=members)


def _find_ai_friendly_root(data_dir: str) -> Optional[str]:
    candidates = []
    base = os.path.join(data_dir, "ai_friendly")
    candidates.extend(
        [
            base,
            os.path.join(base, "ai_friendly"),
            os.path.join(base, "commentaries_ai_friendly"),
        ]
    )
    if os.path.isdir(base):
        for name in os.listdir(base):
            child = os.path.join(base, name)
            if os.path.isdir(child):
                candidates.append(child)
    for c in candidates:
        if os.path.isdir(os.path.join(c, "manifests")) and os.path.isdir(os.path.join(c, "schemas")):
            return c
    return None


def _bootstrap_ai_friendly_archive(data_dir: str, refresh: bool, progress: ProgressReporter) -> bool:
    archive_url = os.environ.get("BIBLE_COMMENTARY_ARCHIVE_URL", DEFAULT_ARCHIVE_URL)
    archive_name = os.environ.get("BIBLE_COMMENTARY_ARCHIVE_FILENAME", DEFAULT_ARCHIVE_NAME)
    downloads_dir = os.path.join(data_dir, "downloads")
    archive_path = os.path.join(downloads_dir, archive_name)
    ai_dir = os.path.join(data_dir, "ai_friendly")

    ready_root = _find_ai_friendly_root(data_dir)
    if ready_root and not refresh:
        progress.emit("SETUP", "using existing local ai_friendly corpus", path=ready_root)
        return True

    try:
        if refresh or not os.path.isfile(archive_path):
            progress.emit("DOWNLOAD", "fetching ai_friendly corpus archive", url=archive_url, filename=archive_name)
            body = _download(archive_url)
            with open(archive_path, "wb") as f:
                f.write(body)
            progress.emit("DOWNLOAD", "saved ai_friendly archive", bytes=len(body), sha256=_sha256_bytes(body)[:12])
        else:
            progress.emit("DOWNLOAD", "using cached ai_friendly archive", path=archive_path)

        # Clear extraction target on refresh.
        if refresh and os.path.isdir(ai_dir):
            for root, dirs, files in os.walk(ai_dir, topdown=False):
                for name in files:
                    os.unlink(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        os.makedirs(ai_dir, exist_ok=True)
        progress.emit("SETUP", "extracting ai_friendly archive", out_dir=ai_dir)
        _safe_extract_tar(archive_path, ai_dir)
        ready_root = _find_ai_friendly_root(data_dir)
        if not ready_root:
            progress.emit("WARN", "archive extracted but ai_friendly structure not detected", out_dir=ai_dir)
            return False
        progress.emit("SETUP", "ai_friendly corpus ready", path=ready_root)
        return True
    except Exception as exc:
        progress.emit("WARN", "ai_friendly archive bootstrap failed", error=str(exc))
        return False


def bootstrap(manifest: dict, refresh: bool, progress: ProgressReporter, skip_build: bool = False) -> int:
    data_dir = os.path.expanduser(os.environ.get("BIBLE_COMMENTARY_DATA_DIR", default_data_dir()))
    ensure_dirs(data_dir)
    raw_root = os.path.join(data_dir, "raw")
    progress.emit("SETUP", "first-time/local corpus setup may take several minutes", data_dir=data_dir)

    # Preferred bootstrap path: pre-normalized ai_friendly archive.
    used_ai_archive = _bootstrap_ai_friendly_archive(data_dir, refresh=refresh, progress=progress)
    if used_ai_archive and skip_build:
        progress.emit("DONE", "ai_friendly setup complete (build skipped)")
        return 0
    if used_ai_archive:
        progress.emit("PARSE", "starting index build from ai_friendly corpus")
        return build_index.build_index(manifest, refresh=refresh, progress=progress)

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
