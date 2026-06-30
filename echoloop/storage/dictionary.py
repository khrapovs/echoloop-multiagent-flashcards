"""Online Wiktionary API client for resolving definitions and grammatical genders."""

import re
from typing import Any

import requests

# Standard headers to comply with Wikimedia's API usage policy
USER_AGENT = "EchoLoop/1.0 (khrapovs@gmail.com; Kaggle Capstone Project)"
HEADERS = {"User-Agent": USER_AGENT}


class GermanWordDetails:
    """Represents resolved lexical metadata for a German word."""

    def __init__(
        self,
        word: str,
        part_of_speech: str = "Unknown",
        gender: str | None = None,
        definitions: list[str] | None = None,
    ) -> None:
        self.word = word
        self.part_of_speech = part_of_speech
        self.gender = gender  # "m" (masculine), "f" (feminine), "n" (neuter), or None
        self.definitions = definitions or []

    def get_article(self) -> str:
        """Return the German definite article matching the word's gender, if applicable."""
        if self.part_of_speech.lower() != "noun":
            return ""
        if self.gender == "m":
            return "der"
        if self.gender == "f":
            return "die"
        if self.gender == "n":
            return "das"
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert the word details to a JSON-serializable dictionary."""
        return {
            "word": self.word,
            "part_of_speech": self.part_of_speech,
            "gender": self.gender,
            "article": self.get_article(),
            "definitions": self.definitions,
        }


class OnlineDictionary:
    """Client for retrieving dictionary metadata from Wiktionary APIs."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout = timeout_seconds

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags from definition snippets."""
        return re.sub(r"<[^>]+>", "", text).strip()

    def fetch_gender(self, word: str) -> str | None:
        """Query the German Wiktionary to extract grammatical gender from wikitext."""
        try:
            url = "https://de.wiktionary.org/w/api.php"
            params = {
                "action": "query",
                "prop": "revisions",
                "titles": word,
                "rvslots": "*",
                "rvprop": "content",
                "format": "json",
            }
            resp = requests.get(url, params=params, headers=HEADERS, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None

            # Extract revision text
            page_id = list(pages.keys())[0]
            if page_id == "-1":  # Word not found in German Wiktionary
                return None

            revisions = pages[page_id].get("revisions", [])
            if not revisions:
                return None

            wikitext = revisions[0].get("slots", {}).get("main", {}).get("*", "")
            if not wikitext:
                return None

            # 1. Look for Genus template parameter (e.g. Genus=m, Genus=f, Genus=n)
            genus_match = re.search(r"\|\s*Genus\s*=\s*([mfn])", wikitext, re.IGNORECASE)
            if genus_match:
                return genus_match.group(1).lower()

            # 2. Look for Part of Speech header gender tag (e.g. === {{Wortart|Substantiv|Deutsch}}, {{m}} ===)
            if re.search(r"Wortart\|Substantiv\|Deutsch.*\{\{m\}\}", wikitext, re.IGNORECASE):
                return "m"
            if re.search(r"Wortart\|Substantiv\|Deutsch.*\{\{f\}\}", wikitext, re.IGNORECASE):
                return "f"
            if re.search(r"Wortart\|Substantiv\|Deutsch.*\{\{n\}\}", wikitext, re.IGNORECASE):
                return "n"

            return None
        except Exception:
            # Degrade gracefully on network timeouts/parsing failures
            return None

    def fetch_definitions_and_pos(self, word: str) -> tuple[str, list[str]]:
        """Query the English Wiktionary REST API for English definitions and Part of Speech."""
        try:
            url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{word}"
            resp = requests.get(url, headers=HEADERS, timeout=self.timeout)
            if resp.status_code == 404:
                return "Unknown", []
            resp.raise_for_status()
            data = resp.json()

            # The response maps language codes to entries. German code is "de".
            entries = data.get("de")
            if not entries:
                # Fallback: check "other" or take first language entry available
                entries = data.get("other") or list(data.values())[0]

            if not entries:
                return "Unknown", []

            entry = entries[0]
            part_of_speech = entry.get("partOfSpeech", "Unknown")

            definitions = []
            for d in entry.get("definitions", []):
                def_text = d.get("definition", "")
                if def_text:
                    clean_def = self._strip_html(def_text)
                    if clean_def:
                        definitions.append(clean_def)

            return part_of_speech, definitions
        except Exception:
            return "Unknown", []

    def lookup(self, word: str) -> GermanWordDetails:
        """Resolve full dictionary details for the word, combining definitions and gender."""
        pos, definitions = self.fetch_definitions_and_pos(word)
        gender = None
        if pos.lower() == "noun":
            gender = self.fetch_gender(word)
        return GermanWordDetails(
            word=word,
            part_of_speech=pos,
            gender=gender,
            definitions=definitions,
        )
