"""Synonyms Agent — generates up to 5 synonyms for a given German word.

This agent is self-sufficient: given a single German word it returns a
structured list of synonyms together with the original word.  It does not
depend on any other agent or prior conversation state.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field

from echoloop.config import configure_genai

configure_genai()


class SynonymEntry(BaseModel):
    """A single synonym with its English translation."""

    synonym_word: str = Field(description="The German synonym.")
    translation: str = Field(description="The English translation of the synonym.")


class SynonymsOutput(BaseModel):
    """Structured output produced by the synonyms agent."""

    original_word: str = Field(description="The original German word that was given as input.")
    synonyms: list[SynonymEntry] = Field(
        description="A list of up to 5 German synonyms for the original word, each with an English translation.",
        max_length=5,
    )


synonyms_agent = Agent(
    name="synonyms_agent",
    model=Gemini(model="gemini-flash-latest", retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=(
        "You are an expert German lexicographer. "
        "Given a single German word, return up to 5 synonyms or closely related words in German. "
        "For each synonym provide its English translation. "
        "Do not repeat the original word in the synonyms list. "
        "If fewer than 5 meaningful synonyms exist, return only those that are genuinely useful."
    ),
    output_schema=SynonymsOutput,
    output_key="synonyms_output",
)
