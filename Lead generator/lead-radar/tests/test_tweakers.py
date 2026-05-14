"""Tests voor tweakers source — pagination depth + parser robuustheid.

De search-source `/forum/find?keywords=<q>&page=N` filtert client-side
op keyword.  Hoe meer pagina's we crawlen, hoe meer kans op older threads
die de keyword nog steeds matchen.  Tweakers' privacy-gate consent
wordt elders al getest impliciet via integratie — hier alleen contract.
"""
from __future__ import annotations

from consumer.sources import tweakers


def test_max_search_pages_is_exposed_as_constant() -> None:
    """Pagination-diepte moet via module-level constant configureerbaar zijn,
    niet hardcoded inline.  Anders is uitbreiden = code-change met merge-risk."""
    assert hasattr(tweakers, "MAX_SEARCH_PAGES"), (
        "Verwacht MAX_SEARCH_PAGES constant op consumer.sources.tweakers"
    )
    assert isinstance(tweakers.MAX_SEARCH_PAGES, int)


def test_max_search_pages_at_least_five() -> None:
    """Default coverage: minimaal 5 pagina's diep.  Voorheen was dit
    hardcoded op 3 (range(1, 4)) — onvoldoende voor brede niches."""
    assert tweakers.MAX_SEARCH_PAGES >= 5, (
        f"Pagination depth ({tweakers.MAX_SEARCH_PAGES}) onder verwachting "
        f"— tweakers heeft veel oudere threads die nog steeds intent kunnen tonen"
    )


def test_parse_search_extracts_thread_anchors_from_fixture() -> None:
    """Regressie-test: parser herkent /forum/list_messages/<id> anchors."""
    html = """
    <html><body>
      <a href="/forum/list_messages/12345">Warmtepomp installateur in Brabant</a>
      <a href="/forum/list_messages/67890">Daikin altherma ervaringen</a>
      <a href="/forum/categories/12">Energie & Klimaat</a>
      <a href="/profiel/jan">jan</a>
    </body></html>
    """
    posts = tweakers._parse_search(html, query_terms=None)
    ids = [p.id for p in posts]
    assert "tweakers:12345" in ids
    assert "tweakers:67890" in ids
    # Categorie-link is geen thread, profielen ook niet
    for p in posts:
        assert "/forum/list_messages/" in p.url
