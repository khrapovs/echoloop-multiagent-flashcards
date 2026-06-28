"""Unit tests for UI IP access control (auth.py)."""

from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from echoloop.ui.auth import verify_ip_access


@pytest.fixture()
def clean_env() -> Iterator[None]:
    """Ensure ALLOWED_IPS is not set in environment during test."""
    old_val = os.environ.get("ALLOWED_IPS")
    if "ALLOWED_IPS" in os.environ:
        del os.environ["ALLOWED_IPS"]
    yield
    if old_val is not None:
        os.environ["ALLOWED_IPS"] = old_val


# Mark all tests in this module to automatically use the clean_env fixture
pytestmark = pytest.mark.usefixtures("clean_env")


def _mock_context(headers: dict[str, str]) -> MagicMock:
    """Build a mock streamlit.context object."""
    mock_ctx = MagicMock()
    mock_ctx.headers = headers
    return mock_ctx


def test_allows_all_when_no_env_configured() -> None:
    """If ALLOWED_IPS is not defined, verify_ip_access should return True (local dev)."""
    assert verify_ip_access() is True


def test_denies_access_if_header_missing() -> None:
    """If ALLOWED_IPS is set but header is missing, deny access."""
    os.environ["ALLOWED_IPS"] = "192.168.1.1"
    mock_ctx = _mock_context({})
    with patch("streamlit.context", mock_ctx):
        assert verify_ip_access() is False


def test_allows_access_if_client_ip_matches_whitelisted() -> None:
    """If client IP matches a single whitelist entry, allow access."""
    os.environ["ALLOWED_IPS"] = "1.2.3.4"
    mock_ctx = _mock_context({"X-Forwarded-For": "1.2.3.4"})
    with patch("streamlit.context", mock_ctx):
        assert verify_ip_access() is True


def test_allows_access_with_multiple_ips_whitelisted() -> None:
    """Test matching against multiple comma-separated whitelisted IPs."""
    os.environ["ALLOWED_IPS"] = "1.2.3.4, 5.6.7.8, 10.11.12.13"
    mock_ctx = _mock_context({"X-Forwarded-For": "5.6.7.8"})
    with patch("streamlit.context", mock_ctx):
        assert verify_ip_access() is True


def test_denies_access_if_client_ip_not_whitelisted() -> None:
    """If client IP does not match any entry, deny access."""
    os.environ["ALLOWED_IPS"] = "1.2.3.4, 5.6.7.8"
    mock_ctx = _mock_context({"X-Forwarded-For": "9.9.9.9"})
    with patch("streamlit.context", mock_ctx):
        assert verify_ip_access() is False


def test_extracts_first_ip_from_proxy_chain() -> None:
    """Google Cloud Front-ends append IPs to X-Forwarded-For. Verify we grab the first (client)."""
    os.environ["ALLOWED_IPS"] = "1.2.3.4"
    # Proxy chain: Client, Proxy1, Proxy2
    mock_ctx = _mock_context({"X-Forwarded-For": "1.2.3.4, 35.190.0.1, 130.211.0.2"})
    with patch("streamlit.context", mock_ctx):
        assert verify_ip_access() is True
