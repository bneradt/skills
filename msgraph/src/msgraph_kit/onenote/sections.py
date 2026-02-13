"""OneNote section operations via Microsoft Graph API."""

from __future__ import annotations

from msgraph import GraphServiceClient
from msgraph.generated.models.onenote_section import OnenoteSection


async def list_sections(client: GraphServiceClient, notebook_id: str) -> list[dict]:
    """List all sections in a notebook."""
    result = await client.me.onenote.notebooks.by_notebook_id(notebook_id).sections.get()
    sections = []
    if result and result.value:
        for sec in result.value:
            sections.append(_section_to_dict(sec))
    return sections


async def create_section(client: GraphServiceClient, notebook_id: str, display_name: str) -> dict:
    """Create a new section in a notebook."""
    body = OnenoteSection(display_name=display_name)
    sec = await client.me.onenote.notebooks.by_notebook_id(notebook_id).sections.post(body)
    return _section_to_dict(sec)


def _section_to_dict(sec: OnenoteSection) -> dict:
    """Convert a Section model to a plain dict."""
    return {
        "id": sec.id,
        "displayName": sec.display_name,
        "createdDateTime": sec.created_date_time.isoformat() if sec.created_date_time else None,
        "lastModifiedDateTime": sec.last_modified_date_time.isoformat() if sec.last_modified_date_time else None,
    }
