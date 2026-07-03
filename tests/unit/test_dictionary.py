"""Unit tests for the OnlineDictionary Wiktionary client."""

from unittest.mock import MagicMock, patch

from echoloop.storage.dictionary import OnlineDictionary


def test_fetch_gender_masculine() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "revisions": [
                        {
                            "slots": {
                                "main": {
                                    "contentmodel": "wikitext",
                                    "contentformat": "text/x-wiki",
                                    "*": "=== {{Wortart|Substantiv|Deutsch}}, {{m}} ===\n|Genus=m",
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    with patch("requests.get", return_value=mock_resp):
        client = OnlineDictionary()
        gender = client.fetch_gender("Hund")
        assert gender == "m"


def test_fetch_gender_feminine() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "query": {
            "pages": {
                "456": {
                    "revisions": [
                        {
                            "slots": {
                                "main": {
                                    "contentmodel": "wikitext",
                                    "contentformat": "text/x-wiki",
                                    "*": "=== {{Wortart|Substantiv|Deutsch}}, {{f}} ===\n|Genus=f",
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
    with patch("requests.get", return_value=mock_resp):
        client = OnlineDictionary()
        gender = client.fetch_gender("Katze")
        assert gender == "f"


def test_fetch_gender_not_found() -> None:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"query": {"pages": {"-1": {"missing": ""}}}}
    with patch("requests.get", return_value=mock_resp):
        client = OnlineDictionary()
        gender = client.fetch_gender("InvalidWord")
        assert gender is None


def test_fetch_definitions_and_pos() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "de": [
            {
                "partOfSpeech": "Noun",
                "definitions": [{"definition": "<a href='/wiki/dog'>dog</a>"}, {"definition": "scoundrel"}],
            }
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        client = OnlineDictionary()
        pos, definitions = client.fetch_definitions_and_pos("Hund")
        assert pos == "Noun"
        assert definitions == ["dog", "scoundrel"]


def test_lookup_full_word() -> None:
    mock_gender_resp = MagicMock()
    mock_gender_resp.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "revisions": [
                        {
                            "slots": {
                                "main": {
                                    "contentmodel": "wikitext",
                                    "contentformat": "text/x-wiki",
                                    "*": "=== {{Wortart|Substantiv|Deutsch}}, {{m}} ===\n|Genus=m",
                                }
                            }
                        }
                    ]
                }
            }
        }
    }

    mock_def_resp = MagicMock()
    mock_def_resp.status_code = 200
    mock_def_resp.json.return_value = {"de": [{"partOfSpeech": "Noun", "definitions": [{"definition": "dog"}]}]}

    def side_effect(url: str, *args: str, **kwargs: str) -> MagicMock:
        _ = args
        _ = kwargs
        if "w/api.php" in url:
            return mock_gender_resp
        return mock_def_resp

    with patch("requests.get", side_effect=side_effect):
        client = OnlineDictionary()
        details = client.lookup("Hund")
        assert details.word == "Hund"
        assert details.part_of_speech == "Noun"
        assert details.gender == "m"
        assert details.get_article() == "der"
        assert details.definitions == ["dog"]
