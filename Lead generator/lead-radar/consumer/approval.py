"""Approval wrapper — combineert pcs-transitie + inventory-row append.

Plan B foundation. Hogere-laag wrapper boven pcs.append_transition en
consumer.inventory.append_inventory_row. Een transactionele eenheid
voor Sem's approval-actie.

Doctrine §00.2.b: closed-group leads vereisen non-empty reviewer_attestation.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pcs
from consumer.inventory import (
    append_inventory_row,
    compute_expires_at,
    VALID_SOURCE_CLASSES,
    VALID_INTENT_STRENGTHS,
)


class ApprovalError(ValueError):
    """Lead voldoet niet aan de approval-eisen (bv missing attestation)."""


def approve_lead(
    *,
    lead_id: str,
    niche: str,
    region_nl: str,
    intent_strength: str,
    captured_at: datetime,
    source_class: str,
    reviewer_name: str,
    decay_windows: dict[str, dict[str, int]],
    inventory_path: str | Path,
    lead_log_path: str | Path,
    reviewer_attestation: str = "",
    approved_at: datetime | None = None,
) -> dict[str, str]:
    """Approve een lead: schrijft een APPROVED-transitie + een inventory-row."""
    if intent_strength not in VALID_INTENT_STRENGTHS:
        raise ValueError(
            f"intent_strength must be one of {sorted(VALID_INTENT_STRENGTHS)}, "
            f"got {intent_strength!r}"
        )
    if source_class not in VALID_SOURCE_CLASSES:
        raise ValueError(
            f"source_class must be one of {sorted(VALID_SOURCE_CLASSES)}, "
            f"got {source_class!r}"
        )

    if source_class == "burner_closed" and not reviewer_attestation.strip():
        raise ApprovalError(
            "Closed-group lead vereist non-empty reviewer_attestation per doctrine §00.2.b"
        )

    expires_at = compute_expires_at(captured_at, niche, intent_strength, decay_windows)
    approved_at = approved_at or datetime.now(captured_at.tzinfo)

    pcs.append_transition(
        lead_id,
        from_state="NEW",
        to_state="APPROVED",
        actor=reviewer_name,
        reason=f"approve_lead:{source_class}:{intent_strength}",
        log_path=lead_log_path,
    )

    captured_iso = captured_at.isoformat(timespec="seconds")
    approved_iso = approved_at.isoformat(timespec="seconds")
    expires_iso = expires_at.isoformat(timespec="seconds")

    append_inventory_row(
        inventory_path,
        lead_id=lead_id,
        niche=niche,
        region_nl=region_nl,
        intent_strength=intent_strength,
        captured_at=captured_iso,
        approved_at=approved_iso,
        expires_at=expires_iso,
        source_class=source_class,
        reviewer_attestation=reviewer_attestation,
    )

    return {
        "lead_id": lead_id,
        "niche": niche,
        "region_nl": region_nl,
        "intent_strength": intent_strength,
        "captured_at": captured_iso,
        "approved_at": approved_iso,
        "expires_at": expires_iso,
        "source_class": source_class,
        "reviewer_attestation": reviewer_attestation,
        "delivered_to": "",
        "demo_used_at": "",
        "still_warm_checked_at": "",
    }
