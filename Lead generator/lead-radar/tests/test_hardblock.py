"""Regression-tests voor hardblock filter."""
from __future__ import annotations

import pytest

from consumer import RawPost
from consumer.processor.hardblock import (
    AGGREGATOR_HOSTS,
    BlockResult,
    _host_from_url,
    check_hardblock,
    is_blocked,
)


def _post(*, url: str = "https://reddit.com/r/x/abc", author: str | None = None,
          title: str = "", text: str = "") -> RawPost:
    return RawPost(
        id="x", source="test", url=url, title=title, text=text, author=author,
    )


@pytest.mark.parametrize("url,expected", [
    ("https://www.reddit.com/r/x/abc", "reddit.com"),
    ("https://www.slimster.nl/offerte/123", "slimster.nl"),
    ("http://example.com:8080/a", "example.com:8080"),
    ("", ""),
    ("not-a-url", ""),
])
def test_host_from_url(url: str, expected: str) -> None:
    assert _host_from_url(url) == expected


def test_block_aggregator_host_exact() -> None:
    p = _post(url="https://www.slimster.nl/offerte/123")
    r = check_hardblock(p)
    assert r.blocked
    assert "slimster.nl" in (r.reason or "")


def test_block_aggregator_host_subdomain() -> None:
    p = _post(url="https://sub.werkspot.nl/lead/1")
    r = check_hardblock(p)
    assert r.blocked
    assert "werkspot.nl" in (r.reason or "")


def test_allow_neutral_host() -> None:
    p = _post(
        url="https://www.reddit.com/r/Bouwen/abc",
        title="Wie kent een installateur",
        text="Ik zoek een goede monteur",
    )
    assert not check_hardblock(p).blocked


def test_block_bot_author() -> None:
    p = _post(author="AutoModerator", title="lead", text="text")
    assert check_hardblock(p).blocked


def test_block_company_author() -> None:
    p = _post(author="Verwarming Smit BV", title="vraag", text="text")
    assert check_hardblock(p).blocked


def test_allow_normal_author() -> None:
    p = _post(author="jansenuser", title="cv kapot", text="zoek monteur")
    assert not check_hardblock(p).blocked


def test_block_spam_pattern() -> None:
    p = _post(
        url="https://example.com",
        title="Geld verdienen vanuit huis met crypto",
        text="Sluit aan bij ons forex programma",
    )
    assert check_hardblock(p).blocked


def test_is_blocked_alias() -> None:
    p = _post(url="https://www.bobex.nl/x")
    assert is_blocked(p) is True


def test_block_result_truthy_bool() -> None:
    r1 = BlockResult(True, "x")
    r2 = BlockResult(False, None)
    assert bool(r1) is True
    assert bool(r2) is False


def test_aggregator_hosts_lowercase() -> None:
    for h in AGGREGATOR_HOSTS:
        assert h == h.lower(), f"host {h!r} must be lowercase"


def test_aggregator_hosts_no_protocol() -> None:
    for h in AGGREGATOR_HOSTS:
        assert "://" not in h
        assert not h.startswith("/")
