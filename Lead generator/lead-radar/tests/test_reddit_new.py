"""Tests voor reddit_new source — direct /r/<sub>/new.json crawler.

Verschil met de bestaande reddit.py (search-based):
- reddit.py:     /r/<sub>/search.json?q=<query>&restrict_sr=on
- reddit_new.py: /r/<sub>/new.json?limit=<n>  (geen query)

Voor HIGH-INTENT subs (r/Klussers, r/Offertes, r/DIYNL) is keyword-
filtering contraproductief — bijna elke post is een intent-signaal.
Deze source pakt ALLE recente posts en laat hardblock/scorer filteren.

Hergebruikt reddit._parse_listing zodat JSON-parsing on één plek staat.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from consumer.sources import reddit_new


SAMPLE_LISTING = {
    "data": {
        "children": [
            {"data": {
                "id": "abc123",
                "permalink": "/r/Klussers/comments/abc123/wie_kan_warmtepomp/",
                "url": "https://www.reddit.com/r/Klussers/comments/abc123/",
                "title": "Wie kan een warmtepomp installeren in Antwerpen?",
                "selftext": "Onze gasketel is kapot, willen overstappen.",
                "author": "huiseigenaar22",
                "created_utc": 1700000000,
                "subreddit": "Klussers",
                "score": 5,
            }},
            {"data": {
                "id": "def456",
                "permalink": "/r/Klussers/comments/def456/badkamer/",
                "url": "https://www.reddit.com/r/Klussers/comments/def456/",
                "title": "Offerte badkamer renovatie",
                "selftext": "",
                "author": "renovator99",
                "created_utc": 1700001000,
                "subreddit": "Klussers",
                "score": 3,
            }},
        ]
    }
}


def _mock_session(json_payload: dict) -> MagicMock:
    """PoliteSession-vervanger die ALLE GET-calls beantwoordt met json_payload."""
    sess = MagicMock()
    resp = MagicMock()
    resp.json.return_value = json_payload
    sess.get.return_value = resp
    return sess


def test_fetch_dispatches_to_new_json_endpoint() -> None:
    """fetch('Klussers') moet GET doen naar /r/Klussers/new.json"""
    sess = _mock_session(SAMPLE_LISTING)
    reddit_new.fetch("Klussers", limit=10, session=sess)
    sess.get.assert_called_once()
    called_url = sess.get.call_args[0][0]
    assert called_url == "https://www.reddit.com/r/Klussers/new.json"


def test_fetch_returns_rawposts_with_reddit_source() -> None:
    """Source-naam blijft 'reddit' — gedeelde dedup-namespace met search-source."""
    sess = _mock_session(SAMPLE_LISTING)
    posts = reddit_new.fetch("Klussers", limit=10, session=sess)
    assert len(posts) == 2
    for p in posts:
        assert p.source == "reddit"
        assert p.id in {"abc123", "def456"}


def test_fetch_captures_metadata() -> None:
    sess = _mock_session(SAMPLE_LISTING)
    posts = reddit_new.fetch("Klussers", limit=10, session=sess)
    by_id = {p.id: p for p in posts}
    assert by_id["abc123"].author == "huiseigenaar22"
    assert by_id["abc123"].metadata["subreddit"] == "Klussers"
    assert "warmtepomp" in by_id["abc123"].title.lower()


def test_fetch_strips_r_prefix_in_sub_name() -> None:
    """Operator mag 'r/Klussers' of 'Klussers' typen — URL moet identiek zijn."""
    sess = _mock_session(SAMPLE_LISTING)
    reddit_new.fetch("r/Klussers", limit=10, session=sess)
    called_url = sess.get.call_args[0][0]
    assert called_url == "https://www.reddit.com/r/Klussers/new.json"


def test_fetch_returns_empty_on_empty_query() -> None:
    """Lege sub-naam → geen request, lege lijst."""
    sess = _mock_session(SAMPLE_LISTING)
    assert reddit_new.fetch("", limit=10, session=sess) == []
    assert reddit_new.fetch("   ", limit=10, session=sess) == []
    sess.get.assert_not_called()


def test_fetch_respects_limit() -> None:
    sess = _mock_session(SAMPLE_LISTING)
    posts = reddit_new.fetch("Klussers", limit=1, session=sess)
    assert len(posts) == 1


def test_fetch_returns_empty_on_none_response() -> None:
    """Als sess.get None returnt (rate-limit, timeout) → []."""
    sess = MagicMock()
    sess.get.return_value = None
    assert reddit_new.fetch("Klussers", limit=10, session=sess) == []


def test_fetch_returns_empty_on_bad_json() -> None:
    sess = MagicMock()
    resp = MagicMock()
    resp.json.side_effect = ValueError("not json")
    sess.get.return_value = resp
    assert reddit_new.fetch("Klussers", limit=10, session=sess) == []
