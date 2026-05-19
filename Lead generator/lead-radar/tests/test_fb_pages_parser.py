"""Tests for Pages parser -- same DOM as Groups but surface=pages."""
from __future__ import annotations

from pathlib import Path

from consumer.sources.facebook.surfaces.pages import parse_pages_feed_html
from consumer.sources.facebook.targets import PageTarget


FIXTURE = Path(__file__).parent / "fixtures" / "fb" / "pages_feed.html"


def test_parse_returns_all_articles() -> None:
    target = PageTarget(slug="warmtepompvergelijken", name="WPV NL", max_posts=10)
    posts = parse_pages_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                   target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 2


def test_parse_source_is_pages() -> None:
    target = PageTarget(slug="warmtepompvergelijken", name="WPV", max_posts=10)
    posts = parse_pages_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                   target=target, niche="warmtepomp", run_id="t")
    for p in posts:
        assert p.source == "facebook_pages"
        assert p.id.startswith("facebook_pages:")


def test_parse_metadata_includes_page_slug() -> None:
    target = PageTarget(slug="warmtepompvergelijken", name="Warmtepomp Vergelijken", max_posts=10)
    posts = parse_pages_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                   target=target, niche="warmtepomp", run_id="rid")
    for p in posts:
        assert p.metadata["niche"] == "warmtepomp"
        assert p.metadata["page_slug"] == "warmtepompvergelijken"
        assert p.metadata["page_name"] == "Warmtepomp Vergelijken"
        assert p.metadata["surface"] == "pages"
        assert p.metadata["run_id"] == "rid"


def test_parse_extracts_post_text() -> None:
    target = PageTarget(slug="warmtepompvergelijken", name="WPV", max_posts=10)
    posts = parse_pages_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                   target=target, niche="warmtepomp", run_id="t")
    assert "8kw warmtepomp" in posts[0].text.lower()


def test_parse_respects_max_posts() -> None:
    target = PageTarget(slug="x", name="x", max_posts=1)
    posts = parse_pages_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                   target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 1
