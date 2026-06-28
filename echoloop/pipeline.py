"""AgentPipeline — orchestrates the two-agent card-generation flow.

Responsibilities
----------------
- Run :class:`~echoloop.agents.synonyms_agent.SynonymsAgent` once on an
  entered word to produce a list of synonym candidates.
- Run :class:`~echoloop.agents.root_agent.ContextAgent` for each
  user-selected word (original + checked synonyms) and yield a
  :class:`FlashcardResult` as each call completes (streaming to the caller).
- Skip words already present in ``CardStore`` (status ``"skipped"``).
- Capture per-word failures without aborting the whole batch
  (status ``"failed"``).

Non-responsibilities
--------------------
- No direct UI concerns — yielding results is the only "streaming" contract.
- No database writes — the caller (UI layer) persists each result.
- No SM-2 logic — level inference is delegated to ``RepetitionEngine``.

Usage example
-------------
>>> pipeline = AgentPipeline(store=card_store, engine=repetition_engine)
>>> synonyms = pipeline.get_synonyms("schlafen")
>>> selected = [synonyms.original_word] + [s.synonym_word for s in synonyms.synonyms]
>>> for result in pipeline.generate_card_batch(selected):
...     if result.status == "saved":
...         persist(result.card)
"""

from collections.abc import Iterator
from typing import Literal

from pydantic import BaseModel

from echoloop.agents.root_agent import FlashcardContext
from echoloop.agents.synonyms_agent import SynonymsOutput
from echoloop.repetition_engine import RepetitionEngine
from echoloop.runner import run_context_agent, run_synonyms_agent
from echoloop.storage.adapter import CardStore


class FlashcardResult(BaseModel):
    """The outcome of one word in a :meth:`AgentPipeline.generate_card_batch` run.

    Attributes:
        word:   The German word that was processed.
        card:   The generated :class:`FlashcardContext`, or ``None`` when the
                word was skipped or the agent call failed.
        status: One of ``"saved"``, ``"skipped"``, or ``"failed"``.
        error:  Human-readable error message when ``status == "failed"``.

    """

    word: str
    card: FlashcardContext | None = None
    status: Literal["saved", "skipped", "failed"]
    error: str | None = None


class AgentPipeline:
    """Orchestrates the two-step card-generation flow.

    Args:
        store:  A :class:`~echoloop.storage.adapter.CardStore` used to check
                for existing cards.  The pipeline never writes to the store —
                it only reads to decide whether to skip a word.
        engine: A :class:`~echoloop.repetition_engine.RepetitionEngine` used
                to infer the current user level once per batch.

    """

    def __init__(self, store: CardStore, engine: RepetitionEngine) -> None:
        self._store = store
        self._engine = engine

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_synonyms(self, word: str) -> SynonymsOutput:
        """Fetch synonyms for *word* via :func:`~echoloop.runner.run_synonyms_agent`.

        Args:
            word: A German vocabulary word.

        Returns:
            A :class:`~echoloop.agents.synonyms_agent.SynonymsOutput` containing
            the original word and up to 5 synonyms.

        """
        return run_synonyms_agent(word)

    def generate_card_batch(self, words: list[str]) -> Iterator[FlashcardResult]:
        """Generate flashcards for each word in *words*, yielding results as they arrive.

        The user CEFR level is inferred once before the loop starts and reused
        for every :class:`~echoloop.agents.root_agent.ContextAgent` call in the
        batch for consistency.

        Words that are already present in ``CardStore`` produce a
        ``status="skipped"`` result without calling the agent.  Agent failures
        produce a ``status="failed"`` result with a descriptive ``error``
        message; the batch continues for remaining words.

        Args:
            words: Ordered list of German words to generate cards for.
                   Typically ``[original_word] + [s.synonym_word for s in synonyms]``
                   after the user has deselected unwanted candidates.

        Yields:
            One :class:`FlashcardResult` per word, in the same order as *words*.

        """
        inferred_level = self._engine.get_inferred_user_level()

        for word in words:
            existing = self._store.get_card_by_word(word)
            if existing is not None:
                yield FlashcardResult(word=word, status="skipped")
                continue

            try:
                card = run_context_agent(word, inferred_level=inferred_level)
                yield FlashcardResult(word=word, card=card, status="saved")
            except Exception as exc:  # noqa: BLE001
                yield FlashcardResult(word=word, status="failed", error=str(exc))
