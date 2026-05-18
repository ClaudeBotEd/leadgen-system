"""Unit tests for the lead-radar -> llm-council HTTP client."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from intelligence import CouncilClient, CouncilClientError, IntelligenceConfig


def _config(**overrides: Any) -> IntelligenceConfig:
    defaults: Dict[str, Any] = dict(
        enabled=True,
        council_url="http://localhost:8001",
        api_token="test-token",
        request_timeout_seconds=2.0,
        max_retries=2,
        max_concurrent=2,
        score_strategy="fast",
        generate_sequence=False,
        locale="en",
        quality_threshold=6,
        crm_path=Path("/tmp/never-written"),
        webhook_url=None,
        webhook_min_score=7,
        fail_open=False,
    )
    defaults.update(overrides)
    return IntelligenceConfig(**defaults)


class FakeTransport(httpx.BaseTransport):
    """Programmable transport so we can simulate retries / errors."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        if not self.responses:
            return httpx.Response(500, text="exhausted")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        status, body = item
        if isinstance(body, dict):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=str(body))


def _patched_client(monkeypatch, transport: FakeTransport, config: IntelligenceConfig) -> CouncilClient:
    client = CouncilClient(config)
    client.close()
    client._client = httpx.Client(  # type: ignore[attr-defined]
        base_url=config.council_url,
        headers={"Authorization": f"Bearer {config.api_token}"},
        timeout=config.request_timeout_seconds,
        transport=transport,
    )
    monkeypatch.setattr(
        "intelligence.council_client._backoff_seconds", lambda attempt: 0.0
    )
    return client


def test_score_lead_happy_path(monkeypatch):
    config = _config()
    body = {
        "intelligence": {"lead_quality_score": 7},
        "json_parsed": True,
        "elapsed_ms": 10,
        "model": "openai/gpt-4.1",
        "strategy": "fast",
    }
    transport = FakeTransport([(200, body)])
    client = _patched_client(monkeypatch, transport, config)

    out = client.score_lead({"company_name": "Acme", "domain": "acme.nl"})
    assert out["intelligence"]["lead_quality_score"] == 7
    assert len(transport.calls) == 1
    sent = transport.calls[0]
    assert sent.url.path == "/api/council/score-lead"
    assert sent.headers["authorization"] == "Bearer test-token"


def test_retries_on_500_then_succeeds(monkeypatch):
    config = _config(max_retries=2)
    transport = FakeTransport(
        [
            (500, "boom"),
            (
                200,
                {
                    "intelligence": {"lead_quality_score": 5},
                    "json_parsed": True,
                    "elapsed_ms": 1,
                    "model": "m",
                    "strategy": "fast",
                },
            ),
        ]
    )
    client = _patched_client(monkeypatch, transport, config)
    out = client.score_lead({"company_name": "Acme"})
    assert out["intelligence"]["lead_quality_score"] == 5
    assert len(transport.calls) == 2


def test_classifies_402_as_insufficient_credits(monkeypatch):
    config = _config(max_retries=0)
    transport = FakeTransport([(402, {"detail": "Insufficient credits"})])
    client = _patched_client(monkeypatch, transport, config)
    with pytest.raises(CouncilClientError) as exc:
        client.score_lead({"company_name": "Acme"})
    assert exc.value.kind == "insufficient_credits"
    assert exc.value.status == 402


def test_classifies_timeout(monkeypatch):
    config = _config(max_retries=0)
    transport = FakeTransport([httpx.ConnectTimeout("slow")])
    client = _patched_client(monkeypatch, transport, config)
    with pytest.raises(CouncilClientError) as exc:
        client.score_lead({"company_name": "Acme"})
    assert exc.value.kind == "timeout"


def test_classifies_transport(monkeypatch):
    config = _config(max_retries=0)
    transport = FakeTransport([httpx.ConnectError("no route")])
    client = _patched_client(monkeypatch, transport, config)
    with pytest.raises(CouncilClientError) as exc:
        client.score_lead({"company_name": "Acme"})
    assert exc.value.kind == "transport"


def test_generate_sequence_posts_analysis(monkeypatch):
    config = _config()
    transport = FakeTransport(
        [
            (
                200,
                {
                    "sequence": {"cold_email": {"subject": "x", "body": "y"}},
                    "json_parsed": True,
                    "elapsed_ms": 5,
                    "model": "m",
                },
            )
        ]
    )
    client = _patched_client(monkeypatch, transport, config)
    out = client.generate_sequence(
        {"company_name": "Acme"},
        {"lead_quality_score": 8, "recommended_channel": "email"},
    )
    assert out["sequence"]["cold_email"]["subject"] == "x"
    sent = transport.calls[0]
    assert sent.url.path == "/api/council/generate-sequence"
