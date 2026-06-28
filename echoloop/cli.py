"""Command-line entry points for EchoLoop."""

import sys
from pathlib import Path

from dotenv import load_dotenv


def run_ui() -> None:
    """Launch the EchoLoop Streamlit UI.

    Invoked via the ``echoloop`` console script defined in pyproject.toml.
    """
    from streamlit.web import cli as stcli  # noqa: PLC0415

    # Load .env file from the root of the repository
    env_path = Path(__file__).parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)
    ui_path = Path(__file__).parent / "ui" / "main.py"
    sys.argv = ["streamlit", "run", ui_path.as_posix()]
    stcli.main()
