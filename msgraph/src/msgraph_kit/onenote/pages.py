"""OneNote page operations via Microsoft Graph API (lightweight HTTP)."""

from __future__ import annotations

import json

import requests

from .. import auth
from ..html_convert import html_to_markdown, make_patch_content, markdown_to_onenote_html

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def list_pages(section_id: str) -> list[dict]:
    """List all pages in a section."""
    resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages",
        headers=auth.get_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [_page_to_dict(p) for p in data.get("value", [])]


def read_page_content(page_id: str) -> dict:
    """Read a page's content and return it as Markdown.

    Fetches the full HTML content via the $value endpoint,
    then converts to Markdown. Also returns page metadata.
    """
    headers = auth.get_headers()

    # Get page metadata
    meta_resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/pages/{page_id}",
        headers=headers,
        timeout=30,
    )
    meta_resp.raise_for_status()
    page_meta = meta_resp.json()

    # Get page HTML content
    content_resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/pages/{page_id}/content",
        headers=headers,
        timeout=30,
    )
    content_resp.raise_for_status()
    html_content = content_resp.text
    md_content = html_to_markdown(html_content)

    return {
        **_page_to_dict(page_meta),
        "content": md_content,
    }


def create_page(section_id: str, title: str, content_md: str) -> dict:
    """Create a new page with Markdown content."""
    html = markdown_to_onenote_html(title, content_md)
    headers = auth.get_headers()
    headers["Content-Type"] = "text/html"

    resp = requests.post(
        f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages",
        headers=headers,
        data=html,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "createdDateTime": data.get("createdDateTime"),
        "selfUrl": data.get("self"),
        "contentUrl": data.get("contentUrl"),
    }


def update_page(page_id: str, action: str, content: str) -> dict:
    """Update (PATCH) a page's content.

    Args:
        page_id: The page ID to update.
        action: 'append', 'replace', or 'insert'.
        content: Content for the patch. If it doesn't look like HTML,
                 it will be converted from Markdown.
    """
    # If content doesn't look like HTML, convert from Markdown
    if not content.strip().startswith("<"):
        from markdown import markdown
        content = markdown(content, extensions=["tables", "fenced_code"])

    patch_body = make_patch_content(action, content)

    resp = requests.patch(
        f"{GRAPH_BASE}/me/onenote/pages/{page_id}/content",
        headers=auth.get_headers(),
        data=patch_body,
        timeout=30,
    )
    resp.raise_for_status()

    return {"status": "updated", "pageId": page_id, "action": action}


def _page_to_dict(p: dict) -> dict:
    """Normalize a page JSON response to a clean dict."""
    return {
        "id": p.get("id"),
        "title": p.get("title"),
        "createdDateTime": p.get("createdDateTime"),
        "lastModifiedDateTime": p.get("lastModifiedDateTime"),
        "contentUrl": p.get("contentUrl"),
    }
