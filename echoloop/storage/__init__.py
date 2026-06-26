"""Storage adapter package for EchoLoop."""

from __future__ import annotations

from pathlib import Path

from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card, Example, Review, Synonym

__all__ = ["CardStore", "Card", "Example", "Review", "Synonym", "get_store"]

# Path to the SQLite database file in the repository root.
_DB_PATH = Path(__file__).parent.parent.parent / "echoloop.db"


def get_store() -> CardStore:
    """Return a CardStore backed by the repository-root SQLite database.

    The database file is created automatically on first access if it does
    not yet exist.  Safe to call repeatedly — ``CardStore.__init__`` only
    runs the schema migration once.
    """
    return CardStore(db_path=str(_DB_PATH))
