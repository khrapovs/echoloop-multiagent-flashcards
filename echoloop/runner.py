"""Synchronous runner helpers for EchoLoop agents.

These thin wrappers isolate ADK session/runner boilerplate so that
both the UI and tests can call agents with a single function call.
"""

from __future__ import annotations

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from echoloop.config import configure_genai

# Configure GenAI credentials once at the application boundary.
# Agent modules are pure definitions and do not call configure_genai() themselves.
configure_genai()

from echoloop.agents.root_agent import FlashcardContext, root_agent  # noqa: E402


def run_context_agent(word: str) -> FlashcardContext:
    """Run the context agent for ``word`` and return a parsed FlashcardContext.

    Creates a fresh in-memory session for each call so the UI remains
    stateless between submissions.

    Args:
        word: A German vocabulary word to generate a flashcard for.

    Returns:
        A populated :class:`FlashcardContext` instance.

    Raises:
        RuntimeError: If the agent does not produce a ``flashcard_context``
            key in the session state.

    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="ui_user", app_name="echoloop")

    runner = Runner(agent=root_agent, session_service=session_service, app_name="echoloop")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=f"Create a flashcard for the German word: '{word}'")],
    )

    list(
        runner.run(
            new_message=message,
            user_id="ui_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )
    )

    updated = session_service.get_session_sync(app_name="echoloop", user_id="ui_user", session_id=session.id)
    if updated is None or "flashcard_context" not in updated.state:
        raise RuntimeError("Agent did not return a flashcard_context in session state.")

    return FlashcardContext(**updated.state["flashcard_context"])
