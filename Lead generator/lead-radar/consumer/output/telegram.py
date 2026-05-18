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
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import quote

import requests

from .. import Lead

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 8
DEFAULT_HOT_THRESHOLD = 80
API_BASE = "https://api.telegram.org"

_MD_V2_ESCAPE = "_*[]()~`>#+-=|{}.!"


def resolve_chat_id(channel: Literal["consumer", "default"] = "default") -> str | None:
    """Resolve which Telegram chat to send to.

    - channel='consumer': prefer CONSUMER_TELEGRAM_CHAT_ID, fall back to TELEGRAM_CHAT_ID
    - channel='default': always TELEGRAM_CHAT_ID
    Returns None if neither var is set or both are blank.
    """
    if channel == "consumer":
        consumer = (os.environ.get("CONSUMER_TELEGRAM_CHAT_ID") or "").strip()
        if consumer:
            return consumer
    default = (os.environ.get("TELEGRAM_CHAT_ID") or "").strip()
    return default or None


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


def _post_to_telegram(
    chat_id: str,
    text: str,
    *,
    bot_token: str | None = None,
    parse_mode: str = "MarkdownV2",
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> bool:
    """Post a message to Telegram. Returns True on success.

    Used by both send_lead_alert and send_run_digest.
    """
    bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return False

    url = f"{API_BASE}/bot{quote(bot_token, safe=':')}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout_s)
    except requests.RequestException as e:
        log.warning("Telegram send failed: %s", e)
        return False

    if resp.status_code != 200:
        log.warning("Telegram non-200: %d %s", resp.status_code, resp.text[:200])
        return False

    try:
        data = resp.json()
        if not data.get("ok"):
            return False
    except (ValueError, AttributeError):
        return False

    return True


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


@dataclass
class SourceStat:
    """Per-source stats for a run-digest message."""
    source: str          # base name (no source_id subcontext)
    posts: int           # raw posts fetched
    leads: int           # leads after scoring + thresholding
    hot: int             # HOT subset (score >= 80 after source-weight)
    dead: bool = False   # true if dead-source detector tripped this run


@dataclass
class RunStats:
    """Aggregated stats for a run-digest message."""
    timestamp: str                       # ISO-8601 NL-tz of run start
    per_source: list[SourceStat] = field(default_factory=list)
    apify_spend_used_usd: float = 0.0
    apify_spend_cap_usd: float = 0.0


def format_run_digest(stats: RunStats) -> str:
    """Format a single Telegram run-digest message.

    Layout matches spec §5 example. Sources sorted by leads desc within
    alive group; dead sources sorted last and marked with ✗.
    """
    # Short date/time form (YYYY-MM-DD HH:MM in original tz)
    short_ts = stats.timestamp[:16].replace("T", " ")

    sorted_stats = sorted(
        stats.per_source,
        key=lambda s: (s.dead, -s.leads, s.source),
    )

    lines = [f"Daily run {short_ts}:"]
    for s in sorted_stats:
        if s.dead:
            lines.append(f"  ✗ {s.source}: 0 posts (DEAD — needs inspection)")
        else:
            lines.append(
                f"  ✓ {s.source}: {s.posts} posts → {s.leads} leads ({s.hot} HOT)"
            )

    total_leads = sum(s.leads for s in stats.per_source)
    total_hot = sum(s.hot for s in stats.per_source)
    lines.append("")
    lines.append(f"Total: {total_leads} leads, {total_hot} HOT")
    if stats.apify_spend_cap_usd > 0:
        lines.append(
            f"Apify spend today: ${stats.apify_spend_used_usd:.2f} / ${stats.apify_spend_cap_usd:.2f} cap"
        )
    return "\n".join(lines)


def send_run_digest(stats: RunStats, *, channel: str = "consumer") -> bool:
    """Send the digest to the resolved chat. Returns True on success.

    Reuses _post_to_telegram helper for HTTP delivery. Uses resolve_chat_id
    to find the target based on channel preference (consumer vs default).
    """
    chat_id = resolve_chat_id(channel=channel)
    if not chat_id:
        return False
    text = format_run_digest(stats)
    return _post_to_telegram(chat_id=chat_id, text=text)


__all__ = [
    "DEFAULT_HOT_THRESHOLD", "DEFAULT_TIMEOUT_S",
    "TelegramResult",
    "SourceStat", "RunStats",
    "send_lead_alert", "ping_bot",
    "format_run_digest", "send_run_digest",
    "resolve_chat_id",
]
