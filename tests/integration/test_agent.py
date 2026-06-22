from echoloop.agent import FlashcardContext
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from echoloop.agent import root_agent


def test_agent_run() -> None:
    """
    Integration test for the context agent.
    Verifies that the agent generates a structured flashcard payload.
    """
    session_service = InMemorySessionService()

    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Create a flashcard for the German word: 'Katze'. User current level: A1")],
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.NONE),
        )
    )
    assert len(events) > 0, "Expected at least one response event"

    updated_session = session_service.get_session_sync(app_name="test", user_id="test_user", session_id=session.id)

    assert updated_session is not None
    assert "flashcard_context" in updated_session.state

    card = FlashcardContext(**updated_session.state["flashcard_context"])

    assert card.word.lower() == "katze"
    assert card.detected_level == "A1"
    assert card.example_sentence_german is not None
