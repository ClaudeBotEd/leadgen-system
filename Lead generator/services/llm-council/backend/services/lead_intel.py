"""Lead intelligence — structured scoring + outreach sequence generation.

This module wraps OpenRouter calls with strict JSON-output prompts and tolerant
parsing, so callers (lead-radar, CRM, n8n) can rely on a typed dict.

Two strategies are supported per call:
  - "fast" (default): single chairman call; cheap, deterministic, sub-second.
  - "council": full 3-stage deliberation, then a final structured extraction
    pass on the chairman's synthesis. Higher cost; richer rationale.
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

log = get_logger("lead_intel")


# ---------------------------------------------------------------------------
# In-memory cache (Phase 6: cost control)
# ---------------------------------------------------------------------------

_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 60 * 60 * 12  # 12 h
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
# Prompts
# ---------------------------------------------------------------------------

SCORE_SCHEMA = {
    "company_name": "string",
    "lead_quality_score": "0-10 integer",
    "automation_fit_score": "0-10 integer",
    "estimated_budget": "string, free-form (e.g. '<5k EUR', '10-50k EUR', 'enterprise')",
    "urgency_score": "0-10 integer",
    "outbound_potential": "0-10 integer",
    "ai_opportunities": "list of 2-5 concrete AI/automation use cases",
    "pain_points": "list of 2-5 specific operational pain points",
    "recommended_offer": "string, single-sentence offer that matches their needs",
    "best_outreach_angle": "string, the hook that opens the conversation",
    "recommended_channel": "one of: email, linkedin, sms, phone",
    "confidence_score": "0-10 integer — how confident you are in this assessment given the data",
    "rationale": "string, 2-3 sentences justifying the scores",
}

SCORE_SCHEMA_JSON = json.dumps(SCORE_SCHEMA, indent=2, ensure_ascii=False)


def _format_lead(lead: Dict[str, Any]) -> str:
    items = []
    for key, value in lead.items():
        if value in (None, "", []):
            continue
        items.append(f"- {key}: {value}")
    return "\n".join(items) or "(no fields provided)"


def build_score_prompt(lead: Dict[str, Any], objective: str, locale: str) -> str:
    return f"""You are a senior B2B lead-qualification analyst working for an AI automation agency.
Your job is to look at a scraped lead record and produce a STRICT JSON object scoring its potential.

Objective: {objective}
Output language for free-text fields: {locale}

Lead record:
{_format_lead(lead)}

Return ONLY a valid JSON object with EXACTLY these keys (no markdown fences, no commentary):

{SCORE_SCHEMA_JSON}

Scoring rules:
- All *_score and confidence_score fields are integers from 0 to 10.
- If data is missing, lower confidence_score; do not invent facts.
- ai_opportunities and pain_points are short bullet phrases, not paragraphs.
- recommended_channel must be one of: email, linkedin, sms, phone.
- Be conservative: a lead with no website, no contact info, and no signals should score low across the board.
- A lead with clear AI/automation pain (manual processes, hiring difficulty, scaling complaints) should score high on automation_fit_score and urgency_score.

JSON only. No prose."""


def build_sequence_prompt(
    lead: Dict[str, Any],
    analysis: Dict[str, Any],
    locale: str,
    tone: str,
) -> str:
    analysis_block = json.dumps(
        {
            k: v
            for k, v in analysis.items()
            if k
            in {
                "recommended_offer",
                "best_outreach_angle",
                "ai_opportunities",
                "pain_points",
                "recommended_channel",
            }
        },
        indent=2,
        ensure_ascii=False,
    )
    return f"""You are a senior outbound copywriter. Generate a full first-touch sequence for this lead.

Lead:
{_format_lead(lead)}

Council analysis (anchor every line to this — do not invent facts):
{analysis_block}

Language: {locale}
Tone: {tone}

Return ONLY valid JSON with EXACTLY these keys (no markdown fences, no commentary):

{{
  "cold_email": {{
    "subject": "<= 60 chars, specific to the lead",
    "body": "120-180 words, 1 hook + 1 value hypothesis + 1 soft CTA, no signature"
  }},
  "linkedin_opener": "<= 280 chars, conversational, ends with a soft question",
  "follow_up_sequence": [
    {{"day": 3, "channel": "email", "subject": "...", "body": "<= 100 words"}},
    {{"day": 7, "channel": "linkedin", "body": "<= 240 chars"}},
    {{"day": 14, "channel": "email", "subject": "...", "body": "<= 80 words, breakup-style"}}
  ],
  "cta_suggestions": ["3 distinct CTAs the rep can swap in"]
}}

Rules:
- Each message must reference at least one concrete signal from the analysis above.
- No buzzwords, no emojis, no "I hope this finds you well".
- Do not promise outcomes — propose a conversation.
JSON only. No prose."""


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


def _clamp_int(v: Any, default: int = 0) -> int:
    try:
        return max(0, min(10, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def _coerce_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v).strip()


def _coerce_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [s.strip() for s in v.split("\n") if s.strip()]
    return []


def normalize_score(raw: Any, lead: Dict[str, Any]) -> Dict[str, Any]:
    """Always return a complete intelligence dict. Missing/malformed values
    default to safe zeros so the downstream pipeline never crashes."""
    if not isinstance(raw, dict):
        raw = {}
    channel = _coerce_str(raw.get("recommended_channel")).lower() or "email"
    if channel not in {"email", "linkedin", "sms", "phone"}:
        channel = "email"
    return {
        "company_name": _coerce_str(
            raw.get("company_name") or lead.get("company_name") or lead.get("company")
        ),
        "lead_quality_score": _clamp_int(raw.get("lead_quality_score")),
        "automation_fit_score": _clamp_int(raw.get("automation_fit_score")),
        "estimated_budget": _coerce_str(raw.get("estimated_budget")),
        "urgency_score": _clamp_int(raw.get("urgency_score")),
        "outbound_potential": _clamp_int(raw.get("outbound_potential")),
        "ai_opportunities": _coerce_list(raw.get("ai_opportunities"))[:5],
        "pain_points": _coerce_list(raw.get("pain_points"))[:5],
        "recommended_offer": _coerce_str(raw.get("recommended_offer")),
        "best_outreach_angle": _coerce_str(raw.get("best_outreach_angle")),
        "recommended_channel": channel,
        "confidence_score": _clamp_int(raw.get("confidence_score")),
        "rationale": _coerce_str(raw.get("rationale")),
    }


def normalize_sequence(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    cold = raw.get("cold_email") or {}
    if not isinstance(cold, dict):
        cold = {}
    follow = raw.get("follow_up_sequence") or []
    if not isinstance(follow, list):
        follow = []
    normalized_follow = []
    for step in follow:
        if not isinstance(step, dict):
            continue
        normalized_follow.append(
            {
                "day": _clamp_int(step.get("day"), default=3),
                "channel": _coerce_str(step.get("channel")).lower() or "email",
                "subject": _coerce_str(step.get("subject")),
                "body": _coerce_str(step.get("body")),
            }
        )
    return {
        "cold_email": {
            "subject": _coerce_str(cold.get("subject")),
            "body": _coerce_str(cold.get("body")),
        },
        "linkedin_opener": _coerce_str(raw.get("linkedin_opener")),
        "follow_up_sequence": normalized_follow,
        "cta_suggestions": _coerce_list(raw.get("cta_suggestions"))[:5],
    }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

Strategy = Literal["fast", "council"]


async def score_lead(
    lead: Dict[str, Any],
    *,
    objective: str = "qualify this lead for outbound AI-automation outreach",
    locale: str = "en",
    strategy: Strategy = "fast",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Return the structured intelligence dict for a single lead."""
    settings = get_settings()
    key = _cache_key(
        "score",
        {"lead": lead, "obj": objective, "locale": locale, "strategy": strategy},
    )
    if use_cache and (cached := _cache_get(key)) is not None:
        log.info(
            "lead_intel_cache_hit",
            lead=lead.get("company_name") or lead.get("domain"),
        )
        return cached

    started = time.monotonic()
    prompt = build_score_prompt(lead, objective, locale)
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
                "message": result.get("message") or "scoring call failed",
            }

    parsed = extract_json(text) if text else None
    normalized = normalize_score(parsed, lead)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    out: Dict[str, Any] = {
        "lead_id": lead.get("lead_id"),
        "intelligence": normalized,
        "raw_response": text if not upstream_error else "",
        "strategy": strategy,
        "model": settings.chairman_model if strategy == "fast" else "council",
        "elapsed_ms": elapsed_ms,
        "json_parsed": parsed is not None,
        "usage": usage,
        "error": upstream_error,
    }
    log.info(
        "lead_intel_scored",
        lead_id=lead.get("lead_id"),
        company=normalized["company_name"],
        quality=normalized["lead_quality_score"],
        automation=normalized["automation_fit_score"],
        elapsed_ms=elapsed_ms,
        json_parsed=parsed is not None,
        strategy=strategy,
        error_kind=(upstream_error or {}).get("kind") if upstream_error else None,
    )
    if use_cache and parsed is not None and upstream_error is None:
        _cache_set(key, out)
    return out


async def generate_sequence(
    lead: Dict[str, Any],
    analysis: Dict[str, Any],
    *,
    locale: str = "en",
    tone: str = "professional, direct, friendly",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Cold email + linkedin opener + follow-up sequence + CTAs."""
    settings = get_settings()
    key = _cache_key(
        "seq",
        {"lead": lead, "analysis": analysis, "locale": locale, "tone": tone},
    )
    if use_cache and (cached := _cache_get(key)) is not None:
        log.info("lead_intel_cache_hit_seq", lead=lead.get("company_name"))
        return cached

    started = time.monotonic()
    prompt = build_sequence_prompt(lead, analysis, locale, tone)
    result = await query_model(
        settings.chairman_model,
        [{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1200,
    )

    upstream_error: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    if result.get("ok"):
        text = result.get("content", "")
        usage = result.get("usage")
    else:
        text = ""
        upstream_error = {
            "kind": result.get("error_kind") or "unknown",
            "status": result.get("status"),
            "message": result.get("message") or "sequence call failed",
        }

    parsed = extract_json(text) if text else None
    normalized = normalize_sequence(parsed)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    out: Dict[str, Any] = {
        "lead_id": lead.get("lead_id"),
        "sequence": normalized,
        "raw_response": text if not upstream_error else "",
        "model": settings.chairman_model,
        "elapsed_ms": elapsed_ms,
        "json_parsed": parsed is not None,
        "usage": usage,
        "error": upstream_error,
    }
    log.info(
        "lead_intel_sequence",
        lead_id=lead.get("lead_id"),
        elapsed_ms=elapsed_ms,
        json_parsed=parsed is not None,
        error_kind=(upstream_error or {}).get("kind") if upstream_error else None,
    )
    if use_cache and parsed is not None and upstream_error is None:
        _cache_set(key, out)
    return out
