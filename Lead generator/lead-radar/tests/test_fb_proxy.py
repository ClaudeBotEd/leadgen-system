"""Tests for the HTTPProxy interface + NoProxy default."""
from __future__ import annotations

import pytest

from consumer.sources.facebook.core.proxy import HTTPProxy, NoProxy, ResidentialProxy


def test_no_proxy_returns_none() -> None:
    assert NoProxy().playwright_proxy_config() is None


def test_no_proxy_implements_protocol() -> None:
    p: HTTPProxy = NoProxy()
    assert p.playwright_proxy_config() is None


def test_residential_proxy_config_shape() -> None:
    p = ResidentialProxy(endpoint="http://proxy.example.com:7777",
                         username="user", password="pw")
    cfg = p.playwright_proxy_config()
    assert cfg == {
        "server": "http://proxy.example.com:7777",
        "username": "user",
        "password": "pw",
    }


def test_residential_proxy_implements_protocol() -> None:
    p: HTTPProxy = ResidentialProxy(endpoint="http://x:1", username="u", password="p")
    assert p.playwright_proxy_config() is not None
