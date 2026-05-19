"""Tests for Marketplace listing parser."""
from __future__ import annotations

from pathlib import Path

from consumer.sources.facebook.surfaces.marketplace import parse_marketplace_html
from consumer.sources.facebook.targets import MarketplaceTarget


FIXTURE = Path(__file__).parent / "fixtures" / "fb" / "marketplace_search.html"


def test_parse_returns_all_listings() -> None:
    target = MarketplaceTarget(query="warmtepomp installateur gezocht")
    posts = parse_marketplace_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 2


def test_parse_extracts_title_and_url() -> None:
    target = MarketplaceTarget(query="x")
    posts = parse_marketplace_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    assert "warmtepomp installateur" in posts[0].title.lower()
    assert posts[0].url.endswith("/marketplace/item/1111/")


def test_parse_source_is_marketplace() -> None:
    target = MarketplaceTarget(query="x")
    posts = parse_marketplace_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    for p in posts:
        assert p.source == "facebook_marketplace"
        assert p.id.startswith("facebook_marketplace:")


def test_parse_metadata_includes_query_and_niche() -> None:
    target = MarketplaceTarget(query="warmtepomp gezocht")
    posts = parse_marketplace_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="rid")
    for p in posts:
        assert p.metadata["niche"] == "warmtepomp"
        assert p.metadata["surface"] == "marketplace"
        assert p.metadata["query"] == "warmtepomp gezocht"
        assert p.metadata["run_id"] == "rid"


def test_parse_respects_max_results() -> None:
    target = MarketplaceTarget(query="x", max_results=1)
    posts = parse_marketplace_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 1


def test_parse_empty_results_returns_empty() -> None:
    target = MarketplaceTarget(query="x")
    posts = parse_marketplace_html(
        '<html><body><div aria-label="Marketplace"></div></body></html>',
        target=target, niche="warmtepomp", run_id="t")
    assert posts == []
