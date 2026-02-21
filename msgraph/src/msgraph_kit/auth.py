"""Shared authentication for Microsoft Graph.

Uses DeviceCodeCredential with persistent token caching
and AuthenticationRecord persistence for silent re-authentication.
Provides a lightweight get_token() for direct HTTP calls (no SDK needed).
"""

import json
import sys
from pathlib import Path

from azure.identity import AuthenticationRecord, DeviceCodeCredential, TokenCachePersistenceOptions

from . import config

_AUTH_RECORD_PATH = config.AUTH_DIR / "auth_record.json"


def _load_auth_record() -> AuthenticationRecord | None:
    """Load a previously saved AuthenticationRecord, if any."""
    if not _AUTH_RECORD_PATH.exists():
        return None
    try:
        data = _AUTH_RECORD_PATH.read_text()
        return AuthenticationRecord.deserialize(data)
    except Exception:
        return None


def _save_auth_record(record: AuthenticationRecord) -> None:
    """Persist AuthenticationRecord for future silent auth."""
    config.AUTH_DIR.mkdir(parents=True, exist_ok=True)
    _AUTH_RECORD_PATH.write_text(record.serialize())


def _make_credential(
    *,
    disable_automatic_authentication: bool = False,
) -> DeviceCodeCredential:
    """Build a DeviceCodeCredential with token cache and optional saved record."""
    cache_options = TokenCachePersistenceOptions(
        name="msgraph-kit", allow_unencrypted_storage=True
    )
    auth_record = _load_auth_record()

    kwargs: dict = {
        "client_id": config.CLIENT_ID,
        "tenant_id": config.TENANT_ID,
        "cache_persistence_options": cache_options,
        "disable_automatic_authentication": disable_automatic_authentication,
    }
    if auth_record:
        kwargs["authentication_record"] = auth_record

    return DeviceCodeCredential(**kwargs)


def authenticate() -> AuthenticationRecord:
    """Run the device code flow interactively and persist the result.

    Prints the device code prompt to stderr so Kit can show it to the user.
    Returns the AuthenticationRecord on success.
    """
    config.validate()

    def prompt_callback(verification_uri: str, user_code: str, expires_on) -> None:
        print(
            f"\nTo sign in, open: {verification_uri}\n"
            f"Enter the code: {user_code}\n",
            file=sys.stderr,
        )

    cache_options = TokenCachePersistenceOptions(
        name="msgraph-kit", allow_unencrypted_storage=True
    )
    credential = DeviceCodeCredential(
        client_id=config.CLIENT_ID,
        tenant_id=config.TENANT_ID,
        cache_persistence_options=cache_options,
        prompt_callback=prompt_callback,
    )

    record = credential.authenticate(scopes=config.SCOPES)
    _save_auth_record(record)
    return record


def check_auth_status() -> dict:
    """Check whether we can authenticate silently.

    Returns a dict with 'authenticated' bool and details.
    """
    auth_record = _load_auth_record()
    if not auth_record:
        return {"authenticated": False, "reason": "No saved authentication record. Run auth_login.py first."}

    try:
        credential = _make_credential(disable_automatic_authentication=True)
        credential.get_token(*config.SCOPES)
        return {
            "authenticated": True,
            "username": auth_record.username,
            "tenant_id": auth_record.tenant_id,
            "authority": auth_record.authority,
        }
    except Exception as exc:
        return {
            "authenticated": False,
            "reason": f"Token expired or invalid: {exc}. Run auth_login.py to re-authenticate.",
            "username": auth_record.username,
        }


def get_token() -> str:
    """Get a valid access token string for direct HTTP calls."""
    config.validate()
    credential = _make_credential()
    token = credential.get_token(*config.SCOPES)
    return token.token


def get_headers() -> dict[str, str]:
    """Get Authorization headers for Graph API HTTP requests."""
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }


def logout() -> None:
    """Remove the saved authentication record."""
    if _AUTH_RECORD_PATH.exists():
        _AUTH_RECORD_PATH.unlink()
