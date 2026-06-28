"""Integration tests for the synonyms agent via its public runner interface.

These tests call the real Gemini model and require valid credentials
(GOOGLE_API_KEY or Application Default Credentials).

Run with:
    uv run pytest tests/integration/test_agents/test_synonyms_agent.py -v
"""

from echoloop.agents.synonyms_agent import SynonymsOutput
from echoloop.runner import run_synonyms_agent


def test_returns_synonyms_output() -> None:
    """run_synonyms_agent returns a SynonymsOutput instance."""
    result = run_synonyms_agent("Hund")
    assert isinstance(result, SynonymsOutput)


def test_original_word_is_echoed_back() -> None:
    """The returned output contains the submitted word."""
    result = run_synonyms_agent("Hund")
    assert result.original_word.lower() == "hund"


def test_returns_at_least_one_synonym() -> None:
    """The agent must suggest at least one synonym for a common German word."""
    result = run_synonyms_agent("Hund")
    assert len(result.synonyms) >= 1


def test_returns_at_most_five_synonyms() -> None:
    """The agent must not exceed the 5-synonym limit."""
    result = run_synonyms_agent("schön")
    assert len(result.synonyms) <= 5


def test_each_synonym_has_non_empty_word_and_translation() -> None:
    """Every SynonymEntry must carry both a German synonym and an English translation."""
    result = run_synonyms_agent("Hund")
    for entry in result.synonyms:
        assert entry.synonym_word.strip(), "synonym_word must not be empty"
        assert entry.translation.strip(), "translation must not be empty"


def test_original_word_not_in_synonyms() -> None:
    """The original word itself must not appear in the synonyms list."""
    result = run_synonyms_agent("Hund")
    synonym_words_lower = [e.synonym_word.lower() for e in result.synonyms]
    assert "hund" not in synonym_words_lower, "Original word must not be repeated as a synonym"
