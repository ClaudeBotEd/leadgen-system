"""Unit tests for the lead-radar -> llm-council moderation HTTP client."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import httpx
import pytest

from moderation import CouncilClient, CouncilClientError, ModerationConfig


def _config(**overrides: Any) -> ModerationConfig:
    defaults: Dict[str, Any] = dict(
        enabled=True,
        council_url="http://localhost:8001",
        api_token="test-token",
        request_timeout_seconds=2.0,
        max_retries=2,
        max_concurrent=2,
        strategy="fast",
        locale="nl",
        approved_temperatures=("HOT",),
        min_confidence_band="high",
        require_provenance=("verified",),
        approved_path=Path("/tmp/never-written-moderation"),
        archive_dir=Path("/tmp/never-written-moderation-archive"),
        webhook_url=None,
        webhook_event="lead.approved",
        fail_open=False,
    )
    defaults.update(overrides)
    return ModerationConfig(**defaults)


class FakeTransport(httpx.BaseTransport):
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


def _patched_client(monkeypatch, transport: FakeTransport, config: ModerationConfig) -> CouncilClient:
    client = CouncilClient(config)
    client.close()
    client._client = httpx.Client(  # type: ignore[attr-defined]
        base_url=config.council_url,
        headers={"Authorization": f"Bearer {config.api_token}"},
        timeout=config.request_timeout_seconds,
        transport=transport,
    )
    monkeypatch.setattr("moderation.council_client._backoff_seconds", lambda attempt: 0.0)
    return client


def test_moderate_lead_happy_path(monkeypatch):
    config = _config()
    body = {
        "review": {"lead_temperature": "HOT"},
        "json_parsed": True,
        "elapsed_ms": 10,
        "model": "openai/gpt-4.1",
        "strategy": "fast",
    }
    transport = FakeTransport([(200, body)])
    client = _patched_client(monkeypatch, transport, config)

    out = client.moderate_lead(
        {
            "candidate_id": "cap_1",
            "source_url": "https://example.test/t/1",
            "snippet": "x",
            "captured_at": "2026-05-18T10:00:00Z",
        }
    )
    assert out["review"]["lead_temperature"] == "HOT"
    sent = transport.calls[0]
    assert sent.url.path == "/api/council/moderate-lead"
    assert sent.headers["authorization"] == "Bearer test-token"


def test_retries_on_503_then_succeeds(monkeypatch):
    config = _config(max_retries=2)
    transport = FakeTransport(
        [
            (503, "boom"),
            (
                200,
                {
                    "review": {"lead_temperature": "WARM"},
                    "json_parsed": True,
                    "elapsed_ms": 1,
                    "model": "m",
                    "strategy": "fast",
                },
            ),
        ]
    )
    client = _patched_client(monkeypatch, transport, config)
    out = client.moderate_lead({"source_url": "u", "snippet": "s", "captured_at": "t"})
    assert out["review"]["lead_temperature"] == "WARM"
    assert len(transport.calls) == 2


def test_classifies_402_as_insufficient_credits(monkeypatch):
    config = _config(max_retries=0)
    transport = FakeTransport([(402, {"detail": "Insufficient credits"})])
    client = _patched_client(monkeypatch, transport, config)
    with pytest.raises(CouncilClientError) as exc:
        client.moderate_lead({"source_url": "u", "snippet": "s", "captured_at": "t"})
    assert exc.value.kind == "insufficient_credits"


def test_classifies_timeout(monkeypatch):
    config = _config(max_retries=0)
    transport = FakeTransport([httpx.ConnectTimeout("slow")])
    client = _patched_client(monkeypatch, transport, config)
    with pytest.raises(CouncilClientError) as exc:
        client.moderate_lead({"source_url": "u", "snippet": "s", "captured_at": "t"})
    assert exc.value.kind == "timeout"
