"""End-to-end-ish tests for the moderation layer.

No network. `CouncilClient` is stubbed in-process so we exercise:

- evaluate_approval applies the doctrine gate correctly
- moderate_one persists only HOT + verified + high + no-flags + clean review
- moderate_one captures upstream errors without crashing
- moderate_posts fans out and aggregates per-temperature stats
- exporter._maybe_run_moderation is a no-op for company-shaped rows
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from moderation import (
    CouncilClientError,
    ModerationConfig,
    evaluate_approval,
    moderate_one,
    moderate_posts,
    save_approved,
)
from moderation import webhooks as webhook_mod


def _config(tmp_path: Path, **overrides: Any) -> ModerationConfig:
    defaults: Dict[str, Any] = dict(
        enabled=True,
        council_url="http://localhost:8001",
        api_token=None,
        request_timeout_seconds=5.0,
        max_retries=1,
        max_concurrent=2,
        strategy="fast",
        locale="nl",
        approved_temperatures=("HOT",),
        min_confidence_band="high",
        require_provenance=("verified",),
        approved_path=tmp_path / "approved.jsonl",
        archive_dir=tmp_path / "archive",
        webhook_url=None,
        webhook_event="lead.approved",
        fail_open=False,
    )
    defaults.update(overrides)
    return ModerationConfig(**defaults)


def _hot_review(**overrides: Any) -> Dict[str, Any]:
    base = {
        "lead_temperature": "HOT",
        "confidence_band": "high",
        "provenance_status": "verified",
        "signal_type": "INTENT_DIRECT",
        "intent_summary": "Homeowner wants quote.",
        "homeowner_motivation": "CV defect.",
        "estimated_purchase_window": "<30 days",
        "estimated_install_value_band": "5-15k EUR",
        "trust_flags": [],
        "review_required": False,
        "duplicate_risk": "low",
        "source_quality": "high",
        "rejection_reason": "",
        "reviewer_notes": "",
        "source_url": "https://example.test/p/1",
        "verbatim_snippet": "Ik zoek een installateur in Utrecht.",
        "captured_at": "2026-05-18T10:00:00Z",
    }
    base.update(overrides)
    return base


class StubClient:
    """In-memory stand-in for CouncilClient."""

    def __init__(
        self,
        config: ModerationConfig,
        *,
        verdicts: Dict[str, Dict[str, Any]] | None = None,
        default_verdict: Dict[str, Any] | None = None,
        fail_call: str | None = None,
        fail_health: str | None = None,
    ):
        self.config = config
        self.verdicts = verdicts or {}
        self.default_verdict = default_verdict or _hot_review()
        self.fail_call = fail_call
        self.fail_health = fail_health
        self.calls = 0

    def health(self):
        if self.fail_health:
            raise CouncilClientError("down", kind=self.fail_health)
        return {"status": "ok"}

    def moderate_lead(self, candidate, **kwargs):
        self.calls += 1
        if self.fail_call:
            raise CouncilClientError("boom", kind=self.fail_call)
        verdict = self.verdicts.get(candidate.get("candidate_id"), self.default_verdict)
        return {
            "candidate_id": candidate.get("candidate_id"),
            "review": verdict,
            "strategy": "fast",
            "model": "stub/chairman",
            "elapsed_ms": 12,
            "json_parsed": True,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "error": None,
        }

    def close(self):
        pass


# ---------------------------------------------------------------------------
# evaluate_approval
# ---------------------------------------------------------------------------


def test_approval_gate_passes_clean_hot(tmp_path):
    assert evaluate_approval(_hot_review(), _config(tmp_path))["approved"] is True


def test_approval_gate_rejects_warm(tmp_path):
    out = evaluate_approval(_hot_review(lead_temperature="WARM"), _config(tmp_path))
    assert out["approved"] is False
    assert "WARM" in out["reason"]


def test_approval_gate_rejects_low_confidence(tmp_path):
    out = evaluate_approval(_hot_review(confidence_band="medium"), _config(tmp_path))
    assert out["approved"] is False
    assert "confidence_band" in out["reason"]


def test_approval_gate_rejects_when_flags_present(tmp_path):
    out = evaluate_approval(
        _hot_review(trust_flags=["marketplace_source"]), _config(tmp_path)
    )
    assert out["approved"] is False
    assert "trust_flags" in out["reason"]


def test_approval_gate_rejects_when_review_required(tmp_path):
    out = evaluate_approval(_hot_review(review_required=True), _config(tmp_path))
    assert out["approved"] is False
    assert "review_required" in out["reason"]


# ---------------------------------------------------------------------------
# save_approved
# ---------------------------------------------------------------------------


def test_save_approved_writes_v2_schema(tmp_path, monkeypatch):
    """save_approved persists v2-schema record with archive embedded.

    Stub archive_source so the test stays offline.
    """
    from moderation import crm_store
    from moderation.archive import ArchiveRecord

    def fake_archive(candidate_id, source_url, output_dir):
        return ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at="2026-05-18T08:00:00+00:00",
            status="ok",
            http_status=200,
            sha256="deadbeef",
            bytes=42,
            path=str(output_dir / candidate_id / "source.html"),
            error=None,
        )

    monkeypatch.setattr(crm_store, "archive_source", fake_archive)
    config = _config(tmp_path)
    save_approved(
        {
            "candidate_id": "cap_1",
            "source_url": "https://example.test/p/1",
            "snippet": "x",
            "captured_at": "2026-05-18T10:00:00Z",
        },
        _hot_review(),
        metadata={"model": "openai/gpt-4.1"},
        config=config,
    )
    lines = config.approved_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["candidate_id"] == "cap_1"
    assert rec["review"]["lead_temperature"] == "HOT"
    assert rec["approval"]["approved"] is True
    assert rec["metadata"]["schema_version"] == 2
    assert rec["metadata"]["model"] == "openai/gpt-4.1"
    assert rec["saved_at"].endswith("Z")


def test_save_approved_invokes_archive(tmp_path, monkeypatch):
    """save_approved must call archive_source and embed the record.

    Doctrine §01.3: every approved lead has an archive entry. Even when
    fetch fails (status='failed'), the gap is recorded — never absent.
    """
    from moderation import crm_store
    from moderation.archive import ArchiveRecord
    captured = {}

    def fake_archive(candidate_id, source_url, output_dir):
        captured["candidate_id"] = candidate_id
        captured["source_url"] = source_url
        captured["output_dir"] = output_dir
        return ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at="2026-05-18T08:00:00+00:00",
            status="ok",
            http_status=200,
            sha256="deadbeef",
            bytes=42,
            path=str(output_dir / candidate_id / "source.html"),
            error=None,
        )

    monkeypatch.setattr(crm_store, "archive_source", fake_archive)
    config = _config(tmp_path)
    save_approved(
        {
            "candidate_id": "cap_arch",
            "source_url": "https://example.test/p/arch",
            "snippet": "x",
            "captured_at": "2026-05-18T10:00:00Z",
        },
        _hot_review(),
        config=config,
    )
    assert captured["candidate_id"] == "cap_arch"
    assert captured["source_url"] == "https://example.test/p/arch"
    assert captured["output_dir"] == config.archive_dir

    lines = config.approved_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert "archive" in rec
    assert rec["archive"]["status"] == "ok"
    assert rec["archive"]["sha256"] == "deadbeef"
    assert rec["archive"]["candidate_id"] == "cap_arch"


# ---------------------------------------------------------------------------
# moderate_one
# ---------------------------------------------------------------------------


def test_moderate_one_persists_clean_hot(tmp_path, monkeypatch):
    from moderation import crm_store
    from moderation.archive import ArchiveRecord

    def fake_archive(candidate_id, source_url, output_dir):
        return ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at="2026-05-18T08:00:00+00:00",
            status="ok",
            http_status=200,
            sha256="deadbeef",
            bytes=42,
            path=str(output_dir / candidate_id / "source.html"),
            error=None,
        )

    monkeypatch.setattr(crm_store, "archive_source", fake_archive)
    config = _config(tmp_path)
    client = StubClient(config)
    result = moderate_one(
        {
            "candidate_id": "cap_a",
            "source_url": "https://example.test/p/1",
            "snippet": "verbatim",
            "captured_at": "2026-05-18T10:00:00Z",
        },
        client=client,
        config=config,
    )
    assert result.approved is True
    assert result.persisted is True
    assert result.review["lead_temperature"] == "HOT"
    assert config.approved_path.exists()


def test_moderate_one_does_not_persist_below_gate(tmp_path):
    config = _config(tmp_path)
    warm = _hot_review(lead_temperature="WARM", review_required=True)
    client = StubClient(config, default_verdict=warm)
    result = moderate_one(
        {"candidate_id": "cap_b", "source_url": "u", "snippet": "s", "captured_at": "t"},
        client=client,
        config=config,
    )
    assert result.review is not None
    assert result.approved is False
    assert result.persisted is False
    assert not config.approved_path.exists()


def test_moderate_one_handles_client_error(tmp_path):
    config = _config(tmp_path)
    client = StubClient(config, fail_call="insufficient_credits")
    result = moderate_one(
        {"candidate_id": "cap_c", "source_url": "u", "snippet": "s", "captured_at": "t"},
        client=client,
        config=config,
    )
    assert result.review is None
    assert result.error_kind == "insufficient_credits"
    assert result.approved is False


# ---------------------------------------------------------------------------
# moderate_posts (batch)
# ---------------------------------------------------------------------------


def test_moderate_posts_aggregates_temperature_counts(tmp_path, monkeypatch):
    from moderation import crm_store
    from moderation.archive import ArchiveRecord

    def fake_archive(candidate_id, source_url, output_dir):
        return ArchiveRecord(
            candidate_id=candidate_id,
            source_url=source_url,
            archived_at="2026-05-18T08:00:00+00:00",
            status="ok",
            http_status=200,
            sha256="deadbeef",
            bytes=42,
            path=str(output_dir / candidate_id / "source.html"),
            error=None,
        )

    monkeypatch.setattr(crm_store, "archive_source", fake_archive)
    config = _config(tmp_path)
    verdicts = {
        "cap_hot":  _hot_review(),
        "cap_warm": _hot_review(lead_temperature="WARM", review_required=True),
        "cap_opp":  _hot_review(
            lead_temperature="OPP",
            provenance_status="rejected",
            review_required=True,
            rejection_reason="marketplace",
        ),
    }
    client = StubClient(config, verdicts=verdicts)
    candidates = [
        {"candidate_id": cid, "source_url": f"u/{cid}", "snippet": "x", "captured_at": "t"}
        for cid in verdicts
    ]
    summary = moderate_posts(candidates, config=config, client=client)
    assert summary.total == 3
    assert summary.reviewed == 3
    assert summary.approved == 1     # only HOT clears the gate
    assert summary.persisted == 1
    assert summary.errors == 0
    assert summary.temperature_counts == {"HOT": 1, "WARM": 1, "OPP": 1}


def test_moderate_posts_short_circuits_on_unhealthy_council(tmp_path):
    config = _config(tmp_path, fail_open=True)
    client = StubClient(config, fail_health="transport")
    candidates = [
        {"candidate_id": "x", "source_url": "u", "snippet": "s", "captured_at": "t"},
        {"candidate_id": "y", "source_url": "u", "snippet": "s", "captured_at": "t"},
    ]
    summary = moderate_posts(candidates, config=config, client=client)
    assert summary.reviewed == 0
    assert summary.errors == 2
    assert summary.error_kinds == {"transport": 2}
    assert not config.approved_path.exists()


# ---------------------------------------------------------------------------
# webhook
# ---------------------------------------------------------------------------


def test_webhook_fires_only_when_url_configured(tmp_path, monkeypatch):
    config = _config(tmp_path, webhook_url="http://localhost:9/dummy")

    class FakeResp:
        status_code = 200
        text = "ok"

    captured: Dict[str, Any] = {}

    def fake_post(url, json=None, timeout=None, headers=None):  # noqa: A002
        captured["url"] = url
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(webhook_mod.httpx, "post", fake_post)
    ok = webhook_mod.emit_webhook(
        {"candidate_id": "cap_w", "source_url": "u", "snippet": "s", "captured_at": "t"},
        _hot_review(),
        approval={"approved": True, "reason": "approved"},
        config=config,
    )
    assert ok is True
    assert captured["json"]["event"] == "lead.approved"
    assert captured["json"]["review"]["lead_temperature"] == "HOT"


# ---------------------------------------------------------------------------
# Exporter hook
# ---------------------------------------------------------------------------


def test_export_leads_does_not_moderate_company_rows(tmp_path, monkeypatch):
    """The legacy company exporter must NOT feed B2B rows into moderation."""
    monkeypatch.setenv("LEAD_RADAR_MODERATION_ENABLED", "1")
    from output import exporter as exporter_mod

    called: Dict[str, Any] = {"candidates": None}

    def fake_moderate(candidates, config=None, client=None):
        called["candidates"] = list(candidates)
        class S:
            reviewed = 0
            approved = 0
            persisted = 0
            webhooks_fired = 0
            errors = 0
            temperature_counts: Dict[str, int] = {}
            error_kinds: Dict[str, int] = {}
        return S()

    monkeypatch.setattr("moderation.moderate_posts", fake_moderate)
    exporter_mod.export_leads(
        [
            {"company_name": "Acme", "domain": "acme.nl"},
            {"company_name": "Beta", "domain": "beta.nl"},
        ],
        niche="test",
        location="local",
        fmt="json",
        directory=tmp_path,
    )
    assert called["candidates"] is None


def test_export_leads_forwards_post_shaped_rows(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_RADAR_MODERATION_ENABLED", "1")
    monkeypatch.setenv(
        "LEAD_RADAR_MODERATION_APPROVED_PATH", str(tmp_path / "approved.jsonl")
    )
    from output import exporter as exporter_mod

    called: Dict[str, Any] = {"candidates": None}

    def fake_moderate(candidates, config=None, client=None):
        called["candidates"] = list(candidates)
        class S:
            reviewed = 1
            approved = 1
            persisted = 1
            webhooks_fired = 0
            errors = 0
            temperature_counts = {"HOT": 1}
            error_kinds: Dict[str, int] = {}
        return S()

    monkeypatch.setattr("moderation.moderate_posts", fake_moderate)
    exporter_mod.export_leads(
        [
            {
                "lead_id": "lr_1",
                "company_name": "Acme",
                "domain": "acme.nl",
                "source_url": "https://forum.test/t/42",
                "snippet": "Ik zoek een installateur in Utrecht.",
                "captured_at": "2026-05-18T10:00:00Z",
            },
        ],
        niche="test",
        location="local",
        fmt="json",
        directory=tmp_path,
    )
    assert called["candidates"] is not None
    assert called["candidates"][0]["source_url"].endswith("/t/42")


def test_default_config_is_fail_closed(monkeypatch):
    """Doctrine §00.4: default behavior must be fail-closed.

    Without explicit LEAD_RADAR_MODERATION_FAIL_OPEN=1, a council outage
    must not silently approve. The default ModerationConfig must report
    fail_open=False.
    """
    monkeypatch.delenv("LEAD_RADAR_MODERATION_FAIL_OPEN", raising=False)
    from moderation.config import get_config
    cfg = get_config()
    assert cfg.fail_open is False


def test_explicit_fail_open_opt_in(monkeypatch):
    """Operators can still opt in explicitly for known-noisy council periods."""
    monkeypatch.setenv("LEAD_RADAR_MODERATION_FAIL_OPEN", "1")
    from moderation.config import get_config
    cfg = get_config()
    assert cfg.fail_open is True
