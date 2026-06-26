"""Pydantic models representing rows in the normalized SQLite schema.

Each model maps 1-to-1 with a database table. All IDs are auto-assigned
by the database; ``None`` means "not yet persisted".
"""

import datetime

from pydantic import BaseModel, Field

from echoloop.types import CEFR_LEVELS_TYPE


class Card(BaseModel):
    """A flashcard row — one entry per vocabulary word."""

    id: int | None = None
    word: str
    translation: str
    detected_level: CEFR_LEVELS_TYPE
    # SM-2 scheduling fields
    easiness_factor: float = Field(default=2.5, ge=1.3)
    interval_days: int = Field(default=1, ge=1)
    repetitions: int = Field(default=0, ge=0)
    next_review_date: datetime.date = Field(default_factory=datetime.date.today)


class Example(BaseModel):
    """An example sentence belonging to a card."""

    id: int | None = None
    card_id: int
    sentence: str
    translation: str


class Synonym(BaseModel):
    """A synonym / related word belonging to a card."""

    id: int | None = None
    card_id: int
    synonym_word: str
    translation: str


class Review(BaseModel):
    """A single review event for a card."""

    id: int | None = None
    card_id: int
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    rating_score: int = Field(ge=0, le=5)
