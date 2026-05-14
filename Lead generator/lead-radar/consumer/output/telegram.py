"""Telegram bot — push HOT leads naar je telefoon, in real-time.

Setup:
1. Maak een bot via @BotFather op Telegram, krijg TELEGRAM_BOT_TOKEN.
2. Start een chat met de bot, stuur willekeurig bericht.
3. Open `https://api.telegram.org/bot<token>/getUpdates`, kopieer chat-ID.
4. Zet env vars:
   export TELEGRAM_BOT_TOKEN="123456:ABC..."
   export TELEGRAM_CHAT_ID="987654321"

Bij ontbrekende env / netwerk-fout: graceful no-op + warning log.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from urllib.parse import quote

import requests

from .. import Lead

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 8
DEFAULT_HOT_THRESHOLD = 80
API_BASE = "https://api.telegram.org"

_MD_V2_ESCAPE = "_*[]()~`>#+-=|{}.!"


@dataclass
class TelegramResult:
    sent: bool
    skipped_reason: str | None = None
    error: str | None = None
    message_id: int | None = None


def _escape_md_v2(text: str) -> str:
    if not text:
        return ""
    out = []
    for ch in text:
        if ch in _MD_V2_ESCAPE:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _escape_md_v2_url(url: str) -> str:
    """Escape \\ en ) binnen MarkdownV2 link-URL.

    Telegram-spec: binnen (...) van [text](url) moeten ) en \\ ge-escaped
    worden, anders sluit de eerste ) de link voortijdig → HTTP 400.

    Backslash eerst (anders dubbel-escape op de \\ die we vóór ) zetten).
    """
    if not url:
        return ""
    return url.replace("\\", "\\\\").replace(")", "\\)")


def _format_lead(lead: Lead, suggested_message: str | None = None) -> str:
    score = lead.score
    intent_emoji = "🔥" if score >= 80 else ("⚡" if score >= 70 else "·")
    city = (lead.city or "—").title()
    title = (lead.title or "").strip()[:140]
    summary = (lead.summary or "").strip()[:240]

    lines = [
        f"{intent_emoji} *{score}* — {_escape_md_v2(lead.niche.upper())} — {_escape_md_v2(city)}",
        "",
        f"*{_escape_md_v2(title)}*",
        "",
        _escape_md_v2(summary),
    ]
    if suggested_message:
        lines += ["", "💬 _Voorstel:_ " + _escape_md_v2(suggested_message)]
    if lead.url:
        lines += ["", f"[Open op {_escape_md_v2(lead.source)}]({_escape_md_v2_url(lead.url)})"]
    return "\n".join(lines)


def send_lead_alert(
    lead: Lead,
    *,
    suggested_message: str | None = None,
    bot_token: str | None = None,
    chat_id: str | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    hot_threshold: int = DEFAULT_HOT_THRESHOLD,
) -> TelegramResult:
    """Verzend een lead-alert naar Telegram.  No-op zonder env vars."""
    if lead.score < hot_threshold:
        return TelegramResult(sent=False, skipped_reason="below_threshold")

    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return TelegramResult(sent=False, skipped_reason="no_credentials")

    body = _format_lead(lead, suggested_message=suggested_message)
    url = f"{API_BASE}/bot{quote(bot_token, safe=':')}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": body,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout_s)
    except requests.RequestException as e:
        log.warning("Telegram send failed: %s", e)
        return TelegramResult(sent=False, error=f"network:{type(e).__name__}")

    if resp.status_code != 200:
        log.warning("Telegram non-200: %d %s", resp.status_code, resp.text[:200])
        return TelegramResult(sent=False, error=f"http_{resp.status_code}")

    try:
        data = resp.json()
        if not data.get("ok"):
            return TelegramResult(sent=False, error=f"api:{data.get('description', '?')}")
        mid = data.get("result", {}).get("message_id")
    except (ValueError, AttributeError) as e:
        return TelegramResult(sent=False, error=f"parse:{type(e).__name__}")

    return TelegramResult(sent=True, message_id=mid)


def ping_bot(
    *, bot_token: str | None = None, timeout_s: int = DEFAULT_TIMEOUT_S,
) -> tuple[bool, str]:
    """Hit /getMe om te verifiëren dat token werkt.  Geen chat_id nodig."""
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return False, "no_token"
    try:
        resp = requests.get(
            f"{API_BASE}/bot{quote(bot_token, safe=':')}/getMe",
            timeout=timeout_s,
        )
    except requests.RequestException as e:
        return False, f"network:{type(e).__name__}"
    if resp.status_code != 200:
        return False, f"http_{resp.status_code}"
    try:
        data = resp.json()
        if not data.get("ok"):
            return False, f"api:{data.get('description', '?')}"
        username = data.get("result", {}).get("username", "?")
        return True, f"@{username}"
    except (ValueError, AttributeError):
        return False, "parse"


__all__ = [
    "DEFAULT_HOT_THRESHOLD", "DEFAULT_TIMEOUT_S",
    "TelegramResult",
    "send_lead_alert", "ping_bot",
]
