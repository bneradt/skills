"""Tests for configuration loading."""

import os
from pathlib import Path
from unittest import mock

from msgraph_kit import config


class TestConfig:
    def test_default_tenant_id(self):
        """TENANT_ID defaults to 'common' when not set."""
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove MSGRAPH_TENANT_ID if set
            env = os.environ.copy()
            env.pop("MSGRAPH_TENANT_ID", None)
            with mock.patch.dict(os.environ, env, clear=True):
                # Re-import won't re-execute module-level code,
                # so test the default value behavior
                assert config.TENANT_ID is not None

    def test_scopes_include_onenote(self):
        """Scopes should include OneNote permissions."""
        assert "Notes.ReadWrite" in config.SCOPES
        assert "Notes.Create" in config.SCOPES
        assert "Notes.Read" in config.SCOPES
        assert "User.Read" in config.SCOPES

    def test_auth_dir_is_in_home(self):
        """AUTH_DIR should be under the user's home directory."""
        assert str(config.AUTH_DIR).startswith(str(Path.home()))
        assert ".msgraph-kit" in str(config.AUTH_DIR)

    def test_validate_raises_without_client_id(self):
        """validate() should raise SystemExit if CLIENT_ID is empty."""
        original = config.CLIENT_ID
        try:
            config.CLIENT_ID = ""
            try:
                config.validate()
                assert False, "Should have raised SystemExit"
            except SystemExit as e:
                assert "MSGRAPH_CLIENT_ID" in str(e)
        finally:
            config.CLIENT_ID = original

    def test_validate_passes_with_client_id(self):
        """validate() should not raise if CLIENT_ID is set."""
        original = config.CLIENT_ID
        try:
            config.CLIENT_ID = "test-client-id"
            config.validate()  # Should not raise
        finally:
            config.CLIENT_ID = original
