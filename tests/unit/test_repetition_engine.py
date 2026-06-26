"""Unit tests for RepetitionEngine.

All tests are pure unit tests — no network calls, no file I/O.
The :memory: CardStore fixture provides isolation between tests.
"""

import datetime

import pytest
from echoloop.repetition_engine import CardMetrics, RepetitionEngine
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card
from echoloop.types import CEFR_LEVELS_TYPE

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store() -> CardStore:
    """Return a fresh in-memory CardStore."""
    return CardStore(db_path=":memory:")


@pytest.fixture()
def engine(store: CardStore) -> RepetitionEngine:
    """Return a RepetitionEngine backed by an empty in-memory store."""
    return RepetitionEngine(store=store)


def _card(
    word: str = "Hund", detected_level: CEFR_LEVELS_TYPE = "A1", repetitions=0, interval_days=1, easiness_factor=2.5
) -> Card:
    """Build a Card with sensible SM-2 defaults, overridable via kwargs."""
    return Card(
        word=word,
        translation="dog",
        detected_level=detected_level,
        easiness_factor=easiness_factor,
        interval_days=interval_days,
        repetitions=repetitions,
        next_review_date=datetime.date.today(),
    )


# ---------------------------------------------------------------------------
# calculate_next_review — input validation
# ---------------------------------------------------------------------------


class TestCalculateNextReviewValidation:
    def test_raises_for_score_below_zero(self, engine: RepetitionEngine) -> None:
        with pytest.raises(ValueError, match="review_score"):
            engine.calculate_next_review(_card(), review_score=-1)

    def test_raises_for_score_above_five(self, engine: RepetitionEngine) -> None:
        with pytest.raises(ValueError, match="review_score"):
            engine.calculate_next_review(_card(), review_score=6)

    def test_boundary_score_zero_accepted(self, engine: RepetitionEngine) -> None:
        result = engine.calculate_next_review(_card(), review_score=0)
        assert isinstance(result, CardMetrics)

    def test_boundary_score_five_accepted(self, engine: RepetitionEngine) -> None:
        result = engine.calculate_next_review(_card(), review_score=5)
        assert isinstance(result, CardMetrics)


# ---------------------------------------------------------------------------
# calculate_next_review — failed recall (score < 3)
# ---------------------------------------------------------------------------


class TestFailedRecall:
    @pytest.mark.parametrize("score", [0, 1, 2])
    def test_repetitions_reset_to_zero(self, engine: RepetitionEngine, score: int) -> None:
        card = _card(repetitions=5, interval_days=30)
        result = engine.calculate_next_review(card, review_score=score)
        assert result.repetitions == 0

    @pytest.mark.parametrize("score", [0, 1, 2])
    def test_interval_reset_to_one(self, engine: RepetitionEngine, score: int) -> None:
        card = _card(repetitions=5, interval_days=30)
        result = engine.calculate_next_review(card, review_score=score)
        assert result.interval_days == 1

    def test_easiness_factor_decreases_on_failure(self, engine: RepetitionEngine) -> None:
        card = _card(easiness_factor=2.5)
        result = engine.calculate_next_review(card, review_score=0)
        assert result.easiness_factor < 2.5

    def test_easiness_factor_never_below_minimum(self, engine: RepetitionEngine) -> None:
        # Drive EF to its floor over repeated failures.
        card = _card(easiness_factor=1.3)
        result = engine.calculate_next_review(card, review_score=0)
        assert result.easiness_factor >= 1.3


# ---------------------------------------------------------------------------
# calculate_next_review — successful recall (score >= 3)
# ---------------------------------------------------------------------------


class TestSuccessfulRecall:
    @pytest.mark.parametrize("score", [3, 4, 5])
    def test_repetitions_increment(self, engine: RepetitionEngine, score: int) -> None:
        card = _card(repetitions=2, interval_days=6)
        result = engine.calculate_next_review(card, review_score=score)
        assert result.repetitions == 3

    def test_first_repetition_gives_interval_one(self, engine: RepetitionEngine) -> None:
        """First successful review → interval stays at 1 day."""
        card = _card(repetitions=0, interval_days=1)
        result = engine.calculate_next_review(card, review_score=4)
        assert result.interval_days == 1

    def test_second_repetition_gives_interval_six(self, engine: RepetitionEngine) -> None:
        """Second successful review → interval jumps to 6 days."""
        card = _card(repetitions=1, interval_days=1)
        result = engine.calculate_next_review(card, review_score=4)
        assert result.interval_days == 6

    def test_subsequent_interval_grows_with_ef(self, engine: RepetitionEngine) -> None:
        """Third+ review → interval = round(prev_interval x EF)."""
        card = _card(repetitions=2, interval_days=6, easiness_factor=2.5)
        result = engine.calculate_next_review(card, review_score=4)
        assert result.interval_days == round(6 * result.easiness_factor)

    def test_perfect_score_increases_easiness_factor(self, engine: RepetitionEngine) -> None:
        card = _card(easiness_factor=2.5)
        result = engine.calculate_next_review(card, review_score=5)
        assert result.easiness_factor > 2.5

    def test_score_three_slightly_decreases_ef(self, engine: RepetitionEngine) -> None:
        """Score 3 (just passing) reduces EF slightly."""
        card = _card(easiness_factor=2.5)
        result = engine.calculate_next_review(card, review_score=3)
        assert result.easiness_factor < 2.5

    def test_next_review_date_is_in_the_future(self, engine: RepetitionEngine) -> None:
        card = _card(repetitions=1, interval_days=1)
        result = engine.calculate_next_review(card, review_score=5)
        assert result.next_review_date >= datetime.date.today()

    def test_next_review_date_matches_interval(self, engine: RepetitionEngine) -> None:
        card = _card(repetitions=0, interval_days=1)
        result = engine.calculate_next_review(card, review_score=5)
        expected = datetime.date.today() + datetime.timedelta(days=result.interval_days)
        assert result.next_review_date == expected


# ---------------------------------------------------------------------------
# get_inferred_user_level
# ---------------------------------------------------------------------------


class TestGetInferredUserLevel:
    def test_returns_a1_when_no_cards(self, engine: RepetitionEngine) -> None:
        assert engine.get_inferred_user_level() == "A1"

    def test_returns_level_of_single_card(self, store: CardStore, engine: RepetitionEngine) -> None:
        store.insert_card(_card(detected_level="B2"))
        assert engine.get_inferred_user_level() == "B2"

    def test_returns_most_frequent_level(self, store: CardStore, engine: RepetitionEngine) -> None:
        store.insert_card(_card(word="Hund", detected_level="A1"))
        store.insert_card(_card(word="Katze", detected_level="B1"))
        store.insert_card(_card(word="Tisch", detected_level="B1"))
        store.insert_card(_card(word="Stuhl", detected_level="C1"))
        assert engine.get_inferred_user_level() == "B1"

    def test_tie_prefers_easier_level(self, store: CardStore, engine: RepetitionEngine) -> None:
        """When two levels tie, the easier one is returned."""
        store.insert_card(_card(word="Hund", detected_level="A1"))
        store.insert_card(_card(word="Katze", detected_level="C2"))
        assert engine.get_inferred_user_level() == "A1"

    def test_all_levels_present_returns_mode(self, store: CardStore, engine: RepetitionEngine) -> None:
        cards: list[tuple[str, CEFR_LEVELS_TYPE]] = [
            ("w1", "A1"),
            ("w2", "A2"),
            ("w3", "B1"),
            ("w4", "B1"),
            ("w5", "B2"),
            ("w6", "C1"),
            ("w7", "C2"),
        ]
        for word, level in cards:
            store.insert_card(_card(word=word, detected_level=level))
        assert engine.get_inferred_user_level() == "B1"
