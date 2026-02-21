"""OneNote notebook operations via Microsoft Graph API (lightweight HTTP)."""

from __future__ import annotations

import requests

from .. import auth

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def list_notebooks() -> list[dict]:
    """List all notebooks for the authenticated user."""
    resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/notebooks",
        headers=auth.get_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [_notebook_to_dict(nb) for nb in data.get("value", [])]


def get_notebook(notebook_id: str) -> dict:
    """Get a single notebook by ID."""
    resp = requests.get(
        f"{GRAPH_BASE}/me/onenote/notebooks/{notebook_id}",
        headers=auth.get_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return _notebook_to_dict(resp.json())


def create_notebook(display_name: str) -> dict:
    """Create a new notebook."""
    resp = requests.post(
        f"{GRAPH_BASE}/me/onenote/notebooks",
        headers=auth.get_headers(),
        json={"displayName": display_name},
        timeout=30,
    )
    resp.raise_for_status()
    return _notebook_to_dict(resp.json())


def _notebook_to_dict(nb: dict) -> dict:
    """Normalize a notebook JSON response to a clean dict."""
    return {
        "id": nb.get("id"),
        "displayName": nb.get("displayName"),
        "createdDateTime": nb.get("createdDateTime"),
        "lastModifiedDateTime": nb.get("lastModifiedDateTime"),
        "isShared": nb.get("isShared"),
        "selfUrl": nb.get("self"),
    }
