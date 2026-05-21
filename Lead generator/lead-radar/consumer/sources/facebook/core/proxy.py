"""HTTPProxy interface + concrete implementations.

Phase 1 ships ``NoProxy``; Phase 2 plugs ``ResidentialProxy`` in without
touching the session module — that's the whole point of the abstraction.
"""
from __future__ import annotations

from typing import Protocol


class HTTPProxy(Protocol):
    """Anything that can produce a Playwright proxy-config dict (or None)."""

    def playwright_proxy_config(self) -> dict | None: ...


class NoProxy:
    """Routes traffic through the host's direct connection (no proxy)."""

    def playwright_proxy_config(self) -> dict | None:
        return None


class ResidentialProxy:
    """A residential proxy with sticky-session credentials.

    Phase 2 wiring — kept here so the interface is locked in now.
    """

    def __init__(self, endpoint: str, username: str, password: str) -> None:
        self._endpoint = endpoint
        self._username = username
        self._password = password

    def playwright_proxy_config(self) -> dict:
        return {
            "server": self._endpoint,
            "username": self._username,
            "password": self._password,
        }
