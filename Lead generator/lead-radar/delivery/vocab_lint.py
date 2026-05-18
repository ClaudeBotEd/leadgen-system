"""Vocabulary linter for rendered receipt copy.

Sources:
- Doctrine §02.3 + Appendix B (B.1 terms we use, B.2 banned terms)
- Spec §3.5 (artifact vocab table)
- Spec §8 (anti-patterns)

A check_no_banned_terms() call on rendered receipt text returns a list of
Violation records. The dispatcher refuses to send any receipt with a
non-empty violation list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

BANNED_VOCAB = frozenset(
    {
        "klant",
        "gebruiker",
        "match",
        "kandidaat",
        "opportunity",
        "lead score",
        "qualified lead",
        "ai-prediction",
        "scraped from web",
        "scraped data",
        "ons systeem",
        "onze ai",
        "data point",
        "support ticket",
        "klacht indienen",
    }
)

REQUIRED_SUBSTITUTIONS = {
    "klant": "installateur",
    "gebruiker": "installateur",
    "match": "lead",
    "kandidaat": "signal",
    "opportunity": "lead",
    "lead score": "(geen score - gebruik band)",
    "qualified lead": "verifieerbare intent",
    "ai-prediction": "(geen AI-claim)",
    "scraped from web": "vastgelegd vanuit {platform}",
    "scraped data": "publieke post",
    "ons systeem": "de reviewer",
    "onze ai": "de reviewer",
    "data point": "signaal",
    "support ticket": "dispuut",
    "klacht indienen": "dispuut openen",
}

AI_CHROME_TERMS = frozenset({"ai", "ml", "gpt", "claude", "llm", "gemini", "model"})
PARAPHRASE_SIGNALS = frozenset(
    {
        "ai-prediction",
        "ai prediction",
        "ai-summary",
        "ai summary",
        "deze homeowner is geïnteresseerd",
    }
)
SENDER_ALIASES = frozenset({"noreply", "no-reply", "leads@", "team@", "support@", "info@"})
URGENCY_EMOJIS = frozenset({"🔥", "⏰", "⚠️", "🚨", "👍", "👎", "🌱"})

BANNED_SUBSTRINGS = BANNED_VOCAB


@dataclass(frozen=True)
class Violation:
    kind: str
    matched: str
    start: int
    suggestion: str


def _word_boundary_iter(text: str, term: str):
    pattern = r"\b" + re.escape(term) + r"\b"
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        yield m.start(), m.group(0)


def _substring_iter(text: str, term: str):
    lower = text.lower()
    needle = term.lower()
    start = 0
    while True:
        idx = lower.find(needle, start)
        if idx == -1:
            return
        yield idx, text[idx : idx + len(term)]
        start = idx + len(needle)


def check_no_banned_terms(text: str) -> List[Violation]:
    out: List[Violation] = []

    for term in BANNED_VOCAB:
        iterator = _word_boundary_iter(text, term) if " " not in term else _substring_iter(text, term)
        for start, matched in iterator:
            suggestion = REQUIRED_SUBSTITUTIONS.get(term, "remove")
            out.append(Violation(kind="vocab_banned", matched=matched, start=start, suggestion=suggestion))

    for term in AI_CHROME_TERMS:
        for start, matched in _word_boundary_iter(text, term):
            out.append(Violation(kind="ai_chrome", matched=matched, start=start, suggestion="remove"))

    for term in PARAPHRASE_SIGNALS:
        for start, matched in _substring_iter(text, term):
            out.append(Violation(kind="paraphrase_signal", matched=matched, start=start, suggestion="remove"))

    for m in re.finditer(r"\b\d{1,3}\s?%", text):
        out.append(Violation(kind="score_numeric", matched=m.group(0), start=m.start(), suggestion="use band glyph"))
    for m in re.finditer(r"(?i)\bscore\b", text):
        out.append(Violation(kind="score_numeric", matched=m.group(0), start=m.start(), suggestion="use band glyph"))

    for term in SENDER_ALIASES:
        for start, matched in _substring_iter(text, term):
            out.append(Violation(kind="sender_alias", matched=matched, start=start, suggestion="use reviewer-named address"))

    for emoji in URGENCY_EMOJIS:
        for start, matched in _substring_iter(text, emoji):
            out.append(Violation(kind="urgency_emoji", matched=matched, start=start, suggestion="remove"))

    return sorted(out, key=lambda v: v.start)
