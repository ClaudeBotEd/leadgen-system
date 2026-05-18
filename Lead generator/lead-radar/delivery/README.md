# delivery/

Per-receipt delivery layer. Reads APPROVED reviewed-leads from
`data/reviewed/approved.jsonl`, routes each to exactly one installer
from `data/installers.csv`, renders the receipt (plain-text + HTML),
sends via SMTP, logs the `APPROVED -> DELIVERED` transition through
`pcs.append_transition`, and appends a full audit row to
`data/delivery_log.jsonl`.

Spec: `docs/superpowers/specs/2026-05-18-receipt-artifact-v0-design.md`.
Doctrine: `specs/doctrine/trust-provenance-moderation.md` v0.1.

Run:  `python -m delivery dispatch --dry-run`
