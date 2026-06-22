from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

import os
import google.auth
from pydantic import BaseModel, Field
from typing import Literal

project_id = google.auth.default()[1]
if project_id:
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


class FlashcardContext(BaseModel):
    word: str = Field(description="The original German word.")
    translation: str = Field(description="The English translation of the word.")
    detected_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] = Field(
        description="The estimated CEFR difficulty level of the word."
    )
    example_sentence_german: str = Field(
        description="A natural, illustrative German sentence using the word, appropriate for the user's current CEFR level."
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

app = App(root_agent=root_agent, name="echoloop")
