"""Tests voor google/DDG source URL-filtering en rate-limit guard.

_is_post_url() is een whitelist op forum-achtige URL-substrings.
Als we site:<nieuw-domein> queries toevoegen aan queries.yaml moet
het filter die domeinen ook accepteren — anders worden alle hits
silent geskipt en levert de site: query 0 leads op.

Rate-limit guard: bij --daily --locations all worden 1000+ DDG-calls
gedaan en gaat DDG zeker throttlen.  Na 2× RatelimitException blijven
alle volgende calls hangen op interne backoff (geen timeout).  Guard
skipt vroeg om cascade te voorkomen.
"""
from __future__ import annotations

import pytest

from consumer.sources.google import _is_post_url


@pytest.mark.parametrize("url", [
    "https://www.ecobouwers.be/forum/warmtepomp-advies",
    "https://ecobouwers.be/forum/topic/welke-warmtepomp-installateur",
])
def test_is_post_url_accepts_ecobouwers_forum(url: str) -> None:
    """Ecobouwers.be is een BE sustainable-building forum — moet als post-URL tellen."""
    assert _is_post_url(url), f"Ecobouwers forum-URL onterecht geskipt: {url}"


@pytest.mark.parametrize("url", [
    "https://www.reddit.com/r/thenetherlands/comments/abc/",
    "https://gathering.tweakers.net/forum/list_messages/12345",
    "https://www.bouwinfo.be/topic/123",
    "https://www.facebook.com/groups/warmtepomp-nl/posts/xyz",
])
def test_is_post_url_existing_patterns_still_match(url: str) -> None:
    """Regressie: bestaande forum-domeinen blijven match'en."""
    assert _is_post_url(url), f"Bestaand forum-patroon brak: {url}"


@pytest.mark.parametrize("url", [
    "https://www.vaillant.nl/producten/warmtepompen/",
    "https://daikin.nl/airconditioning/",
    "https://example-vendor.nl/contact",
    "",
])
def test_is_post_url_rejects_non_forum(url: str) -> None:
    """Vendor homepages en lege URLs zijn géén leads — moeten geskipt blijven."""
    assert not _is_post_url(url), f"Niet-forum URL onterecht geaccepteerd: {url}"


# ─── Rate-limit guard ────────────────────────────────────────────────────


def test_reset_ratelimit_state_exists() -> None:
    """API moet reset-functie hebben om state per run te clearen."""
    from consumer.sources.google import reset_ratelimit_state
    reset_ratelimit_state()  # should not raise


def test_fetch_skips_after_ratelimit_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Na 2× RatelimitException: 3e en volgende fetch-calls returnen [] zonder DDG aan te roepen.

    Voorkomt dat 1380 DDG-calls allemaal door 10s+ backoff gaan wanneer
    DDG ons al heeft geblokt.
    """
    from consumer.sources import google as google_mod
    from duckduckgo_search.exceptions import RatelimitException

    google_mod.reset_ratelimit_state()

    call_log: list[str] = []

    class FakeDDGS:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def text(self, q, **_):  # noqa: ANN001
            call_log.append(q)
            raise RatelimitException("simulated 429")

    monkeypatch.setattr(google_mod, "DDGS", FakeDDGS)
    monkeypatch.setattr(google_mod, "_HAS_DDG", True)

    google_mod.fetch("query A", limit=10)
    google_mod.fetch("query B", limit=10)
    # Threshold reached — 3e call moet NIET DDG raken
    google_mod.fetch("query C", limit=10)
    google_mod.fetch("query D", limit=10)

    assert call_log == ["query A", "query B"], (
        f"Verwacht 2 DDG-calls (de 2 die rate-limit hitten); kreeg {call_log}"
    )


def test_fetch_succeeds_before_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vóór 2× rate-limit blijft fetch gewoon werken."""
    from consumer.sources import google as google_mod

    google_mod.reset_ratelimit_state()

    class FakeDDGS:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def text(self, q, **_):  # noqa: ANN001
            return [{"href": "https://reddit.com/r/test/abc",
                     "title": "test", "body": "snippet"}]

    monkeypatch.setattr(google_mod, "DDGS", FakeDDGS)
    monkeypatch.setattr(google_mod, "_HAS_DDG", True)

    result = google_mod.fetch("query", limit=10)
    assert len(result) == 1
    assert result[0].url == "https://reddit.com/r/test/abc"


def test_reset_ratelimit_state_clears_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reset moet rate-limit counter terug op 0 zetten — voor nieuwe runs."""
    from consumer.sources import google as google_mod
    from duckduckgo_search.exceptions import RatelimitException

    google_mod.reset_ratelimit_state()

    class FakeDDGS:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def text(self, q, **_):  # noqa: ANN001
            raise RatelimitException("simulated 429")

    monkeypatch.setattr(google_mod, "DDGS", FakeDDGS)
    monkeypatch.setattr(google_mod, "_HAS_DDG", True)

    # Triggers state
    google_mod.fetch("q1", limit=10)
    google_mod.fetch("q2", limit=10)
    # Skip-mode active
    google_mod.fetch("q3", limit=10)

    # Reset → moet weer DDG aan willen roepen
    google_mod.reset_ratelimit_state()

    call_log: list[str] = []

    class CountingDDGS:
        def __init__(self, *a, **kw):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def text(self, q, **_):  # noqa: ANN001
            call_log.append(q)
            return []

    monkeypatch.setattr(google_mod, "DDGS", CountingDDGS)
    google_mod.fetch("q-post-reset", limit=10)
    assert call_log == ["q-post-reset"], f"Na reset zou DDG weer geraakt moeten worden; calls={call_log}"
