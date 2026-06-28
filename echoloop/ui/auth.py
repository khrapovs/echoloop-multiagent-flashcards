"""Authentication and access control utilities for the EchoLoop UI."""

import os

import streamlit as st


def verify_ip_access() -> bool:
    """Check if the client's IP address matches the ALLOWED_IPS whitelist.

    Whitelist is configured via the ``ALLOWED_IPS`` environment variable
    (comma-separated).  If the variable is not set, access is granted
    (defaults to open for local development).

    Extracts the client's public IP address from the ``X-Forwarded-For``
    header supplied by the Google Cloud Run front-end proxy.

    Returns:
        ``True`` if access is permitted, ``False`` if forbidden.

    """
    allowed_ips_raw = os.getenv("ALLOWED_IPS")
    if not allowed_ips_raw:
        return True

    # Extract client IP (first entry in X-Forwarded-For chain)
    headers = st.context.headers
    forwarded_for = headers.get("X-Forwarded-For", "")
    if not forwarded_for:
        return False

    client_ip = forwarded_for.split(",")[0].strip()
    allowed_ips = [ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()]

    return client_ip in allowed_ips


def enforce_ip_access() -> None:
    """Enforce IP access control on the current Streamlit page.

    Halts execution with a warning banner if the client IP is not
    whitelisted.
    """
    if not verify_ip_access():
        st.error("Access Forbidden: Your IP is not whitelisted.", icon="🚫")
        st.stop()
