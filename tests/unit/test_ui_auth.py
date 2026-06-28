"""Unit tests for Google SSO access control (auth.py)."""

import os
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from echoloop.ui.auth import enforce_google_sso, get_redirect_uri, verify_email_whitelist


@pytest.fixture()
def clean_env() -> Iterator[None]:
    """Ensure environment is clean of OAuth settings before each test."""
    old_env = {k: os.environ.get(k) for k in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ALLOWED_EMAILS"]}
    for k in old_env:
        if k in os.environ:
            del os.environ[k]
    yield
    for k, v in old_env.items():
        if v is not None:
            os.environ[k] = v


@pytest.fixture()
def clean_session() -> Iterator[dict]:
    """Provide a clean session state dictionary."""
    session = {}
    with patch("streamlit.session_state", session):
        yield session


# Mark all tests in this module to automatically use the clean_env fixture
pytestmark = pytest.mark.usefixtures("clean_env")


def _mock_context(headers: dict[str, str]) -> MagicMock:
    """Build a mock streamlit.context object."""
    mock_ctx = MagicMock()
    mock_ctx.headers = headers
    return mock_ctx


# ---------------------------------------------------------------------------
# get_redirect_uri
# ---------------------------------------------------------------------------


class TestGetRedirectUri:
    def test_local_default_uri(self) -> None:
        mock_ctx = _mock_context({"host": "localhost:8501"})
        with patch("streamlit.context", mock_ctx):
            assert get_redirect_uri() == "http://localhost:8501/"

    def test_production_forwarded_headers(self) -> None:
        mock_ctx = _mock_context({
            "x-forwarded-proto": "https",
            "host": "echoloop-ui-xxxx.a.run.app",
        })
        with patch("streamlit.context", mock_ctx):
            assert get_redirect_uri() == "https://echoloop-ui-xxxx.a.run.app/"


# ---------------------------------------------------------------------------
# verify_email_whitelist
# ---------------------------------------------------------------------------


class TestVerifyEmailWhitelist:
    def test_allows_all_when_no_env_set(self) -> None:
        assert verify_email_whitelist("any@gmail.com") is True

    def test_allows_matching_email(self) -> None:
        os.environ["ALLOWED_EMAILS"] = "test@gmail.com"
        assert verify_email_whitelist("test@gmail.com") is True

    def test_allows_matching_case_insensitive(self) -> None:
        os.environ["ALLOWED_EMAILS"] = "TEST@gmail.com"
        assert verify_email_whitelist("test@gmail.com") is True

    def test_denies_unlisted_email(self) -> None:
        os.environ["ALLOWED_EMAILS"] = "allowed@gmail.com"
        assert verify_email_whitelist("hacker@gmail.com") is False

    def test_matches_in_multiple_whitelisted_emails(self) -> None:
        os.environ["ALLOWED_EMAILS"] = "friend1@gmail.com, friend2@gmail.com, me@gmail.com"
        assert verify_email_whitelist("me@gmail.com") is True


# ---------------------------------------------------------------------------
# enforce_google_sso
# ---------------------------------------------------------------------------


class TestEnforceGoogleSSO:
    def test_bypasses_auth_if_credentials_missing(self, clean_session: dict) -> None:
        """If GOOGLE_CLIENT_ID is missing, bypass authorization (for dev)."""
        with patch("streamlit.sidebar") as mock_sidebar:
            enforce_google_sso()
        mock_sidebar.warning.assert_called_once()
        assert "auth_email" not in clean_session

    def test_allows_already_authenticated_user(self, clean_session: dict) -> None:
        """If auth_email is in session_state, let the page load without redirecting."""
        os.environ["GOOGLE_CLIENT_ID"] = "client123"
        os.environ["GOOGLE_CLIENT_SECRET"] = "secret123"
        clean_session["auth_email"] = "me@gmail.com"

        with patch("streamlit.sidebar") as mock_sidebar:
            enforce_google_sso()

        mock_sidebar.markdown.assert_called_once_with("👤 **Logged in as:**\n`me@gmail.com`")

    def test_handles_successful_oauth_callback(self, clean_session: dict) -> None:
        """If code param is in url, exchange it and authenticate the user."""
        os.environ["GOOGLE_CLIENT_ID"] = "client123"
        os.environ["GOOGLE_CLIENT_SECRET"] = "secret123"
        os.environ["ALLOWED_EMAILS"] = "user@gmail.com"

        # Mock Streamlit URL query parameters
        mock_query = {"code": "authcode123"}
        # Mock requests.post (token exchange) and requests.get (userinfo email lookup)
        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"access_token": "token123"}
        mock_get_resp = MagicMock()
        mock_get_resp.json.return_value = {"email": "user@gmail.com"}

        mock_ctx = _mock_context({"host": "localhost:8501"})

        with (
            patch("streamlit.query_params", mock_query),
            patch("streamlit.context", mock_ctx),
            patch("requests.post", return_value=mock_post_resp) as mock_post,
            patch("requests.get", return_value=mock_get_resp) as mock_get,
            patch("streamlit.rerun") as mock_rerun,
        ):
            enforce_google_sso()

        # Token exchange called with code
        mock_post.assert_called_once()
        # Profile lookup called with header token
        mock_get.assert_called_once()
        assert clean_session.get("auth_email") == "user@gmail.com"
        mock_rerun.assert_called_once()

    def test_redirects_unauthenticated_user_to_login(self, clean_session: dict) -> None:
        """If unauthenticated and no code callback, draw the Google Login redirect button."""
        os.environ["GOOGLE_CLIENT_ID"] = "client123"
        os.environ["GOOGLE_CLIENT_SECRET"] = "secret123"

        mock_query = {}
        mock_ctx = _mock_context({"host": "localhost:8501"})

        with (
            patch("streamlit.query_params", mock_query),
            patch("streamlit.context", mock_ctx),
            patch("streamlit.stop") as mock_stop,
        ):
            enforce_google_sso()

        mock_stop.assert_called_once()
        assert "auth_email" not in clean_session
