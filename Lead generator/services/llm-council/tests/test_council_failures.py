"""Tests for graceful-degradation paths in the 3-stage council.

These cover:
- openrouter HTTP errors are classified (insufficient_credits, etc).
- stage3 falls back to top-ranked stage1 response when the chairman fails.
- run_full_council returns a structured error when all stage1 models fail.
"""

from __future__ import annotations

import httpx
import pytest

from backend.services import council as council_svc
from backend.services import openrouter as openrouter_svc


def test_classify_402_returns_insufficient_credits():
    kind, msg = openrouter_svc._classify_http_error(
        402,
        '{"error":{"message":"Insufficient credits. Top up at https://openrouter.ai/settings/credits","code":402}}',
    )
    assert kind == "insufficient_credits"
    assert "Insufficient credits" in msg


def test_classify_404_returns_invalid_model():
    kind, _ = openrouter_svc._classify_http_error(
        404, '{"error":{"message":"Model not found"}}'
    )
    assert kind == "invalid_model"


def test_classify_5xx_returns_upstream():
    kind, _ = openrouter_svc._classify_http_error(503, "")
    assert kind == "upstream_5xx"


@pytest.mark.asyncio
async def test_query_model_returns_classified_failure_on_402(monkeypatch):
    async def fake_post(self, url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            402,
            text='{"error":{"message":"Insufficient credits","code":402}}',
            request=request,
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    result = await openrouter_svc.query_model(
        "any/model", [{"role": "user", "content": "hi"}]
    )
    assert result["ok"] is False
    assert result["error_kind"] == "insufficient_credits"
    assert result["status"] == 402
    assert "Insufficient credits" in result["message"]


@pytest.mark.asyncio
async def test_stage3_falls_back_to_top_ranked_when_chairman_fails(monkeypatch):
    """If the chairman call fails, stage3 should return the best Stage 1
    response (per aggregate ranking) with a clear notice, plus an `error`
    field describing what happened."""
    stage1 = [
        {"model": "model-a", "response": "A's full answer."},
        {"model": "model-b", "response": "B's full answer."},
    ]
    stage2 = [
        {
            "model": "model-a",
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
            "parsed_ranking": ["Response A", "Response B"],
        },
        {
            "model": "model-b",
            "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
            "parsed_ranking": ["Response A", "Response B"],
        },
    ]
    label_to_model = {"Response A": "model-a", "Response B": "model-b"}

    async def failing_chairman(model, messages, **kwargs):  # noqa: ARG001
        return {
            "ok": False,
            "error_kind": "insufficient_credits",
            "status": 402,
            "message": "OpenRouter account has insufficient credits.",
        }

    monkeypatch.setattr("backend.services.council.query_model", failing_chairman)

    result = await council_svc.stage3_synthesize_final(
        "q?", stage1, stage2, label_to_model
    )
    assert "A's full answer." in result["response"]
    assert "model-a" in result["response"]
    assert "insufficient_credits" in result["response"]
    assert result["error"]["kind"] == "insufficient_credits"
    assert result["error"]["fallback_model"] == "model-a"


@pytest.mark.asyncio
async def test_run_full_council_surfaces_error_when_all_stage1_fail(monkeypatch):
    """When every council model fails, the synthesized stage3 must
    explain WHY (kind + message) rather than say 'unable to generate'."""

    async def all_fail(models, messages, **kwargs):  # noqa: ARG001
        return {
            m: {
                "ok": False,
                "error_kind": "insufficient_credits",
                "status": 402,
                "message": "OpenRouter account has insufficient credits.",
            }
            for m in models
        }

    monkeypatch.setattr("backend.services.council.query_models_parallel", all_fail)

    stage1, stage2, stage3, metadata = await council_svc.run_full_council("hello")
    assert stage1 == []
    assert stage2 == []
    assert "insufficient_credits" in stage3["response"]
    assert "insufficient credits" in stage3["response"].lower()
    assert stage3["error"]["kind"] == "insufficient_credits"
    assert len(metadata["stage1_failures"]) >= 1
