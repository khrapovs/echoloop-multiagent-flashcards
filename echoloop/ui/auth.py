"""Authentication and access control utilities for the EchoLoop UI using Google SSO."""

import os
import urllib.parse

import requests
import streamlit as st


def get_redirect_uri() -> str:
    """Construct the redirect URI dynamically based on the request headers."""
    headers = st.context.headers
    proto = headers.get("x-forwarded-proto", "http")
    host = headers.get("host", "localhost:8501")
    return f"{proto}://{host}/"


def verify_email_whitelist(email: str) -> bool:
    """Check if the given email is present in the ALLOWED_EMAILS environment variable."""
    allowed_emails_raw = os.getenv("ALLOWED_EMAILS")
    if not allowed_emails_raw:
        # If not configured, allow access (defaults to open for local development)
        return True

    allowed_emails = [e.strip().lower() for e in allowed_emails_raw.split(",") if e.strip()]
    return email.lower() in allowed_emails


def enforce_google_sso() -> None:
    """Enforce Google SSO authentication on the current Streamlit page.

    Checks if the user has an active session. If not, it either handles
    the incoming OAuth2 callback code or displays a Google login button.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    # If OAuth is not configured, bypass authentication (useful for local development)
    if not client_id or not client_secret:
        st.sidebar.warning("OAuth credentials not configured. Auth bypassed.")
        return

    # 1. User is already authenticated in this session
    if "auth_email" in st.session_state:
        st.sidebar.markdown(f"👤 **Logged in as:**\n`{st.session_state['auth_email']}`")
        if st.sidebar.button("Log out"):
            del st.session_state["auth_email"]
            st.rerun()
        return

    redirect_uri = get_redirect_uri()

    # 2. Check for OAuth callback code in query parameters
    query_params = st.query_params
    code = query_params.get("code")

    if code:
        with st.spinner("Authenticating with Google..."):
            try:
                # Exchange auth code for access token
                token_url = "https://oauth2.googleapis.com/token"
                token_data = {
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
                token_resp = requests.post(token_url, data=token_data, timeout=10)
                token_resp.raise_for_status()
                token_json = token_resp.json()
                access_token = token_json.get("access_token")

                if not access_token:
                    st.error("Failed to retrieve access token from Google.", icon="🚫")
                    st.stop()

                # Retrieve user email using the access token
                userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
                userinfo_headers = {"Authorization": f"Bearer {access_token}"}
                userinfo_resp = requests.get(userinfo_url, headers=userinfo_headers, timeout=10)
                userinfo_resp.raise_for_status()
                userinfo_json = userinfo_resp.json()
                email = userinfo_json.get("email")

                if not email:
                    st.error("Could not retrieve email address from Google profile.", icon="🚫")
                    st.stop()

                # Verify whitelist access
                if verify_email_whitelist(email):
                    st.session_state["auth_email"] = email
                    # Clear query params to make the URL clean
                    st.query_params.clear()
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error(f"Access Denied: Email '{email}' is not whitelisted.", icon="🚫")
                    st.stop()

            except Exception as exc:
                st.error(f"Authentication error: {exc}", icon="🚫")
                st.stop()

    # 3. Render Google Login Button (unauthenticated state)
    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "access_type": "online",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(auth_params)}"

    st.markdown(
        """
        <div class="login-container">
            <h3>🔐 Private Demonstration Service</h3>
            <p style="color:#9CA3AF; font-size:0.95rem;">
                This deployment is private. Please sign in with your Google account to access EchoLoop.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render a link styled as a Google Login Button
    st.markdown(
        f'<div style="text-align:center;"><a class="login-btn" href="{auth_url}">🔑 Sign in with Google</a></div>',
        unsafe_allow_html=True,
    )
    st.stop()
