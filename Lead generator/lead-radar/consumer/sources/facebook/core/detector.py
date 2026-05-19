"""ChallengeDetector — classifies the current FB page state.

URL inspection is cheap and unambiguous, so we check the URL first. Only if
the URL looks "normal" do we read the body and look for challenge dialogs
or rate-limit banners. This keeps detection latency low and avoids false
positives from text that happens to mention 'verify' in an unrelated post.
"""
from __future__ import annotations

from enum import Enum
from typing import Protocol


class ChallengeState(Enum):
    OK = "ok"
    CHALLENGED = "challenged"
    LOGIN_WALL = "login_wall"
    RATE_LIMITED = "rate_limited"


_URL_CHECKPOINT_MARKERS = ("/checkpoint/", "/security/")
_URL_LOGIN_MARKERS = ("/login/", "/login.php", "/r.php")

_HTML_CHALLENGE_NEEDLES = (
    "verify identity",
    "we beschermen je account",
    'role="dialog"',
)
_HTML_RATE_LIMIT_NEEDLES = (
    "you're temporarily blocked",
    "vertraag het tempo",
    "slow down",
)
_HTML_LOGIN_NEEDLES = (
    'action="/login/"',
    'id="loginbutton"',
    'name="login"',
)


class _PageLike(Protocol):
    url: str
    async def content(self) -> str: ...


async def detect_state(page: _PageLike) -> ChallengeState:
    """Classify the current page state.

    Order: URL-based markers first (cheap), then body inspection.  If the
    URL is normal we still scan the body for challenge dialogs that may
    overlay on top of the regular feed.
    """
    url = (page.url or "").lower()

    if any(marker in url for marker in _URL_CHECKPOINT_MARKERS):
        return ChallengeState.CHALLENGED
    if any(marker in url for marker in _URL_LOGIN_MARKERS):
        return ChallengeState.LOGIN_WALL

    html = (await page.content() or "").lower()

    if any(needle in html for needle in _HTML_RATE_LIMIT_NEEDLES):
        return ChallengeState.RATE_LIMITED
    if any(needle in html for needle in _HTML_CHALLENGE_NEEDLES):
        if 'role="dialog"' in html or "verify identity" in html or "we beschermen je account" in html:
            return ChallengeState.CHALLENGED
    if any(needle in html for needle in _HTML_LOGIN_NEEDLES) and "/login" in html:
        return ChallengeState.LOGIN_WALL

    return ChallengeState.OK
