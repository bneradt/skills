"""OneNote notebook operations via Microsoft Graph API."""

from __future__ import annotations

from msgraph import GraphServiceClient
from msgraph.generated.models.notebook import Notebook


async def list_notebooks(client: GraphServiceClient) -> list[dict]:
    """List all notebooks for the authenticated user."""
    result = await client.me.onenote.notebooks.get()
    notebooks = []
    if result and result.value:
        for nb in result.value:
            notebooks.append(_notebook_to_dict(nb))
    return notebooks


async def get_notebook(client: GraphServiceClient, notebook_id: str) -> dict:
    """Get a single notebook by ID."""
    nb = await client.me.onenote.notebooks.by_notebook_id(notebook_id).get()
    return _notebook_to_dict(nb)


async def create_notebook(client: GraphServiceClient, display_name: str) -> dict:
    """Create a new notebook."""
    body = Notebook(display_name=display_name)
    nb = await client.me.onenote.notebooks.post(body)
    return _notebook_to_dict(nb)


def _notebook_to_dict(nb: Notebook) -> dict:
    """Convert a Notebook model to a plain dict."""
    return {
        "id": nb.id,
        "displayName": nb.display_name,
        "createdDateTime": nb.created_date_time.isoformat() if nb.created_date_time else None,
        "lastModifiedDateTime": nb.last_modified_date_time.isoformat() if nb.last_modified_date_time else None,
        "isShared": nb.is_shared,
        "selfUrl": nb.self_ if hasattr(nb, "self_") else None,
    }
