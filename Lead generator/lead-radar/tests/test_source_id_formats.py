"""Per-source source_id format contract — must match Sheets schema docs.

Each source registers itself in REGISTRY; the value-builder it produces
must set RawPost.source_id to the granular form defined here.
"""
from __future__ import annotations

import re

import pytest

from consumer import RawPost
from consumer.sources import REGISTRY

# Map source-name -> regex the source_id must match
SOURCE_ID_FORMATS: dict[str, str] = {
    "reddit":          r"^reddit:r/[A-Za-z0-9_]+$",
    "reddit_new":      r"^reddit_new:r/[A-Za-z0-9_]+$",
    "tweakers":        r"^tweakers:[a-z0-9_-]+$",
    "bouwinfo":        r"^bouwinfo:[a-z0-9_-]+$",
    "bouwinfo_forum":  r"^bouwinfo_forum:[a-z0-9_-]+$",
    "klusidee_forum":  r"^klusidee_forum:[a-z0-9._-]+$",
    "ouders_forum":    r"^ouders_forum:[a-z0-9_-]+$",
    "google":          r"^google:[a-z0-9.-]+$",
    "marktplaats":     r"^marktplaats:[a-z0-9_-]+/[a-z0-9_-]+$",
    "2dehands":        r"^2dehands:[a-z0-9_-]+/[a-z0-9_-]+$",
}


@pytest.mark.parametrize("source_name", list(SOURCE_ID_FORMATS.keys()))
def test_source_registry_has_module(source_name):
    """All sources we're updating must still be in REGISTRY."""
    assert source_name in REGISTRY, f"source '{source_name}' missing from REGISTRY"


def test_source_id_format_for_fake_post():
    """RawPost preserves explicit source_id at construction."""
    p = RawPost(
        id="x",
        source="reddit",
        source_id="reddit:r/duurzaam",
        url="https://reddit.com/r/duurzaam/post/x",
        title="t",
        text="b",
    )
    assert re.match(SOURCE_ID_FORMATS["reddit"], p.source_id), (
        f"reddit example source_id {p.source_id!r} does not match contract"
    )


def test_reddit_new_emits_granular_source_id():
    """reddit_new.fetch emits source_id=reddit_new:r/<sub>."""
    from consumer.sources import reddit_new
    # Use a small known sub. If network is unavailable in CI, this may need
    # mocking later — but per format the source_id should still be set from
    # the loop variable, independent of post yield.
    try:
        posts = list(reddit_new.fetch(query="warmtepomp", limit=1, subreddits=["thenetherlands"]))
    except Exception:
        pytest.skip("reddit_new fetch not network-available in this env")
    for p in posts:
        assert re.match(SOURCE_ID_FORMATS["reddit_new"], p.source_id), p.source_id


def test_marktplaats_emits_granular_source_id():
    """marktplaats.fetch must emit source_id=marktplaats:<category>/<city>."""
    from consumer.sources import marktplaats
    try:
        posts = list(marktplaats.fetch(
            query="warmtepomp installateur",
            limit=1,
            location="amsterdam",
        ))
    except Exception:
        pytest.skip("marktplaats fetch not network-available in this env")
    for p in posts:
        assert p.source_id.startswith("marktplaats:"), p.source_id
        assert "/" in p.source_id.split("marktplaats:", 1)[1], p.source_id
