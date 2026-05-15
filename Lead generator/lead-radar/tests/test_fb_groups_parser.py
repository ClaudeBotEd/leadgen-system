"""Tests for the Groups DOM parser using BeautifulSoup on a static fixture.

The parser logic is split out from the Playwright-driving scrape() method so
we can unit-test it without launching a browser.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.sources.facebook.surfaces.groups import parse_groups_feed_html
from consumer.sources.facebook.targets import GroupTarget


FIXTURE = Path(__file__).parent / "fixtures" / "fb" / "groups_feed.html"


def test_parse_returns_all_articles() -> None:
    target = GroupTarget(id="123456789", name="Warmtepomp NL Ervaringen", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t1")
    assert len(posts) == 3


def test_parse_extracts_text() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t1")
    assert "warmtepomp installateur" in posts[0].text.lower()
    assert "offerte gekregen" in posts[1].text.lower()


def test_parse_extracts_author() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t1")
    assert posts[0].author == "Jan de Vries"
    assert posts[1].author == "Marie Peters"


def test_parse_extracts_post_url() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t1")
    assert posts[0].url.endswith("/groups/123456789/posts/987654321/")


def test_parse_sets_source_to_facebook_groups() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t1")
    for p in posts:
        assert p.source == "facebook_groups"
        assert p.id.startswith("facebook_groups:")


def test_parse_metadata_includes_niche_and_group() -> None:
    target = GroupTarget(id="123456789", name="Warmtepomp NL Ervaringen", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="run-x")
    for p in posts:
        assert p.metadata["niche"] == "warmtepomp"
        assert p.metadata["group_id"] == "123456789"
        assert p.metadata["group_name"] == "Warmtepomp NL Ervaringen"
        assert p.metadata["surface"] == "groups"
        assert p.metadata["run_id"] == "run-x"


def test_parse_respects_max_posts_cap() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=2)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 2


def test_parse_empty_feed_returns_empty_list() -> None:
    target = GroupTarget(id="1", name="empty", max_posts=10)
    posts = parse_groups_feed_html(
        "<html><body><div role='feed'></div></body></html>",
        target=target, niche="warmtepomp", run_id="t")
    assert posts == []


def test_parse_post_with_no_text_is_skipped() -> None:
    """Articles without any [data-ad-preview=message] or fallback text are dropped."""
    html = """
    <html><body><div role="feed">
      <div role="article">
        <strong><a role="link" href="/x">X</a></strong>
        <a href="/groups/1/posts/2/"><span>1u</span></a>
        <!-- no message div -->
      </div>
    </div></body></html>
    """
    target = GroupTarget(id="1", name="t", max_posts=10)
    posts = parse_groups_feed_html(html, target=target, niche="warmtepomp", run_id="t")
    assert posts == []


def test_parse_includes_title_from_first_line() -> None:
    target = GroupTarget(id="123456789", name="WP NL", max_posts=10)
    posts = parse_groups_feed_html(FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="t")
    assert posts[0].title.startswith("Wie kent een goede warmtepomp installateur")


# -- Real-fixture acceptance test ------------------------------------------
# This test validates the parser against operator-captured live FB HTML.
# It is skipped if the real fixture does not exist (so the test suite stays
# green in environments without operator setup), but if the fixture IS
# present, the parser MUST extract at least 1 post -- otherwise our DOM
# selectors are wrong against the real FB DOM and we'd silently ship a
# broken scraper.
REAL_FIXTURE = Path(__file__).parent / "fixtures" / "fb" / "groups_feed_real_001.html"


@pytest.mark.skipif(not REAL_FIXTURE.exists(),
                    reason="real FB fixture not captured yet -- run Task 9 Step 0")
def test_parse_real_fixture_extracts_at_least_one_post() -> None:
    """If a real captured HTML fixture exists, the parser MUST work on it."""
    target = GroupTarget(id="0", name="real fixture", max_posts=50)
    posts = parse_groups_feed_html(REAL_FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="real")
    assert len(posts) >= 1, (
        "Parser extracted 0 posts from real FB HTML -- DOM selectors in "
        "_selectors.py are likely wrong against current FB.  Inspect the "
        "fixture and update FEED_CONTAINER / POST_ARTICLE / POST_TEXT_* "
        "before continuing."
    )


@pytest.mark.skipif(not REAL_FIXTURE.exists(),
                    reason="real FB fixture not captured yet -- run Task 9 Step 0")
def test_parse_real_fixture_posts_have_text() -> None:
    """Every extracted post from real FB must have non-empty text."""
    target = GroupTarget(id="0", name="real fixture", max_posts=50)
    posts = parse_groups_feed_html(REAL_FIXTURE.read_text(encoding="utf-8"),
                                    target=target, niche="warmtepomp", run_id="real")
    for p in posts:
        assert p.text.strip(), "extracted post has empty text -- selector matches container but not body"


def test_parse_graphql_response_extracts_posts() -> None:
    from consumer.sources.facebook.surfaces.groups import parse_groups_graphql_response

    response = {
        "data": {
            "node": {
                "group_feed": {
                    "edges": [
                        {"node": {"story": {
                            "id": "story_1",
                            "message": {"text": "Wie kent goede installateur warmtepomp Tilburg?"},
                            "actors": [{"name": "Jan de Vries"}],
                            "wwwURL": "https://www.facebook.com/groups/123/posts/777/",
                            "creation_time": 1715760000,
                        }}},
                        {"node": {"story": {
                            "id": "story_2",
                            "message": {"text": "Wat kost een warmtepomp installatie tegenwoordig?"},
                            "actors": [{"name": "Marie Peters"}],
                            "wwwURL": "https://www.facebook.com/groups/123/posts/888/",
                            "creation_time": 1715846400,
                        }}},
                    ]
                }
            }
        }
    }
    target = GroupTarget(id="123", name="WP NL", max_posts=10)
    posts = parse_groups_graphql_response(response, target=target, niche="warmtepomp", run_id="rid")
    assert len(posts) == 2
    assert posts[0].author == "Jan de Vries"
    assert posts[0].url.endswith("/groups/123/posts/777/")
    assert posts[0].metadata["surface"] == "groups"
    assert posts[0].metadata["extraction"] == "graphql"


def test_parse_graphql_response_skips_missing_message() -> None:
    from consumer.sources.facebook.surfaces.groups import parse_groups_graphql_response
    response = {
        "data": {"node": {"group_feed": {"edges": [
            {"node": {"story": {"id": "x", "actors": [{"name": "A"}],
                                 "wwwURL": "https://fb.com/x", "creation_time": 1}}},
            {"node": {"story": {"id": "y", "message": {"text": "ok"},
                                 "actors": [{"name": "B"}],
                                 "wwwURL": "https://www.facebook.com/groups/1/posts/2/",
                                 "creation_time": 2}}},
        ]}}}
    }
    target = GroupTarget(id="1", name="t", max_posts=10)
    posts = parse_groups_graphql_response(response, target=target, niche="warmtepomp", run_id="t")
    assert len(posts) == 1
    assert posts[0].text == "ok"


def test_parse_graphql_response_empty_edges_returns_empty() -> None:
    from consumer.sources.facebook.surfaces.groups import parse_groups_graphql_response
    target = GroupTarget(id="1", name="t", max_posts=10)
    assert parse_groups_graphql_response(
        {"data": {"node": {"group_feed": {"edges": []}}}},
        target=target, niche="warmtepomp", run_id="t",
    ) == []


def test_parse_graphql_response_malformed_returns_empty() -> None:
    from consumer.sources.facebook.surfaces.groups import parse_groups_graphql_response
    target = GroupTarget(id="1", name="t", max_posts=10)
    assert parse_groups_graphql_response({}, target=target, niche="warmtepomp", run_id="t") == []
    assert parse_groups_graphql_response({"data": None}, target=target, niche="warmtepomp", run_id="t") == []
