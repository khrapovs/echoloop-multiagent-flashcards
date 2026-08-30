import os

from echoloop.config import configure_genai
from pytest import MonkeyPatch


def test_configure_genai_uses_enterprise_env_var(monkeypatch: MonkeyPatch) -> None:
    """Ensure GOOGLE_GENAI_USE_ENTERPRISE is set and GOOGLE_GENAI_USE_VERTEXAI is popped to avoid warnings."""
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    monkeypatch.delenv("GOOGLE_GENAI_USE_ENTERPRISE", raising=False)

    configure_genai()

    assert os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE") == "True"
    assert "GOOGLE_GENAI_USE_VERTEXAI" not in os.environ
