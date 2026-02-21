"""OneNote section operations via Microsoft Graph API (lightweight HTTP)."""

from __future__ import annotations

import requests

from .. import auth

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def list_sections(notebook_id: str) -> list[dict]:
    """List all sections in a notebook."""
    resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/notebooks/{notebook_id}/sections",
        headers=auth.get_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [_section_to_dict(sec) for sec in data.get("value", [])]


def create_section(notebook_id: str, display_name: str) -> dict:
    """Create a new section in a notebook."""
    resp = requests.post(
        f"{GRAPH_BASE}/me/onenote/notebooks/{notebook_id}/sections",
        headers=auth.get_headers(),
        json={"displayName": display_name},
        timeout=30,
    )
    resp.raise_for_status()
    return _section_to_dict(resp.json())


def _section_to_dict(sec: dict) -> dict:
    """Normalize a section JSON response to a clean dict."""
    return {
        "id": sec.get("id"),
        "displayName": sec.get("displayName"),
        "createdDateTime": sec.get("createdDateTime"),
        "lastModifiedDateTime": sec.get("lastModifiedDateTime"),
    }
