"""Command-line entry points for EchoLoop."""

import sys
from pathlib import Path


def run_ui() -> None:
    """Launch the EchoLoop Streamlit UI.

    Invoked via the ``echoloop`` console script defined in pyproject.toml.
    """
    from streamlit.web import cli as stcli  # noqa: PLC0415

    ui_path = Path(__file__).parent / "ui" / "main.py"
    sys.argv = ["streamlit", "run", ui_path.as_posix()]
    stcli.main()
