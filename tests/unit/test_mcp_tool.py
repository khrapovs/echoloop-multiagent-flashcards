"""Unit tests for the FastMCP dictionary server."""

import json
from unittest.mock import MagicMock, patch

import pytest
from echoloop.agents.mcp_server import mcp
from mcp.types import TextContent


@pytest.mark.anyio()
async def test_mcp_tool_execution() -> None:
    """Verify that the lookup_german_word tool executes correctly via FastMCP's test client."""
    mock_details = MagicMock()
    mock_details.to_dict.return_value = {
        "word": "Hund",
        "part_of_speech": "Noun",
        "gender": "m",
        "article": "der",
        "definitions": ["dog"],
    }

    # Patch the dictionary client's lookup call
    with patch("echoloop.agents.mcp_server.dictionary_client.lookup", return_value=mock_details) as mock_lookup:
        # Call the tool directly on the mcp app instance
        result = await mcp.call_tool("lookup_german_word", {"word": "Hund"})
        mock_lookup.assert_called_once_with("Hund")

    # Verify output formatting
    assert result is not None
    # FastMCP returns a tuple: (list of content blocks, metadata)
    assert isinstance(result, tuple)
    content_list = result[0]
    assert isinstance(content_list, list)

    text_block = content_list[0]
    assert isinstance(text_block, TextContent)

    text_content = text_block.text
    data = json.loads(text_content)
    assert data["word"] == "Hund"
    assert data["gender"] == "m"
    assert data["article"] == "der"
    assert data["definitions"] == ["dog"]
