"""EchoLoop — Streamlit entry point.

This file is the root script that Streamlit runs (passed to ``streamlit run``).
It shows a brief welcome screen and lets Streamlit's sidebar navigation guide
the user to the two pages inside the ``pages/`` folder:

- **Add Card** — generate and persist a new German flashcard.
- **Review**   — interactive spaced-repetition review session.
"""

from __future__ import annotations

import streamlit as st

from echoloop.ui.styles import inject_styles

st.set_page_config(page_title="EchoLoop", page_icon="🔁", layout="centered")
inject_styles()

st.markdown(
    """
    <div class="hero">
        <h1>🔁 EchoLoop</h1>
        <p>Your AI-powered German ↔ English flashcard generator</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

col_add, col_review = st.columns(2)
with col_add:
    st.page_link("pages/add_card.py", label="➕ Add Card", use_container_width=True)
with col_review:
    st.page_link("pages/review.py", label="📖 Review", use_container_width=True)
