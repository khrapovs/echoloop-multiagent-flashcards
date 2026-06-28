"""Unit tests for AgentPipeline.

All agent calls are mocked so no network or LLM access is needed.
The CardStore uses an in-memory SQLite database for isolation.
"""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from echoloop.agents.root_agent import FlashcardContext
from echoloop.agents.synonyms_agent import SynonymEntry, SynonymsOutput
from echoloop.pipeline import AgentPipeline, FlashcardResult
from echoloop.repetition_engine import RepetitionEngine
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> CardStore:
    """Fresh in-memory CardStore."""
    return CardStore(db_path=":memory:")


@pytest.fixture()
def engine(store: CardStore) -> RepetitionEngine:
    """RepetitionEngine backed by the same in-memory store."""
    return RepetitionEngine(store=store)


@pytest.fixture()
def pipeline(store: CardStore, engine: RepetitionEngine) -> AgentPipeline:
    """AgentPipeline under test."""
    return AgentPipeline(store=store, engine=engine)


def _make_flashcard(word: str = "Hund", level: str = "A1") -> FlashcardContext:
    """Return a minimal FlashcardContext for a given word."""
    return FlashcardContext(
        word=word,
        translation="dog",
        detected_level=level,
        example_sentence_german=f"Der {word} ist groß.",
        example_sentence_english="The dog is big.",
    )


def _make_synonyms(original: str, synonyms: list[str]) -> SynonymsOutput:
    """Return a SynonymsOutput with the given words."""
    return SynonymsOutput(
        original_word=original,
        synonyms=[SynonymEntry(synonym_word=s, translation=f"{s}_en") for s in synonyms],
    )


def _existing_card(word: str) -> Card:
    """Return a minimal Card (as if already in the DB)."""
    return Card(
        id=1,
        word=word,
        translation="dog",
        detected_level="A1",
        next_review_date=datetime.date.today(),
    )


# ---------------------------------------------------------------------------
# get_synonyms
# ---------------------------------------------------------------------------


class TestGetSynonyms:
    def test_delegates_to_run_synonyms_agent(self, pipeline: AgentPipeline) -> None:
        expected = _make_synonyms("Hund", ["Köter", "Vierbeiner"])
        with patch("echoloop.pipeline.run_synonyms_agent", return_value=expected) as mock:
            result = pipeline.get_synonyms("Hund")
        mock.assert_called_once_with("Hund")
        assert result == expected

    def test_returns_synonyms_output(self, pipeline: AgentPipeline) -> None:
        output = _make_synonyms("Katze", ["Mieze"])
        with patch("echoloop.pipeline.run_synonyms_agent", return_value=output):
            result = pipeline.get_synonyms("Katze")
        assert isinstance(result, SynonymsOutput)
        assert result.original_word == "Katze"


# ---------------------------------------------------------------------------
# generate_card_batch — happy path
# ---------------------------------------------------------------------------


class TestGenerateCardBatchSaved:
    def test_yields_one_result_per_word(self, pipeline: AgentPipeline) -> None:
        words = ["Hund", "Katze"]
        side_effects = [_make_flashcard("Hund"), _make_flashcard("Katze")]
        with patch("echoloop.pipeline.run_context_agent", side_effect=side_effects):
            results = list(pipeline.generate_card_batch(words))
        assert len(results) == 2

    def test_status_is_saved_for_new_words(self, pipeline: AgentPipeline) -> None:
        with patch("echoloop.pipeline.run_context_agent", return_value=_make_flashcard("Hund")):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].status == "saved"

    def test_card_is_populated_on_success(self, pipeline: AgentPipeline) -> None:
        card = _make_flashcard("Hund")
        with patch("echoloop.pipeline.run_context_agent", return_value=card):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].card == card

    def test_word_is_echoed_in_result(self, pipeline: AgentPipeline) -> None:
        with patch("echoloop.pipeline.run_context_agent", return_value=_make_flashcard("Hund")):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].word == "Hund"

    def test_results_preserve_word_order(self, pipeline: AgentPipeline) -> None:
        words = ["Hund", "Katze", "Tisch"]
        side_effects = [_make_flashcard(w) for w in words]
        with patch("echoloop.pipeline.run_context_agent", side_effect=side_effects):
            results = list(pipeline.generate_card_batch(words))
        assert [r.word for r in results] == words

    def test_context_agent_receives_inferred_level(self, store: CardStore, pipeline: AgentPipeline) -> None:
        """Inferred level from the engine is passed to run_context_agent."""
        # Seed a B1 card so the engine infers B1.
        store.insert_card(Card(word="X", translation="x", detected_level="B1", next_review_date=datetime.date.today()))
        with patch("echoloop.pipeline.run_context_agent", return_value=_make_flashcard("Hund")) as mock:
            list(pipeline.generate_card_batch(["Hund"]))
        _, kwargs = mock.call_args
        assert kwargs.get("inferred_level") == "B1"


# ---------------------------------------------------------------------------
# generate_card_batch — skipped words
# ---------------------------------------------------------------------------


def _seed_card(store: CardStore, word: str = "Hund") -> None:
    """Insert a minimal card into the store."""
    store.insert_card(Card(word=word, translation="dog", detected_level="A1", next_review_date=datetime.date.today()))


class TestGenerateCardBatchSkipped:
    def test_status_is_skipped_when_word_already_in_db(self, store: CardStore, pipeline: AgentPipeline) -> None:
        _seed_card(store)
        with patch("echoloop.pipeline.run_context_agent") as mock:
            results = list(pipeline.generate_card_batch(["Hund"]))
        mock.assert_not_called()
        assert results[0].status == "skipped"

    def test_skipped_result_has_no_card(self, store: CardStore, pipeline: AgentPipeline) -> None:
        _seed_card(store)
        results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].card is None

    def test_skipped_word_does_not_block_others(self, store: CardStore, pipeline: AgentPipeline) -> None:
        _seed_card(store)
        with patch("echoloop.pipeline.run_context_agent", return_value=_make_flashcard("Katze")):
            results = list(pipeline.generate_card_batch(["Hund", "Katze"]))
        assert results[0].status == "skipped"
        assert results[1].status == "saved"


# ---------------------------------------------------------------------------
# generate_card_batch — failures
# ---------------------------------------------------------------------------


class TestGenerateCardBatchFailed:
    def test_status_is_failed_on_agent_error(self, pipeline: AgentPipeline) -> None:
        with patch("echoloop.pipeline.run_context_agent", side_effect=RuntimeError("API error")):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].status == "failed"

    def test_error_message_is_captured(self, pipeline: AgentPipeline) -> None:
        with patch("echoloop.pipeline.run_context_agent", side_effect=RuntimeError("timeout")):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert "timeout" in results[0].error

    def test_failed_card_is_none(self, pipeline: AgentPipeline) -> None:
        with patch("echoloop.pipeline.run_context_agent", side_effect=RuntimeError("boom")):
            results = list(pipeline.generate_card_batch(["Hund"]))
        assert results[0].card is None

    def test_failure_does_not_abort_batch(self, pipeline: AgentPipeline) -> None:
        """A failure on word N must not prevent word N+1 from being processed."""
        side_effects = [RuntimeError("error"), _make_flashcard("Katze")]
        with patch("echoloop.pipeline.run_context_agent", side_effect=side_effects):
            results = list(pipeline.generate_card_batch(["Hund", "Katze"]))
        assert results[0].status == "failed"
        assert results[1].status == "saved"

    def test_empty_word_list_yields_nothing(self, pipeline: AgentPipeline) -> None:
        results = list(pipeline.generate_card_batch([]))
        assert results == []


# ---------------------------------------------------------------------------
# FlashcardResult — data model
# ---------------------------------------------------------------------------


class TestFlashcardResult:
    def test_saved_result_has_card(self) -> None:
        card = _make_flashcard("Hund")
        r = FlashcardResult(word="Hund", card=card, status="saved")
        assert r.card is not None
        assert r.error is None

    def test_skipped_result_defaults(self) -> None:
        r = FlashcardResult(word="Hund", status="skipped")
        assert r.card is None
        assert r.error is None

    def test_failed_result_carries_error(self) -> None:
        r = FlashcardResult(word="Hund", status="failed", error="timeout")
        assert r.card is None
        assert r.error == "timeout"
