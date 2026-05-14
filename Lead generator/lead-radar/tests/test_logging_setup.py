"""Tests voor structured logging setup."""
from __future__ import annotations

import json
import logging

import pytest

from consumer.logging_setup import JsonFormatter, setup_logging


def test_json_formatter_basic_fields() -> None:
    rec = logging.LogRecord(
        name="x.y", level=logging.INFO, pathname="x.py", lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    out = JsonFormatter(run_id="abc").format(rec)
    payload = json.loads(out)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "x.y"
    assert payload["msg"] == "hello world"
    assert payload["run_id"] == "abc"
    assert isinstance(payload["ts"], int)


def test_json_formatter_includes_custom_fields() -> None:
    rec = logging.LogRecord(
        name="x", level=logging.INFO, pathname="x.py", lineno=1,
        msg="m", args=(), exc_info=None,
    )
    rec.custom = "value"
    rec.score = 42
    out = JsonFormatter(run_id="abc").format(rec)
    payload = json.loads(out)
    assert payload["custom"] == "value"
    assert payload["score"] == 42


def test_setup_logging_returns_run_id() -> None:
    run_id = setup_logging(run_id="test-run-1234")
    assert run_id == "test-run-1234"


def test_setup_logging_emits_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.setenv("LEAD_RADAR_LOG_FORMAT", "json")
    setup_logging(run_id="abc", json_format=None)
    logging.getLogger("test.x").info("hello")
    captured = capsys.readouterr()
    line = captured.err.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["msg"] == "hello"
    assert payload["run_id"] == "abc"


def test_setup_logging_plain_format_has_run_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture,
) -> None:
    monkeypatch.delenv("LEAD_RADAR_LOG_FORMAT", raising=False)
    setup_logging(run_id="zzz", json_format=False)
    logging.getLogger("test.y").info("hi")
    captured = capsys.readouterr()
    assert "zzz" in captured.err
    assert "hi" in captured.err


def test_setup_logging_silences_noisy_libs() -> None:
    setup_logging()
    assert logging.getLogger("urllib3").level == logging.WARNING
    assert logging.getLogger("requests").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_setup_logging_no_sentry_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    run_id = setup_logging()
    assert isinstance(run_id, str)
    assert len(run_id) >= 8
