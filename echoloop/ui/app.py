"""EchoLoop — Streamlit frontend.

Entry point:
    uv run echoloop
"""

import streamlit as st

from echoloop.constants import _DB_PATH
from echoloop.storage.adapter import CardStore
from echoloop.ui.styles import inject_styles

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(page_title="EchoLoop", page_icon="🔁", layout="centered")

inject_styles()

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
