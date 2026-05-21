"""Tests for ChallengeDetector — uses a fake Page returning fixture URL+HTML."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import pytest

from consumer.sources.facebook.core.detector import ChallengeState, detect_state


FIXTURES = Path(__file__).parent / "fixtures" / "fb"


@dataclass
class FakePage:
    """Minimal stand-in for a Playwright Page exposing url + content()."""
    url: str
    html: str

    async def content(self) -> str:
        return self.html


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


async def test_detect_ok_clean_session() -> None:
    page = FakePage(url="https://www.facebook.com/groups/123/", html=_load("state_ok.html"))
    assert await detect_state(page) == ChallengeState.OK


async def test_detect_checkpoint_by_url() -> None:
    page = FakePage(url="https://www.facebook.com/checkpoint/?u=123", html="<html></html>")
    assert await detect_state(page) == ChallengeState.CHALLENGED


async def test_detect_security_path_url() -> None:
    page = FakePage(url="https://www.facebook.com/security/begin/?intent=verify",
                    html="<html></html>")
    assert await detect_state(page) == ChallengeState.CHALLENGED


async def test_detect_checkpoint_by_dialog() -> None:
    page = FakePage(url="https://www.facebook.com/", html=_load("state_checkpoint.html"))
    assert await detect_state(page) == ChallengeState.CHALLENGED


async def test_detect_login_wall_redirect() -> None:
    page = FakePage(url="https://www.facebook.com/login/?next=%2Fgroups%2F123",
                    html=_load("state_login_wall.html"))
    assert await detect_state(page) == ChallengeState.LOGIN_WALL


async def test_detect_rate_limited_banner() -> None:
    page = FakePage(url="https://www.facebook.com/groups/123/",
                    html=_load("state_rate_limited.html"))
    assert await detect_state(page) == ChallengeState.RATE_LIMITED


async def test_url_check_takes_priority_over_html() -> None:
    """If URL signals challenge, we don't parse the body."""
    page = FakePage(url="https://www.facebook.com/checkpoint/", html=_load("state_ok.html"))
    assert await detect_state(page) == ChallengeState.CHALLENGED
