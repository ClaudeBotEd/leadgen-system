"""Human-pace timing helpers — random jitter to mimic a real user.

Bounds live in ``THROTTLE_CONFIG`` so the operator can tune timing in one
place without grepping for magic numbers.  Each helper samples a
uniform-random duration from its configured range and asyncio.sleep's
for it.

Tests monkeypatch ``asyncio.sleep`` via this module's namespace, so we
import asyncio at module level rather than rebinding ``sleep`` directly.
"""
from __future__ import annotations

import asyncio
import random
from typing import Final

THROTTLE_CONFIG: Final[dict[str, tuple[float, float]]] = {
    "between_clicks": (3.0, 8.0),
    "between_targets": (10.0, 20.0),
    "between_surfaces": (30.0, 90.0),
    "read_dwell": (2.0, 5.0),
    "scroll_gap": (0.5, 2.0),
}


class HumanPace:
    """Static helpers that sleep for a random duration in their configured range."""

    @staticmethod
    async def _sleep_in(name: str) -> None:
        lo, hi = THROTTLE_CONFIG[name]
        await asyncio.sleep(random.uniform(lo, hi))

    @staticmethod
    async def between_clicks() -> None:
        """Pause between two consecutive clicks (3-8s)."""
        await HumanPace._sleep_in("between_clicks")

    @staticmethod
    async def between_targets() -> None:
        """Pause between two targets within the same surface (10-20s)."""
        await HumanPace._sleep_in("between_targets")

    @staticmethod
    async def between_surfaces() -> None:
        """Pause when moving from one surface to the next (30-90s)."""
        await HumanPace._sleep_in("between_surfaces")

    @staticmethod
    async def read_dwell() -> None:
        """Pause to simulate reading a post (2-5s)."""
        await HumanPace._sleep_in("read_dwell")

    @staticmethod
    async def scroll_gap() -> None:
        """Tiny pause between burst-scrolls (0.5-2s)."""
        await HumanPace._sleep_in("scroll_gap")
