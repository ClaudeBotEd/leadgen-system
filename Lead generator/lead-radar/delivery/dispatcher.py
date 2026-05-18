"""Dispatcher orchestrator."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pcs

from .case_id import generate_case_id, next_sequence_for_date
from .config import DeliveryConfig
from .model import ReviewedLead, RoutedLead
from .preheader import build_preheader, reviewer_first_name
from .render_html import render_html
from .render_text import render_text
from .route import load_installers, pick_installer
from .send import build_email_message, send_smtp
from .subject import build_subject
from .vocab_lint import check_no_banned_terms

log = logging.getLogger("delivery.dispatcher")


@dataclass
class DispatchSummary:
    total: int = 0
    delivered: int = 0
    unrouted: int = 0
    vocab_violations: int = 0
    errors: int = 0
    errors_by_kind: dict = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _append_audit(audit_path: Path, row: dict) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _bump_error(summary: DispatchSummary, kind: str) -> None:
    summary.errors_by_kind[kind] = summary.errors_by_kind.get(kind, 0) + 1


def dispatch(config: DeliveryConfig, *, limit: Optional[int] = None) -> DispatchSummary:
    summary = DispatchSummary()
    if not config.input_path.exists():
        log.warning("No input at %s", config.input_path)
        return summary

    installers = load_installers(config.installers_path)
    now = _now()
    base_sequence = next_sequence_for_date(now.date(), log_path=config.log_path)

    with config.input_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            if limit is not None and summary.total >= limit:
                break
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            summary.total += 1

            try:
                raw = json.loads(raw_line)
                reviewed_lead = ReviewedLead.from_dict(raw)
            except (ValueError, KeyError) as exc:
                summary.errors += 1
                _bump_error(summary, "input_invalid")
                _append_audit(
                    config.audit_path,
                    {
                        "at": now.isoformat(timespec="seconds"),
                        "status": "input_invalid",
                        "error": str(exc),
                        "raw": raw_line[:500],
                        "dry_run": config.dry_run,
                    },
                )
                continue

            installer = pick_installer(reviewed_lead, installers, log_path=config.log_path)
            if installer is None:
                summary.unrouted += 1
                _append_audit(
                    config.audit_path,
                    {
                        "at": now.isoformat(timespec="seconds"),
                        "status": "unrouted",
                        "lead_id": reviewed_lead.lead_id,
                        "region": reviewed_lead.region,
                        "niche": reviewed_lead.niche,
                        "dry_run": config.dry_run,
                    },
                )
                continue

            sequence = base_sequence + summary.delivered
            case_id = generate_case_id(now.date(), sequence)
            routed = RoutedLead(reviewed_lead=reviewed_lead, installer=installer, case_id=case_id)

            subject = reviewed_lead.subject_override or build_subject(
                region=reviewed_lead.region,
                niche=reviewed_lead.niche,
                band=reviewed_lead.confidence_band,
            )
            preheader = build_preheader(
                reviewer_first=reviewer_first_name(reviewed_lead.reviewer_name),
                platform=reviewed_lead.source_platform,
                region=reviewed_lead.region,
            )
            body_text = render_text(routed, now=now)
            body_html = render_html(routed, now=now)

            violations = check_no_banned_terms(
                subject + "\n" + body_text + "\n" + body_html
            )
            if violations:
                summary.vocab_violations += 1
                _append_audit(
                    config.audit_path,
                    {
                        "at": now.isoformat(timespec="seconds"),
                        "status": "vocab_violation",
                        "lead_id": reviewed_lead.lead_id,
                        "case_id": case_id,
                        "violations": [
                            {"kind": v.kind, "matched": v.matched, "start": v.start} for v in violations
                        ],
                        "dry_run": config.dry_run,
                    },
                )
                continue

            from_display = f"{reviewed_lead.reviewer_name} — Lead Radar"
            message = build_email_message(
                subject=subject,
                preheader=preheader,
                from_display=from_display,
                from_address=reviewed_lead.reviewer_email,
                to_display=installer.contact_name,
                to_address=installer.email,
                body_text=body_text,
                body_html=body_html,
                case_id=case_id,
            )

            try:
                message_id = send_smtp(message, config)
            except Exception as exc:
                summary.errors += 1
                _bump_error(summary, "smtp_failure")
                _append_audit(
                    config.audit_path,
                    {
                        "at": now.isoformat(timespec="seconds"),
                        "status": "smtp_error",
                        "lead_id": reviewed_lead.lead_id,
                        "case_id": case_id,
                        "error": str(exc),
                        "dry_run": config.dry_run,
                    },
                )
                continue

            if not config.dry_run:
                pcs.append_transition(
                    reviewed_lead.lead_id,
                    "APPROVED",
                    "DELIVERED",
                    actor=reviewed_lead.reviewer_email,
                    reason=f"sent to {installer.email}; case_id={case_id}",
                    log_path=config.log_path,
                )

            summary.delivered += 1
            _append_audit(
                config.audit_path,
                {
                    "at": now.isoformat(timespec="seconds"),
                    "status": "delivered",
                    "lead_id": reviewed_lead.lead_id,
                    "case_id": case_id,
                    "installer_id": installer.installer_id,
                    "installer_email": installer.email,
                    "subject": subject,
                    "message_id": message_id,
                    "dry_run": config.dry_run,
                },
            )

    return summary
