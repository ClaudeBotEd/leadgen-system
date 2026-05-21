"""Tests for HumanPace timing helpers.

asyncio.sleep is monkeypatched and we assert the sampled duration falls
within the configured range.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from consumer.sources.facebook.core.throttle import HumanPace, THROTTLE_CONFIG


@pytest.fixture
def sleep_spy(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    spy = AsyncMock()
    monkeypatch.setattr("consumer.sources.facebook.core.throttle.asyncio.sleep", spy)
    return spy


async def test_between_clicks_in_range(sleep_spy: AsyncMock) -> None:
    await HumanPace.between_clicks()
    lo, hi = THROTTLE_CONFIG["between_clicks"]
    sleep_spy.assert_awaited_once()
    (duration,) = sleep_spy.await_args.args
    assert lo <= duration <= hi


async def test_between_targets_in_range(sleep_spy: AsyncMock) -> None:
    await HumanPace.between_targets()
    lo, hi = THROTTLE_CONFIG["between_targets"]
    (duration,) = sleep_spy.await_args.args
    assert lo <= duration <= hi


async def test_between_surfaces_in_range(sleep_spy: AsyncMock) -> None:
    await HumanPace.between_surfaces()
    lo, hi = THROTTLE_CONFIG["between_surfaces"]
    (duration,) = sleep_spy.await_args.args
    assert lo <= duration <= hi


async def test_read_dwell_in_range(sleep_spy: AsyncMock) -> None:
    await HumanPace.read_dwell()
    lo, hi = THROTTLE_CONFIG["read_dwell"]
    (duration,) = sleep_spy.await_args.args
    assert lo <= duration <= hi


async def test_jitter_distribution(sleep_spy: AsyncMock) -> None:
    """Repeated calls produce varied durations (not a constant)."""
    durations: list[float] = []
    for _ in range(20):
        sleep_spy.reset_mock()
        await HumanPace.between_clicks()
        durations.append(sleep_spy.await_args.args[0])
    assert len(set(round(d, 2) for d in durations)) > 5, (
        "expected jittered durations across 20 samples"
    )


def test_throttle_config_bounds_sane() -> None:
    for name, (lo, hi) in THROTTLE_CONFIG.items():
        assert 0 < lo <= hi, f"{name} bounds out of order: {lo}-{hi}"
