"""PoliteSession retry-strategie — onderscheid recoverable vs non-recoverable.

Voorheen: alles 3× retry met 3s+6s+9s = 18s backoff.  Bij DNS-failure
of connection-refused is retry zinloos en kost het ~18s per call extra
× 12 queries × ... = veel verspilde wall-clock.

Nu:
- 429/5xx + generieke RequestException: 3 attempts met backoff (huidig)
- requests.Timeout (ConnectTimeout, ReadTimeout): max 2 attempts
- requests.ConnectionError (DNS, refused): 1 attempt, geen retry
- requests.SSLError: 1 attempt, geen retry (config issue)
"""
from __future__ import annotations

from unittest.mock import patch

import requests

from consumer.utils import HttpConfig, PoliteSession


def _make_session(*, backoff: float = 0.0, max_retries: int = 2) -> PoliteSession:
    """Build sessie met backoff=0 zodat tests snel runnen."""
    cfg = HttpConfig(request_delay=0.0, jitter=0.0,
                     max_retries=max_retries, backoff=backoff, timeout=1.0)
    return PoliteSession(cfg)


def test_connection_error_no_retry() -> None:
    """ConnectionError (DNS/refused) is niet retriable — 1 call, return None."""
    sess = _make_session()
    call_count = 0

    def fake_get(*a, **kw):  # noqa: ANN001, ANN003, ANN201
        nonlocal call_count
        call_count += 1
        raise requests.exceptions.ConnectionError("Name resolution failed")

    with patch.object(sess.session, "get", side_effect=fake_get):
        result = sess.get("https://no-such-host.example/")
    assert result is None
    assert call_count == 1, f"ConnectionError zou 1× attempted moeten zijn; was {call_count}"


def test_ssl_error_no_retry() -> None:
    """SSLError = config issue, niet recoverable — 1 call."""
    sess = _make_session()
    call_count = 0

    def fake_get(*a, **kw):  # noqa: ANN001, ANN003, ANN201
        nonlocal call_count
        call_count += 1
        raise requests.exceptions.SSLError("certificate verify failed")

    with patch.object(sess.session, "get", side_effect=fake_get):
        result = sess.get("https://broken-cert.example/")
    assert result is None
    assert call_count == 1


def test_timeout_max_two_attempts() -> None:
    """Timeout: max 2 attempts (1 retry).  Vroeger: 3 attempts × 15s = 45s."""
    sess = _make_session()
    call_count = 0

    def fake_get(*a, **kw):  # noqa: ANN001, ANN003, ANN201
        nonlocal call_count
        call_count += 1
        raise requests.exceptions.Timeout("timed out")

    with patch.object(sess.session, "get", side_effect=fake_get):
        result = sess.get("https://slow.example/")
    assert result is None
    assert call_count == 2, f"Timeout zou 2× attempted moeten zijn (1 retry); was {call_count}"


def test_generic_request_exception_still_retries_thrice() -> None:
    """Generieke RequestException blijft 3 attempts gebruiken (huidig gedrag)."""
    sess = _make_session(max_retries=2)
    call_count = 0

    def fake_get(*a, **kw):  # noqa: ANN001, ANN003, ANN201
        nonlocal call_count
        call_count += 1
        raise requests.exceptions.RequestException("generic transient")

    with patch.object(sess.session, "get", side_effect=fake_get):
        result = sess.get("https://flaky.example/")
    assert result is None
    assert call_count == 3, f"Generic RequestException → 3 attempts; was {call_count}"


def test_429_status_still_retries() -> None:
    """HTTP 429 (throttled) blijft 3 attempts met backoff (huidig gedrag)."""
    sess = _make_session(max_retries=2)
    call_count = 0

    class FakeResp:
        def __init__(self, code):
            self.status_code = code

    def fake_get(*a, **kw):  # noqa: ANN001, ANN003, ANN201
        nonlocal call_count
        call_count += 1
        return FakeResp(429)

    with patch.object(sess.session, "get", side_effect=fake_get):
        result = sess.get("https://throttled.example/")
    assert result is None
    assert call_count == 3


def test_default_timeout_is_ten_seconds() -> None:
    """Default timeout verlaagd van 15 naar 10 sec — passender voor JSON/HTML endpoints."""
    cfg = HttpConfig()
    assert cfg.timeout == 10.0, f"Default timeout zou 10 moeten zijn, was {cfg.timeout}"


def test_lean_headers_strips_accept_headers() -> None:
    """lean_headers=True strip session-level Accept/Accept-Language voor anti-bot
    workaround (Tweakers/DPG)."""
    sess = _make_session()
    captured: dict = {}

    class FakeResp:
        status_code = 200

    def fake_get(url, *, params=None, timeout=None, headers=None):  # noqa: ANN001
        captured["headers"] = headers or {}
        return FakeResp()

    with patch.object(sess.session, "get", side_effect=fake_get):
        sess.get("https://anti-bot.example/", lean_headers=True)

    h = captured["headers"]
    assert h.get("Accept") is None, f"Accept moest None zijn (gestript); was {h.get('Accept')!r}"
    assert h.get("Accept-Language") is None, (
        f"Accept-Language moest None zijn; was {h.get('Accept-Language')!r}"
    )
    assert h.get("Accept-Encoding") is None, (
        f"Accept-Encoding moest None zijn; was {h.get('Accept-Encoding')!r}"
    )


def test_lean_headers_false_keeps_session_headers() -> None:
    """lean_headers=False (default) laat session-level headers ongemoeid."""
    sess = _make_session()
    captured: dict = {}

    class FakeResp:
        status_code = 200

    def fake_get(url, *, params=None, timeout=None, headers=None):  # noqa: ANN001
        captured["headers"] = headers or {}
        return FakeResp()

    with patch.object(sess.session, "get", side_effect=fake_get):
        sess.get("https://normal.example/", lean_headers=False)

    h = captured["headers"]
    assert "Accept" not in h or h.get("Accept") is not None
    assert "Accept-Language" not in h or h.get("Accept-Language") is not None
