"""Pilot Core System v0: local CSV workflow helpers.

Geen database, geen queues, geen services. Alleen kleine CSV-primitives voor
founder operations.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


STATES = {"NEW", "APPROVED", "DELIVERED", "OUTCOME", "REJECTED", "EXPIRED"}

LEAD_LOG_FIELDS = ["at", "lead_id", "from_state", "to_state", "actor", "reason"]

LEADS_WORKFLOW_FIELDS = ["assigned_to", "sent_at", "state"]

INSTALLERS_FIELDS = [
    "installer_id",
    "company_name",
    "contact_name",
    "email",
    "phone",
    "city",
    "regions",
    "niches",
    "active",
    "notes",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_state(state: str | None) -> str:
    normalized = (state or "NEW").strip().upper()
    if normalized not in STATES:
        raise ValueError(f"Unknown PCS state: {state!r}")
    return normalized


def ensure_csv(path: str | Path, fieldnames: list[str]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=fieldnames).writeheader()
    return path


def require_header(path: str | Path, fieldnames: list[str]) -> None:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        header = next(csv.reader(f), [])
    if header != fieldnames:
        raise ValueError(f"{Path(path).name} header mismatch: expected {fieldnames}, got {header}")


def append_transition(
    lead_id: str,
    from_state: str | None,
    to_state: str,
    *,
    actor: str,
    reason: str,
    log_path: str | Path = "data/lead_log.csv",
    at: str | None = None,
) -> Path:
    """Append exactly one transition row to lead_log.csv."""
    to_state = normalize_state(to_state)
    from_state = normalize_state(from_state)
    log_path = ensure_csv(log_path, LEAD_LOG_FIELDS)
    require_header(log_path, LEAD_LOG_FIELDS)

    with Path(log_path).open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_LOG_FIELDS)
        writer.writerow({
            "at": at or now_utc(),
            "lead_id": lead_id,
            "from_state": from_state,
            "to_state": to_state,
            "actor": actor,
            "reason": reason,
        })
    return Path(log_path)


def ensure_leads_master_workflow(
    master_path: str | Path = "data/leads_master.csv",
    *,
    base_fields: Iterable[str] | None = None,
) -> Path:
    """Ensure leads_master.csv has assigned_to, sent_at, and state columns."""
    master_path = Path(master_path)
    fieldnames = list(base_fields or [])
    for field in LEADS_WORKFLOW_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    if not master_path.exists() or master_path.stat().st_size == 0:
        return ensure_csv(master_path, fieldnames)

    with master_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        existing_fields = list(reader.fieldnames or [])
        rows = list(reader)

    updated_fields = existing_fields[:]
    changed = False
    for field in LEADS_WORKFLOW_FIELDS:
        if field not in updated_fields:
            updated_fields.append(field)
            changed = True

    if not changed:
        return master_path

    for row in rows:
        row.setdefault("assigned_to", "")
        row.setdefault("sent_at", "")
        row["state"] = normalize_state(row.get("state"))

    with master_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=updated_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return master_path


def load_installers(path: str | Path = "data/installers.csv") -> list[dict[str, str]]:
    """Load installers.csv as plain dictionaries."""
    path = ensure_csv(path, INSTALLERS_FIELDS)
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [field for field in INSTALLERS_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"installers.csv missing fields: {', '.join(missing)}")
        return [{field: (row.get(field) or "") for field in INSTALLERS_FIELDS} for row in reader]


def transition_lead_state(
    lead_id: str,
    to_state: str,
    *,
    actor: str,
    reason: str,
    assigned_to: str | None = None,
    sent_at: str | None = None,
    master_path: str | Path = "data/leads_master.csv",
    log_path: str | Path = "data/lead_log.csv",
) -> dict[str, str]:
    """Update a lead row in leads_master.csv and append one log transition."""
    to_state = normalize_state(to_state)
    master_path = ensure_leads_master_workflow(master_path)

    with Path(master_path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    match: dict[str, str] | None = None
    for row in rows:
        if row.get("lead_id") == lead_id:
            match = row
            break
    if match is None:
        raise ValueError(f"lead_id not found in leads_master.csv: {lead_id}")

    from_state = normalize_state(match.get("state"))
    match["state"] = to_state
    if assigned_to is not None:
        match["assigned_to"] = assigned_to
    if sent_at is not None:
        match["sent_at"] = sent_at

    with Path(master_path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    append_transition(
        lead_id,
        from_state,
        to_state,
        actor=actor,
        reason=reason,
        log_path=log_path,
    )
    return match


def approve_lead(lead_id: str, *, actor: str, reason: str, **kwargs) -> dict[str, str]:
    return transition_lead_state(lead_id, "APPROVED", actor=actor, reason=reason, **kwargs)


def deliver_lead(
    lead_id: str,
    *,
    actor: str,
    reason: str,
    assigned_to: str,
    sent_at: str | None = None,
    **kwargs,
) -> dict[str, str]:
    return transition_lead_state(
        lead_id,
        "DELIVERED",
        actor=actor,
        reason=reason,
        assigned_to=assigned_to,
        sent_at=sent_at or now_utc(),
        **kwargs,
    )


def record_outcome(lead_id: str, *, actor: str, reason: str, **kwargs) -> dict[str, str]:
    return transition_lead_state(lead_id, "OUTCOME", actor=actor, reason=reason, **kwargs)


def reject_lead(lead_id: str, *, actor: str, reason: str, **kwargs) -> dict[str, str]:
    return transition_lead_state(lead_id, "REJECTED", actor=actor, reason=reason, **kwargs)


def expire_lead(lead_id: str, *, actor: str, reason: str, **kwargs) -> dict[str, str]:
    return transition_lead_state(lead_id, "EXPIRED", actor=actor, reason=reason, **kwargs)
