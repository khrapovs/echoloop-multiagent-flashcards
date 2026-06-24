"""Integration tests for the synonyms agent.

These tests call the real Gemini model, so they require valid Google Cloud
credentials (Application Default Credentials) to be configured.

Run with:
    uv run pytest tests/integration/test_synonyms_agent.py -v
"""

from __future__ import annotations

import pytest
from echoloop.synonyms_agent import SynonymsOutput, synonyms_agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


@pytest.fixture()
def runner() -> Runner:
    """Return a fresh runner backed by an in-memory session service."""
    session_service = InMemorySessionService()
    return Runner(agent=synonyms_agent, session_service=session_service, app_name="test_synonyms")


def _run_agent(runner: Runner, word: str) -> tuple[InMemorySessionService, str]:
    """Create a session, send ``word`` to the agent, and return (session_service, session_id)."""
    session_service: InMemorySessionService = runner.session_service
    session = session_service.create_session_sync(user_id="test_user", app_name="test_synonyms")
    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Give me synonyms for the German word: '{word}'")],
    )
    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )
    )
    assert len(events) > 0, "Expected at least one response event from the agent"
    return session_service, session.id


class TestSynonymsAgentOutput:
    def test_output_key_present_in_session_state(self, runner: Runner) -> None:
        """The agent must write its result under the 'synonyms_output' key."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        assert session is not None
        assert "synonyms_output" in session.state

    def test_output_parses_to_schema(self, runner: Runner) -> None:
        """The raw session state must deserialise into SynonymsOutput without error."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        assert isinstance(result, SynonymsOutput)

    def test_original_word_is_echoed_back(self, runner: Runner) -> None:
        """The agent must echo the original input word."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        assert result.original_word.lower() == "hund"

    def test_returns_at_least_one_synonym(self, runner: Runner) -> None:
        """The agent must suggest at least one synonym for a common German word."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        assert len(result.synonyms) >= 1

    def test_returns_at_most_five_synonyms(self, runner: Runner) -> None:
        """The agent must not exceed the 5-synonym limit."""
        session_service, session_id = _run_agent(runner, "schön")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        assert len(result.synonyms) <= 5

    def test_each_synonym_has_non_empty_word_and_translation(self, runner: Runner) -> None:
        """Every SynonymEntry must carry both a German synonym and an English translation."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        for entry in result.synonyms:
            assert entry.synonym_word.strip(), "synonym_word must not be empty"
            assert entry.translation.strip(), "translation must not be empty"

    def test_original_word_not_in_synonyms(self, runner: Runner) -> None:
        """The original word itself must not appear in the synonyms list."""
        session_service, session_id = _run_agent(runner, "Hund")
        session = session_service.get_session_sync(app_name="test_synonyms", user_id="test_user", session_id=session_id)
        result = SynonymsOutput(**session.state["synonyms_output"])
        synonym_words_lower = [e.synonym_word.lower() for e in result.synonyms]
        assert "hund" not in synonym_words_lower, "Original word must not be repeated as a synonym"
