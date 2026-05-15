"""Tests voor bouwinfo_forum source — directe deelforum-crawl.

Aanvulling op de bestaande bouwinfo.py search-source: in plaats van
het lukrake `/?s=<query>` zoekendpoint crawlen we hier de
`/categories/<path>` pagina's voor RECENTE topics in niche-specifieke
deelfora (warmtepompen, zonne-energie, sanitair, isolatie, etc.).

Thread-URLs hebben format `/bouwforum/threads/<id>` (geverifieerd via
live page-inspect 2026-05-14).
"""
from __future__ import annotations

from consumer.sources.bouwinfo_forum import _parse_category_page, fetch


FIXTURE_CATEGORY_HTML = """
<html><body>
  <div class="category-container">
    <a href="/bouwforum/threads/416681">Plaatsing airco's in slaapkamer</a>
    <a href="/bouwforum/threads/416649">Vervanging gasketel</a>
    <a href="/bouwforum/threads/416641">daikin altherma regeling temperatuur</a>
    <a href="/bouwforum/threads/416472">Warmtepomp efficient sturen</a>
    <!-- niet-thread links moeten genegeerd worden -->
    <a href="/categories/technieken/verwarming-en-koeling">Verwarming</a>
    <a href="/profiel/john">john</a>
    <a href="/bouwforum">Forum index</a>
    <!-- dezelfde thread tweemaal (paginatie/duplicaten) -->
    <a href="/bouwforum/threads/416681">Plaatsing airco's in slaapkamer</a>
  </div>
</body></html>
"""


def test_parse_category_extracts_thread_links() -> None:
    """Pluckt alleen /bouwforum/threads/<id> anchors, niet category/profile links."""
    posts = _parse_category_page(FIXTURE_CATEGORY_HTML)
    ids = [p.id for p in posts]
    assert "bouwinfo:416681" in ids
    assert "bouwinfo:416649" in ids
    assert "bouwinfo:416641" in ids
    assert "bouwinfo:416472" in ids


def test_parse_category_dedups_within_page() -> None:
    """Dezelfde thread-link tweemaal in HTML → één RawPost."""
    posts = _parse_category_page(FIXTURE_CATEGORY_HTML)
    ids = [p.id for p in posts]
    assert ids.count("bouwinfo:416681") == 1


def test_parse_category_skips_non_thread_links() -> None:
    """Category-link, profile-link, forum-index moeten genegeerd worden."""
    posts = _parse_category_page(FIXTURE_CATEGORY_HTML)
    urls = [p.url for p in posts]
    assert not any("/categories/" in u for u in urls)
    assert not any("/profiel/" in u for u in urls)
    # Forum-index zou matchen op '/bouwforum' maar mist /threads/<id>
    assert not any(u.endswith("/bouwforum") for u in urls)


def test_parse_category_captures_title_text() -> None:
    posts = _parse_category_page(FIXTURE_CATEGORY_HTML)
    by_id = {p.id: p for p in posts}
    assert by_id["bouwinfo:416641"].title == "daikin altherma regeling temperatuur"


def test_parse_category_uses_bouwinfo_source_name() -> None:
    """RawPost.source moet 'bouwinfo' zijn (zelfde dedup-namespace als
    de search-source — duplicaten cross-strategie worden gevangen)."""
    posts = _parse_category_page(FIXTURE_CATEGORY_HTML)
    assert all(p.source == "bouwinfo" for p in posts)


def test_parse_category_returns_empty_on_empty_html() -> None:
    assert _parse_category_page("") == []
    assert _parse_category_page("<html></html>") == []


def test_parse_category_returns_empty_on_garbage() -> None:
    """Robuustheid: kapotte HTML mag niet crashen."""
    assert _parse_category_page("<<<>>not html") == []


def test_fetch_skips_unrecognized_query() -> None:
    """fetch verwacht een category-pad als 'query'.  Onbekend formaat
    (bv. een normale zoekterm) returnt graceful een lege lijst — geen
    crash, geen onbedoelde requests."""
    posts = fetch("warmtepomp installateur gezocht", limit=5)
    assert posts == []


# ─── Regressie: absolute thread URLs (Bouwinfo mei-2026 layout) ─────────


ABSOLUTE_URL_HTML = """
<html><body>
  <a href="https://www.bouwinfo.be/bouwforum/threads/416681">Plaatsing airco's in slaapkamer</a>
  <a href="https://www.bouwinfo.be/bouwforum/threads/416649">Vervanging gasketel</a>
  <a href="https://www.bouwinfo.be/bouwforum/threads/416641/latest">daikin altherma regeling temperatuur</a>
</body></html>
"""


def test_parse_category_handles_absolute_thread_urls() -> None:
    """Bouwinfo rendert sinds mei-2026 absolute URLs in category pages.
    Parser moest oorspronkelijk relatieve hrefs (anchored regex .match);
    nu accepteert hij ook https-prefix dankzij flexible regex."""
    posts = _parse_category_page(ABSOLUTE_URL_HTML)
    ids = [p.id for p in posts]
    assert "bouwinfo:416681" in ids
    assert "bouwinfo:416649" in ids
    assert "bouwinfo:416641" in ids
