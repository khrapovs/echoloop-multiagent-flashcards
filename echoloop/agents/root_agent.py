from typing import Literal

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field

from echoloop.config import configure_genai

configure_genai()


class FlashcardContext(BaseModel):
    word: str = Field(description="The original German word.")
    translation: str = Field(description="The English translation of the word.")
    detected_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] = Field(
        description="The estimated CEFR difficulty level of the word."
    )
    example_sentence_german: str = Field(
        description=(
            "A natural, illustrative German sentence using the word, appropriate for the user's current CEFR level."
        )
    )
    example_sentence_english: str = Field(description="The English translation of the German example sentence.")


root_agent = Agent(
    name="context_agent",
    model=Gemini(model="gemini-flash-latest", retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=(
        "You are an expert German language teacher. Given a German word and the user's current inferred CEFR level "
        "(e.g., A1, B2, etc.) in the conversation history or state, analyze the word and generate a structured "
        "flashcard context. Ensure the example sentence uses grammar and vocabulary appropriate for that CEFR level."
    ),
    output_schema=FlashcardContext,
    output_key="flashcard_context",
)
