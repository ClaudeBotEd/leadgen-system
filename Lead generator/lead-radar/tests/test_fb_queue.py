"""Tests for the FB queue (JSONL writer + drainer)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from consumer import RawPost
from consumer.sources.facebook.queue import write_jsonl, drain


def _sample_post(idx: int = 0) -> RawPost:
    return RawPost(
        id=f"facebook_groups:abc-{idx}",
        source="facebook_groups",
        url=f"https://www.facebook.com/groups/123/posts/{idx}/",
        title=f"Post {idx}",
        text=f"Body of post {idx}",
        author="Jan de Vries",
        created_at="2026-05-15T08:04:12Z",
        metadata={"niche": "warmtepomp", "group_id": "123", "surface": "groups"},
    )


def test_write_jsonl_one_post(tmp_path: Path) -> None:
    out = tmp_path / "run.jsonl"
    write_jsonl(out, [_sample_post(0)])
    assert out.exists()
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["id"] == "facebook_groups:abc-0"
    assert rec["metadata"]["niche"] == "warmtepomp"


def test_write_jsonl_multiple_posts(tmp_path: Path) -> None:
    out = tmp_path / "run.jsonl"
    write_jsonl(out, [_sample_post(i) for i in range(5)])
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    for i, line in enumerate(lines):
        rec = json.loads(line)
        assert rec["id"] == f"facebook_groups:abc-{i}"


def test_write_jsonl_empty_list_creates_empty_file(tmp_path: Path) -> None:
    out = tmp_path / "run.jsonl"
    write_jsonl(out, [])
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


def test_drain_reads_all_files_in_dir(tmp_path: Path) -> None:
    write_jsonl(tmp_path / "run_a.jsonl", [_sample_post(0), _sample_post(1)])
    write_jsonl(tmp_path / "run_b.jsonl", [_sample_post(2)])
    posts = list(drain(tmp_path))
    assert len(posts) == 3
    ids = {p.id for p in posts}
    assert ids == {
        "facebook_groups:abc-0",
        "facebook_groups:abc-1",
        "facebook_groups:abc-2",
    }


def test_drain_moves_consumed_files_to_processed(tmp_path: Path) -> None:
    queue_file = tmp_path / "run.jsonl"
    write_jsonl(queue_file, [_sample_post(0)])
    list(drain(tmp_path))  # exhaust generator
    assert not queue_file.exists(), "queue file should be moved out of queue_dir"
    assert (tmp_path / "processed" / "run.jsonl").exists()


def test_drain_skips_processed_subdir(tmp_path: Path) -> None:
    (tmp_path / "processed").mkdir()
    write_jsonl(tmp_path / "processed" / "old.jsonl", [_sample_post(99)])
    write_jsonl(tmp_path / "fresh.jsonl", [_sample_post(0)])
    posts = list(drain(tmp_path))
    assert len(posts) == 1
    assert posts[0].id == "facebook_groups:abc-0"


def test_drain_handles_malformed_line(tmp_path: Path) -> None:
    f = tmp_path / "run.jsonl"
    f.write_text(
        json.dumps({
            "id": "facebook_groups:ok-0", "source": "facebook_groups",
            "url": "https://www.facebook.com/groups/1/posts/0/",
            "title": "ok", "text": "body",
        }) + "\n"
        "this is not json\n"
        + json.dumps({
            "id": "facebook_groups:ok-1", "source": "facebook_groups",
            "url": "https://www.facebook.com/groups/1/posts/1/",
            "title": "ok", "text": "body",
        }) + "\n",
        encoding="utf-8",
    )
    posts = list(drain(tmp_path))
    assert len(posts) == 2, "malformed line skipped, valid records returned"


def test_drain_empty_dir_returns_nothing(tmp_path: Path) -> None:
    assert list(drain(tmp_path)) == []
