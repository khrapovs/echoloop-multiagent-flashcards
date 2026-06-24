"""Runtime configuration for EchoLoop agents.

Sets the required environment variables for the Google GenAI SDK based on
whether a Vertex AI setup or a plain Gemini Developer API key is available.

Priority:
1. If ``GOOGLE_GENAI_USE_VERTEXAI`` is already set in the environment, respect it.
2. If ``GOOGLE_API_KEY`` is present, switch to the Developer API (no Vertex AI).
3. Otherwise, attempt to resolve a GCP project via Application Default Credentials
   and use Vertex AI.
"""

from __future__ import annotations

import os


def configure_genai() -> None:
    """Set Google GenAI environment variables exactly once.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    # Already configured by the caller or a previous call — leave it alone.
    if "GOOGLE_GENAI_USE_VERTEXAI" in os.environ:
        return

    if os.environ.get("GOOGLE_API_KEY"):
        # Developer API key present — use the Gemini Developer API directly.
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
        return

    # No API key — fall back to Vertex AI with Application Default Credentials.
    try:
        import google.auth  # noqa: PLC0415

        _, project_id = google.auth.default()
    except Exception:
        project_id = None

    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
