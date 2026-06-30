"""Model Context Protocol (MCP) server exposing Wiktionary dictionary lookup tools."""

import json

from loguru import logger
from mcp.server.fastmcp import FastMCP

from echoloop.storage.dictionary import OnlineDictionary

# Initialize the FastMCP server instance
mcp = FastMCP("EchoLoop Dictionary Server")
dictionary_client = OnlineDictionary()


@mcp.tool()
def lookup_german_word(word: str) -> str:
    """Lookup part of speech, grammatical gender, and English definitions for a German word.

    Use this tool to verify translations and retrieve exact grammatical genders (e.g., der/die/das for nouns)
    to ground flashcard examples.

    Args:
        word: The German word to lookup (e.g., 'Entscheidung', 'Haus').

    """
    details = dictionary_client.lookup(word).to_dict()
    logger.debug(f"Dictionary lookup for '{word}': {details}")
    return json.dumps(details, ensure_ascii=False)


if __name__ == "__main__":
    # fastmcp run() automatically listens on stdio for MCP clients
    mcp.run()
