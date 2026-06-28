"""EchoLoop — Add Card page.

Three-phase user journey
------------------------
Phase 1  (input)   — User enters a German word and submits.
Phase 2  (select)  — SynonymsAgent runs; user checks/unchecks candidate words.
Phase 3  (results) — AgentPipeline generates cards one-by-one; summary shown.
"""

import streamlit as st
from echoloop.constants import _DB_PATH
from echoloop.pipeline import AgentPipeline, FlashcardResult
from echoloop.repetition_engine import RepetitionEngine
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card, Example
from echoloop.ui.styles import inject_styles

# ---------------------------------------------------------------------------
# Page config — must be the very first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(page_title="EchoLoop · Add Card", page_icon="➕", layout="centered")
inject_styles()


# ---------------------------------------------------------------------------
# Shared singletons (created once per process)
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_store() -> CardStore:
    return CardStore(db_path=str(_DB_PATH))


@st.cache_resource
def _get_pipeline() -> AgentPipeline:
    store = _get_store()
    engine = RepetitionEngine(store=store)
    return AgentPipeline(store=store, engine=engine)


store = _get_store()
pipeline = _get_pipeline()

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------
if "ac_phase" not in st.session_state:
    st.session_state.ac_phase = "input"  # "input" | "select" | "results"
if "ac_word" not in st.session_state:
    st.session_state.ac_word = ""
if "ac_candidates" not in st.session_state:
    st.session_state.ac_candidates: list[str] = []
if "ac_results" not in st.session_state:
    st.session_state.ac_results: list[FlashcardResult] = []

# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
total_cards = len(store.list_cards())
st.markdown(
    """
    <div class="hero">
        <h2>Add words to your deck</h2>
    </div>
    """,
    unsafe_allow_html=True,
)
if total_cards:
    st.caption(f"📚 {total_cards} card{'s' if total_cards != 1 else ''} in your deck")
st.divider()

# ---------------------------------------------------------------------------
# ── Phase 1: word input ──────────────────────────────────────────────────────
# ---------------------------------------------------------------------------
if st.session_state.ac_phase == "input":
    with st.form(key="word_form", clear_on_submit=False):
        word = st.text_input(
            label="German word",
            placeholder="e.g. Hund, Katze, Freundschaft …",
            help="Type any German word — EchoLoop will find synonyms and generate flashcards for each.",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Find synonyms ✨", type="primary")

    if submitted:
        word = word.strip()
        if not word:
            st.warning("Please enter a German word first.", icon="⚠️")
        else:
            with st.spinner(f"Looking up synonyms for **{word}** …"):
                try:
                    synonyms_output = pipeline.get_synonyms(word)
                except Exception as exc:
                    st.error(f"Failed to fetch synonyms: {exc}", icon="❌")
                    st.stop()

            # Build candidate list: original word first, then synonyms
            candidates = [synonyms_output.original_word] + [s.synonym_word for s in synonyms_output.synonyms]
            st.session_state.ac_word = synonyms_output.original_word
            st.session_state.ac_candidates = candidates
            st.session_state.ac_phase = "select"
            st.rerun()

# ---------------------------------------------------------------------------
# ── Phase 2: synonym checklist ───────────────────────────────────────────────
# ---------------------------------------------------------------------------
elif st.session_state.ac_phase == "select":
    word = st.session_state.ac_word
    candidates = st.session_state.ac_candidates

    st.markdown(f"### Words found for **{word}**")
    st.markdown(
        '<div class="synonym-header">Select the words you want flashcards for</div>',
        unsafe_allow_html=True,
    )

    # Render one checkbox per candidate; original word is checked and disabled
    selected: list[str] = []
    for i, candidate in enumerate(candidates):
        is_original = i == 0
        label = f"**{candidate}**" if is_original else candidate
        suffix = " *(original)*" if is_original else ""
        checked = st.checkbox(label + suffix, value=True, key=f"chk_{i}")
        if checked:
            selected.append(candidate)

    st.divider()
    col_generate, col_back = st.columns([3, 1])
    with col_generate:
        generate_clicked = st.button(
            f"Generate {len(selected)} flashcard{'s' if len(selected) != 1 else ''} ✨",
            type="primary",
            disabled=not selected,
            use_container_width=True,
        )
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.ac_phase = "input"
            st.rerun()

    if generate_clicked:
        st.session_state.ac_results = []
        st.session_state.ac_phase = "results"
        st.session_state.ac_selected = selected
        st.rerun()

# ---------------------------------------------------------------------------
# ── Phase 3: generate + stream results ───────────────────────────────────────
# ---------------------------------------------------------------------------
elif st.session_state.ac_phase == "results":
    selected: list[str] = st.session_state.get("ac_selected", [])
    existing_results: list[FlashcardResult] = st.session_state.ac_results

    st.markdown(f"### Generating flashcards for **{st.session_state.ac_word}**")

    # If we still have words left to process, run the next batch step.
    # We process results lazily: regenerate only when the stored results list
    # is shorter than the selected list (i.e., there are still words to do).
    if len(existing_results) < len(selected):
        progress_bar = st.progress(0, text="Starting …")
        cards_container = st.empty()

        # Stream all results at once, updating UI per card.
        all_results: list[FlashcardResult] = []
        for result in pipeline.generate_card_batch(selected):
            all_results.append(result)

            # Persist saved cards immediately.
            if result.status == "saved" and result.card is not None:
                fc = result.card
                saved = store.insert_card(
                    Card(
                        word=fc.word,
                        translation=fc.translation,
                        detected_level=fc.detected_level,
                    )
                )
                store.insert_example(
                    Example(
                        card_id=saved.id,
                        sentence=fc.example_sentence_german,
                        translation=fc.example_sentence_english,
                    )
                )

            # Update progress.
            progress = len(all_results) / len(selected)
            done = len(all_results)
            total = len(selected)
            progress_bar.progress(progress, text=f"Processing {done} of {total} …")

            # Render cards generated so far.
            with cards_container.container():
                for r in all_results:
                    if r.status == "saved" and r.card is not None:
                        fc = r.card
                        badge = (
                            f'<span class="cefr-badge" '
                            f'style="font-size:0.72rem;padding:0.1rem 0.5rem">'
                            f"{fc.detected_level}</span>"
                        )
                        st.markdown(
                            f"""
                            <div class="mini-card">
                                <div class="mini-card-headline">
                                    <span class="mini-card-word">{fc.word}</span>
                                    <span class="mini-card-translation">{fc.translation}</span>
                                    {badge}
                                </div>
                                <div class="fc-sentence-de">🇩🇪 {fc.example_sentence_german}</div>
                                <div class="fc-sentence-en">🇬🇧 {fc.example_sentence_english}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif r.status == "skipped":
                        st.info(f"**{r.word}** — already in your deck", icon="ℹ️")
                    # Failures shown in summary only.

        st.session_state.ac_results = all_results
        progress_bar.empty()

    # ── Summary panel ────────────────────────────────────────────────────────
    results = st.session_state.ac_results
    n_saved = sum(1 for r in results if r.status == "saved")
    n_skipped = sum(1 for r in results if r.status == "skipped")
    n_failed = sum(1 for r in results if r.status == "failed")
    failures = [r for r in results if r.status == "failed"]

    summary_rows = ""
    if n_saved:
        plural = "s" if n_saved != 1 else ""
        summary_rows += f'<div class="summary-row">✅ <strong>{n_saved}</strong> card{plural} saved</div>'
    if n_skipped:
        summary_rows += f'<div class="summary-row">ℹ️ <strong>{n_skipped}</strong> already in deck</div>'
    if n_failed:
        summary_rows += f'<div class="summary-row">❌ <strong>{n_failed}</strong> failed</div>'

    st.markdown(
        f'<div class="summary-panel"><h3>Summary</h3>{summary_rows}</div>',
        unsafe_allow_html=True,
    )

    if failures:
        with st.expander("Failed words"):
            for r in failures:
                st.error(f"**{r.word}**: {r.error}", icon="❌")

    st.divider()
    if st.button("➕ Add another word", type="primary", use_container_width=True):
        st.session_state.ac_phase = "input"
        st.session_state.ac_results = []
        st.rerun()
