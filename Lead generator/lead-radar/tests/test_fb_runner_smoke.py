"""End-to-end Groups MVP smoke test — opt-in via FB_E2E=1.

Launches a real Playwright browser, requires a warmed FB account under
data/fb_state/main/, and at least one group target in
config/facebook_targets.yaml.  Skipped by default so CI stays green
without operator setup.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

REQUIRES_E2E = pytest.mark.skipif(
    os.environ.get("FB_E2E") != "1",
    reason="set FB_E2E=1 to run the live Playwright smoke test",
)

REPO_ROOT = Path(__file__).resolve().parent.parent


@REQUIRES_E2E
async def test_groups_scrape_produces_queue_file(tmp_path, monkeypatch) -> None:
    """A real run against one group should yield >=1 RawPost into the queue."""
    from consumer.sources.facebook import runner

    monkeypatch.setattr(runner, "QUEUE_DIR", tmp_path / "fb_queue")
    monkeypatch.setattr(runner, "STATE_DIR", REPO_ROOT / "data" / "fb_state")

    # Operator must edit config/facebook_targets.yaml so at least one group
    # is listed under any niche before running this test.
    rc = await runner._cmd_scrape(niche_arg="all", account_id="main")
    assert rc == 0
    queue_files = list((tmp_path / "fb_queue").glob("*.jsonl"))
    assert len(queue_files) == 1
    contents = queue_files[0].read_text(encoding="utf-8")
    assert contents.count("\n") >= 1
