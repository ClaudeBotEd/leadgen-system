"""HOT-tab admission gate — all six fields must be present and meaningful.

A lead that fails the gate is auto-demoted from HOT to OPP for manual
review. Prevents selling a "HOT lead" that turns out to have no working
contact path.

Spec: docs/superpowers/specs/2026-05-17-supply-expansion-design.md §6.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import Lead

MIN_SUMMARY_LEN = 30
TRUNCATION_MARKERS = ("...", "…", "see full post", "read more")


@dataclass
class GateResult:
    ok: bool
    missing: list[str]


def _has_mid_text_truncation(summary: str) -> bool:
    """Return True only if a truncation marker appears mid-text (not at the end).

    make_summary appends a trailing "…" or "..." after natural sentence cuts,
    which is fine. We only want to flag summaries where truncation markers
    suggest the SOURCE post was already cut off (e.g. "wat zijn de... show more").
    """
    s = summary.lower().rstrip(".… \t\n")
    return any(m in s for m in TRUNCATION_MARKERS)


def is_sellable(lead: Lead) -> GateResult:
    missing: list[str] = []

    if not lead.url:
        missing.append("url")

    if not lead.summary or len(lead.summary) < MIN_SUMMARY_LEN:
        missing.append("summary")
    elif _has_mid_text_truncation(lead.summary):
        missing.append("summary")

    if not lead.city:
        missing.append("city")

    if not lead.author:
        # author_context (Reddit author_enrich) substitutes for raw author
        if not (isinstance(lead.breakdown, dict) and lead.breakdown.get("author_context")):
            missing.append("author")

    if lead.score < 80:
        missing.append("score")

    if not lead.intent or lead.intent in ("unknown", "cold"):
        missing.append("intent")

    return GateResult(ok=not missing, missing=missing)
