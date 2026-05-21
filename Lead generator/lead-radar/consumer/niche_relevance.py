"""Per-niche relevance gate for Sheets writes.

Loads anchor terms from `consumer/niche_anchors.yaml` and tests whether
a lead's title+text contains at least one anchor for the claimed niche.
The gate runs in `run_consumer.run_single` / `run_daily` immediately
before `sync_to_sheets`, so CSV/JSON exports stay unfiltered.

Design: case-insensitive substring match. No stemming, no fuzzy. Anchors
are config (niche_anchors.yaml) — tune them when real posts are dropped
or contaminants slip through.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml

log = logging.getLogger("consumer.niche_relevance")

_ANCHORS_PATH = Path(__file__).resolve().parent / "niche_anchors.yaml"


@lru_cache(maxsize=1)
def _load_all_anchors() -> dict[str, list[str]]:
    if not _ANCHORS_PATH.exists():
        log.warning(
            "niche_anchors.yaml not found at %s — gate closed for all niches",
            _ANCHORS_PATH,
        )
        return {}
    try:
        data = yaml.safe_load(_ANCHORS_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        log.error("niche_anchors.yaml parse error: %s — gate closed", exc)
        return {}
    niches = data.get("niches") or {}
    out: dict[str, list[str]] = {}
    for niche, anchors in niches.items():
        if not isinstance(anchors, list):
            continue
        out[str(niche)] = [str(a).strip().lower() for a in anchors if str(a).strip()]
    return out


def load_anchors(niche: str) -> list[str]:
    """Return the anchor list for `niche`, or [] if unknown.

    Lower-cased copies; safe to mutate the returned list.
    """
    return list(_load_all_anchors().get(niche, []))


def is_niche_relevant(
    lead_title: str | None,
    lead_text: str | None,
    niche: str,
) -> bool:
    """True iff title+text contains any anchor for `niche`.

    Substring match, case-insensitive. Returns False on unknown niche,
    empty anchor list, or empty input.
    """
    anchors = load_anchors(niche)
    if not anchors:
        return False
    haystack = " ".join(part for part in (lead_title, lead_text) if part).lower()
    if not haystack.strip():
        return False
    return any(anchor in haystack for anchor in anchors)
