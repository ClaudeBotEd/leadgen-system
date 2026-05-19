"""Tests voor ouders_forum source — Ouders.nl deelforum-crawler.

Ouders.nl heeft een "huis-tuin-en-keuken" subforum waar gezinnen praten
over vloerverwarming, airco, zonnepanelen, energie.  Klein-volume maar
hoge intent (consumenten-vragen, geen vendor-ads).

URL-pattern (live geverifieerd 2026-05-15):
  Subforum:  /forum/<sub>           bv. /forum/huis-tuin-en-keuken
  Thread:    /forum/<sub>/<slug>    bv. /forum/huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek
  Paginatie: /forum/<sub>/<slug>?page=N

Anchor-class is `nav-link font-weight-bold p-0` voor threads,
`page-link` voor paginatie — wij filteren via URL-pattern (robuust
tegen skin-wijzigingen).
"""
from __future__ import annotations

from consumer.sources.ouders_forum import _parse_subforum_page, fetch


FIXTURE_SUBFORUM_HTML = """
<html><body>
  <div class="forum-listing">
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek">Hoe omgaan met vloerverwarming en bezoek?</a>
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/hoe-hou-ik-mijn-huis-het-beste-en-betaalbaar-koel">Hoe hou ik mijn huis het beste en betaalbaar koel</a>
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/keuze-energieleverancier-voor-huis-met-zonnepanelen">Keuze energieleverancier voor huis met zonnepanelen</a>
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/glasvezel-kpn-of-odido-kiezen">Glasvezel KPN of Odido kiezen?</a>
    <!-- paginatie: zelfde slug + ?page= → moet genegeerd -->
    <a class="page-link" href="/forum/huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek">1</a>
    <a class="page-link" href="/forum/huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek?page=1">2</a>
    <!-- subforum-index zelf -->
    <a href="/forum/huis-tuin-en-keuken">Huis, tuin en keuken</a>
    <!-- forum index -->
    <a href="/forum">Forum</a>
    <!-- account/profile/login -->
    <a href="/login">Inloggen</a>
    <a href="/profile/jane">Jane</a>
    <!-- duplicate thread (paginatie kan zelfde thread opleveren) -->
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek">Hoe omgaan met vloerverwarming en bezoek?</a>
  </div>
</body></html>
"""


def test_parse_extracts_thread_links() -> None:
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    ids = [p.id for p in posts]
    assert "ouders:huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek" in ids
    assert "ouders:huis-tuin-en-keuken/hoe-hou-ik-mijn-huis-het-beste-en-betaalbaar-koel" in ids
    assert "ouders:huis-tuin-en-keuken/keuze-energieleverancier-voor-huis-met-zonnepanelen" in ids
    assert "ouders:huis-tuin-en-keuken/glasvezel-kpn-of-odido-kiezen" in ids


def test_parse_dedups_within_page() -> None:
    """Dezelfde thread-link tweemaal → één RawPost."""
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    ids = [p.id for p in posts]
    assert ids.count("ouders:huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek") == 1


def test_parse_skips_pagination_links() -> None:
    """Paginatie-anchors wijzen naar `?page=N` of zijn cijfer-titels — geen aparte threads."""
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    for p in posts:
        assert "?page=" not in p.url
        assert p.title not in ("1", "2", "3")


def test_parse_skips_subforum_index() -> None:
    """De subforum-index `/forum/huis-tuin-en-keuken` is geen thread."""
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    for p in posts:
        # Een thread-URL heeft minstens 3 path-segmenten: /forum/<sub>/<slug>
        assert p.url.count("/") >= 5  # https://www.ouders.nl/forum/<sub>/<slug>


def test_parse_skips_non_forum_paths() -> None:
    """Login/profielpagina's zitten niet in /forum/... → niet opgepikt."""
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    for p in posts:
        assert "/login" not in p.url
        assert "/profile/" not in p.url


def test_parse_uses_ouders_source_name() -> None:
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    assert all(p.source == "ouders" for p in posts)


def test_parse_titles_match_anchor_text() -> None:
    posts = _parse_subforum_page(FIXTURE_SUBFORUM_HTML)
    by_id = {p.id: p for p in posts}
    assert by_id["ouders:huis-tuin-en-keuken/hoe-omgaan-met-vloerverwarming-en-bezoek"].title == \
        "Hoe omgaan met vloerverwarming en bezoek?"
    assert by_id["ouders:huis-tuin-en-keuken/glasvezel-kpn-of-odido-kiezen"].title == \
        "Glasvezel KPN of Odido kiezen?"


def test_parse_returns_empty_on_empty_html() -> None:
    assert _parse_subforum_page("") == []
    assert _parse_subforum_page("<html></html>") == []


def test_parse_returns_empty_on_garbage() -> None:
    """Robuustheid: kapotte HTML mag niet crashen."""
    assert _parse_subforum_page("<<<>>not html") == []


def test_fetch_skips_unrecognized_query() -> None:
    """fetch verwacht een /forum/<sub> pad als 'query'.  Niet-pad → graceful []."""
    assert fetch("warmtepomp installateur gezocht", limit=5) == []
    assert fetch("/random/path", limit=5) == []


def test_id_includes_subforum_to_prevent_collision() -> None:
    """Zelfde slug kan in meerdere subforums voorkomen — id moet uniek zijn."""
    html = """
    <a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/over-de-vloer">Over de vloer (HTK)</a>
    <a class="nav-link font-weight-bold p-0" href="/forum/relaties/over-de-vloer">Over de vloer (Relaties)</a>
    """
    posts = _parse_subforum_page(html)
    ids = {p.id for p in posts}
    assert "ouders:huis-tuin-en-keuken/over-de-vloer" in ids
    assert "ouders:relaties/over-de-vloer" in ids
    assert len(posts) == 2


def test_parse_ignores_thread_too_short_title() -> None:
    """Korte/lege titels (< 3 tekens) zijn ruis (icoon-anchors etc.)."""
    html = '<a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/x">A</a>'
    assert _parse_subforum_page(html) == []


def test_parse_skips_new_topic_cta() -> None:
    """`/forum/<sub>/nieuw` is de "Start een nieuw topic"-knop, geen thread."""
    html = '<a class="nav-link font-weight-bold p-0" href="/forum/huis-tuin-en-keuken/nieuw">Start een nieuw topic</a>'
    posts = _parse_subforum_page(html)
    assert posts == []
