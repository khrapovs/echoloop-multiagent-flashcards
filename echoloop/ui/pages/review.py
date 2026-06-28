"""EchoLoop — Interactive Session-based Review page.

Pattern
-------
1. On session start, load all due cards (next_review_date <= today) into
   st.session_state so the queue is stable across reruns.
2. Show the current card's German word and wait for the user to recall.
3. After the user reveals the answer, display translation + example sentence.
4. Present a 0-5 rating row; on rating, update SM-2 fields + write a review
   record, then advance to the next card.
5. When the queue is exhausted, show a session-complete summary.
"""

import datetime

import streamlit as st
from echoloop.constants import _DB_PATH
from echoloop.repetition_engine import RepetitionEngine
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card, Review
from echoloop.ui.auth import enforce_ip_access
from echoloop.ui.styles import inject_styles

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Review", page_icon="🔁", layout="centered")


enforce_ip_access()

inject_styles()


# ---------------------------------------------------------------------------
# Shared store (cached for the whole process)
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_store() -> CardStore:
    """Return the singleton CardStore."""
    return CardStore(db_path=str(_DB_PATH))


store = _get_store()
engine = RepetitionEngine(store=store)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_RATING_LABELS: dict[int, str] = {
    0: "0 — Blackout",
    1: "1 — Wrong",
    2: "2 — Hard",
    3: "3 — OK",
    4: "4 — Good",
    5: "5 — Easy",
}

_RATING_COLORS: dict[int, str] = {
    0: "#EF4444",
    1: "#F97316",
    2: "#EAB308",
    3: "#84CC16",
    4: "#22C55E",
    5: "#10B981",
}


def _load_due_cards() -> list[Card]:
    """Return cards whose next_review_date is today or earlier."""
    today = datetime.date.today()
    return [c for c in store.list_cards() if c.next_review_date <= today]


def _init_session() -> None:
    """Populate session_state for a fresh review session."""
    due = _load_due_cards()
    st.session_state.review_queue = due
    st.session_state.review_index = 0
    st.session_state.revealed = False
    st.session_state.session_reviewed = 0


# ---------------------------------------------------------------------------
# Initialise (or restart) the session
# ---------------------------------------------------------------------------
if "review_queue" not in st.session_state:
    _init_session()

queue: list[Card] = st.session_state.review_queue
idx: int = st.session_state.review_index

# ---------------------------------------------------------------------------
# No cards at all
# ---------------------------------------------------------------------------
total_cards = len(store.list_cards())
if total_cards == 0:
    st.info(
        "You haven't added any cards yet. Go to the **Add Card** page and enter your first German word!",
        icon="📭",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Session complete (queue exhausted)
# ---------------------------------------------------------------------------
if idx >= len(queue):
    reviewed = st.session_state.get("session_reviewed", 0)
    next_cards = _load_due_cards()
    st.markdown(
        f"""
        <div class="session-complete">
            <h2>🎉 Session complete!</h2>
            <p>You reviewed <strong>{reviewed}</strong> card{"s" if reviewed != 1 else ""} today.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if next_cards:
        st.info(
            f"There {'are' if len(next_cards) != 1 else 'is'} still "
            f"**{len(next_cards)}** card{'s' if len(next_cards) != 1 else ''} due. "
            "Start a new session?"
        )
        if st.button("▶ Start new session", type="primary"):
            _init_session()
            st.rerun()
    else:
        remaining = len(store.list_cards()) - reviewed
        st.success(
            f"All caught up! Come back tomorrow — you have "
            f"**{total_cards}** card{'s' if total_cards != 1 else ''} in your deck.",
            icon="✅",
        )
    st.stop()

# ---------------------------------------------------------------------------
# Nothing due today
# ---------------------------------------------------------------------------
if not queue:
    st.success(
        f"Nothing due today! 🎉 You have **{total_cards}** "
        f"card{'s' if total_cards != 1 else ''} in your deck — check back tomorrow.",
        icon="✅",
    )
    st.stop()

# ---------------------------------------------------------------------------
# Active review
# ---------------------------------------------------------------------------
card = queue[idx]
progress = idx / len(queue)

st.progress(progress, text=f"Card {idx + 1} of {len(queue)}")

# ── Word prompt ──────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="review-word">{card.word}</div>
    <div class="review-hint">What does this word mean?</div>
    """,
    unsafe_allow_html=True,
)

# ── Reveal button ────────────────────────────────────────────────────────────
if not st.session_state.revealed:
    if st.button("👁 Reveal answer", use_container_width=True):
        st.session_state.revealed = True
        st.rerun()
    st.stop()

# ── Answer card ──────────────────────────────────────────────────────────────
examples = store.get_examples_for_card(card.id) if card.id is not None else []

example_html = ""

if len(examples) > 0:
    ex = examples[0]
    example_html = (
        f'<div class="fc-section-label">Example sentence</div>'
        f'<div class="fc-sentence-de">🇩🇪 {ex.sentence}</div>'
        f'<div class="fc-sentence-en">🇬🇧 {ex.translation}</div>'
    )

st.markdown(
    f"""
    <div class="review-answer">
        <div class="cefr-badge">{card.detected_level}</div>
        <div class="review-translation">{card.translation}</div>
        {example_html}
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Rating buttons ───────────────────────────────────────────────────────────
st.markdown('<div class="rating-label">How well did you remember?</div>', unsafe_allow_html=True)

cols = st.columns(6)
for score, col in enumerate(cols):
    with col:
        if st.button(_RATING_LABELS[score], key=f"rate_{score}", use_container_width=True, help=f"Score {score}"):
            # Compute new SM-2 metrics and persist.
            metrics = engine.calculate_next_review(card, review_score=score)
            updated = card.model_copy(
                update={
                    "easiness_factor": metrics.easiness_factor,
                    "interval_days": metrics.interval_days,
                    "repetitions": metrics.repetitions,
                    "next_review_date": metrics.next_review_date,
                }
            )
            store.update_card(updated)
            if card.id is not None:
                store.insert_review(Review(card_id=card.id, rating_score=score))

            # Advance the queue.
            st.session_state.review_index += 1
            st.session_state.session_reviewed += 1
            st.session_state.revealed = False
            st.rerun()
