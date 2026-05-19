"""Verifies existing FB module API still imports after package migration."""
from __future__ import annotations


def test_load_posts_from_file_importable_from_old_path() -> None:
    from consumer.sources.facebook import load_posts_from_file
    assert callable(load_posts_from_file)


def test_analyze_manual_posts_importable_from_old_path() -> None:
    from consumer.sources.facebook import analyze_manual_posts
    assert callable(analyze_manual_posts)


def test_analyze_manual_posts_default_platform() -> None:
    from consumer.sources.facebook import analyze_manual_posts
    leads = analyze_manual_posts(
        ["Wie kent een goede warmtepomp installateur in Antwerpen?"],
        niche="warmtepomp",
    )
    assert len(leads) == 1
    assert leads[0].source == "facebook"
    assert leads[0].id.startswith("facebook:")
