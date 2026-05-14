"""Regression-tests voor Telegram bot alert."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from consumer import Lead
from consumer.output.telegram import (
    DEFAULT_HOT_THRESHOLD,
    _escape_md_v2,
    _format_lead,
    send_lead_alert,
    ping_bot,
)


def _lead(score: int = 85, niche: str = "warmtepomp", city: str | None = "utrecht") -> Lead:
    return Lead(
        id="abc", source="reddit", title="CV kapot Utrecht zoek monteur",
        text="Mijn cv is kapot, spoed.", summary="Mijn cv is kapot, spoed.",
        url="https://reddit.com/r/x/abc", city=city, score=score,
        intent="hot", breakdown={"location": 20}, niche=niche,
    )


def test_escape_md_v2_basic() -> None:
    assert _escape_md_v2("hello (world)") == "hello \\(world\\)"
    assert _escape_md_v2("a.b") == "a\\.b"
    assert _escape_md_v2("") == ""


def test_escape_md_v2_no_specials() -> None:
    assert _escape_md_v2("abc xyz") == "abc xyz"


def test_format_lead_contains_score_and_city() -> None:
    out = _format_lead(_lead(score=85, city="utrecht"))
    assert "85" in out
    assert "Utrecht" in out
    assert "WARMTEPOMP" in out


def test_format_lead_no_city() -> None:
    out = _format_lead(_lead(city=None))
    assert "—" in out


def test_format_lead_includes_suggested_message() -> None:
    out = _format_lead(_lead(), suggested_message="Hoi, las dat je cv kapot is.")
    assert "Voorstel" in out
    assert "cv kapot is" in out


def test_send_below_threshold_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    result = send_lead_alert(_lead(score=50))
    assert result.sent is False
    assert result.skipped_reason == "below_threshold"


def test_send_no_credentials_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    result = send_lead_alert(_lead(score=85))
    assert result.sent is False
    assert result.skipped_reason == "no_credentials"


def test_send_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 42},
    }
    posted = {}

    def fake_post(url, json=None, timeout=None):
        posted["url"] = url
        posted["json"] = json
        return fake_resp

    monkeypatch.setattr("consumer.output.telegram.requests.post", fake_post)

    result = send_lead_alert(_lead(score=90), bot_token="t", chat_id="c")
    assert result.sent is True
    assert result.message_id == 42
    assert posted["json"]["chat_id"] == "c"
    assert posted["json"]["parse_mode"] == "MarkdownV2"


def test_send_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_resp = MagicMock(status_code=403, text="Forbidden")
    monkeypatch.setattr(
        "consumer.output.telegram.requests.post",
        lambda *a, **k: fake_resp,
    )
    result = send_lead_alert(_lead(score=90), bot_token="t", chat_id="c")
    assert result.sent is False
    assert "403" in (result.error or "")


def test_send_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import requests as _r
    def raise_err(*a, **k):
        raise _r.ConnectionError("timeout")

    monkeypatch.setattr("consumer.output.telegram.requests.post", raise_err)
    result = send_lead_alert(_lead(score=90), bot_token="t", chat_id="c")
    assert result.sent is False
    assert "network" in (result.error or "")


def test_ping_bot_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    ok, msg = ping_bot()
    assert ok is False
    assert msg == "no_token"


def test_ping_bot_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {
        "ok": True,
        "result": {"username": "myleadbot"},
    }
    monkeypatch.setattr(
        "consumer.output.telegram.requests.get",
        lambda *a, **k: fake_resp,
    )
    ok, msg = ping_bot(bot_token="t")
    assert ok is True
    assert msg == "@myleadbot"


def test_threshold_constant() -> None:
    assert DEFAULT_HOT_THRESHOLD == 80


def test_format_lead_escapes_close_paren_in_url() -> None:
    """Telegram MarkdownV2 vereist \\) binnen URL-pad. Reddit-URLs bevatten
    regelmatig haakjes (/r/community_(NL)/) — onge-escaped → HTTP 400."""
    lead = Lead(
        id="abc", source="reddit",
        title="CV kapot", text="spoed", summary="spoed",
        url="https://reddit.com/r/foo_(bar)/comments/abc",
        city="utrecht", score=85, intent="hot", breakdown={}, niche="cv",
    )
    out = _format_lead(lead)
    assert "foo_(bar\\)/comments" in out, f"Expected escaped \\) in URL, got: {out!r}"


def test_format_lead_url_without_parens_unchanged() -> None:
    """URL zonder bijzondere tekens moet ongewijzigd doorgegeven worden."""
    lead = Lead(
        id="abc", source="reddit",
        title="x", text="y", summary="y",
        url="https://reddit.com/r/x/abc",
        city="utrecht", score=85, intent="hot", breakdown={}, niche="cv",
    )
    out = _format_lead(lead)
    assert "(https://reddit.com/r/x/abc)" in out


def test_format_lead_escapes_backslash_in_url() -> None:
    """Backslash binnen URL moet ook ge-escaped worden (\\\\)."""
    lead = Lead(
        id="abc", source="reddit",
        title="x", text="y", summary="y",
        url="https://example.com/path\\with\\backslash",
        city="utrecht", score=85, intent="hot", breakdown={}, niche="cv",
    )
    out = _format_lead(lead)
    assert "path\\\\with\\\\backslash" in out
