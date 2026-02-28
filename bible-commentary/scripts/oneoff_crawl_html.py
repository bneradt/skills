#!/usr/bin/env python3
"""One-off HTML crawler/downloader for building an offline commentary corpus.

Example:
  python3 oneoff_crawl_html.py \
    --start-url "https://www.sacred-texts.com/bib/cmt/gill/index.htm" \
    --allowed-prefix "https://www.sacred-texts.com/bib/cmt/gill/" \
    --out-dir ~/Downloads/gill-html \
    --cookie-header "cf_clearance=...; other=..." \
    --zip-output ~/Downloads/gill-html.zip \
    --delay 0.6
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import deque
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, Iterable, List, Optional, Set


DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and v:
                self.links.append(v.strip())
                break


@dataclass
class CrawlResult:
    url: str
    status: int
    content_type: str
    output_path: str
    bytes: int
    sha256: str
    discovered_links: int


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    # collapse duplicate slashes
    path = re.sub(r"/{2,}", "/", path)
    return urllib.parse.urlunsplit((scheme, netloc, path, parsed.query, ""))


def safe_local_path(root: str, base: str, url: str) -> str:
    rel = url[len(base) :] if url.startswith(base) else urllib.parse.urlsplit(url).path.lstrip("/")
    rel = urllib.parse.unquote(rel)
    if not rel or rel.endswith("/"):
        rel = posixpath.join(rel, "index.html")
    if rel.endswith(".htm"):
        rel = rel + "l"  # normalize to .html
    if not rel.lower().endswith(".html"):
        rel = rel + ".html"
    rel = rel.replace("\\", "/")
    rel = re.sub(r"^\.+/", "", rel)
    rel = re.sub(r"/\.+/", "/", rel)
    rel = rel.lstrip("/")
    full = os.path.abspath(os.path.join(root, rel))
    root_abs = os.path.abspath(root)
    if not full.startswith(root_abs + os.sep) and full != root_abs:
        raise ValueError(f"Unsafe path derived from URL: {url}")
    return full


def extract_links(html: str, page_url: str, allowed_prefix: str) -> List[str]:
    parser = LinkParser()
    parser.feed(html)
    out: List[str] = []
    for href in parser.links:
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        joined = urllib.parse.urljoin(page_url, href)
        joined = normalize_url(joined)
        if not joined.startswith(allowed_prefix):
            continue
        out.append(joined)
    # preserve order while deduping
    seen: Set[str] = set()
    ordered: List[str] = []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        ordered.append(u)
    return ordered


def fetch_url(url: str, timeout: int, user_agent: str, cookie_header: str, referer: Optional[str]) -> tuple[int, str, bytes]:
    headers = {"User-Agent": user_agent}
    if cookie_header:
        headers["Cookie"] = cookie_header
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = int(resp.getcode() or 200)
        ctype = str(resp.headers.get("Content-Type", ""))
        body = resp.read()
    return status, ctype, body


def crawl(
    start_url: str,
    allowed_prefix: str,
    out_dir: str,
    timeout: int,
    delay: float,
    max_pages: int,
    user_agent: str,
    cookie_header: str,
) -> List[CrawlResult]:
    os.makedirs(out_dir, exist_ok=True)
    queue = deque([normalize_url(start_url)])
    visited: Set[str] = set()
    results: List[CrawlResult] = []

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        if not url.startswith(allowed_prefix):
            continue
        visited.add(url)
        print(f"FETCH {len(visited)}/{max_pages}: {url}", flush=True)

        try:
            status, ctype, body = fetch_url(
                url=url,
                timeout=timeout,
                user_agent=user_agent,
                cookie_header=cookie_header,
                referer=start_url,
            )
        except urllib.error.HTTPError as exc:
            print(f"WARN HTTP {exc.code}: {url}", flush=True)
            continue
        except urllib.error.URLError as exc:
            print(f"WARN URL error: {url} ({exc})", flush=True)
            continue

        text = body.decode("utf-8", errors="replace")
        local_path = safe_local_path(out_dir, allowed_prefix, url)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(text)

        links = extract_links(text, url, allowed_prefix)
        for link in links:
            if link not in visited:
                queue.append(link)

        digest = hashlib.sha256(body).hexdigest()
        results.append(
            CrawlResult(
                url=url,
                status=status,
                content_type=ctype,
                output_path=local_path,
                bytes=len(body),
                sha256=digest,
                discovered_links=len(links),
            )
        )
        print(
            f"SAVED {os.path.relpath(local_path, out_dir)} bytes={len(body)} links={len(links)}",
            flush=True,
        )
        if delay > 0:
            time.sleep(delay)

    return results


def write_manifest(out_dir: str, records: List[CrawlResult]) -> str:
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(records),
        "records": [
            {
                "url": r.url,
                "status": r.status,
                "content_type": r.content_type,
                "output_path": os.path.relpath(r.output_path, out_dir),
                "bytes": r.bytes,
                "sha256": r.sha256,
                "discovered_links": r.discovered_links,
            }
            for r in records
        ],
    }
    path = os.path.join(out_dir, "crawl-manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def zip_dir(root: str, zip_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                arcname = os.path.relpath(full, root)
                zf.write(full, arcname)


def main() -> int:
    ap = argparse.ArgumentParser(description="One-off HTML crawler for offline commentary corpus capture")
    ap.add_argument("--start-url", required=True, help="First page to crawl")
    ap.add_argument("--allowed-prefix", required=True, help="Only crawl URLs with this prefix")
    ap.add_argument("--out-dir", required=True, help="Output directory for saved HTML files")
    ap.add_argument("--timeout", type=int, default=25, help="HTTP timeout seconds")
    ap.add_argument("--delay", type=float, default=0.5, help="Delay between requests in seconds")
    ap.add_argument("--max-pages", type=int, default=5000, help="Maximum pages to crawl")
    ap.add_argument("--user-agent", default=DEFAULT_UA, help="User-Agent string")
    ap.add_argument("--cookie-header", default="", help="Raw Cookie header value (useful for Cloudflare-protected sites)")
    ap.add_argument("--zip-output", default="", help="Optional zip output path")
    args = ap.parse_args()

    start_url = normalize_url(args.start_url)
    allowed_prefix = normalize_url(args.allowed_prefix)
    if not allowed_prefix.endswith("/"):
        allowed_prefix += "/"
    if not start_url.startswith(allowed_prefix):
        print("--start-url must be inside --allowed-prefix", flush=True)
        return 2

    results = crawl(
        start_url=start_url,
        allowed_prefix=allowed_prefix,
        out_dir=os.path.abspath(os.path.expanduser(args.out_dir)),
        timeout=args.timeout,
        delay=args.delay,
        max_pages=args.max_pages,
        user_agent=args.user_agent,
        cookie_header=args.cookie_header.strip(),
    )
    manifest_path = write_manifest(os.path.abspath(os.path.expanduser(args.out_dir)), results)
    print(f"DONE: saved {len(results)} pages", flush=True)
    print(f"MANIFEST: {manifest_path}", flush=True)
    if args.zip_output:
        zip_path = os.path.abspath(os.path.expanduser(args.zip_output))
        zip_dir(os.path.abspath(os.path.expanduser(args.out_dir)), zip_path)
        print(f"ZIP: {zip_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

