"""Surface ABC — every per-surface scraper implements scrape() returning RawPosts.

Surfaces stay decoupled from session/account/throttle by receiving them as
arguments; this keeps each surface unit-testable on a static HTML fixture
without touching Playwright.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from consumer import RawPost

from ..core.detector import ChallengeState

if TYPE_CHECKING:
    from playwright.async_api import Page
    from ..core.accounts import Account


class ChallengeRaised(RuntimeError):
    """Raised by a surface when the page hits a HARD state (CHALLENGED or LOGIN_WALL).

    The runner catches this, marks the account, and aborts the rest of the run.
    Trigger states: CHALLENGED, LOGIN_WALL.
    """

    def __init__(self, state: ChallengeState, *, surface: str, url: str) -> None:
        super().__init__(f"{surface}: challenge state {state.value} at {url}")
        self.state = state
        self.surface = surface
        self.url = url


class BackoffRaised(RuntimeError):
    """Raised by a surface when the page hits a SOFT state (RATE_LIMITED, EMPTY_FEED).

    The runner catches this, increments the per-surface backoff counter, and
    skips remaining targets in this surface but does NOT flip account state.
    After 3 consecutive runs with backoff on the same surface, the runner
    escalates to ChallengeRaised behavior on its own.
    """

    def __init__(self, state: ChallengeState, *, surface: str, url: str) -> None:
        super().__init__(f"{surface}: soft backoff state {state.value} at {url}")
        self.state = state
        self.surface = surface
        self.url = url


class Surface(ABC):
    """A pluggable FB surface scraper (groups/marketplace/pages)."""

    name: str

    @abstractmethod
    async def scrape(self, account: "Account", target: Any, page: "Page") -> list[RawPost]:
        """Drive ``page`` to the given target and return extracted RawPosts.

        Raises ChallengeRaised on CHALLENGED / LOGIN_WALL (fatal for the run).
        Raises BackoffRaised on RATE_LIMITED / EMPTY_FEED (skip surface, keep account).
        """
