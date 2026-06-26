"""SQLite storage adapter (CardStore).

Responsibilities
----------------
- Create / migrate the schema (4 normalized tables + indices + FK enforcement).
- Provide raw CRUD operations for each table.
- Hide all SQLite-specific details (connection, cursors, row factories, FKs).

Non-responsibilities
--------------------
- No SM-2 calculations.
- No level inference or aggregation.
- No business rules about when a card is "due".
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from loguru import logger

from echoloop.storage.models import Card, Example, Review, Synonym

# Each entry is a single DDL statement executed individually so we stay
# inside our managed transaction context (executescript() issues an implicit
# COMMIT which breaks :memory: test isolation).
_DDL_STATEMENTS = [
    "PRAGMA journal_mode=WAL",
    """CREATE TABLE IF NOT EXISTS cards (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        word             TEXT    NOT NULL UNIQUE,
        translation      TEXT    NOT NULL,
        detected_level   TEXT    NOT NULL CHECK(detected_level IN ('A1','A2','B1','B2','C1','C2')),
        easiness_factor  REAL    NOT NULL DEFAULT 2.5,
        interval_days    INTEGER NOT NULL DEFAULT 1,
        repetitions      INTEGER NOT NULL DEFAULT 0,
        next_review_date TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_cards_next_review ON cards(next_review_date)",
    """CREATE TABLE IF NOT EXISTS examples (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id     INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
        sentence    TEXT    NOT NULL,
        translation TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_examples_card_id ON examples(card_id)",
    """CREATE TABLE IF NOT EXISTS synonyms (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id      INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
        synonym_word TEXT    NOT NULL,
        translation  TEXT    NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_synonyms_card_id ON synonyms(card_id)",
    """CREATE TABLE IF NOT EXISTS reviews (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id      INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
        timestamp    TEXT    NOT NULL,
        rating_score INTEGER NOT NULL CHECK(rating_score BETWEEN 0 AND 5)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_reviews_card_id ON reviews(card_id)",
]


class CardStore:
    """Thin SQLite adapter — raw persistence only, no domain logic.

    For file-backed databases a new connection is opened per operation.
    For ``:memory:`` databases a single persistent connection is reused,
    because each ``sqlite3.connect(':memory:')`` call would produce an
    independent, empty database.
    """

    def __init__(self, db_path: str = "echoloop.db") -> None:
        self._db_path = db_path
        # Keep a persistent connection for in-memory databases so that
        # schema and data survive across method calls.
        self._persistent_conn: sqlite3.Connection | None = None
        if db_path == ":memory:":
            self._persistent_conn = self._open_connection()
        self._init_schema()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_connection(self) -> sqlite3.Connection:
        """Open a new SQLite connection with FK enforcement and a row factory."""
        conn = sqlite3.connect(self._db_path)
        logger.debug(f"Connected to database: {self._db_path}")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection; commit on success, rollback on error.

        For in-memory DBs the persistent connection is reused so that
        schema and data survive across multiple method calls.
        For file DBs a fresh connection is opened and closed per call.
        """
        if self._persistent_conn is not None:
            conn = self._persistent_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        else:
            conn = self._open_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
                logger.debug("Connection closed")

    def _init_schema(self) -> None:
        with self._connection() as conn:
            for stmt in _DDL_STATEMENTS:
                conn.execute(stmt)
        logger.debug("Schema initialized")

    # ------------------------------------------------------------------
    # cards table
    # ------------------------------------------------------------------

    def insert_card(self, card: Card) -> Card:
        """Insert a new card row and return it with the assigned ``id``."""
        sql = """
            INSERT INTO cards
                (word, translation, detected_level, easiness_factor,
                 interval_days, repetitions, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._connection() as conn:
            cur = conn.execute(
                sql,
                (
                    card.word,
                    card.translation,
                    card.detected_level,
                    card.easiness_factor,
                    card.interval_days,
                    card.repetitions,
                    card.next_review_date.isoformat(),
                ),
            )
            return card.model_copy(update={"id": cur.lastrowid})

    def get_card(self, card_id: int) -> Card | None:
        """Return the card with ``card_id``, or ``None`` if not found."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM cards WHERE id = ?", (card_id,)).fetchone()
        return Card(**dict(row)) if row else None

    def get_card_by_word(self, word: str) -> Card | None:
        """Return the card matching ``word`` (unique), or ``None``."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM cards WHERE word = ?", (word,)).fetchone()
        return Card(**dict(row)) if row else None

    def update_card(self, card: Card) -> None:
        """Overwrite the mutable scheduling fields of an existing card."""
        sql = """
            UPDATE cards
               SET translation      = ?,
                   detected_level   = ?,
                   easiness_factor  = ?,
                   interval_days    = ?,
                   repetitions      = ?,
                   next_review_date = ?
             WHERE id = ?
        """
        with self._connection() as conn:
            conn.execute(
                sql,
                (
                    card.translation,
                    card.detected_level,
                    card.easiness_factor,
                    card.interval_days,
                    card.repetitions,
                    card.next_review_date.isoformat(),
                    card.id,
                ),
            )

    def list_cards(self) -> list[Card]:
        """Return all cards ordered by ``next_review_date``."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM cards ORDER BY next_review_date").fetchall()
        return [Card(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # examples table
    # ------------------------------------------------------------------

    def insert_example(self, example: Example) -> Example:
        """Insert an example sentence row and return it with the assigned ``id``."""
        sql = "INSERT INTO examples (card_id, sentence, translation) VALUES (?, ?, ?)"
        with self._connection() as conn:
            cur = conn.execute(sql, (example.card_id, example.sentence, example.translation))
            return example.model_copy(update={"id": cur.lastrowid})

    def get_examples_for_card(self, card_id: int) -> list[Example]:
        """Return all example sentences belonging to ``card_id``."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM examples WHERE card_id = ?", (card_id,)).fetchall()
        return [Example(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # synonyms table
    # ------------------------------------------------------------------

    def insert_synonym(self, synonym: Synonym) -> Synonym:
        """Insert a synonym row and return it with the assigned ``id``."""
        sql = "INSERT INTO synonyms (card_id, synonym_word, translation) VALUES (?, ?, ?)"
        with self._connection() as conn:
            cur = conn.execute(sql, (synonym.card_id, synonym.synonym_word, synonym.translation))
            return synonym.model_copy(update={"id": cur.lastrowid})

    def get_synonyms_for_card(self, card_id: int) -> list[Synonym]:
        """Return all synonyms belonging to ``card_id``."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM synonyms WHERE card_id = ?", (card_id,)).fetchall()
        return [Synonym(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # reviews table
    # ------------------------------------------------------------------

    def insert_review(self, review: Review) -> Review:
        """Insert a review event row and return it with the assigned ``id``."""
        sql = "INSERT INTO reviews (card_id, timestamp, rating_score) VALUES (?, ?, ?)"
        with self._connection() as conn:
            cur = conn.execute(sql, (review.card_id, review.timestamp.isoformat(), review.rating_score))
            return review.model_copy(update={"id": cur.lastrowid})

    def get_reviews_for_card(self, card_id: int) -> list[Review]:
        """Return all review events for ``card_id`` ordered by ``timestamp``."""
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM reviews WHERE card_id = ? ORDER BY timestamp", (card_id,)).fetchall()
        return [Review(**dict(r)) for r in rows]
