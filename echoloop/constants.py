import os
from pathlib import Path

from echoloop.types import CEFR_LEVELS_TYPE

# The six CEFR levels ordered from easiest to hardest.
CEFR_LEVELS: tuple[CEFR_LEVELS_TYPE, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# SM-2 easiness-factor lower bound.
_MIN_EF: float = 1.3

# Path to the SQLite database file. Allow redirection via env var for deployment persistence.
_DB_DIR = os.getenv("ECHOLOOP_DB_DIR")
if _DB_DIR:
    _DB_PATH = Path(_DB_DIR) / "echoloop.db"
else:
    _DB_PATH = Path(__file__).parents[1] / "echoloop.db"
