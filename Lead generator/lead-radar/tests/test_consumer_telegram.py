"""Telegram chat-id resolution: consumer can route to a separate chat."""
from __future__ import annotations

from consumer.output import telegram as tg


def test_chat_id_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="consumer") == "123"


def test_chat_id_uses_consumer_when_set(monkeypatch):
    monkeypatch.setenv("CONSUMER_TELEGRAM_CHAT_ID", "456")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="consumer") == "456"


def test_chat_id_default_channel_uses_TELEGRAM_CHAT_ID(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="default") == "123"


def test_chat_id_returns_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert tg.resolve_chat_id(channel="consumer") is None


def test_chat_id_empty_string_treated_as_missing(monkeypatch):
    monkeypatch.setenv("CONSUMER_TELEGRAM_CHAT_ID", "   ")  # whitespace only
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "789")
    assert tg.resolve_chat_id(channel="consumer") == "789"
