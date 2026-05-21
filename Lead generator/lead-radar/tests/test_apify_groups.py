"""Tests for the Apify FB Groups item → RawPost mapper.

Pure-function tests — no network, no Apify SDK import (the mapper module
imports the SDK lazily inside ApifyRunner.__init__, so importing
``apify_groups`` itself doesn't pull it in).
"""
from __future__ import annotations

import pytest

from consumer import RawPost
from consumer.sources.facebook.apify_groups import (
    items_to_rawposts,
    map_item_to_rawpost,
)
from consumer.sources.facebook.targets import GroupTarget


@pytest.fixture
def target() -> GroupTarget:
    return GroupTarget(id="1520566101657472", name="Hybride warmtepomp", max_posts=3)


def test_maps_basic_item_to_rawpost(target: GroupTarget) -> None:
    item = {
        "text": "Wie heeft ervaring met de Quatt warmtepomp?\nIs het echt zo stil?",
        "postUrl": "https://www.facebook.com/groups/1520566101657472/posts/abc/",
        "user": {"name": "Jan de Vries"},
        "time": "2026-05-16T12:34:00Z",
    }
    rp = map_item_to_rawpost(item, target=target, niche="warmtepomp", run_id="r1", idx=0)
    assert isinstance(rp, RawPost)
    assert rp.source == "facebook_groups"
    assert rp.text.startswith("Wie heeft ervaring met de Quatt")
    assert rp.title == "Wie heeft ervaring met de Quatt warmtepomp?"
    assert rp.author == "Jan de Vries"
    assert rp.created_at and rp.created_at.startswith("2026-05-16T12:34")
    assert rp.url == "https://www.facebook.com/groups/1520566101657472/posts/abc/"
    assert rp.metadata["niche"] == "warmtepomp"
    assert rp.metadata["group_id"] == target.id
    assert rp.metadata["collector"] == "apify"


def test_skips_items_without_text(target: GroupTarget) -> None:
    item = {"postUrl": "https://www.facebook.com/groups/x/posts/1/", "user": "Jan"}
    assert map_item_to_rawpost(item, target=target, niche="warmtepomp", run_id="r1", idx=0) is None


def test_falls_back_to_alternate_field_names(target: GroupTarget) -> None:
    item = {
        "message": "Zoek installateur voor warmtepomp in Tilburg",
        "url": "https://www.facebook.com/groups/x/posts/2/",
        "author": "Piet",
        "publishedAt": 1747400040,
    }
    rp = map_item_to_rawpost(item, target=target, niche="warmtepomp", run_id="r1", idx=1)
    assert rp is not None
    assert rp.text == "Zoek installateur voor warmtepomp in Tilburg"
    assert rp.author == "Piet"
    assert rp.created_at is not None  # epoch coerced


def test_handles_string_author_and_missing_timestamp(target: GroupTarget) -> None:
    item = {"text": "test post", "postUrl": "/groups/x/posts/3/", "userName": "Marie"}
    rp = map_item_to_rawpost(item, target=target, niche="warmtepomp", run_id="r1", idx=2)
    assert rp is not None
    assert rp.author == "Marie"
    assert rp.created_at is None
    assert rp.url.startswith("https://www.facebook.com/")


def test_handles_dict_author_with_no_name(target: GroupTarget) -> None:
    item = {"text": "x", "postUrl": "https://fb.com/p/1", "user": {"id": "999"}}
    rp = map_item_to_rawpost(item, target=target, niche="warmtepomp", run_id="r1", idx=3)
    assert rp is not None
    assert rp.author == "999"


def test_items_to_rawposts_respects_max_posts(target: GroupTarget) -> None:
    items = [
        {"text": f"post {i}", "postUrl": f"https://fb.com/p/{i}"} for i in range(10)
    ]
    posts = items_to_rawposts(items, target=target, niche="warmtepomp", run_id="r1")
    assert len(posts) == target.max_posts == 3


def test_items_to_rawposts_skips_blanks(target: GroupTarget) -> None:
    items = [
        {"text": "", "postUrl": "https://fb.com/p/0"},
        {"text": "real one", "postUrl": "https://fb.com/p/1"},
        {"postUrl": "https://fb.com/p/2"},
        {"text": "another", "postUrl": "https://fb.com/p/3"},
    ]
    posts = items_to_rawposts(items, target=target, niche="warmtepomp", run_id="r1")
    assert [p.text for p in posts] == ["real one", "another"]


def test_post_ids_are_stable_and_unique(target: GroupTarget) -> None:
    items = [
        {"text": "a", "postUrl": "https://fb.com/p/1"},
        {"text": "b", "postUrl": "https://fb.com/p/2"},
    ]
    posts1 = items_to_rawposts(items, target=target, niche="warmtepomp", run_id="r1")
    posts2 = items_to_rawposts(items, target=target, niche="warmtepomp", run_id="r2")
    assert posts1[0].id == posts2[0].id  # run_id doesn't change id
    assert posts1[0].id != posts1[1].id  # different URLs -> different ids
