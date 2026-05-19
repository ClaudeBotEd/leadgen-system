"""Tests that run_consumer.py drains data/fb_queue/ into its RawPost stream."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer import RawPost
from consumer.sources.facebook.queue import write_jsonl, drain


def test_drain_yields_posts_from_queue_dir(tmp_path: Path) -> None:
    sample = RawPost(
        id="facebook_groups:abc-0",
        source="facebook_groups",
        url="https://www.facebook.com/groups/123/posts/0/",
        title="Wie kent goede installateur?",
        text="Body text",
        author="Jan",
        created_at="2026-05-15T08:04:12Z",
        metadata={"niche": "warmtepomp", "surface": "groups"},
    )
    write_jsonl(tmp_path / "run.jsonl", [sample])
    posts = list(drain(tmp_path))
    assert len(posts) == 1
    assert posts[0].source == "facebook_groups"
    assert posts[0].metadata["niche"] == "warmtepomp"


def test_drained_posts_pass_hardblock(tmp_path: Path) -> None:
    """End-to-end: a FB-sourced RawPost survives the existing pipeline filters."""
    from consumer.processor import check_hardblock

    sample = RawPost(
        id="facebook_groups:wp-0",
        source="facebook_groups",
        url="https://www.facebook.com/groups/123/posts/0/",
        title="Wie kent goede warmtepomp installateur in Tilburg?",
        text="Mijn ketel is kapot en ik wil hybride. Spoed gevraagd.",
        author="Jan de Vries",
        created_at="2026-05-15T08:04:12Z",
        metadata={"niche": "warmtepomp", "surface": "groups"},
    )
    write_jsonl(tmp_path / "run.jsonl", [sample])
    drained = list(drain(tmp_path))
    # check_hardblock returns a BlockResult dataclass, not a tuple.  Access fields directly.
    result = check_hardblock(drained[0])
    assert not result.blocked, f"hardblock falsely rejected consumer post: {result.reason}"
