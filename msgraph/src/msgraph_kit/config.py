"""Load configuration from .env file."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Walk up from this file to find .env at the repo root
_repo_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_repo_root / ".env")

CLIENT_ID: str = os.environ.get("MSGRAPH_CLIENT_ID", "")
TENANT_ID: str = os.environ.get("MSGRAPH_TENANT_ID", "common")

# Where to store auth artifacts (non-sensitive account record)
AUTH_DIR: Path = Path.home() / ".msgraph-kit"

# Microsoft Graph scopes for OneNote
SCOPES: list[str] = [
    "User.Read",
    "Notes.Read",
    "Notes.ReadWrite",
    "Notes.Create",
]


def validate() -> None:
    """Raise if required config is missing."""
    if not CLIENT_ID:
        raise SystemExit(
            "MSGRAPH_CLIENT_ID not set. "
            "Copy .env.example to .env and fill in your Azure app registration values. "
            "See references/azure-setup.md for help."
        )
