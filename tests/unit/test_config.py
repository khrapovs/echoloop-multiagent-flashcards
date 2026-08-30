import os

from echoloop.config import configure_genai
from pytest import MonkeyPatch


def test_configure_genai_removes_enterprise_env_var(monkeypatch: MonkeyPatch) -> None:
    """Ensure GOOGLE_GENAI_USE_ENTERPRISE is popped to avoid warnings in google.genai SDK."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_ENTERPRISE", "FALSE")
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    configure_genai()

    assert "GOOGLE_GENAI_USE_ENTERPRISE" not in os.environ
