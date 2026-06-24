"""Integration tests for the context agent via its public runner interface.

These tests call the real Gemini model and require valid credentials
(GOOGLE_API_KEY or Application Default Credentials).

Run with:
    uv run pytest tests/integration/test_agent.py -v
"""

from __future__ import annotations

from echoloop.agent import FlashcardContext
from echoloop.runner import run_context_agent


def test_returns_flashcard_context() -> None:
    """run_context_agent returns a FlashcardContext instance."""
    card = run_context_agent("Katze")
    assert isinstance(card, FlashcardContext)


def test_word_is_echoed_back() -> None:
    """The returned card contains the submitted word."""
    card = run_context_agent("Katze")
    assert card.word.lower() == "katze"


def test_detected_level_is_valid_cefr() -> None:
    """The detected CEFR level is one of the six standard values."""
    card = run_context_agent("Katze")
    assert card.detected_level in {"A1", "A2", "B1", "B2", "C1", "C2"}


def test_example_sentences_are_present() -> None:
    """Both the German example sentence and its English translation are non-empty."""
    card = run_context_agent("Katze")
    assert card.example_sentence_german.strip()
    assert card.example_sentence_english.strip()


def test_translation_is_present() -> None:
    """The English translation of the word itself is non-empty."""
    card = run_context_agent("Katze")
    assert card.translation.strip()
