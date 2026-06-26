"""Spaced Repetition Engine for EchoLoop.

Implements the SM-2 algorithm for scheduling flashcard reviews and infers
the user's CEFR level from the distribution of cards in the database.

Responsibilities
----------------
- Calculate the next review date and updated SM-2 parameters for a card
  given a review score (0-5).
- Infer the user's current CEFR level by analysing the "detected_level"
  distribution across all stored cards.

Non-responsibilities
--------------------
- No database writes — the engine is a pure computation layer. Callers
  are responsible for persisting the returned "CardMetrics" via
  "CardStore".
"""

import datetime
from collections import Counter

from pydantic import BaseModel, Field

from echoloop.constants import _MIN_EF, CEFR_LEVELS
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card
from echoloop.types import CEFR_LEVELS_TYPE


class CardMetrics(BaseModel):
    """Updated SM-2 scheduling parameters returned by ``calculate_next_review``.

    These values are ready to be written back to the ``cards`` table via
    ``CardStore.update_card``.  They carry no ``id`` or ``word`` — the
    caller must apply them to the original :class:`~echoloop.storage.models.Card`.
    """

    easiness_factor: float = Field(ge=_MIN_EF)
    interval_days: int = Field(ge=1)
    repetitions: int = Field(ge=0)
    next_review_date: datetime.date


class RepetitionEngine:
    """Coordinates SM-2 scheduling and user-level inference.

    Args:
        store: A :class:`~echoloop.storage.adapter.CardStore` used to read
            cards when inferring the user's level.  The engine never writes
            to the store itself.

    """

    def __init__(self, store: CardStore) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def calculate_next_review(self, card: Card, review_score: int) -> CardMetrics:
        """Apply the SM-2 algorithm and return updated scheduling metrics.

        Args:
            card: The card that was just reviewed.
            review_score: Quality of recall on a 0-5 scale (0 = complete
                blackout, 5 = perfect response).

        Returns:
            A :class:`CardMetrics` instance with the new ``easiness_factor``,
            ``interval_days``, ``repetitions``, and ``next_review_date``.

        Raises:
            ValueError: If ``review_score`` is not in the range [0, 5].

        """
        if not 0 <= review_score <= 5:
            raise ValueError(f"review_score must be between 0 and 5, got {review_score}")

        new_ef = self._updated_easiness_factor(card.easiness_factor, review_score)

        if review_score < 3:
            # Failed recall — restart the repetition sequence.
            new_repetitions = 0
            new_interval = 1
        else:
            # Successful recall — advance the interval.
            new_repetitions = card.repetitions + 1
            if card.repetitions == 0:
                new_interval = 1
            elif card.repetitions == 1:
                new_interval = 6
            else:
                new_interval = round(card.interval_days * new_ef)
            # Ensure the interval never shrinks below 1.
            new_interval = max(1, new_interval)

        new_next_review = datetime.date.today() + datetime.timedelta(days=new_interval)

        return CardMetrics(
            easiness_factor=new_ef,
            interval_days=new_interval,
            repetitions=new_repetitions,
            next_review_date=new_next_review,
        )

    def get_inferred_user_level(self) -> CEFR_LEVELS_TYPE:
        """Infer the user's current CEFR level from their card database.

        Uses the mode (most frequent ``detected_level``) across all stored
        cards.  When multiple levels tie, the easier one is preferred so that
        the UI does not overwhelm a beginner.  Falls back to ``"A1"`` when
        no cards exist yet.

        Returns:
            One of the six CEFR level strings: ``"A1"``, ``"A2"``, …, ``"C2"``.

        """
        cards = self._store.list_cards()
        if not cards:
            return "A1"

        counts = Counter(card.detected_level for card in cards)

        # Find the maximum count, then pick the *easiest* level among ties.
        max_count = max(counts.values())
        tied_levels = [lvl for lvl in CEFR_LEVELS if counts.get(lvl, 0) == max_count]
        # tied_levels is already sorted easiest-first because CEFR_LEVELS is ordered.
        return tied_levels[0]  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _updated_easiness_factor(ef: float, score: int) -> float:
        """Return the new easiness factor after a review.

        SM-2 formula:  EF' = EF + 0.1 - (5 - score) x (0.08 + (5 - score) x 0.02)
        Clamped to a minimum of 1.3.
        """
        delta = 0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)
        return max(_MIN_EF, ef + delta)
