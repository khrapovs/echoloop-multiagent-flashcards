"""Runtime configuration for EchoLoop agents.

Sets the required environment variables for the Google GenAI SDK based on
whether a Vertex AI setup or a plain Gemini Developer API key is available.

Priority:
1. If ``GOOGLE_GENAI_USE_VERTEXAI`` is already set in the environment, respect it.
2. If ``GOOGLE_API_KEY`` is present, switch to the Developer API (no Vertex AI).
3. Otherwise, attempt to resolve a GCP project via Application Default Credentials
   and use Vertex AI.
"""

import os


def configure_genai() -> None:
    """Set Google GenAI environment variables exactly once.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    # Pop deprecated GOOGLE_GENAI_USE_VERTEXAI to avoid deprecation warnings from google-adk
    legacy_val = os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)

    # Already configured by the caller or a previous call
    if "GOOGLE_GENAI_USE_ENTERPRISE" in os.environ:
        return

    if legacy_val is not None:
        os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = legacy_val
        return

    if os.environ.get("GOOGLE_API_KEY"):
        # Developer API key present — use the Gemini Developer API directly.
        os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "False"
        return

    # No API key — fall back to Vertex AI / Enterprise with Application Default Credentials.
    try:
        import google.auth  # noqa: PLC0415

        _, project_id = google.auth.default()
    except Exception:
        project_id = None

    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "True"
