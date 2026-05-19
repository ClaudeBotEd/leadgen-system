"""Lead moderation — provenance and intent verification for public posts.

This module is the AI side of the trust-provenance-moderation doctrine.
Given a single captured public post (forum thread, social reply, etc.),
the council returns a structured *recommendation* on whether the post
should be promoted to a deliverable lead.

Hard rules baked into the prompt:
  - provenance > volume; when in doubt, downgrade
  - HOT requires explicit, recent, verifiable homeowner intent
  - reject directories, marketplaces, speculative threads, non-homeowners
  - never paraphrase the homeowner — snippet must echo verbatim
  - never write outreach / sales copy
  - the council recommends; humans assign the final delivery band
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple

from ..config import get_settings
from ..logging import get_logger
from . import council as council_svc
from .openrouter import query_model

log = get_logger("lead_moderation")


# ---------------------------------------------------------------------------
# Allowed enum values (doctrine-aligned, kept in sync with schemas.py)
# ---------------------------------------------------------------------------

_TEMPERATURES = ("HOT", "WARM", "OPP")
_CONFIDENCE_BANDS = ("high", "medium", "low")
_PROVENANCE_STATUS = ("verified", "likely", "unverifiable", "rejected")
_SIGNAL_TYPES = (
    "INTENT_DIRECT", "INTENT_RESEARCH", "INTENT_QUOTE",
    "INTENT_PROBLEM", "INTENT_TIMELINE", "NONE",
)
_PURCHASE_WINDOWS = ("<30 days", "30-90 days", "90+ days", "unknown")
_VALUE_BANDS = ("<5k EUR", "5-15k EUR", "15-30k EUR", "30k+ EUR", "unknown")
_DUPLICATE_RISK = ("low", "medium", "high")
_SOURCE_QUALITY = ("high", "medium", "low")


# ---------------------------------------------------------------------------
# In-memory cache (Phase 6: cost control)
# ---------------------------------------------------------------------------

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 12
_CACHE_MAX_ENTRIES = 1024


def _cache_key(prefix: str, payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return prefix + ":" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(key)
    if item is None:
        return None
    ts, value = item
    if time.time() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Dict[str, Any]) -> None:
    if len(_CACHE) >= _CACHE_MAX_ENTRIES:
        oldest = min(_CACHE.items(), key=lambda kv: kv[1][0])[0]
        _CACHE.pop(oldest, None)
    _CACHE[key] = (time.time(), value)


def reset_cache() -> None:
    """Test hook."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_REVIEW_SCHEMA = {
    "lead_temperature": "one of: HOT | WARM | OPP",
    "confidence_band": "one of: high | medium | low",
    "provenance_status": "one of: verified | likely | unverifiable | rejected",
    "signal_type": ("one of: INTENT_DIRECT | INTENT_RESEARCH | INTENT_QUOTE | "
                    "INTENT_PROBLEM | INTENT_TIMELINE | NONE"),
    "intent_summary": "string, 1 sentence the reviewer could repeat verbatim",
    "homeowner_motivation": "string, in the homeowner's own framing, 1-2 sentences",
    "estimated_purchase_window": "one of: <30 days | 30-90 days | 90+ days | unknown",
    "estimated_install_value_band": "one of: <5k EUR | 5-15k EUR | 15-30k EUR | 30k+ EUR | unknown",
    "trust_flags": ("list of short flags. Allowed values include: "
                    "directory_source, marketplace_source, outdated_thread, "
                    "non_homeowner, speculative_language, unverifiable_author, "
                    "decayed_url, spam_signals, off_topic, missing_region, "
                    "second_hand_account. Empty list if none apply."),
    "review_required": "boolean; true unless the post is unambiguously deliverable as HOT",
    "duplicate_risk": "one of: low | medium | high",
    "source_quality": "one of: high | medium | low",
    "rejection_reason": "string; filled iff lead_temperature is OPP or provenance_status is rejected",
    "reviewer_notes": "string, <= 2 sentences",
}

_REVIEW_SCHEMA_JSON = json.dumps(_REVIEW_SCHEMA, indent=2, ensure_ascii=False)


def _format_candidate(candidate: Dict[str, Any]) -> str:
    keys_first = [
        "source_url", "source_platform", "captured_at", "posted_at",
        "snippet_lang", "region", "niche", "author_handle",
    ]
    rendered: List[str] = []
    for k in keys_first:
        v = candidate.get(k)
        if v:
            rendered.append(f"- {k}: {v}")
    snippet = (candidate.get("snippet") or "").strip()
    extras = {
        k: v for k, v in candidate.items()
        if k not in {*keys_first, "snippet"} and v not in (None, "", [], {})
    }
    if extras:
        rendered.append("- extra_context: " + json.dumps(extras, ensure_ascii=False, default=str))
    rendered.append("")
    rendered.append("VERBATIM POST (do not paraphrase):")
    rendered.append('"""')
    rendered.append(snippet)
    rendered.append('"""')
    return "\n".join(rendered)


def build_moderation_prompt(candidate: Dict[str, Any], locale: str) -> str:
    return f"""You are a moderation reviewer for a public-intent verification service for installateurs (Dutch installer trade).

You are NOT an AI lead-generation engine. You do not write outreach.
You verify whether a captured public post is a real, deliverable homeowner-intent signal.

Doctrine (non-negotiable):
- Provenance over volume. When in doubt, downgrade.
- HOT requires explicit, recent, verifiable homeowner intent expressed in the post itself.
- Marketplaces, directories, comparison portals, and second-hand referrals are REJECTED.
- Non-homeowners (companies, installateurs, agents, journalists) are REJECTED.
- Speculative discussion ("what would be best?") without a buying signal is WARM at most.
- Outdated threads (>120 days since posted_at, if known) drop to OPP.
- Never paraphrase the homeowner. The verbatim snippet must remain untouched.
- You make a *recommendation*. A human reviewer assigns the final delivery band.

Output language for free-text fields: {locale}.

Captured post under review:

{_format_candidate(candidate)}

Return ONLY a valid JSON object with EXACTLY these keys (no markdown fences, no commentary):

{_REVIEW_SCHEMA_JSON}

Calibration rules:
- HOT only if the post explicitly says or strongly implies: I want to buy / quote / install / replace, within a clear region, and the author is the homeowner.
- WARM if there is research intent or a problem description but no explicit buying request.
- OPP for anything below WARM: rumour, second-hand, speculation, unclear authorship, marketplace listing.
- provenance_status="rejected" => lead_temperature MUST be OPP.
- confidence_band reflects YOUR confidence in this classification, not the homeowner's confidence.
- estimated_install_value_band: pick the closest band based on niche signals; otherwise "unknown".
- review_required=false ONLY if HOT + verified + high confidence_band + no trust_flags.
- If you set lead_temperature=OPP, fill rejection_reason with one short clause.
- trust_flags: only include flags that actually apply.
- duplicate_risk: high if the snippet looks templated, generic, or reposted across platforms.

JSON only. No prose. No outreach copy. No "AI" recommendations."""


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL | re.IGNORECASE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON object out of an LLM response.

    Tolerates: markdown fences, leading/trailing prose, trailing commas
    (best-effort), and stray BOMs.
    """
    if not text:
        return None
    text = text.strip().lstrip("﻿")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = _OBJECT.search(text)
    if m:
        candidate = m.group(0)
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Coercion helpers — never let a malformed model break the pipeline
# ---------------------------------------------------------------------------


def _enum(value: Any, allowed: Tuple[str, ...], default: str) -> str:
    if not isinstance(value, str):
        return default
    v = value.strip()
    if v in allowed:
        return v
    upper = {a.upper(): a for a in allowed}
    if v.upper() in upper:
        return upper[v.upper()]
    lower = {a.lower(): a for a in allowed}
    if v.lower() in lower:
        return lower[v.lower()]
    return default


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


def _coerce_bool(v: Any, default: bool = True) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in {"true", "yes", "1", "on"}
    return default


_ALLOWED_FLAGS = {
    "directory_source", "marketplace_source", "outdated_thread",
    "non_homeowner", "speculative_language", "unverifiable_author",
    "decayed_url", "spam_signals", "off_topic", "missing_region",
    "second_hand_account",
}


def _coerce_flags(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        raw = [str(x).strip() for x in v if str(x).strip()]
    elif isinstance(v, str):
        raw = [s.strip() for s in re.split(r"[,\n;]", v) if s.strip()]
    else:
        return []
    seen: set = set()
    out: List[str] = []
    for f in raw:
        norm = f.lower().replace(" ", "_").replace("-", "_")
        if norm in seen:
            continue
        seen.add(norm)
        if norm in _ALLOWED_FLAGS or re.fullmatch(r"[a-z][a-z0-9_]{2,40}", norm):
            out.append(norm)
    return out[:10]


def normalize_review(raw: Any, candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Always return a complete LeadReview dict.

    Missing or malformed values default to the most conservative
    ("safest to reject") option, so an unparseable model response still
    yields a deterministic, doctrine-aligned record.
    """
    if not isinstance(raw, dict):
        raw = {}

    temperature = _enum(raw.get("lead_temperature"), _TEMPERATURES, "OPP")
    confidence = _enum(raw.get("confidence_band"), _CONFIDENCE_BANDS, "low")
    provenance = _enum(raw.get("provenance_status"), _PROVENANCE_STATUS, "unverifiable")
    signal = _enum(raw.get("signal_type"), _SIGNAL_TYPES, "NONE")

    # Doctrine invariant: provenance=rejected forces OPP.
    if provenance == "rejected":
        temperature = "OPP"

    raw_flags = _coerce_flags(raw.get("trust_flags"))

    review_required = _coerce_bool(raw.get("review_required"), default=True)
    # Safety floor: anything below HOT-verified-high-no-flags must require human review.
    if not (
        temperature == "HOT"
        and provenance == "verified"
        and confidence == "high"
        and not raw_flags
    ):
        review_required = True

    snippet = _coerce_str(raw.get("verbatim_snippet")) or _coerce_str(candidate.get("snippet"))

    return {
        "source_url": _coerce_str(raw.get("source_url")) or _coerce_str(candidate.get("source_url")),
        "verbatim_snippet": snippet,
        "captured_at": _coerce_str(raw.get("captured_at")) or _coerce_str(candidate.get("captured_at")),
        "lead_temperature": temperature,
        "confidence_band": confidence,
        "provenance_status": provenance,
        "signal_type": signal,
        "intent_summary": _coerce_str(raw.get("intent_summary"))[:600],
        "homeowner_motivation": _coerce_str(raw.get("homeowner_motivation"))[:600],
        "estimated_purchase_window": _enum(
            raw.get("estimated_purchase_window"), _PURCHASE_WINDOWS, "unknown"
        ),
        "estimated_install_value_band": _enum(
            raw.get("estimated_install_value_band"), _VALUE_BANDS, "unknown"
        ),
        "trust_flags": raw_flags,
        "review_required": review_required,
        "duplicate_risk": _enum(raw.get("duplicate_risk"), _DUPLICATE_RISK, "low"),
        "source_quality": _enum(raw.get("source_quality"), _SOURCE_QUALITY, "low"),
        "rejection_reason": _coerce_str(raw.get("rejection_reason"))[:400],
        "reviewer_notes": _coerce_str(raw.get("reviewer_notes"))[:400],
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

Strategy = Literal["fast", "council"]


async def moderate_lead(
    candidate: Dict[str, Any],
    *,
    locale: str = "nl",
    strategy: Strategy = "fast",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Return the council's moderation verdict for a single captured post."""
    settings = get_settings()
    key = _cache_key(
        "moderate",
        {"candidate": candidate, "locale": locale, "strategy": strategy},
    )
    if use_cache and (cached := _cache_get(key)) is not None:
        log.info(
            "moderation_cache_hit",
            candidate_id=candidate.get("candidate_id"),
            source_url=candidate.get("source_url"),
        )
        return cached

    started = time.monotonic()
    prompt = build_moderation_prompt(candidate, locale)
    upstream_error: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None

    if strategy == "council":
        _stage1, _stage2, stage3, _meta = await council_svc.run_full_council(prompt)
        text = stage3.get("response", "")
        upstream_error = stage3.get("error")
    else:
        result = await query_model(
            settings.chairman_model,
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=900,
        )
        if result.get("ok"):
            text = result.get("content", "")
            usage = result.get("usage")
        else:
            text = ""
            upstream_error = {
                "kind": result.get("error_kind") or "unknown",
                "status": result.get("status"),
                "message": result.get("message") or "moderation call failed",
            }

    parsed = extract_json(text) if text else None
    normalized = normalize_review(parsed, candidate)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    out: Dict[str, Any] = {
        "candidate_id": candidate.get("candidate_id"),
        "review": normalized,
        "raw_response": text if not upstream_error else "",
        "strategy": strategy,
        "model": settings.chairman_model if strategy == "fast" else "council",
        "elapsed_ms": elapsed_ms,
        "json_parsed": parsed is not None,
        "usage": usage,
        "error": upstream_error,
    }
    log.info(
        "moderation_review",
        candidate_id=candidate.get("candidate_id"),
        source_url=candidate.get("source_url"),
        temperature=normalized["lead_temperature"],
        confidence_band=normalized["confidence_band"],
        provenance=normalized["provenance_status"],
        review_required=normalized["review_required"],
        flags=len(normalized["trust_flags"]),
        elapsed_ms=elapsed_ms,
        json_parsed=parsed is not None,
        strategy=strategy,
        error_kind=(upstream_error or {}).get("kind") if upstream_error else None,
    )
    if use_cache and parsed is not None and upstream_error is None:
        _cache_set(key, out)
    return out
