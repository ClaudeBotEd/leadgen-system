"""Tests for structured lead scoring + sequence generation."""

from __future__ import annotations

import json

import pytest

from backend.services import lead_intel


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_extract_json_handles_markdown_fences():
    text = "```json\n{\"lead_quality_score\": 7, \"automation_fit_score\": 8}\n```"
    parsed = lead_intel.extract_json(text)
    assert parsed == {"lead_quality_score": 7, "automation_fit_score": 8}


def test_extract_json_handles_prose_wrapping():
    text = "Sure, here you go:\n{\"a\": 1, \"b\": 2}\nThanks!"
    parsed = lead_intel.extract_json(text)
    assert parsed == {"a": 1, "b": 2}


def test_extract_json_repairs_trailing_comma():
    text = '{"a": 1, "b": 2,}'
    parsed = lead_intel.extract_json(text)
    assert parsed == {"a": 1, "b": 2}


def test_extract_json_returns_none_on_garbage():
    assert lead_intel.extract_json("totally not json") is None
    assert lead_intel.extract_json("") is None


def test_normalize_score_clamps_and_defaults():
    raw = {
        "company_name": "Acme",
        "lead_quality_score": 99,
        "automation_fit_score": -3,
        "urgency_score": "5",
        "outbound_potential": None,
        "recommended_channel": "carrier-pigeon",
        "ai_opportunities": "intake automation\ncrm scoring",
        "pain_points": ["manual quoting", "  ", "no crm"],
    }
    out = lead_intel.normalize_score(raw, {"company_name": "Fallback BV"})
    assert out["company_name"] == "Acme"
    assert out["lead_quality_score"] == 10
    assert out["automation_fit_score"] == 0
    assert out["urgency_score"] == 5
    assert out["outbound_potential"] == 0
    assert out["recommended_channel"] == "email"
    assert out["ai_opportunities"] == ["intake automation", "crm scoring"]
    assert out["pain_points"] == ["manual quoting", "no crm"]


def test_normalize_score_falls_back_to_lead_company_when_missing():
    out = lead_intel.normalize_score({}, {"company_name": "Fallback BV"})
    assert out["company_name"] == "Fallback BV"
    for k in (
        "lead_quality_score",
        "automation_fit_score",
        "urgency_score",
        "outbound_potential",
        "confidence_score",
    ):
        assert out[k] == 0


def test_normalize_sequence_safe_defaults_on_garbage():
    out = lead_intel.normalize_sequence("not a dict")
    assert out["cold_email"] == {"subject": "", "body": ""}
    assert out["follow_up_sequence"] == []
    assert out["cta_suggestions"] == []


# ---------------------------------------------------------------------------
# score_lead happy + cache + failure paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_lead_parses_json_and_returns_intelligence(monkeypatch):
    lead_intel.reset_cache()

    intel = {
        "company_name": "TestCo",
        "lead_quality_score": 8,
        "automation_fit_score": 9,
        "estimated_budget": "10-50k EUR",
        "urgency_score": 7,
        "outbound_potential": 8,
        "ai_opportunities": ["intake automation", "lead scoring"],
        "pain_points": ["manual quoting", "no CRM"],
        "recommended_offer": "AI intake bot",
        "best_outreach_angle": "Free intake audit",
        "recommended_channel": "email",
        "confidence_score": 7,
        "rationale": "Clear automation pain plus warm web signals.",
    }

    async def fake(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": json.dumps(intel),
            "reasoning_details": None,
            "usage": {"prompt_tokens": 200, "completion_tokens": 120, "total_tokens": 320},
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fake)

    out = await lead_intel.score_lead({"company_name": "TestCo", "domain": "testco.nl"})
    assert out["json_parsed"] is True
    assert out["error"] is None
    assert out["intelligence"]["lead_quality_score"] == 8
    assert out["intelligence"]["recommended_channel"] == "email"
    assert out["intelligence"]["ai_opportunities"] == ["intake automation", "lead scoring"]


@pytest.mark.asyncio
async def test_score_lead_cache_returns_same_object(monkeypatch):
    lead_intel.reset_cache()
    calls = {"n": 0}

    async def fake(model, messages, **kwargs):  # noqa: ARG001
        calls["n"] += 1
        return {
            "ok": True,
            "content": '{"company_name":"X","lead_quality_score":4}',
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fake)
    lead = {"company_name": "X", "domain": "x.nl"}
    a = await lead_intel.score_lead(lead)
    b = await lead_intel.score_lead(lead)
    assert a["intelligence"]["lead_quality_score"] == 4
    assert b["intelligence"]["lead_quality_score"] == 4
    assert calls["n"] == 1  # second call served from cache


@pytest.mark.asyncio
async def test_score_lead_surfaces_error_when_chairman_fails(monkeypatch):
    lead_intel.reset_cache()

    async def fail(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": False,
            "error_kind": "insufficient_credits",
            "status": 402,
            "message": "OpenRouter account has insufficient credits.",
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fail)

    out = await lead_intel.score_lead({"company_name": "X"})
    assert out["json_parsed"] is False
    assert out["error"]["kind"] == "insufficient_credits"
    assert out["intelligence"]["company_name"] == "X"
    assert out["intelligence"]["lead_quality_score"] == 0


# ---------------------------------------------------------------------------
# generate_sequence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_sequence_round_trip(monkeypatch):
    lead_intel.reset_cache()
    seq = {
        "cold_email": {"subject": "Quick idea for Acme", "body": "Hi …"},
        "linkedin_opener": "Noticed your intake form is manual — open to a quick chat?",
        "follow_up_sequence": [
            {"day": 3, "channel": "email", "subject": "Bump", "body": "Just in case…"},
            {"day": 7, "channel": "linkedin", "body": "Following up…"},
        ],
        "cta_suggestions": ["15-min call", "send 1-page audit", "demo intake bot"],
    }

    async def fake(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": json.dumps(seq),
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fake)

    out = await lead_intel.generate_sequence(
        {"company_name": "Acme", "domain": "acme.nl"},
        {
            "recommended_offer": "Intake bot",
            "best_outreach_angle": "Free audit",
            "ai_opportunities": ["intake"],
            "pain_points": ["manual"],
            "recommended_channel": "email",
        },
    )
    assert out["json_parsed"] is True
    assert out["sequence"]["cold_email"]["subject"] == "Quick idea for Acme"
    assert len(out["sequence"]["follow_up_sequence"]) == 2
    assert out["sequence"]["follow_up_sequence"][0]["day"] == 3


# ---------------------------------------------------------------------------
# HTTP endpoint round-trips
# ---------------------------------------------------------------------------


def test_score_lead_endpoint(client, monkeypatch, mock_openrouter):  # noqa: ARG001
    lead_intel.reset_cache()
    intel_blob = json.dumps(
        {
            "company_name": "Acme",
            "lead_quality_score": 7,
            "automation_fit_score": 8,
            "estimated_budget": "10-50k EUR",
            "urgency_score": 6,
            "outbound_potential": 7,
            "ai_opportunities": ["intake automation"],
            "pain_points": ["manual quoting"],
            "recommended_offer": "AI intake bot",
            "best_outreach_angle": "Audit",
            "recommended_channel": "email",
            "confidence_score": 6,
            "rationale": "Strong signals.",
        }
    )

    async def fake_query_model(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": intel_blob,
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fake_query_model)

    r = client.post(
        "/api/council/score-lead",
        json={
            "lead": {
                "company_name": "Acme",
                "domain": "acme.nl",
                "lead_id": "lr_00001",
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intelligence"]["lead_quality_score"] == 7
    assert body["intelligence"]["recommended_channel"] == "email"
    assert body["json_parsed"] is True
    assert body["lead_id"] == "lr_00001"


def test_generate_sequence_endpoint(client, monkeypatch, mock_openrouter):  # noqa: ARG001
    lead_intel.reset_cache()
    seq_blob = json.dumps(
        {
            "cold_email": {"subject": "Acme — quick idea", "body": "Hi ..."},
            "linkedin_opener": "Quick question about your intake?",
            "follow_up_sequence": [
                {"day": 3, "channel": "email", "subject": "Bump", "body": "Following up..."},
            ],
            "cta_suggestions": ["15-min call"],
        }
    )

    async def fake_query_model(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": True,
            "content": seq_blob,
            "reasoning_details": None,
            "usage": None,
        }

    monkeypatch.setattr("backend.services.lead_intel.query_model", fake_query_model)

    r = client.post(
        "/api/council/generate-sequence",
        json={
            "lead": {"company_name": "Acme", "domain": "acme.nl"},
            "analysis": {
                "company_name": "Acme",
                "lead_quality_score": 7,
                "automation_fit_score": 8,
                "estimated_budget": "10-50k EUR",
                "urgency_score": 6,
                "outbound_potential": 7,
                "ai_opportunities": ["intake automation"],
                "pain_points": ["manual quoting"],
                "recommended_offer": "AI intake bot",
                "best_outreach_angle": "Audit",
                "recommended_channel": "email",
                "confidence_score": 6,
                "rationale": "Strong signals.",
            },
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sequence"]["cold_email"]["subject"] == "Acme — quick idea"
    assert body["json_parsed"] is True
