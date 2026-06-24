"""EchoLoop — Streamlit frontend.

Entry point:
    uv run streamlit run echoloop/ui.py
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(page_title="EchoLoop", page_icon="🔁", layout="centered")

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── Global font ───────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Hero header ───────────────────────────────────────────────────── */
    .hero {
        text-align: center;
        padding: 2.5rem 0 1rem;
    }
    .hero h1 {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6C63FF 0%, #48C8E8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .hero p {
        font-size: 1.05rem;
        color: #9CA3AF;
        margin-top: 0;
    }

    /* ── Word input box ─────────────────────────────────────────────────── */
    div[data-testid="stTextInput"] > div > div > input {
        font-size: 1.3rem;
        padding: 0.8rem 1.1rem;
        border-radius: 12px;
        border: 2px solid #6C63FF44;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stTextInput"] > div > div > input:focus {
        border-color: #6C63FF;
        box-shadow: 0 0 0 3px #6C63FF22;
    }

    /* ── Primary button ─────────────────────────────────────────────────── */
    div[data-testid="stButton"] > button[kind="primary"] {
        width: 100%;
        padding: 0.75rem;
        font-size: 1.05rem;
        font-weight: 600;
        border-radius: 12px;
        background: linear-gradient(135deg, #6C63FF, #48C8E8);
        border: none;
        color: white;
        transition: opacity 0.15s ease, transform 0.1s ease;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        opacity: 0.88;
        transform: translateY(-1px);
    }

    /* ── Submitted word badge ───────────────────────────────────────────── */
    .word-badge {
        display: inline-block;
        background: linear-gradient(135deg, #6C63FF22, #48C8E822);
        border: 1.5px solid #6C63FF55;
        border-radius: 24px;
        padding: 0.45rem 1.2rem;
        font-size: 1.4rem;
        font-weight: 600;
        color: #6C63FF;
        letter-spacing: 0.03em;
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Word input form
# ---------------------------------------------------------------------------
with st.form(key="word_form", clear_on_submit=False):
    word = st.text_input(
        label="German word",
        placeholder="e.g. Hund, Katze, Freundschaft …",
        help="Type any German word and press **Generate** to create a flashcard.",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Generate flashcard ✨", type="primary")

# ---------------------------------------------------------------------------
# Result area
# ---------------------------------------------------------------------------
if submitted:
    word = word.strip()
    if not word:
        st.warning("Please enter a German word before generating.", icon="⚠️")
    else:
        st.markdown(
            f'<div style="text-align:center">Word submitted:<br><span class="word-badge">{word}</span></div>',
            unsafe_allow_html=True,
        )
        st.info("Flashcard generation will appear here in the next iteration.", icon="🚧")
