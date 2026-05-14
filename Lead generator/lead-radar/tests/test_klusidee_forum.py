"""Tests voor klusidee_forum source — NL DIY-forum deelforum-crawler.

NL-tegenhanger van bouwinfo_forum (BE).  Klusidee.nl draait op XenForo:
  - Subforums: /Forum/forum/<slug>.<id>/
  - Threads:   /Forum/topic/<slug>.<id>/post-<post-id>

Live-geverifieerd 2026-05-14.  Niche → relevante deelfora:
- cv:        cv-ketels-gaskachels-en-geisers.33, verwarming-inclusief-leidingwerk.5
- airco:     elektrisch-verlichting-en-ventilatie.11
- zonnepanelen: elektrisch-verlichting-en-ventilatie.11
- renovatie: draagconstructie.13, binnenmuren-wanden-en-plafonds.8,
             badkamer-waterleiding-en-afvoer.2, keuken.3, dak-en-schoorsteen.4
"""
from __future__ import annotations

from consumer.sources.klusidee_forum import _parse_category_page, fetch


FIXTURE_SUBFORUM_HTML = """
<html><body>
  <div class="forum-listing">
    <a href="/Forum/topic/cv-ketel-vervangen-advies.172076/">CV-ketel vervangen, advies gezocht</a>
    <a href="/Forum/topic/warmtepomp-installateur-zoeken.172100/post-1083500">Warmtepomp installateur zoeken</a>
    <a href="/Forum/topic/zonnepanelen-omvormer-vraag.171999/">Zonnepanelen omvormer keuze</a>
    <a href="/Forum/topic/badkamer-renovatie-aannemer.172050/post-1083100">Badkamer renovatie aannemer</a>
    <!-- niet-thread links moeten genegeerd worden -->
    <a href="/Forum/forum/cv-ketels-gaskachels-en-geisers.33/">CV-ketels deelforum</a>
    <a href="/Forum/members/jan.123/">Profielpagina jan</a>
    <a href="/Forum/">Forum index</a>
    <!-- duplicate (paginatie kan zelfde thread opleveren) -->
    <a href="/Forum/topic/cv-ketel-vervangen-advies.172076/">CV-ketel vervangen, advies gezocht</a>
  </div>
</body></html>
"""


def test_parse_extracts_thread_links() -> None:
    posts = _parse_category_page(FIXTURE_SUBFORUM_HTML)
    ids = [p.id for p in posts]
    assert "klusidee:172076" in ids
    assert "klusidee:172100" in ids
    assert "klusidee:171999" in ids
    assert "klusidee:172050" in ids


def test_parse_dedups_within_page() -> None:
    """Dezelfde thread-link tweemaal → één RawPost."""
    posts = _parse_category_page(FIXTURE_SUBFORUM_HTML)
    ids = [p.id for p in posts]
    assert ids.count("klusidee:172076") == 1


def test_parse_skips_non_thread_links() -> None:
    """Subforum-link, profielpagina, forum-index: niet-threads."""
    posts = _parse_category_page(FIXTURE_SUBFORUM_HTML)
    for p in posts:
        assert "/Forum/topic/" in p.url
        assert "/Forum/forum/" not in p.url
        assert "/Forum/members/" not in p.url


def test_parse_captures_title_text() -> None:
    posts = _parse_category_page(FIXTURE_SUBFORUM_HTML)
    by_id = {p.id: p for p in posts}
    assert by_id["klusidee:172076"].title == "CV-ketel vervangen, advies gezocht"
    assert by_id["klusidee:171999"].title == "Zonnepanelen omvormer keuze"


def test_parse_uses_klusidee_source_name() -> None:
    posts = _parse_category_page(FIXTURE_SUBFORUM_HTML)
    assert all(p.source == "klusidee" for p in posts)


def test_parse_returns_empty_on_empty_html() -> None:
    assert _parse_category_page("") == []
    assert _parse_category_page("<html></html>") == []


def test_parse_returns_empty_on_garbage() -> None:
    """Robuustheid: kapotte HTML mag niet crashen."""
    assert _parse_category_page("<<<>>not html") == []


def test_fetch_skips_unrecognized_query() -> None:
    """fetch verwacht een subforum-pad als 'query'.  Niet-pad → graceful []."""
    posts = fetch("warmtepomp installateur gezocht", limit=5)
    assert posts == []


def test_parse_extracts_id_from_xenforo_dot_id_pattern() -> None:
    """XenForo packt id in URL als <slug>.<id>/  — moet correct gepluct worden."""
    html = '<a href="/Forum/topic/my-thread-title.42/">Test</a>'
    posts = _parse_category_page(html)
    assert len(posts) == 1
    assert posts[0].id == "klusidee:42"
