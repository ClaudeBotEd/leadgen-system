"""Tests voor _with_retry helper in consumer.output.sheets.

Bug: een enkele 429 (quota) of 503 (transient backend) tijdens Sheets-sync
liet alle leads van die batch verloren gaan zonder retry, ook al was de
API een seconde later weer beschikbaar.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from consumer.output.sheets import _with_retry


class _FakeResponse:
    """Mimics requests.Response API surface used by gspread.APIError."""

    def __init__(self, status_code: int, message: str = "fake error") -> None:
        self.status_code = status_code
        self.text = message
        self._payload = {
            "error": {
                "code": status_code,
                "message": message,
                "status": "ERROR",
            }
        }

    def json(self) -> dict:
        return self._payload


def _make_api_error(status: int) -> Exception:
    """Construct een geldige gspread.APIError met response.status_code."""
    try:
        import gspread.exceptions as gs_exc
    except ImportError:
        pytest.skip("gspread not installed")
    return gs_exc.APIError(_FakeResponse(status))


def test_with_retry_succeeds_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    """Functie die direct succeed't wordt 1x aangeroepen."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    fn = MagicMock(return_value="ok")
    result = _with_retry(fn, "arg1", kw="val")
    assert result == "ok"
    assert fn.call_count == 1
    fn.assert_called_with("arg1", kw="val")


def test_with_retry_retries_on_429_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """429 → backoff → retry; tweede call succeed't → return value."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    err = _make_api_error(429)
    fn = MagicMock(side_effect=[err, "ok-after-retry"])
    result = _with_retry(fn)
    assert result == "ok-after-retry"
    assert fn.call_count == 2


def test_with_retry_retries_on_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """503 = transient backend; moet retryd worden net als 429."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    err = _make_api_error(503)
    fn = MagicMock(side_effect=[err, "ok"])
    result = _with_retry(fn)
    assert result == "ok"


def test_with_retry_does_not_retry_on_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """401 = auth probleem; retry helpt niet, direct raise."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    err = _make_api_error(401)
    fn = MagicMock(side_effect=err)
    with pytest.raises(Exception):
        _with_retry(fn)
    assert fn.call_count == 1  # geen retry


def test_with_retry_raises_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Na 3 pogingen met retryable error: raise de laatste."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    err = _make_api_error(429)
    fn = MagicMock(side_effect=err)
    with pytest.raises(Exception):
        _with_retry(fn)
    assert fn.call_count == 3


def test_with_retry_does_not_retry_on_non_apierror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Niet-APIError (bv. ValueError vanuit caller) wordt direct geraised."""
    monkeypatch.setattr("consumer.output.sheets.time.sleep", lambda *_: None)
    fn = MagicMock(side_effect=ValueError("bad input"))
    with pytest.raises(ValueError):
        _with_retry(fn)
    assert fn.call_count == 1
