"""Hard-block filter — vroege exits voor posts die NOOIT een lead kunnen zijn.

Wordt direct na fetch + dedup gedraaid, vóór cleaning/classifying/scoring.
Voorbeelden:
- Lead-aggregators (Slimster/Werkspot/Bobex) die "tip nodig"-posts plaatsen
- Recruiters/bureau-advertenties die job ads als lead vermomd plaatsen
- Bedrijfsaccounts van installateurs die zelf vragen stellen (eigen marketing)
- Bot-/spam-patronen

Geeft (blocked: bool, reason: str | None) terug. Reason is voor logging/audit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .. import RawPost

# URL/host-patterns voor lead-aggregators (DIRECTE CONCURRENTEN).  Een post
# vanuit deze domeinen is geen consumer-lead — we pitchen ze niet en we
# verwerken hun listings niet.
AGGREGATOR_HOSTS: frozenset[str] = frozenset({
    "slimster.nl", "slimster.com",
    "bobex.nl", "bobex.be", "bobex.com",
    "trustoo.nl",
    "solvari.nl", "solvari.com",
    "werkspot.nl", "werkspot.com",
    "offerteadviseur.nl", "offerte-vergelijker.nl",
    "offerte.nl", "offertes.nl", "bouwoffertes.nl",
    "casius.nl", "moving.nl", "homedeal.nl",
    "warmtepompgids.nl", "warmtepomp.nu", "warmtepompplek.nl",
    "warmtepompspot.nl", "warmtepomprevolutie.nl",
    "warmtepompaanbieders.nl", "warmtepompnederland.nl",
    "warmtepompamsterdam.com", "warmtepompamsterdam.nl",
    "warmtepomp-amsterdam.com", "warmtepomp-info.nl",
    "warmtepompbedrijf.nl",
    "warmgarant.nl", "warmplus.nl", "zenovo.nl",
})

# Hard-block op auteur-namen die typisch corporate/bot zijn.  Lowercase.
BLOCKED_AUTHOR_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(
        r"^(admin|moderator|automoderator|automod|bot|systeem|system|"
        r"removalbot|reposterbot|mod[\-_]bot)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(installateur|installatie|verwarming|monteurs?|hvac|loodgieter)\b"
        r".*\b(bv|bvba|nv|gmbh|bedrijf)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(marketing|reclame|advertising|sales)\b", re.IGNORECASE),
)

# Titel/text patterns die ALTIJD spam/promo zijn — geen verdere processing.
HARD_PROMO_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(
        r"\b(verdien online|geld verdienen vanuit huis|crypto|forex|"
        r"online casino|betting|gokken)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(escort|massage|adult|18\+|seks|porno)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(daikin|mitsubishi|panasonic|lg|samsung|bosch|atag|"
        r"nefit|remeha|vaillant|stiebel|viessmann|intergas)\s+"
        r"(nederland|belgië|belgium|nv|bv)\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class BlockResult:
    blocked: bool
    reason: str | None

    def __bool__(self) -> bool:
        return self.blocked


def _host_from_url(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"^https?://(?:www\.)?([^/]+)", url, re.IGNORECASE)
    return (m.group(1).lower() if m else "")


def check_hardblock(post: RawPost) -> BlockResult:
    """True = block (drop deze post zonder verdere processing)."""
    host = _host_from_url(post.url)
    if host:
        for agg in AGGREGATOR_HOSTS:
            if host == agg or host.endswith("." + agg):
                return BlockResult(True, f"aggregator:{agg}")

    if post.author:
        for pat in BLOCKED_AUTHOR_PATTERNS:
            if pat.search(post.author):
                return BlockResult(True, f"author_pattern:{pat.pattern[:40]}")

    title_text = f"{post.title or ''}\n{post.text or ''}"
    for pat in HARD_PROMO_PATTERNS:
        if pat.search(title_text):
            return BlockResult(True, f"promo_pattern:{pat.pattern[:40]}")

    return BlockResult(False, None)


def is_blocked(post: RawPost) -> bool:
    return bool(check_hardblock(post))


__all__ = [
    "AGGREGATOR_HOSTS",
    "BLOCKED_AUTHOR_PATTERNS",
    "HARD_PROMO_PATTERNS",
    "BlockResult",
    "check_hardblock",
    "is_blocked",
]
