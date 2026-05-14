"""Tests voor google/DDG source URL-filtering.

_is_post_url() is een whitelist op forum-achtige URL-substrings.
Als we site:<nieuw-domein> queries toevoegen aan queries.yaml moet
het filter die domeinen ook accepteren — anders worden alle hits
silent geskipt en levert de site: query 0 leads op.
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
