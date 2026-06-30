"""Synchronous runner helpers for EchoLoop agents.

These thin wrappers isolate ADK session/runner boilerplate so that
both the UI and tests can call agents with a single function call.
"""

import json
import re

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from echoloop.agents.context_agent import FlashcardContext, context_agent
from echoloop.agents.synonyms_agent import SynonymsOutput, synonyms_agent
from echoloop.config import configure_genai
from echoloop.types import CEFR_LEVELS_TYPE

# Configure GenAI credentials once at the application boundary.
# Agent modules are pure definitions and do not call configure_genai() themselves.
configure_genai()


def _run_agent(agent, message_text: str, output_key: str, app_name: str) -> dict:
    """Run *agent* with *message_text* and return the session state dict.

    Shared boilerplate: creates a fresh in-memory session, runs the agent to
    completion, and returns the session state so callers can extract the
    structured output they need.

    Args:
        agent:        An ADK :class:`~google.adk.agents.Agent` instance.
        message_text: The user message to send.
        output_key:   Session-state key expected to hold the agent's output.
        app_name:     Application name tag used by the session service.

    Returns:
        The session ``state`` dict after the agent run.

    Raises:
        RuntimeError: If the expected *output_key* is absent from state.

    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="runner_user", app_name=app_name)
    runner = Runner(agent=agent, session_service=session_service, app_name=app_name)

    message = types.Content(role="user", parts=[types.Part.from_text(text=message_text)])
    list(
        runner.run(
            new_message=message,
            user_id="runner_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )
    )

    updated = session_service.get_session_sync(app_name=app_name, user_id="runner_user", session_id=session.id)
    if updated is None or output_key not in updated.state:
        raise RuntimeError(f"Agent did not return '{output_key}' in session state.")
    return updated.state


def run_context_agent(word: str, inferred_level: CEFR_LEVELS_TYPE = "A1") -> FlashcardContext:
    """Run the context agent for *word* and return a parsed :class:`FlashcardContext`.

    Creates a fresh in-memory session for each call so the UI remains
    stateless between submissions.

    Args:
        word:            A German vocabulary word to generate a flashcard for.
        inferred_level:  The user's current CEFR level (default ``"A1"``).
                         Included in the prompt so the agent tailors the
                         example sentence to the appropriate difficulty.

    Returns:
        A populated :class:`FlashcardContext` instance.

    Raises:
        RuntimeError: If the agent does not produce a ``flashcard_context``
            key in the session state.

    """
    prompt = f"Create a flashcard for the German word: '{word}'. The user's current CEFR level is {inferred_level}."
    state = _run_agent(context_agent, prompt, output_key="flashcard_context_raw", app_name="echoloop")

    raw_response = state["flashcard_context_raw"]
    # Extract JSON content from the raw string block
    json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
    if not json_match:
        raise RuntimeError(f"Agent response did not contain a valid JSON block: {raw_response}")

    card_data = json.loads(json_match.group(0))
    return FlashcardContext(**card_data)


def run_synonyms_agent(word: str) -> SynonymsOutput:
    """Run the synonyms agent for *word* and return a parsed :class:`SynonymsOutput`.

    Creates a fresh in-memory session for each call.

    Args:
        word: A German vocabulary word.

    Returns:
        A populated :class:`SynonymsOutput` instance with up to 5 synonyms.

    Raises:
        RuntimeError: If the agent does not produce a ``synonyms_output``
            key in the session state.

    """
    prompt = f"Find synonyms for the German word: '{word}'"
    state = _run_agent(synonyms_agent, prompt, output_key="synonyms_output", app_name="echoloop_synonyms")
    return SynonymsOutput(**state["synonyms_output"])
