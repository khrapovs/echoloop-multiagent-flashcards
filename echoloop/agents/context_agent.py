"""Context agent for generating flashcard sentences and difficulty levels, using Wiktionary MCP tools."""

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from pydantic import BaseModel, Field

from echoloop.types import CEFR_LEVELS_TYPE


class FlashcardContext(BaseModel):
    word: str = Field(description="The original German word.")
    translation: str = Field(description="The English translation of the word.")
    detected_level: CEFR_LEVELS_TYPE = Field(description="The estimated CEFR difficulty level of the word.")
    example_sentence_german: str = Field(
        description=(
            "A natural, illustrative German sentence using the word, appropriate for the user's current CEFR level."
        )
    )
    example_sentence_english: str = Field(description="The English translation of the German example sentence.")


# Define the MCP toolset connection params pointing to our local FastMCP server module
dictionary_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=["-m", "echoloop.agents.mcp_server"],
        )
    )
)

context_agent = Agent(
    name="context_agent",
    model=Gemini(model="gemini-flash-latest", retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=(
        "You are an expert German language teacher. Given a German word and the user's current inferred CEFR level "
        "(e.g., A1, B2, etc.), you MUST first call the lookup_german_word tool to fetch the verified dictionary "
        "definition and grammatical gender.\n\n"
        "Then, generate a structured flashcard context. "
        "You MUST format your output as a raw JSON object matching the following structure, with NO extra markdown "
        "formatting outside the JSON block:\n"
        "{\n"
        '  "word": "The original German word, matching the queried word EXACTLY without articles '
        "(e.g. 'Katze', NOT 'die Katze')\",\n"
        '  "translation": "The English translation of the word",\n'
        '  "detected_level": "The CEFR level (A1, A2, B1, B2, C1, or C2)",\n'
        '  "example_sentence_german": "A natural, illustrative German sentence using the word, '
        'appropriate for the level",\n'
        '  "example_sentence_english": "The English translation of the German example sentence"\n'
        "}\n\n"
        "Use the retrieved gender and definitions from the tool to ground your translation and definite articles. "
        "Ensure the example sentence grammar and vocabulary are appropriate for the requested CEFR level."
    ),
    tools=[dictionary_toolset],
    output_key="flashcard_context_raw",
)
