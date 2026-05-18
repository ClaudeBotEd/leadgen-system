"""3-stage council orchestration + lead-generation domain prompts."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from ..config import get_settings
from ..logging import get_logger
from .openrouter import query_model, query_models_parallel

log = get_logger("council")


# ---------------------------------------------------------------------------
# Stage 1
# ---------------------------------------------------------------------------


def _is_ok(response: Any) -> bool:
    """True if the openrouter call returned usable content.

    Accepts both legacy success dicts (no `ok` key) and the new {ok: True} shape.
    """
    return isinstance(response, dict) and response.get("ok", True) and "content" in response


def _summarize_failures(failures: List[Dict[str, Any]]) -> str:
    """Compact human-readable summary of model failures for the UI."""
    if not failures:
        return ""
    by_kind: Dict[str, List[str]] = defaultdict(list)
    msg_by_kind: Dict[str, str] = {}
    for f in failures:
        err = f.get("error") or {}
        kind = err.get("kind") or "unknown"
        by_kind[kind].append(f["model"])
        msg_by_kind.setdefault(kind, err.get("message") or "")
    parts = []
    for kind, models in by_kind.items():
        m = msg_by_kind.get(kind, "")
        parts.append(f"- {kind} ({', '.join(models)}): {m}" if m else f"- {kind} ({', '.join(models)})")
    return "\n".join(parts)


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """Parallel query to every council model. Survives partial failures.

    Returns successful responses only. Failures are logged but not included
    so downstream stages can rank what actually has content.
    """
    successes, _failures = await _stage1_internal(user_query)
    return successes


async def _stage1_internal(
    user_query: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    settings = get_settings()
    messages = [{"role": "user", "content": user_query}]
    responses = await query_models_parallel(settings.council_models, messages)

    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for model, response in responses.items():
        if _is_ok(response):
            successes.append({"model": model, "response": response.get("content", "")})
        else:
            err = response if isinstance(response, dict) else {}
            log.warning(
                "stage1_model_failed",
                model=model,
                error_kind=err.get("error_kind"),
                status=err.get("status"),
            )
            failures.append(
                {
                    "model": model,
                    "error": {
                        "kind": err.get("error_kind") or "unknown",
                        "status": err.get("status"),
                        "message": err.get("message") or "model call failed",
                    },
                }
            )
    return successes, failures


# ---------------------------------------------------------------------------
# Stage 2
# ---------------------------------------------------------------------------


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """Anonymise responses, ask each model to rank, return rankings + label->model map."""
    settings = get_settings()
    labels = [chr(65 + i) for i in range(len(stage1_results))]
    label_to_model = {
        f"Response {label}": result["model"]
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join(
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    )

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]
    responses = await query_models_parallel(settings.council_models, messages)

    stage2: List[Dict[str, Any]] = []
    for model, response in responses.items():
        if not _is_ok(response):
            err = response if isinstance(response, dict) else {}
            log.warning(
                "stage2_model_failed",
                model=model,
                error_kind=err.get("error_kind"),
                status=err.get("status"),
            )
            continue
        text = response.get("content", "")
        stage2.append(
            {
                "model": model,
                "ranking": text,
                "parsed_ranking": parse_ranking_from_text(text),
            }
        )
    return stage2, label_to_model


# ---------------------------------------------------------------------------
# Stage 3
# ---------------------------------------------------------------------------


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    settings = get_settings()

    stage1_text = "\n\n".join(
        f"Model: {r['model']}\nResponse: {r['response']}" for r in stage1_results
    )
    stage2_text = "\n\n".join(
        f"Model: {r['model']}\nRanking: {r['ranking']}" for r in stage2_results
    )

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]
    response = await query_model(settings.chairman_model, messages)

    if _is_ok(response):
        return {
            "model": settings.chairman_model,
            "response": response.get("content", ""),
        }

    err = response if isinstance(response, dict) else {}
    error_info = {
        "kind": err.get("error_kind") or "unknown",
        "status": err.get("status"),
        "message": err.get("message") or "Chairman synthesis failed.",
    }
    log.warning(
        "stage3_chairman_failed",
        model=settings.chairman_model,
        error_kind=error_info["kind"],
        status=error_info["status"],
    )

    fallback = _pick_fallback(stage1_results, stage2_results, label_to_model)
    if fallback is not None:
        notice = (
            f"_Chairman ({settings.chairman_model}) failed: "
            f"**{error_info['kind']}** — {error_info['message']}._\n\n"
            f"_Falling back to top-ranked council response from "
            f"**{fallback['model']}**._\n\n---\n\n"
        )
        return {
            "model": settings.chairman_model,
            "response": notice + (fallback.get("response") or ""),
            "error": {**error_info, "fallback_model": fallback["model"]},
        }

    return {
        "model": settings.chairman_model,
        "response": (
            f"Council synthesis failed: **{error_info['kind']}** — {error_info['message']}"
        ),
        "error": error_info,
    }


def _pick_fallback(
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    label_to_model: Optional[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    """Choose the best Stage 1 response when the chairman can't synthesize."""
    if not stage1_results:
        return None
    if stage2_results and label_to_model:
        aggregate = calculate_aggregate_rankings(stage2_results, label_to_model)
        if aggregate:
            top_model = aggregate[0]["model"]
            for r in stage1_results:
                if r["model"] == top_model:
                    return r
    return stage1_results[0]


# ---------------------------------------------------------------------------
# Parsing & aggregation
# ---------------------------------------------------------------------------


_RANKING_NUMBERED = re.compile(r"\d+\.\s*Response [A-Z]")
_RANKING_LABEL = re.compile(r"Response [A-Z]")


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    if "FINAL RANKING:" in ranking_text:
        section = ranking_text.split("FINAL RANKING:", 1)[1]
        numbered = _RANKING_NUMBERED.findall(section)
        if numbered:
            return [_RANKING_LABEL.search(m).group() for m in numbered]
        return _RANKING_LABEL.findall(section)
    return _RANKING_LABEL.findall(ranking_text)


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
) -> List[Dict[str, Any]]:
    positions: Dict[str, List[int]] = defaultdict(list)
    for ranking in stage2_results:
        for position, label in enumerate(parse_ranking_from_text(ranking["ranking"]), start=1):
            model = label_to_model.get(label)
            if model:
                positions[model].append(position)

    aggregate = [
        {
            "model": model,
            "average_rank": round(sum(p) / len(p), 2),
            "rankings_count": len(p),
        }
        for model, p in positions.items()
        if p
    ]
    aggregate.sort(key=lambda x: x["average_rank"])
    return aggregate


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


async def run_full_council(
    user_query: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Run all 3 stages end-to-end. Returns (stage1, stage2, stage3, metadata)."""
    settings = get_settings()

    stage1, stage1_failures = await _stage1_internal(user_query)
    if not stage1:
        summary = _summarize_failures(stage1_failures) or "no detail available"
        # Most common kind across failures, for the structured error field.
        kinds = [f["error"]["kind"] for f in stage1_failures if f.get("error")]
        primary_kind = kinds[0] if kinds else "unknown"
        primary_msg = (
            stage1_failures[0]["error"]["message"]
            if stage1_failures and stage1_failures[0].get("error")
            else "All council models failed to respond."
        )
        log.error(
            "council_all_stage1_failed",
            primary_kind=primary_kind,
            failure_count=len(stage1_failures),
        )
        return (
            [],
            [],
            {
                "model": "error",
                "response": (
                    f"**All council models failed.**\n\n"
                    f"Primary cause: **{primary_kind}** — {primary_msg}\n\n"
                    f"Details:\n{summary}"
                ),
                "error": {
                    "kind": primary_kind,
                    "message": primary_msg,
                },
            },
            {"stage1_failures": stage1_failures},
        )

    stage2, label_to_model = await stage2_collect_rankings(user_query, stage1)
    aggregate = calculate_aggregate_rankings(stage2, label_to_model)
    stage3 = await stage3_synthesize_final(user_query, stage1, stage2, label_to_model)

    log.info(
        "council_run_complete",
        council_models=settings.council_models,
        chairman=settings.chairman_model,
        stage1_count=len(stage1),
        stage2_count=len(stage2),
        stage1_failed=len(stage1_failures),
        stage3_fallback=bool(stage3.get("error")),
    )
    return stage1, stage2, stage3, {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate,
        "stage1_failures": stage1_failures,
    }


async def generate_conversation_title(user_query: str) -> str:
    """Short 3-5 word title generated by the cheap title model."""
    settings = get_settings()
    prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""
    response = await query_model(
        settings.title_model, [{"role": "user", "content": prompt}], timeout=30.0
    )
    if not _is_ok(response):
        return "New Conversation"
    title = (response.get("content") or "New Conversation").strip().strip("\"'")
    return title[:47] + "..." if len(title) > 50 else title


# ---------------------------------------------------------------------------
# Lead-generation domain prompts (reusable from the API layer)
# ---------------------------------------------------------------------------


def _format_lead(lead: Dict[str, Any]) -> str:
    """Render a lead dict as a readable bullet list for prompts."""
    items = []
    for key, value in lead.items():
        if value in (None, "", []):
            continue
        items.append(f"- {key}: {value}")
    return "\n".join(items) or "(no fields provided)"


def build_analyze_lead_prompt(lead: Dict[str, Any], objective: str, locale: str) -> str:
    return f"""You are a lead-qualification analyst for a B2B sales team.

Lead record:
{_format_lead(lead)}

Objective: {objective}

Respond in {locale}. Structure your answer with these sections:
1. Fit summary (1-2 sentences)
2. ICP score (0-100) with one-line justification
3. Buying signals & risks (bullets)
4. Recommended next action (single concrete step)
5. Open questions for human follow-up
Keep it concrete and actionable. Do not invent data not present in the record."""


def build_outreach_prompt(
    lead: Dict[str, Any],
    angle: str,
    channel: str,
    locale: str,
    tone: str,
    max_length_chars: int,
) -> str:
    channel_hint = {
        "email": "Format as: SUBJECT: ... then a blank line, then the body. No signature.",
        "linkedin": "Format as a single LinkedIn DM, max ~3 short paragraphs.",
        "sms": "Format as a single short SMS, <= 320 characters total.",
    }[channel]
    return f"""You are an outbound copywriter. Draft a single {channel} outreach message.

Lead:
{_format_lead(lead)}

Positioning angle: {angle}
Tone: {tone}
Language: {locale}
Hard length cap: ~{max_length_chars} characters.

{channel_hint}

Rules:
- Open with something specific to the lead (do not invent facts).
- One clear value hypothesis. No buzzwords.
- One soft CTA at the end.
- No emojis unless the tone explicitly requests them."""


def build_review_scrape_prompt(
    sample: List[Dict[str, Any]],
    source_name: str,
    criteria: str | None,
) -> str:
    rendered = json.dumps(sample[:20], ensure_ascii=False, indent=2)
    crit = criteria or "general data quality + ICP relevance for B2B lead generation"
    return f"""You are a data-quality reviewer. Inspect this scraped sample and produce a structured QA report.

Source: {source_name}
Quality criteria: {crit}

Sample (up to 20 rows):
{rendered}

Produce:
1. Overall verdict: keep / fix / discard.
2. Top 5 quality issues (with row index when applicable).
3. Field-by-field assessment (completeness, plausibility).
4. Recommended cleaning / enrichment steps.
5. Estimated useful-yield % of this sample."""
