"""Facebook source — package with self-hosted scraper + legacy manual-paste mode.

Backward-compat re-exports preserve the pre-migration API:

    from consumer.sources.facebook import analyze_manual_posts, load_posts_from_file

New self-hosted scraper lives under consumer/sources/facebook/{core,surfaces,runner}.
"""
from __future__ import annotations

from ._legacy import (
    analyze_manual_posts,
    load_posts_from_file,
)

__all__ = ["analyze_manual_posts", "load_posts_from_file"]
