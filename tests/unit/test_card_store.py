"""Unit tests for the CardStore SQLite adapter.

All tests use an in-memory SQLite database so there are no side-effects
on disk and each test is fully isolated via the ``store`` fixture.
"""

from __future__ import annotations

import datetime

import pytest
from echoloop.storage.adapter import CardStore
from echoloop.storage.models import Card, Example, Review, Synonym


@pytest.fixture()
def store() -> CardStore:
    """Fresh in-memory CardStore for each test."""
    return CardStore(db_path=":memory:")


def _make_card(**kwargs) -> Card:
    defaults = dict(
        word="Hund",
        translation="dog",
        detected_level="A1",
    )
    defaults.update(kwargs)
    return Card(**defaults)


# ---------------------------------------------------------------------------
# cards table
# ---------------------------------------------------------------------------


class TestInsertCard:
    def test_returns_card_with_id(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        assert card.id > 0

    def test_inserted_fields_are_preserved(self, store: CardStore) -> None:
        card = store.insert_card(_make_card(word="Katze", translation="cat", detected_level="A2"))
        assert card.word == "Katze"
        assert card.translation == "cat"
        assert card.detected_level == "A2"

    def test_default_sm2_fields(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.easiness_factor == 2.5
        assert card.interval_days == 1
        assert card.repetitions == 0


class TestGetCard:
    def test_returns_inserted_card(self, store: CardStore) -> None:
        inserted = store.insert_card(_make_card())
        assert inserted.id is not None
        fetched = store.get_card(inserted.id)
        assert fetched is not None
        assert fetched.id == inserted.id
        assert fetched.word == "Hund"

    def test_returns_none_for_missing_id(self, store: CardStore) -> None:
        assert store.get_card(9999) is None


class TestGetCardByWord:
    def test_returns_card_for_known_word(self, store: CardStore) -> None:
        store.insert_card(_make_card())
        card = store.get_card_by_word("Hund")
        assert card is not None
        assert card.word == "Hund"

    def test_returns_none_for_unknown_word(self, store: CardStore) -> None:
        assert store.get_card_by_word("unknown") is None


class TestUpdateCard:
    def test_updated_fields_are_persisted(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        updated = card.model_copy(
            update={
                "easiness_factor": 2.1,
                "interval_days": 6,
                "repetitions": 3,
                "next_review_date": datetime.date(2099, 1, 1),
            }
        )
        store.update_card(updated)
        fetched = store.get_card(card.id)
        assert fetched is not None
        assert fetched.easiness_factor == 2.1
        assert fetched.interval_days == 6
        assert fetched.repetitions == 3
        assert fetched.next_review_date == datetime.date(2099, 1, 1)


class TestListCards:
    def test_returns_all_inserted_cards(self, store: CardStore) -> None:
        store.insert_card(_make_card(word="Hund"))
        store.insert_card(_make_card(word="Katze", translation="cat", detected_level="A2"))
        cards = store.list_cards()
        words = {c.word for c in cards}
        assert words == {"Hund", "Katze"}

    def test_empty_store_returns_empty_list(self, store: CardStore) -> None:
        assert store.list_cards() == []


# ---------------------------------------------------------------------------
# examples table
# ---------------------------------------------------------------------------


class TestExamples:
    def test_insert_and_fetch(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        ex = store.insert_example(Example(card_id=card.id, sentence="Der Hund bellt.", translation="The dog barks."))
        assert ex.id is not None
        examples = store.get_examples_for_card(card.id)
        assert len(examples) == 1
        assert examples[0].sentence == "Der Hund bellt."

    def test_multiple_examples_per_card(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        store.insert_example(Example(card_id=card.id, sentence="S1", translation="T1"))
        store.insert_example(Example(card_id=card.id, sentence="S2", translation="T2"))
        assert len(store.get_examples_for_card(card.id)) == 2

    def test_examples_isolated_by_card(self, store: CardStore) -> None:
        c1 = store.insert_card(_make_card(word="Hund"))
        c2 = store.insert_card(_make_card(word="Katze", translation="cat", detected_level="A2"))
        assert c1.id is not None
        assert c2.id is not None
        store.insert_example(Example(card_id=c1.id, sentence="S1", translation="T1"))
        assert store.get_examples_for_card(c2.id) == []

    def test_cascade_delete_examples_with_card(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        store.insert_example(Example(card_id=card.id, sentence="S1", translation="T1"))
        with store._connection() as conn:
            conn.execute("DELETE FROM cards WHERE id = ?", (card.id,))
        assert store.get_examples_for_card(card.id) == []


# ---------------------------------------------------------------------------
# synonyms table
# ---------------------------------------------------------------------------


class TestSynonyms:
    def test_insert_and_fetch(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        syn = store.insert_synonym(Synonym(card_id=card.id, synonym_word="Köter", translation="mutt"))
        assert syn.id is not None
        synonyms = store.get_synonyms_for_card(card.id)
        assert len(synonyms) == 1
        assert synonyms[0].synonym_word == "Köter"

    def test_cascade_delete_synonyms_with_card(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        store.insert_synonym(Synonym(card_id=card.id, synonym_word="Köter", translation="mutt"))
        with store._connection() as conn:
            conn.execute("DELETE FROM cards WHERE id = ?", (card.id,))
        assert store.get_synonyms_for_card(card.id) == []


# ---------------------------------------------------------------------------
# reviews table
# ---------------------------------------------------------------------------


class TestReviews:
    def test_insert_and_fetch(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        rev = store.insert_review(Review(card_id=card.id, rating_score=4))
        assert rev.id is not None
        reviews = store.get_reviews_for_card(card.id)
        assert len(reviews) == 1
        assert reviews[0].rating_score == 4

    def test_multiple_reviews_ordered_by_timestamp(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        t1 = datetime.datetime(2024, 1, 1, 10, 0, 0)
        t2 = datetime.datetime(2024, 1, 2, 10, 0, 0)
        store.insert_review(Review(card_id=card.id, rating_score=3, timestamp=t2))
        store.insert_review(Review(card_id=card.id, rating_score=5, timestamp=t1))
        reviews = store.get_reviews_for_card(card.id)
        assert reviews[0].rating_score == 5  # t1 is earlier
        assert reviews[1].rating_score == 3

    def test_cascade_delete_reviews_with_card(self, store: CardStore) -> None:
        card = store.insert_card(_make_card())
        assert card.id is not None
        store.insert_review(Review(card_id=card.id, rating_score=2))
        with store._connection() as conn:
            conn.execute("DELETE FROM cards WHERE id = ?", (card.id,))
        assert store.get_reviews_for_card(card.id) == []
