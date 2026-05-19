"""Vocab linter must cover the final wire content, both text and HTML.

Doctrine §02.3 + A9 + A14: banned vocabulary appearing anywhere in a
delivered receipt is a doctrine violation. The lint must therefore see
both body_text and body_html (and any opening_override that flows into
either) before the message goes out.
"""

import json
from pathlib import Path

from delivery.config import DeliveryConfig
from delivery.dispatcher import dispatch


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _base_lead() -> dict:
    return {
        "lead_id": "L-TEST-001",
        "snippet": "Ik zoek een installateur voor een warmtepomp.",
        "source_url": "https://reddit.com/r/Verbouwen/post/abc",
        "source_platform": "reddit",
        "captured_at": "2026-05-18T08:00:00+00:00",
        "region": "Utrecht",
        "niche": "warmtepomp",
        "confidence_band": "HOT",
        "band_reason": "Expliciete koopvraag met deadline binnen 2 maanden.",
        "reviewer_name": "Marieke de Vries",
        "reviewer_email": "marieke@lead-radar.nl",
        "reviewed_at": "2026-05-18T08:30:00+00:00",
    }


def _installer_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
        "I1,TestCo,Jan Janssen,jan@test.nl,0612345678,Utrecht,Utrecht,warmtepomp,1,\n",
        encoding="utf-8",
    )


def _cfg(tmp_path: Path, input_path: Path) -> DeliveryConfig:
    installers_path = tmp_path / "installers.csv"
    _installer_csv(installers_path)
    return DeliveryConfig(
        reply_domain="lead-radar.nl",
        dry_run=True,
        smtp_host=None,
        smtp_user=None,
        smtp_password=None,
        decay_days=8,
        input_path=input_path,
        installers_path=installers_path,
        log_path=tmp_path / "lead_log.csv",
        audit_path=tmp_path / "audit.jsonl",
    )


def test_opening_override_with_banned_term_blocks_delivery(tmp_path: Path):
    lead = _base_lead()
    lead["opening_override"] = "Goedemorgen — ai-prediction toont een sterke lead score hier."
    input_path = tmp_path / "approved.jsonl"
    _write_jsonl(input_path, [lead])
    summary = dispatch(_cfg(tmp_path, input_path))
    assert summary.vocab_violations == 1
    assert summary.delivered == 0


def test_html_only_banned_term_blocks_delivery(tmp_path: Path, monkeypatch):
    """A banned term present in body_html but not body_text must still block."""
    import delivery.dispatcher as disp
    original = disp.render_html

    def poisoned_render(routed, *, now):
        return original(routed, now=now) + "<p>ai-prediction</p>"

    monkeypatch.setattr(disp, "render_html", poisoned_render)

    lead = _base_lead()
    input_path = tmp_path / "approved.jsonl"
    _write_jsonl(input_path, [lead])
    summary = dispatch(_cfg(tmp_path, input_path))
    assert summary.vocab_violations == 1
    assert summary.delivered == 0


def test_clean_lead_still_delivers(tmp_path: Path):
    """Sanity: a lead without banned terms still flows through."""
    lead = _base_lead()
    input_path = tmp_path / "approved.jsonl"
    _write_jsonl(input_path, [lead])
    summary = dispatch(_cfg(tmp_path, input_path))
    assert summary.vocab_violations == 0
    assert summary.delivered == 1
