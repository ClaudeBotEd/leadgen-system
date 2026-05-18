"""End-to-end-ish tests for the AI intelligence layer.

These tests do NOT hit the network — `CouncilClient` is replaced with a
stub. They prove:

- enrich_one threads scoring + sequence + persist correctly
- the quality threshold gate filters low-score leads
- council errors surface but never crash the batch
- enrich_leads respects max_concurrent without dropping leads
- the CRM JSONL store writes the right schema
- exporter._maybe_run_intelligence is a no-op when disabled
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from intelligence import (
    CouncilClientError,
    IntelligenceConfig,
    enrich_leads,
    enrich_one,
    save_qualified,
)
from intelligence import webhooks as webhook_mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path, **overrides: Any) -> IntelligenceConfig:
    defaults: Dict[str, Any] = dict(
        enabled=True,
        council_url="http://localhost:8001",
        api_token=None,
        request_timeout_seconds=5.0,
        max_retries=1,
        max_concurrent=2,
        score_strategy="fast",
        generate_sequence=True,
        locale="en",
        quality_threshold=6,
        crm_path=tmp_path / "qualified.jsonl",
        webhook_url=None,
        webhook_min_score=7,
        fail_open=False,
    )
    defaults.update(overrides)
    return IntelligenceConfig(**defaults)


class StubClient:
    """In-memory stand-in for CouncilClient."""

    def __init__(
        self,
        config: IntelligenceConfig,
        *,
        score_map: Dict[str, int] | None = None,
        fail_score: str | None = None,
        fail_sequence: bool = False,
        fail_health: str | None = None,
    ):
        self.config = config
        self.score_map = score_map or {}
        self.fail_score = fail_score
        self.fail_sequence = fail_sequence
        self.fail_health = fail_health
        self.score_calls = 0
        self.sequence_calls = 0

    def health(self):
        if self.fail_health:
            raise CouncilClientError("down", kind=self.fail_health)
        return {"status": "ok"}

    def score_lead(self, lead, **kwargs):
        self.score_calls += 1
        if self.fail_score:
            raise CouncilClientError("boom", kind=self.fail_score)
        score = self.score_map.get(lead.get("lead_id"), 8)
        return {
            "lead_id": lead.get("lead_id"),
            "intelligence": {
                "company_name": lead.get("company_name") or "X",
                "lead_quality_score": score,
                "automation_fit_score": score,
                "estimated_budget": "10-50k EUR",
                "urgency_score": 5,
                "outbound_potential": 6,
                "ai_opportunities": ["a"],
                "pain_points": ["b"],
                "recommended_offer": "offer",
                "best_outreach_angle": "angle",
                "recommended_channel": "email",
                "confidence_score": 7,
                "rationale": "ok",
            },
            "strategy": "fast",
            "model": "stub/chairman",
            "elapsed_ms": 12,
            "json_parsed": True,
            "error": None,
        }

    def generate_sequence(self, lead, analysis, **kwargs):
        self.sequence_calls += 1
        if self.fail_sequence:
            raise CouncilClientError("seq boom", kind="upstream_5xx")
        return {
            "lead_id": lead.get("lead_id"),
            "sequence": {
                "cold_email": {"subject": "S", "body": "B"},
                "linkedin_opener": "hi",
                "follow_up_sequence": [],
                "cta_suggestions": ["call"],
            },
            "model": "stub/chairman",
            "elapsed_ms": 24,
            "json_parsed": True,
            "error": None,
        }

    def close(self):
        pass


# ---------------------------------------------------------------------------
# crm_store
# ---------------------------------------------------------------------------


def test_save_qualified_writes_jsonl_with_expected_schema(tmp_path):
    config = _make_config(tmp_path)
    save_qualified(
        {"lead_id": "lr_00001", "company_name": "Acme"},
        {"lead_quality_score": 8},
        {"cold_email": {"subject": "x", "body": "y"}},
        metadata={"model": "openai/gpt-4.1"},
        config=config,
    )
    lines = config.crm_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["lead_id"] == "lr_00001"
    assert rec["lead"]["company_name"] == "Acme"
    assert rec["intelligence"]["lead_quality_score"] == 8
    assert rec["sequence"]["cold_email"]["subject"] == "x"
    assert rec["metadata"]["threshold"] == 6
    assert rec["metadata"]["model"] == "openai/gpt-4.1"
    assert rec["metadata"]["schema_version"] == 1
    assert rec["saved_at"].endswith("Z")


# ---------------------------------------------------------------------------
# enrich_one
# ---------------------------------------------------------------------------


def test_enrich_one_persists_above_threshold(tmp_path):
    config = _make_config(tmp_path, quality_threshold=6)
    client = StubClient(config, score_map={"lr_00001": 8})

    result = enrich_one(
        {"lead_id": "lr_00001", "company_name": "Acme", "domain": "acme.nl"},
        client=client,
        config=config,
    )
    assert result.saved is True
    assert result.score == 8
    assert result.sequence is not None
    assert client.sequence_calls == 1
    assert config.crm_path.exists()


def test_enrich_one_skips_below_threshold(tmp_path):
    config = _make_config(tmp_path, quality_threshold=7)
    client = StubClient(config, score_map={"lr_00001": 4})

    result = enrich_one(
        {"lead_id": "lr_00001", "company_name": "Bad", "domain": "bad.nl"},
        client=client,
        config=config,
    )
    assert result.saved is False
    assert result.score == 4
    assert client.sequence_calls == 0
    assert not config.crm_path.exists()


def test_enrich_one_handles_score_error(tmp_path):
    config = _make_config(tmp_path)
    client = StubClient(config, fail_score="insufficient_credits")
    result = enrich_one({"lead_id": "x"}, client=client, config=config)
    assert result.saved is False
    assert result.error_kind == "insufficient_credits"
    assert result.intelligence is None


def test_enrich_one_continues_when_sequence_fails(tmp_path):
    config = _make_config(tmp_path)
    client = StubClient(config, score_map={"lr_00001": 9}, fail_sequence=True)
    result = enrich_one(
        {"lead_id": "lr_00001", "company_name": "Acme"},
        client=client,
        config=config,
    )
    assert result.sequence is None
    assert result.saved is True


# ---------------------------------------------------------------------------
# enrich_leads (batch)
# ---------------------------------------------------------------------------


def test_enrich_leads_fans_out_and_filters(tmp_path):
    config = _make_config(tmp_path, quality_threshold=6)
    client = StubClient(
        config,
        score_map={"lr_00001": 8, "lr_00002": 3, "lr_00003": 7},
    )
    leads = [
        {"lead_id": "lr_00001", "company_name": "A"},
        {"lead_id": "lr_00002", "company_name": "B"},
        {"lead_id": "lr_00003", "company_name": "C"},
    ]
    summary = enrich_leads(leads, config=config, client=client)

    assert summary.total == 3
    assert summary.scored == 3
    assert summary.qualified == 2  # 8 and 7 pass; 3 fails
    assert summary.persisted == 2
    assert summary.errors == 0

    lines = config.crm_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    ids = {json.loads(line)["lead_id"] for line in lines}
    assert ids == {"lr_00001", "lr_00003"}


def test_enrich_leads_short_circuits_on_unhealthy_council(tmp_path):
    config = _make_config(tmp_path, fail_open=True)
    client = StubClient(config, fail_health="transport")
    leads = [{"lead_id": "x"}, {"lead_id": "y"}]
    summary = enrich_leads(leads, config=config, client=client)
    assert summary.scored == 0
    assert summary.errors == 2
    assert summary.error_kinds == {"transport": 2}
    assert not config.crm_path.exists()


# ---------------------------------------------------------------------------
# webhook gating
# ---------------------------------------------------------------------------


def test_webhook_skipped_when_no_url_configured(tmp_path):
    config = _make_config(tmp_path)
    assert webhook_mod.emit_webhook(
        {"lead_id": "x"},
        {"lead_quality_score": 9},
        None,
        config=config,
    ) is False


def test_webhook_skipped_below_min_score(tmp_path, monkeypatch):
    config = _make_config(
        tmp_path,
        webhook_url="http://localhost:9/dummy",
        webhook_min_score=8,
    )
    called = {"n": 0}

    def fake_post(*args, **kwargs):
        called["n"] += 1
        raise AssertionError("should not be called")

    monkeypatch.setattr(webhook_mod.httpx, "post", fake_post)
    assert webhook_mod.emit_webhook(
        {"lead_id": "x"},
        {"lead_quality_score": 5},
        None,
        config=config,
    ) is False
    assert called["n"] == 0


def test_webhook_fires_when_above_threshold(tmp_path, monkeypatch):
    config = _make_config(
        tmp_path,
        webhook_url="http://localhost:9/dummy",
        webhook_min_score=7,
    )

    class FakeResp:
        status_code = 200
        text = "ok"

    captured: Dict[str, Any] = {}

    def fake_post(url, json=None, timeout=None, headers=None):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(webhook_mod.httpx, "post", fake_post)
    assert webhook_mod.emit_webhook(
        {"lead_id": "lr_99", "company_name": "Acme"},
        {"lead_quality_score": 8, "company_name": "Acme"},
        {"cold_email": {"subject": "s", "body": "b"}},
        config=config,
    ) is True
    assert captured["json"]["event"] == "lead.qualified"
    assert captured["json"]["lead"]["company_name"] == "Acme"
    assert captured["json"]["intelligence"]["lead_quality_score"] == 8


# ---------------------------------------------------------------------------
# Exporter integration (no-op when disabled)
# ---------------------------------------------------------------------------


def test_export_leads_does_not_run_intelligence_when_disabled(tmp_path, monkeypatch):
    monkeypatch.delenv("LEAD_RADAR_INTELLIGENCE_ENABLED", raising=False)
    from output import exporter as exporter_mod

    called = {"n": 0}

    def fake_enrich(*args, **kwargs):
        called["n"] += 1

    monkeypatch.setattr("intelligence.enrich_leads", fake_enrich)
    exporter_mod.export_leads(
        [{"company_name": "X", "domain": "x.nl"}],
        niche="test",
        location="local",
        fmt="json",
        directory=tmp_path,
    )
    assert called["n"] == 0


def test_export_leads_runs_intelligence_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_RADAR_INTELLIGENCE_ENABLED", "1")
    monkeypatch.setenv("LEAD_RADAR_INTELLIGENCE_CRM_PATH", str(tmp_path / "crm.jsonl"))
    from output import exporter as exporter_mod

    called: Dict[str, Any] = {"leads": None}

    class FakeSummary:
        scored = 1
        qualified = 1
        persisted = 1
        webhooks_fired = 0
        errors = 0
        error_kinds: Dict[str, int] = {}

    def fake_enrich(leads, config=None, client=None):
        called["leads"] = list(leads)
        return FakeSummary()

    monkeypatch.setattr("intelligence.enrich_leads", fake_enrich)
    exporter_mod.export_leads(
        [{"company_name": "Acme", "domain": "acme.nl"}],
        niche="test",
        location="local",
        fmt="json",
        directory=tmp_path,
    )
    assert called["leads"] is not None
    assert called["leads"][0]["company_name"] == "Acme"
