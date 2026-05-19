# FB Primary — Plan B: Moderation & Approval-flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship de Python-zijde van het FB-primary tijdperk: LLM pre-screen (twee-categorisch, false-positive tolerant), `approve_lead()` wrapper die pcs-transitie + inventory-row append combineert, pre-screen-kwaliteits-monitor. Console-UI integratie blijft voor Plan B2.

**Architecture:** Geen monkey-patches op `pcs.py`. Nieuwe module `consumer/approval.py` bevat `approve_lead()` als hogere-laag wrapper die zowel pcs.append_transition (NEW -> APPROVED) als inventory.append_inventory_row aanroept. LLM pre-screen draait als nieuwe stap in moderation pipeline, schrijft `prescreen_class` (auto_present / needs_human) naar lead-records voor Sem's review. Metrics-CSV vangt Sem's override-rate.

**Tech Stack:** Python 3, pytest, Anthropic Claude SDK (haiku voor goedkope classificatie), CSV, geen DB.

**Bron-spec:** `lead-radar/docs/superpowers/specs/2026-05-19-facebook-primary-source-design.md` (§4-5)

**Depends on:** Plan A merged (deze plan gebruikt `consumer.inventory.append_inventory_row` + `compute_expires_at`)

---

## File Structure

| Bestand | Actie | Verantwoordelijkheid |
|---------|-------|---------------------|
| `lead-radar/consumer/approval.py` | Create | `approve_lead()` wrapper: combineert pcs-transitie + inventory append |
| `lead-radar/consumer/processor/prescreen.py` | Create | LLM pre-screen module — twee-categorisch (auto_present / needs_human) |
| `lead-radar/consumer/processor/prescreen_metrics.py` | Create | Override-rate logging in `data/prescreen_metrics.csv` |
| `lead-radar/run_consumer.py` | Modify | Voeg pre-screen-stap toe na bestaande classifier/scorer/moderation |
| `lead-radar/run_prescreen_report.py` | Create | CLI wrapper voor weekly override-rate rapport |
| `lead-radar/tests/test_approval.py` | Create | Unit tests voor approve_lead |
| `lead-radar/tests/test_prescreen.py` | Create | Unit tests voor pre-screen classifier (mocked LLM) |
| `lead-radar/tests/test_prescreen_metrics.py` | Create | Unit tests voor metrics CSV append + report |
| `lead-radar/tests/test_consumer_prescreen_integration.py` | Create | Integration test — pipeline schrijft prescreen_class per lead |

---

## Pre-flight check

- [ ] **Verify Plan A is in place + maak Plan B branch**

```bash
cd "/Users/claudebot/Lead generator"
ls lead-radar/consumer/inventory.py lead-radar/utils/regions.py lead-radar/run_inventory_sweep.py
git checkout feat/fb-primary-a-foundation
git checkout -b feat/fb-primary-b-moderation
```

---

## Task 1: `consumer/approval.py` — approve_lead wrapper

**Files:**
- Create: `lead-radar/consumer/approval.py`
- Create: `lead-radar/tests/test_approval.py`

- [ ] **Step 1.1: Schrijf falende test**

Create `lead-radar/tests/test_approval.py` with 6 test methods covering: writes-inventory-row-and-pcs-transition, closed_group_requires_attestation, closed_group_with_attestation_ok, apify_public_no_attestation_required, unknown_niche_raises, returns_inventory_row_dict. All use `tmp_path` fixture and a `decay_windows` fixture.

(Full test code: see plan-as-written in spec; ~120 lines pytest)

- [ ] **Step 1.2: Run test om falen te verifiëren**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
pytest tests/test_approval.py -v
```

Expected: FAIL — "No module named 'consumer.approval'".

- [ ] **Step 1.3: Implementeer consumer/approval.py**

```python
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
```

- [ ] **Step 1.4: Run tests & commit**

```bash
pytest tests/test_approval.py -v  # expect 6 passed
cd "/Users/claudebot/Lead generator"
git add lead-radar/consumer/approval.py lead-radar/tests/test_approval.py
git commit -m "feat(approval): approve_lead wrapper combining pcs + inventory

Doctrine §00.2.b enforcement: closed-group leads require non-empty
reviewer_attestation. Transactionele eenheid voor Sem's approve.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

(Full test code in source spec — implementer schrijft per Task 1.1 stub above.)

---

## Task 2: LLM pre-screen module (`consumer/processor/prescreen.py`)

**Files:**
- Create: `lead-radar/consumer/processor/prescreen.py`
- Create: `lead-radar/tests/test_prescreen.py`

- [ ] **Step 2.1: Schrijf falende test** (mocked Anthropic, 6 cases)

Test cases:
1. `test_clear_rfq_intent_returns_auto_present` — mock returns auto_present JSON
2. `test_general_question_returns_needs_human` — mock returns needs_human JSON
3. `test_invalid_llm_response_defaults_to_needs_human` — malformed JSON fallback
4. `test_unknown_category_in_response_defaults_to_needs_human` — unknown category fallback
5. `test_empty_post_text_returns_needs_human` — empty input edge case
6. `test_api_error_returns_needs_human` — exception fallback

All use `@patch("consumer.processor.prescreen._get_anthropic_client")` to mock.

- [ ] **Step 2.2: Run om falen te verifiëren**

```bash
pytest tests/test_prescreen.py -v
```

- [ ] **Step 2.3: Implementeer prescreen.py**

```python
"""LLM pre-screen — twee-categorisch lead-classificatie (auto_present / needs_human).

Doctrine §00.0: false-positive tolerant. Liever ruisige auto_present dan
gefilterde bruikbare WARM. Bij onzekerheid → needs_human.

Doctrine A8: geen numerieke score. Categorisch only.

Gebruikt Claude Haiku. Fail-open: alle errors → needs_human.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal


PrescreenCategory = Literal["auto_present", "needs_human"]


@dataclass(frozen=True)
class PrescreenResult:
    category: PrescreenCategory
    reasoning: str


_PROMPT_TEMPLATE = """\
Je bent een classifier voor lead-radar. Je classificeert posts uit publieke
Nederlandse fora en groepen voor installateurs van duurzaamheidsoplossingen.

Niche: {niche}
Region hint: {region_hint}

Post text:
\"\"\"
{post_text}
\"\"\"

Classificeer in EXACT een van deze twee categorieen:

- auto_present: Post bevat commercieel bruikbare intent. HOT (expliciete RFQ
  + regio + niche-fit) OF WARM (orienterende intent). BIJ TWIJFEL: kies
  auto_present (false-positives zijn aanvaardbaar; false-negatives kosten
  bruikbaar volume).

- needs_human: Ambigu, alleen geschikt voor menselijke beoordeling. Of
  duidelijke off-topic (geen niche-relevantie, geen koop-intent).

Antwoord ALLEEN met geldige JSON in deze vorm:
{{"category": "auto_present" OR "needs_human", "reasoning": "korte zin"}}
"""


def _get_anthropic_client():
    from anthropic import Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
    return Anthropic(api_key=api_key)


def classify_lead_prescreen(
    *,
    post_text: str,
    niche: str,
    region_hint: str | None,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 200,
) -> PrescreenResult:
    if not post_text or not post_text.strip():
        return PrescreenResult(
            category="needs_human",
            reasoning="empty post text",
        )

    prompt = _PROMPT_TEMPLATE.format(
        niche=niche,
        region_hint=region_hint or "(geen)",
        post_text=post_text[:3000],
    )

    try:
        client = _get_anthropic_client()
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text.strip()
    except Exception as e:
        return PrescreenResult(
            category="needs_human",
            reasoning=f"prescreen error: {type(e).__name__}",
        )

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        return PrescreenResult(
            category="needs_human",
            reasoning="prescreen returned unparseable JSON",
        )

    category = parsed.get("category", "")
    reasoning = parsed.get("reasoning", "")[:200]

    if category not in ("auto_present", "needs_human"):
        return PrescreenResult(
            category="needs_human",
            reasoning=f"prescreen returned unknown category {category!r}",
        )

    return PrescreenResult(category=category, reasoning=reasoning)
```

- [ ] **Step 2.4: Run tests + commit**

---

## Task 3: Pre-screen metrics CSV + override-rate calc

**Files:**
- Create: `lead-radar/consumer/processor/prescreen_metrics.py`
- Create: `lead-radar/tests/test_prescreen_metrics.py`

5 tests covering: writes_row_to_csv, idempotent_creates_header_once, no_overrides, partial_overrides, no_rows_returns_zero.

Module exports:
- `PRESCREEN_METRICS_FIELDS = ["at", "lead_id", "prescreen_class", "sem_decision", "override_flag", "override_reason"]`
- `log_prescreen_decision(path, *, lead_id, prescreen_class, sem_decision, override_flag, override_reason="", at=None) -> Path`
- `compute_override_rate(path, *, prescreen_class) -> float`

Implementation per spec §5.4 — append-only CSV, override-rate = overrides / total per class.

---

## Task 4: Pre-screen integration in run_consumer.py

**Files:**
- Modify: `lead-radar/run_consumer.py`
- Create: `lead-radar/tests/test_consumer_prescreen_integration.py`

Add to `run_consumer.py`:

```python
import os
from consumer.processor.prescreen import classify_lead_prescreen


def _is_prescreen_enabled() -> bool:
    return os.environ.get("LEAD_RADAR_PRESCREEN_ENABLED", "1") != "0"


def _attach_prescreen_class(lead: dict) -> dict:
    if not _is_prescreen_enabled():
        return lead
    try:
        result = classify_lead_prescreen(
            post_text=lead.get("text", "") or lead.get("body", ""),
            niche=lead.get("niche", ""),
            region_hint=lead.get("region", None),
        )
        lead["prescreen_class"] = result.category
        lead["prescreen_reasoning"] = result.reasoning
    except Exception:
        lead["prescreen_class"] = "needs_human"
        lead["prescreen_reasoning"] = "prescreen integration error"
    return lead
```

Call `_attach_prescreen_class(lead)` at the moderation-exit point. Exact location requires reading `run_consumer.py` to find where leads pass through the moderation gate. If unclear: escalate as NEEDS_CONTEXT.

Tests verify: `_is_prescreen_enabled` env-var handling, default-on, integration point exists.

---

## Task 5: Weekly prescreen report CLI

**Files:**
- Create: `lead-radar/run_prescreen_report.py`

```python
"""CLI: weekly prescreen override-rate report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from consumer.processor.prescreen_metrics import compute_override_rate


THRESHOLD_HIGH = 0.20


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", default="data/prescreen_metrics.csv")
    args = parser.parse_args(argv)

    metrics_path = Path(args.metrics)
    if not metrics_path.exists():
        print(f"Metrics file not found: {metrics_path}")
        return 0

    rate_auto = compute_override_rate(metrics_path, prescreen_class="auto_present")
    rate_human = compute_override_rate(metrics_path, prescreen_class="needs_human")

    print(f"Prescreen override-rates:")
    print(f"  auto_present: {rate_auto:.1%}" + ("  WARN >20% — prompt-revisie nodig" if rate_auto > THRESHOLD_HIGH else ""))
    print(f"  needs_human:  {rate_human:.1%}" + ("  WARN >20% — prompt-revisie nodig" if rate_human > THRESHOLD_HIGH else ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Smoke test: `python3 run_prescreen_report.py --metrics /tmp/nonexistent.csv` → exit 0 with "Metrics file not found".

---

## Task 6: End-to-end smoke test + regression + PR

### Step 6.1: End-to-end approve_lead → inventory → sweep

Test script with two approve_lead calls (one public, one closed-with-attestation) followed by sweep. Verify lead_log has 2 APPROVED + 2 EXPIRED entries.

### Step 6.2: Run Plan B test-suite

```bash
pytest tests/test_approval.py tests/test_prescreen.py tests/test_prescreen_metrics.py tests/test_consumer_prescreen_integration.py -v
```

Expected: 20 passed.

### Step 6.3: Full regression suite — expect no regressions vs Plan A baseline (1134 passed).

### Step 6.4: Push branch + open PR

```bash
cd "/Users/claudebot/Lead generator"
git push -u origin feat/fb-primary-b-moderation
gh pr create --title "Plan B: FB-primary moderation (pre-screen LLM + approve_lead wrapper)" --body "..."
```

---

## Self-Review

**Spec coverage:**

| Spec-sectie | Plan-task |
|-------------|-----------|
| §4 Reviewer attestation enforcement | Task 1 ✓ |
| §4 Vocab-lint source-class-aware | Deferred to Plan B2 (console TS) |
| §5 LLM pre-screen | Task 2 ✓ |
| §5 Pre-screen integration | Task 4 ✓ |
| §5 Pre-screen metrics + weekly report | Tasks 3, 5 ✓ |
| §5 Console /inventory/review view | Deferred to Plan B2 (TS console) |
| §6 Inventory wiring | Task 1 (approve_lead) ✓ |

**Placeholder scan:** Task 4 Step heeft NEEDS_CONTEXT note voor implementer (exact integration point in run_consumer.py needs reading). Acceptabel als escalation marker.

**Type consistency:** `approve_lead` retourneert `dict[str, str]`. PrescreenCategory = Literal["auto_present", "needs_human"]. Consistent.

**Scope:** Python-only Plan B. Plan B2 (console UI in TypeScript) en Plan C (burner) volgen.

---

## Execution Handoff

Plan complete. Stacks bovenop `feat/fb-primary-a-foundation`. Bij PR #2 merge: deze branch rebase op nieuwe main.
