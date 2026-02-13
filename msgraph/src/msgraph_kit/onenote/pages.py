"""OneNote page operations via Microsoft Graph API."""

from __future__ import annotations

import httpx
from msgraph import GraphServiceClient

from .. import auth, config
from ..html_convert import html_to_markdown, make_patch_content, markdown_to_onenote_html

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def list_pages(client: GraphServiceClient, section_id: str) -> list[dict]:
    """List all pages in a section."""
    result = await client.me.onenote.sections.by_onenote_section_id(section_id).pages.get()
    pages = []
    if result and result.value:
        for page in result.value:
            pages.append(_page_to_dict(page))
    return pages


async def read_page_content(client: GraphServiceClient, page_id: str) -> dict:
    """Read a page's content and return it as Markdown.

    Uses the $value endpoint to get the full HTML content,
    then converts to Markdown.
    """
    content_bytes = await client.me.onenote.pages.by_onenote_page_id(page_id).content.get()
    html_content = content_bytes.decode("utf-8") if isinstance(content_bytes, bytes) else str(content_bytes)
    md_content = html_to_markdown(html_content)

    # Also get page metadata
    page = await client.me.onenote.pages.by_onenote_page_id(page_id).get()

    return {
        **_page_to_dict(page),
        "content": md_content,
    }


async def create_page(section_id: str, title: str, content_md: str) -> dict:
    """Create a new page with Markdown content.

    Uses raw HTTP because the SDK typed models don't support
    the multipart HTML body format that OneNote requires.
    """
    html = markdown_to_onenote_html(title, content_md)

    credential = auth._make_credential()
    token = credential.get_token(*config.SCOPES)

    url = f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages"
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "text/html",
    }

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(url, content=html, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "createdDateTime": data.get("createdDateTime"),
        "selfUrl": data.get("self"),
        "contentUrl": data.get("contentUrl"),
    }


async def update_page(page_id: str, action: str, content_html: str) -> dict:
    """Update (PATCH) a page's content.

    Args:
        page_id: The page ID to update.
        action: 'append', 'replace', or 'insert'.
        content_html: HTML content for the patch. If this looks like Markdown,
                      it will be converted to HTML first.
    """
    # If content doesn't look like HTML, convert from Markdown
    if not content_html.strip().startswith("<"):
        from markdown import markdown
        content_html = markdown(content_html, extensions=["tables", "fenced_code"])

    patch_body = make_patch_content(action, content_html)

    credential = auth._make_credential()
    token = credential.get_token(*config.SCOPES)

    url = f"{GRAPH_BASE}/me/onenote/pages/{page_id}/content"
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as http_client:
        resp = await http_client.patch(url, content=patch_body, headers=headers)
        resp.raise_for_status()

    return {"status": "updated", "pageId": page_id, "action": action}


def _page_to_dict(page) -> dict:
    """Convert a Page model to a plain dict."""
    return {
        "id": page.id,
        "title": page.title,
        "createdDateTime": page.created_date_time.isoformat() if page.created_date_time else None,
        "lastModifiedDateTime": page.last_modified_date_time.isoformat() if page.last_modified_date_time else None,
        "contentUrl": page.content_url if hasattr(page, "content_url") else None,
    }
