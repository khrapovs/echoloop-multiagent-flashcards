"""Style injection helper for the EchoLoop Streamlit UI."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "styles.css"


def inject_styles() -> None:
    """Read styles.css and inject it into the Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
