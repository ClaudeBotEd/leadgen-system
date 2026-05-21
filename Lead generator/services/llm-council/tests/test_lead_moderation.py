"""Tests for the moderation layer (replaces test_lead_intel.py).

Covers:
- extract_json tolerates fences / prose / trailing commas / garbage
- normalize_review clamps to allowed enums, applies doctrine invariants
- moderate_lead round-trips a HOT verdict, caches identical inputs
- /api/council/moderate-lead works through the HTTP layer with a mock
- upstream errors are surfaced without breaking the pipeline
"""

from __future__ import annotations

import json

import pytest

from backend.services import lead_moderation


def test_extract_json_handles_markdown_fences():
    text = "```json\n{\"lead_temperature\": \"HOT\"}\n```"
    assert lead_moderation.extract_json(text) == {"lead_temperature": "HOT"}


def test_extract_json_returns_none_on_garbage():
    assert lead_moderation.extract_json("not json") is None
    assert lead_moderation.extract_json("") is None


def test_normalize_review_clamps_unknown_enums_to_safe_defaults():
    raw = {
        "lead_temperature": "blazing",
        "confidence_band": "Medium",
        "provenance_status": "rejected",
        "signal_type": "INTENT_DIRECT",
        "estimated_purchase_window": "next week",
        "estimated_install_value_band": "30k EUR+",
        "trust_flags": ["marketplace_source", "unknown_flag_x"],
        "review_required": False,
        "duplicate_risk": "HIGH",
        "source_quality": "LOW",
    }
    out = lead_moderation.normalize_review(
        raw, {"snippet": "s", "source_url": "u", "captured_at": "c"}
    )
    assert out["lead_temperature"] == "OPP"            # provenance=rejected forces OPP
    assert out["confidence_band"] == "medium"
    assert out["provenance_status"] == "rejected"
    assert out["estimated_purchase_window"] == "unknown"
    assert out["estimated_install_value_band"] == "unknown"
    assert "marketplace_source" in out["trust_flags"]
    # Safety floor: anything below HOT-verified-high must force review_required.
    assert out["review_required"] is True


def test_normalize_review_only_clears_review_required_for_clean_hot():
    raw = {
        "lead_temperature": "HOT",
        "confidence_band": "high",
        "provenance_status": "verified",
        "signal_type": "INTENT_DIRECT",
        "trust_flags": [],
        "review_required": False,
    }
    out = lead_moderation.normalize_review(
        raw, {"snippet": "s", "source_url": "u", "captured_at": "c"}
    )
    assert out["review_required"] is False


def test_normalize_review_falls_back_to_candidate_provenance_fields():
    out = lead_moderation.normalize_review(
        {},
        {
            "source_url": "https://example.test/post/1",
            "snippet": "Verbatim text from the homeowner.",
            "captured_at": "2026-05-18T10:00:00Z",
        },
    )
    assert out["source_url"] == "https://example.test/post/1"
    assert out["verbatim_snippet"] == "Verbatim text from the homeowner."
    assert out["captured_at"] == "2026-05-18T10:00:00Z"
    assert out["lead_temperature"] == "OPP"
    assert out["review_required"] is True
    assert out["provenance_status"] == "unverifiable"


def test_normalize_review_strips_unknown_freeform_flags():
    out = lead_moderation.normalize_review(
        {"trust_flags": ["MARKETPLACE source ", "blarg!", "spam_signals"]},
        {"snippet": "s", "source_url": "u", "captured_at": "c"},
    )
    assert "marketplace_source" in out["trust_flags"]
    assert "spam_signals" in out["trust_flags"]
    assert "blarg!" not in out["trust_flags"]


@pytest.mark.asyncio
async def test_moderate_lead_round_trip(monkeypatch):
    lead_moderation.reset_cache()

    verdict = {
        "lead_temperature": "HOT",
        "confidence_band": "high",
        "provenance_status": "verified",
        "signal_type": "INTENT_DIRECT",
        "intent_summary": "Homeowner asks installer to quote replacement.",
        "homeowner_motivation": "Oude cv-ketel valt uit, wil snel een warmtepomp.",
        "estimated_purchase_window": "<30 days",
        "estimated_install_value_band": "5-15k EUR",
        "trust_flags": [],
        "review_required": False,
        "duplicate_risk": "low",
        "source_quality": "high",
        "rejection_reason": "",
        "reviewer_notes": "Clear, recent, region given.",
    }

    async def fake(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": json.dumps(verdict),
            "reasoning_details": None,
            "usage": {"prompt_tokens": 250, "completion_tokens": 120, "total_tokens": 370},
        }

    monkeypatch.setattr("backend.services.lead_moderation.query_model", fake)

    out = await lead_moderation.moderate_lead(
        {
            "candidate_id": "cap_001",
            "source_url": "https://example.test/thread/42",
            "snippet": "Onze cv begeeft het, wie kan een warmtepomp plaatsen in Utrecht?",
            "captured_at": "2026-05-18T10:00:00Z",
            "posted_at": "2026-05-18T09:55:00Z",
            "source_platform": "gathering-of-tweakers",
            "region": "Utrecht",
        }
    )

    assert out["json_parsed"] is True
    assert out["error"] is None
    review = out["review"]
    assert review["lead_temperature"] == "HOT"
    assert review["provenance_status"] == "verified"
    assert review["review_required"] is False
    assert review["source_url"].endswith("/thread/42")
    assert "warmtepomp" in review["verbatim_snippet"]
    assert out["usage"]["total_tokens"] == 370


@pytest.mark.asyncio
async def test_moderate_lead_cache_hit(monkeypatch):
    lead_moderation.reset_cache()
    calls = {"n": 0}

    async def fake(model, messages, **kwargs):  # noqa: ARG001
        calls["n"] += 1
        return {
            "ok": True,
            "content": '{"lead_temperature":"WARM","provenance_status":"likely"}',
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_moderation.query_model", fake)
    candidate = {
        "source_url": "https://example.test/a",
        "snippet": "test",
        "captured_at": "2026-05-18T10:00:00Z",
    }
    a = await lead_moderation.moderate_lead(candidate)
    b = await lead_moderation.moderate_lead(candidate)
    assert a["review"]["lead_temperature"] == "WARM"
    assert b["review"]["lead_temperature"] == "WARM"
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_moderate_lead_surfaces_error_when_chairman_fails(monkeypatch):
    lead_moderation.reset_cache()

    async def fail(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": False,
            "error_kind": "insufficient_credits",
            "status": 402,
            "message": "OpenRouter account has insufficient credits.",
        }

    monkeypatch.setattr("backend.services.lead_moderation.query_model", fail)

    out = await lead_moderation.moderate_lead(
        {
            "source_url": "https://example.test/x",
            "snippet": "post",
            "captured_at": "2026-05-18T10:00:00Z",
        }
    )
    assert out["json_parsed"] is False
    assert out["error"]["kind"] == "insufficient_credits"
    assert out["review"]["lead_temperature"] == "OPP"
    assert out["review"]["provenance_status"] == "unverifiable"
    assert out["review"]["review_required"] is True


def test_moderate_lead_endpoint(client, monkeypatch, mock_openrouter):  # noqa: ARG001
    lead_moderation.reset_cache()
    verdict_blob = json.dumps(
        {
            "lead_temperature": "HOT",
            "confidence_band": "high",
            "provenance_status": "verified",
            "signal_type": "INTENT_QUOTE",
            "intent_summary": "Homeowner wants a quote.",
            "homeowner_motivation": "Wil warmtepomp laten plaatsen.",
            "estimated_purchase_window": "<30 days",
            "estimated_install_value_band": "5-15k EUR",
            "trust_flags": [],
            "review_required": False,
            "duplicate_risk": "low",
            "source_quality": "high",
            "rejection_reason": "",
            "reviewer_notes": "Clean.",
        }
    )

    async def fake_query_model(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": verdict_blob,
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_moderation.query_model", fake_query_model)

    r = client.post(
        "/api/council/moderate-lead",
        json={
            "candidate": {
                "candidate_id": "cap_42",
                "source_url": "https://example.test/post/42",
                "snippet": "Ik zoek een installateur voor een warmtepomp in Utrecht.",
                "captured_at": "2026-05-18T10:00:00Z",
                "source_platform": "gathering-of-tweakers",
                "region": "Utrecht",
            },
            "locale": "nl",
            "strategy": "fast",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidate_id"] == "cap_42"
    assert body["review"]["lead_temperature"] == "HOT"
    assert body["review"]["provenance_status"] == "verified"
    assert body["json_parsed"] is True
