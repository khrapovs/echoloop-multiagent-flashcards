"""Command-line entry points for EchoLoop."""

from __future__ import annotations

import sys
from pathlib import Path


def run_ui() -> None:
    """Launch the EchoLoop Streamlit UI.

    Invoked via the ``echoloop`` console script defined in pyproject.toml.
    """
    from streamlit.web import cli as stcli  # noqa: PLC0415

    ui_path = Path(__file__).parent / "ui.py"
    sys.argv = ["streamlit", "run", str(ui_path)]
    stcli.main()
