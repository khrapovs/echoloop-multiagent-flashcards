"""EchoLoop — Streamlit frontend.

Entry point:
    uv run echoloop
"""

import streamlit as st

from echoloop.constants import _DB_PATH
from echoloop.storage.adapter import CardStore

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
    .hero { text-align: center; padding: 2.5rem 0 1rem; }
    .hero h1 {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6C63FF 0%, #48C8E8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .hero p { font-size: 1.05rem; color: #9CA3AF; margin-top: 0; }

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

    /* ── Flashcard container ────────────────────────────────────────────── */
    .flashcard {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border: 1.5px solid #6C63FF44;
        border-radius: 20px;
        padding: 2rem 2.2rem;
        margin-top: 1.5rem;
        box-shadow: 0 8px 32px #6C63FF18;
        animation: fadeSlideIn 0.4s ease;
    }
    @keyframes fadeSlideIn {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Word + translation headline */
    .fc-headline {
        display: flex;
        align-items: baseline;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin-bottom: 0.4rem;
    }
    .fc-word  { font-size: 2.2rem; font-weight: 700; color: #ffffff; }
    .fc-translation { font-size: 1.25rem; color: #9CA3AF; font-style: italic; }

    /* CEFR badge */
    .cefr-badge {
        display: inline-block;
        background: linear-gradient(135deg, #6C63FF, #48C8E8);
        border-radius: 8px;
        padding: 0.2rem 0.7rem;
        font-size: 0.85rem;
        font-weight: 700;
        color: #fff;
        letter-spacing: 0.06em;
        margin-bottom: 1.2rem;
    }

    /* Example sentences */
    .fc-section-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #6C63FF;
        margin-bottom: 0.3rem;
    }
    .fc-sentence-de { font-size: 1.1rem; color: #e2e8f0; margin-bottom: 0.15rem; }
    .fc-sentence-en { font-size: 0.95rem; color: #9CA3AF; font-style: italic; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Database — initialise once per process, shared across all reruns
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_store():
    """Return the singleton CardStore (created once, reused across reruns)."""
    return CardStore(db_path=str(_DB_PATH))


store = _get_store()

# ---------------------------------------------------------------------------
# Hero header + card counter
# ---------------------------------------------------------------------------
total_cards = len(store.list_cards())

st.markdown(
    """
    <div class="hero">
        <h1>🔁 EchoLoop</h1>
        <p>Your AI-powered German ↔ English flashcard generator</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if total_cards:
    st.caption(f"📚 {total_cards} card{'s' if total_cards != 1 else ''} saved in your deck")

st.divider()

# ---------------------------------------------------------------------------
# Word input form
# ---------------------------------------------------------------------------
with st.form(key="word_form", clear_on_submit=True):
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
        with st.spinner(f"Generating flashcard for **{word}** …"):
            try:
                from echoloop.runner import run_context_agent  # noqa: PLC0415
                from echoloop.storage.models import Card, Example  # noqa: PLC0415

                flashcard = run_context_agent(word)
            except Exception as exc:
                st.error(f"Failed to generate flashcard: {exc}", icon="❌")
                st.stop()

        # Persist the card (or skip silently if the word already exists).
        existing = store.get_card_by_word(flashcard.word)
        if existing is None:
            saved_card = store.insert_card(
                Card(
                    word=flashcard.word,
                    translation=flashcard.translation,
                    detected_level=flashcard.detected_level,
                )
            )
            store.insert_example(
                Example(
                    card_id=saved_card.id,
                    sentence=flashcard.example_sentence_german,
                    translation=flashcard.example_sentence_english,
                )
            )
            save_label = "✅ Saved to your deck"
        else:
            save_label = "ℹ️ Already in your deck"

        # Render the flashcard.
        st.markdown(
            f"""
            <div class="flashcard">
                <div class="fc-headline">
                    <span class="fc-word">{flashcard.word}</span>
                    <span class="fc-translation">{flashcard.translation}</span>
                </div>
                <div class="cefr-badge">{flashcard.detected_level}</div>
                <div class="fc-section-label">Example sentence</div>
                <div class="fc-sentence-de">🇩🇪 {flashcard.example_sentence_german}</div>
                <div class="fc-sentence-en">🇬🇧 {flashcard.example_sentence_english}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.success(save_label)
