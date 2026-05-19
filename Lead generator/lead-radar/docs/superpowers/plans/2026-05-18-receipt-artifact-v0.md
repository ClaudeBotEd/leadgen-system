# Receipt Artifact v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python delivery package that turns one APPROVED reviewed-lead into one email receipt per the doctrine v0.1 + Receipt Artifact v0 spec (`docs/superpowers/specs/2026-05-18-receipt-artifact-v0-design.md`), with Q1=A (email-only), Q2=A (name + reply-email), Q3=A (case-id in footer), Q4=A (explicit exclusivity sentence).

**Architecture:** New `delivery/` package sibling to `moderation/`. Reads APPROVED reviewed-leads from `data/reviewed/approved.jsonl` (V0 input contract; downstream of operator console). Routes each to one installer (`data/installers.csv`) by region + niche, enforces exclusivity via `data/lead_log.csv`, renders plain-text + HTML alternatives per §7.5/§7.9, sends via stdlib `smtplib` (no vendor lock-in V0), appends `APPROVED → DELIVERED` transition through `pcs.append_transition`, and writes a fully-audited line to `data/delivery_log.jsonl`. CLI entrypoint `python -m delivery dispatch` with `--dry-run` and `--limit`.

**Tech Stack:** Python 3.10+, stdlib (`smtplib`, `email.message.EmailMessage`, `dataclasses`, `pathlib`, `csv`, `json`, `argparse`, `re`), `pcs.py` (existing), `pytest` (existing). No new third-party dependencies V0.

**Critical implementation disciplines (from spec):**
- One lead = one receipt = one installer (§4, doctrine 04.3, 04.5)
- Five canonical fields above the fold in §2.1 order, no exceptions (doctrine 02.1, 04.5)
- Snippet verbatim, never paraphrased (doctrine A3, A9)
- Reviewer named (first + last), reply-to-human (doctrine A24, A26)
- Band glyphs only (HOT ●, WARM ○, OPP ·), never numbers or percentages (doctrine 02.2, A8)
- One reason sentence next to band, ≤20 words, written by reviewer (§3.4, §12)
- Subject hand-written or reviewer-confirmed template, never auto-generated (doctrine A13)
- Plain-text fallback is canonical, identical element order as HTML (§9.1)
- Vocabulary linter is build-fail on B.1/B.2 violations (§3.5, §12)
- No `noreply@`, no analytics pixel, no tracking redirect (§7.1, §6.2)
- Exclusivity enforced before send: lead_id with prior `DELIVERED` transition aborts (doctrine 04.3)

---

## Phase Index

- **Phase 0** — Package scaffold (1 task)
- **Phase 1** — Primitives: case-id, time formatting, decay, vocab linter (4 tasks)
- **Phase 2** — Composers: subject, preheader, opening line (3 tasks)
- **Phase 3** — Models + renderers (3 tasks)
- **Phase 4** — Routing + config (2 tasks)
- **Phase 5** — Send + dispatcher (2 tasks)
- **Phase 6** — CLI + golden anti-pattern suite (2 tasks)

**Total: 17 tasks**

---

## File Structure

```
lead-radar/
├── delivery/                                # NEW package
│   ├── __init__.py
│   ├── config.py                            # Env-driven SMTP/runtime config
│   ├── model.py                             # ReviewedLead, Installer, Receipt, RoutedLead dataclasses
│   ├── case_id.py                           # LR-YYYY-MM-DD-NNNN generator
│   ├── time_fmt.py                          # relative_time, absolute_iso
│   ├── decay.py                             # is_decayed(captured_at, now, days)
│   ├── vocab_lint.py                        # B.1/B.2 + custom banned strings
│   ├── subject.py                           # build_subject(region, niche, band)
│   ├── preheader.py                         # build_preheader(reviewer_first, platform, region)
│   ├── opening.py                           # build_opening(installer_first, platform, band)
│   ├── render_text.py                       # render_text(routed) -> str
│   ├── render_html.py                       # render_html(routed) -> str
│   ├── route.py                             # pick_installer(reviewed_lead, installers, log_path) -> Installer | None
│   ├── send.py                              # send_smtp(message, config) -> message_id
│   ├── dispatcher.py                        # dispatch(config, limit=None) -> DispatchSummary
│   ├── cli.py                               # argparse entrypoint
│   ├── __main__.py                          # python -m delivery
│   └── fixtures/
│       └── reviewed_sample.jsonl            # 3 sample reviewed leads for tests + dry-runs
├── tests/delivery/                          # NEW test package
│   ├── __init__.py
│   ├── test_case_id.py
│   ├── test_time_fmt.py
│   ├── test_decay.py
│   ├── test_vocab_lint.py
│   ├── test_subject.py
│   ├── test_preheader.py
│   ├── test_opening.py
│   ├── test_model.py
│   ├── test_render_text.py
│   ├── test_render_html.py
│   ├── test_route.py
│   ├── test_config.py
│   ├── test_send.py
│   ├── test_dispatcher.py
│   ├── test_cli.py
│   └── test_anti_patterns_golden.py
└── data/
    ├── reviewed/                            # NEW dir, gitignored
    │   └── approved.jsonl                   # operator-console output / V0 contract
    └── delivery_log.jsonl                   # NEW append-only audit log per delivery (gitignored)
```

### Input data contract: `data/reviewed/approved.jsonl`

Each line is one JSON object with these required fields:

```
lead_id          string, unique, stable across pipeline
snippet          string, verbatim homeowner sentence, 1..2000 chars
source_url       string, https://... (or http:// for archive)
source_platform  string, one of: tweakers | reddit | facebook | bouwinfo | klusidee | ouders | other
captured_at      string, ISO 8601 UTC (e.g. "2026-05-18T10:21:00+00:00")
region           string, NL region or postcode-prefix (e.g. "Amsterdam", "1015AA")
niche            string, one of: warmtepomp | airco | zonnepanelen | laadpaal | verduurzaming
confidence_band  string, one of: HOT | WARM | OPP
band_reason      string, 1..200 chars, reviewer-written, ≤20 words recommended
reviewer_name    string, first + last (e.g. "Marieke de Vries")
reviewer_email   string, valid email address
reviewed_at      string, ISO 8601 UTC
archive_url      string, optional — set when source_url is decayed (HTTP 404 / takedown / paywall)
subject_override string, optional — reviewer-typed subject overriding the template
opening_override string, optional — reviewer-typed opening line replacing the default
```

---

## Phase 0 — Package scaffold

### Task 1: Create `delivery/` package skeleton

**Files:**
- Create: `delivery/__init__.py`
- Create: `delivery/__main__.py`
- Create: `delivery/README.md`
- Create: `tests/delivery/__init__.py`

- [ ] **Step 1: Create `delivery/__init__.py`**

```python
"""Lead Radar delivery layer (Receipt Artifact v0).

Turns one APPROVED reviewed-lead into one email receipt per doctrine v0.1
and spec docs/superpowers/specs/2026-05-18-receipt-artifact-v0-design.md.

Founder-decisions (frozen 2026-05-18):
    Q1 = A   email-only V0, no web permalink, no Telegram mirror
    Q2 = A   reviewer surface: name + reply-email only (no photo, no handle)
    Q3 = A   case-id visible in footer as LR-YYYY-MM-DD-NNNN
    Q4 = A   explicit operational exclusivity sentence in footer
"""

from .config import DeliveryConfig, load_config
from .dispatcher import DispatchSummary, dispatch
from .model import Installer, Receipt, ReviewedLead, RoutedLead

__all__ = [
    "DeliveryConfig",
    "DispatchSummary",
    "Installer",
    "Receipt",
    "ReviewedLead",
    "RoutedLead",
    "dispatch",
    "load_config",
]
```

- [ ] **Step 2: Create `delivery/__main__.py`**

```python
"""Allow `python -m delivery ...` to invoke the CLI."""
from .cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `delivery/README.md`**

```markdown
# delivery/

Per-receipt delivery layer. Reads APPROVED reviewed-leads from
`data/reviewed/approved.jsonl`, routes each to exactly one installer
from `data/installers.csv`, renders the receipt (plain-text + HTML),
sends via SMTP, logs the `APPROVED → DELIVERED` transition through
`pcs.append_transition`, and appends a full audit row to
`data/delivery_log.jsonl`.

Spec: `docs/superpowers/specs/2026-05-18-receipt-artifact-v0-design.md`.
Doctrine: `specs/doctrine/trust-provenance-moderation.md` v0.1.

Run:  `python -m delivery dispatch --dry-run`
```

- [ ] **Step 4: Create `tests/delivery/__init__.py`** (empty file)

```python
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
git add delivery/__init__.py delivery/__main__.py delivery/README.md tests/delivery/__init__.py
git commit -m "feat(delivery): scaffold delivery package (Receipt Artifact v0)"
```

Note: `python -c "import delivery"` will fail until Task 2+ are complete because `__init__.py` imports symbols not yet defined. That is expected; subsequent tasks add the dependencies.

---

## Phase 1 — Primitives

### Task 2: Case-id generator (`LR-YYYY-MM-DD-NNNN`)

**Files:**
- Create: `delivery/case_id.py`
- Create: `tests/delivery/test_case_id.py`

- [ ] **Step 1: Write failing tests** — `tests/delivery/test_case_id.py`

```python
from datetime import date
from pathlib import Path

import pytest

from delivery.case_id import generate_case_id, next_sequence_for_date


def test_format_pattern():
    cid = generate_case_id(date(2026, 5, 18), 42)
    assert cid == "LR-2026-05-18-0042"


def test_pads_sequence_to_four_digits():
    assert generate_case_id(date(2026, 5, 18), 1).endswith("-0001")
    assert generate_case_id(date(2026, 5, 18), 9999).endswith("-9999")


def test_sequence_overflow_raises():
    with pytest.raises(ValueError, match="exceeds 9999"):
        generate_case_id(date(2026, 5, 18), 10000)


def test_sequence_negative_raises():
    with pytest.raises(ValueError, match="must be >= 1"):
        generate_case_id(date(2026, 5, 18), 0)


def test_next_sequence_empty_log(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text("at,lead_id,from_state,to_state,actor,reason\n", encoding="utf-8")
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 1


def test_next_sequence_counts_same_day_deliveries(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-18T08:00:00+00:00,L1,APPROVED,DELIVERED,m@x,case=LR-2026-05-18-0001\n"
        "2026-05-18T09:15:00+00:00,L2,APPROVED,DELIVERED,m@x,case=LR-2026-05-18-0002\n"
        "2026-05-17T22:00:00+00:00,L0,APPROVED,DELIVERED,m@x,case=LR-2026-05-17-0007\n",
        encoding="utf-8",
    )
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 3


def test_next_sequence_ignores_non_delivered(tmp_path: Path):
    log = tmp_path / "lead_log.csv"
    log.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-18T08:00:00+00:00,L1,NEW,APPROVED,m@x,reviewed\n"
        "2026-05-18T08:30:00+00:00,L2,APPROVED,REJECTED,m@x,off-topic\n",
        encoding="utf-8",
    )
    assert next_sequence_for_date(date(2026, 5, 18), log_path=log) == 1


def test_next_sequence_missing_log_returns_one(tmp_path: Path):
    assert next_sequence_for_date(date(2026, 5, 18), log_path=tmp_path / "missing.csv") == 1
```

- [ ] **Step 2: Run and confirm failure**

Run: `cd "/Users/claudebot/Lead generator/lead-radar" && python -m pytest tests/delivery/test_case_id.py -v`
Expected: `ModuleNotFoundError: No module named 'delivery.case_id'` (or similar collection error).

- [ ] **Step 3: Implement `delivery/case_id.py`**

```python
"""Case-id generator. LR-YYYY-MM-DD-NNNN, sequence per delivery date.

Sequence comes from counting prior APPROVED -> DELIVERED transitions in
data/lead_log.csv whose `at` falls on the same UTC date. New leads get
sequence = count + 1. Max sequence per day is 9999.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Union

DEFAULT_LOG_PATH = Path("data/lead_log.csv")


def generate_case_id(delivery_date: date, sequence: int) -> str:
    if sequence < 1:
        raise ValueError(f"sequence must be >= 1, got {sequence}")
    if sequence > 9999:
        raise ValueError(f"sequence {sequence} exceeds 9999 (per-day max)")
    return f"LR-{delivery_date.isoformat()}-{sequence:04d}"


def next_sequence_for_date(
    delivery_date: date,
    log_path: Union[str, Path] = DEFAULT_LOG_PATH,
) -> int:
    path = Path(log_path)
    if not path.exists():
        return 1
    count = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("to_state") != "DELIVERED":
                continue
            at_raw = row.get("at", "")
            try:
                at = datetime.fromisoformat(at_raw)
            except ValueError:
                continue
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at.astimezone(timezone.utc).date() == delivery_date:
                count += 1
    return count + 1
```

- [ ] **Step 4: Run and confirm pass**

Run: `python -m pytest tests/delivery/test_case_id.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/case_id.py tests/delivery/test_case_id.py
git commit -m "feat(delivery): case-id generator (LR-YYYY-MM-DD-NNNN, per-day sequence)"
```

---

### Task 3: Relative + absolute time formatting

**Files:**
- Create: `delivery/time_fmt.py`
- Create: `tests/delivery/test_time_fmt.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import datetime, timezone, timedelta

from delivery.time_fmt import absolute_iso, relative_time

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def test_minutes_ago():
    assert relative_time(NOW - timedelta(minutes=12), now=NOW) == "12 minuten geleden"


def test_one_minute_ago_singular():
    assert relative_time(NOW - timedelta(minutes=1), now=NOW) == "1 minuut geleden"


def test_hours_ago():
    assert relative_time(NOW - timedelta(hours=4, minutes=30), now=NOW) == "4 uur geleden"


def test_one_hour_ago_singular():
    assert relative_time(NOW - timedelta(hours=1), now=NOW) == "1 uur geleden"


def test_days_ago():
    assert relative_time(NOW - timedelta(days=2), now=NOW) == "2 dagen geleden"


def test_one_day_ago_singular():
    assert relative_time(NOW - timedelta(days=1), now=NOW) == "1 dag geleden"


def test_one_week_label():
    assert relative_time(NOW - timedelta(days=7), now=NOW) == "vorige week"


def test_two_weeks_ago_falls_back_to_days():
    assert relative_time(NOW - timedelta(days=14), now=NOW) == "14 dagen geleden"


def test_under_one_minute_never_says_now():
    assert relative_time(NOW - timedelta(seconds=30), now=NOW) == "1 minuut geleden"


def test_absolute_iso_format():
    assert absolute_iso(datetime(2026, 5, 18, 14, 21, 0, tzinfo=UTC)) == "2026-05-18 14:21 UTC"
```

- [ ] **Step 2: Confirm failure** — `python -m pytest tests/delivery/test_time_fmt.py -v`

- [ ] **Step 3: Implement `delivery/time_fmt.py`**

```python
"""Relative + absolute time formatting per spec §3.3.

Rules:
- Never say "now" / "just now"; minimum granularity is 1 minute.
- 7 days -> "vorige week"; otherwise N days.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def relative_time(captured: datetime, *, now: datetime) -> str:
    captured = _ensure_utc(captured)
    now = _ensure_utc(now)
    delta = now - captured
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "1 minuut geleden"
    minutes = total_seconds // 60
    if minutes < 60:
        return "1 minuut geleden" if minutes == 1 else f"{minutes} minuten geleden"
    hours = minutes // 60
    if hours < 24:
        return "1 uur geleden" if hours == 1 else f"{hours} uur geleden"
    days = hours // 24
    if days == 1:
        return "1 dag geleden"
    if days == 7:
        return "vorige week"
    return f"{days} dagen geleden"


def absolute_iso(dt: datetime) -> str:
    dt = _ensure_utc(dt)
    return dt.strftime("%Y-%m-%d %H:%M UTC")
```

- [ ] **Step 4: Confirm pass** — Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/time_fmt.py tests/delivery/test_time_fmt.py
git commit -m "feat(delivery): relative + absolute time formatting per spec §3.3"
```

---

### Task 4: Decay detection (signal-age past window)

**Files:**
- Create: `delivery/decay.py`
- Create: `tests/delivery/test_decay.py`

- [ ] **Step 1: Failing tests**

```python
from datetime import datetime, timezone, timedelta

from delivery.decay import is_decayed, DEFAULT_DECAY_DAYS

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def test_default_window_is_eight_days():
    assert DEFAULT_DECAY_DAYS == 8


def test_fresh_lead_not_decayed():
    assert is_decayed(NOW - timedelta(hours=2), now=NOW) is False


def test_seven_days_not_decayed():
    assert is_decayed(NOW - timedelta(days=7, hours=23), now=NOW) is False


def test_eight_days_exactly_decayed():
    assert is_decayed(NOW - timedelta(days=8), now=NOW) is True


def test_well_past_window_decayed():
    assert is_decayed(NOW - timedelta(days=30), now=NOW) is True


def test_custom_window_override():
    captured = NOW - timedelta(days=3)
    assert is_decayed(captured, now=NOW, decay_days=2) is True
    assert is_decayed(captured, now=NOW, decay_days=4) is False
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/decay.py`**

```python
"""Decay window check per doctrine 01.6.

A captured signal is `decayed` when its age exceeds the configured
window (default 8 days). Decay does NOT prevent delivery — it tells
the renderer to add a DECAYED pill and (if archive_url is present)
swap the source link.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DEFAULT_DECAY_DAYS = 8


def is_decayed(captured: datetime, *, now: datetime, decay_days: int = DEFAULT_DECAY_DAYS) -> bool:
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - captured) >= timedelta(days=decay_days)
```

- [ ] **Step 4: Confirm pass** — Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/decay.py tests/delivery/test_decay.py
git commit -m "feat(delivery): decay-window check per doctrine 01.6"
```

---

### Task 5: Vocabulary linter

**Files:**
- Create: `delivery/vocab_lint.py`
- Create: `tests/delivery/test_vocab_lint.py`

The linter scans rendered receipt text (subject + body). Violations are returned as a list; the dispatcher refuses to send when the list is non-empty. Build-fail discipline (§12).

- [ ] **Step 1: Failing tests**

```python
import pytest

from delivery.vocab_lint import (
    BANNED_SUBSTRINGS,
    REQUIRED_SUBSTITUTIONS,
    Violation,
    check_no_banned_terms,
)


def test_clean_text_returns_empty():
    text = "Marieke reviewde een Tweakers-post uit regio Amsterdam."
    assert check_no_banned_terms(text) == []


def test_flags_ai_in_chrome():
    violations = check_no_banned_terms("Powered by AI scoring")
    assert any("AI" in v.matched for v in violations)


def test_flags_model_name():
    violations = check_no_banned_terms("Powered by GPT-4")
    assert any("GPT" in v.matched for v in violations)


def test_flags_paraphrase_marker():
    violations = check_no_banned_terms("AI-prediction: high intent for heat pump")
    kinds = {v.kind for v in violations}
    assert "ai_chrome" in kinds or "paraphrase_signal" in kinds


def test_flags_percentage_score():
    violations = check_no_banned_terms("Lead score: 87%")
    assert any(v.kind == "score_numeric" for v in violations)


def test_flags_qualified_lead_vocab():
    violations = check_no_banned_terms("Hierbij een qualified lead voor u.")
    assert any(v.kind == "vocab_banned" and "qualified" in v.matched.lower() for v in violations)


def test_flags_noreply_alias():
    violations = check_no_banned_terms("Antwoord aan noreply@lead-radar.nl")
    assert any(v.kind == "sender_alias" for v in violations)


def test_flags_emoji_in_subject():
    violations = check_no_banned_terms("🔥 Last chance!")
    assert any(v.kind == "urgency_emoji" for v in violations)


def test_substitutions_map_defined():
    assert REQUIRED_SUBSTITUTIONS["klant"] == "installateur"


def test_word_boundary_for_ai_avoids_false_positive():
    assert check_no_banned_terms("De AIB-norm is gehaald.") == []


def test_banned_substrings_is_immutable():
    with pytest.raises((AttributeError, TypeError)):
        BANNED_SUBSTRINGS.add("foo")  # type: ignore[attr-defined]
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/vocab_lint.py`**

```python
"""Vocabulary linter for rendered receipt copy.

Sources:
- Doctrine §02.3 + Appendix B (B.1 terms we use, B.2 banned terms)
- Spec §3.5 (artifact vocab table)
- Spec §8 (anti-patterns)

A check_no_banned_terms() call on rendered receipt text returns a list of
Violation records. The dispatcher refuses to send any receipt with a
non-empty violation list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

BANNED_VOCAB = frozenset({
    "klant",
    "gebruiker",
    "match",
    "kandidaat",
    "opportunity",
    "lead score",
    "qualified lead",
    "ai-prediction",
    "scraped from web",
    "scraped data",
    "ons systeem",
    "onze ai",
    "data point",
    "support ticket",
    "klacht indienen",
})

REQUIRED_SUBSTITUTIONS = {
    "klant": "installateur",
    "gebruiker": "installateur",
    "match": "lead",
    "kandidaat": "signal",
    "opportunity": "lead",
    "lead score": "(geen score — gebruik band)",
    "qualified lead": "verifieerbare intent",
    "ai-prediction": "(geen AI-claim)",
    "scraped from web": "vastgelegd vanuit {platform}",
    "scraped data": "publieke post",
    "ons systeem": "de reviewer",
    "onze ai": "de reviewer",
    "data point": "signaal",
    "support ticket": "dispuut",
    "klacht indienen": "dispuut openen",
}

AI_CHROME_TERMS = frozenset({"ai", "ml", "gpt", "claude", "llm", "gemini", "model"})
PARAPHRASE_SIGNALS = frozenset({
    "ai-prediction", "ai prediction", "ai-summary", "ai summary",
    "deze homeowner is geïnteresseerd",
})
SENDER_ALIASES = frozenset({"noreply", "no-reply", "leads@", "team@", "support@", "info@"})
URGENCY_EMOJIS = frozenset({"🔥", "⏰", "⚠️", "🚨", "👍", "👎", "🌱"})

BANNED_SUBSTRINGS = BANNED_VOCAB  # re-exported, immutable


@dataclass(frozen=True)
class Violation:
    kind: str          # one of: vocab_banned, ai_chrome, paraphrase_signal,
                       #         score_numeric, sender_alias, urgency_emoji
    matched: str
    start: int
    suggestion: str


def _word_boundary_iter(text: str, term: str):
    pattern = r"\b" + re.escape(term) + r"\b"
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        yield m.start(), m.group(0)


def _substring_iter(text: str, term: str):
    lower = text.lower()
    needle = term.lower()
    start = 0
    while True:
        idx = lower.find(needle, start)
        if idx == -1:
            return
        yield idx, text[idx : idx + len(term)]
        start = idx + len(needle)


def check_no_banned_terms(text: str) -> List[Violation]:
    out: List[Violation] = []

    for term in BANNED_VOCAB:
        iterator = _word_boundary_iter(text, term) if " " not in term else _substring_iter(text, term)
        for start, matched in iterator:
            suggestion = REQUIRED_SUBSTITUTIONS.get(term, "remove")
            out.append(Violation(kind="vocab_banned", matched=matched, start=start, suggestion=suggestion))

    for term in AI_CHROME_TERMS:
        for start, matched in _word_boundary_iter(text, term):
            out.append(Violation(kind="ai_chrome", matched=matched, start=start, suggestion="remove"))

    for term in PARAPHRASE_SIGNALS:
        for start, matched in _substring_iter(text, term):
            out.append(Violation(kind="paraphrase_signal", matched=matched, start=start, suggestion="remove"))

    for m in re.finditer(r"\b\d{1,3}\s?%", text):
        out.append(Violation(kind="score_numeric", matched=m.group(0), start=m.start(), suggestion="use band glyph"))
    for m in re.finditer(r"(?i)\bscore\b", text):
        out.append(Violation(kind="score_numeric", matched=m.group(0), start=m.start(), suggestion="use band glyph"))

    for term in SENDER_ALIASES:
        for start, matched in _substring_iter(text, term):
            out.append(Violation(kind="sender_alias", matched=matched, start=start, suggestion="use reviewer-named address"))

    for emoji in URGENCY_EMOJIS:
        for start, matched in _substring_iter(text, emoji):
            out.append(Violation(kind="urgency_emoji", matched=matched, start=start, suggestion="remove"))

    return sorted(out, key=lambda v: v.start)
```

- [ ] **Step 4: Confirm pass** — Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/vocab_lint.py tests/delivery/test_vocab_lint.py
git commit -m "feat(delivery): vocabulary linter (B.1/B.2 + anti-pattern §8 enforcement)"
```

---

## Phase 2 — Composers

### Task 6: Subject line builder

**Files:**
- Create: `delivery/subject.py`
- Create: `tests/delivery/test_subject.py`

Template per spec §7.2: `{region} · {niche} · {BAND}`.

- [ ] **Step 1: Failing tests**

```python
import pytest

from delivery.subject import build_subject


def test_canonical_template():
    assert build_subject(region="Amsterdam", niche="warmtepomp", band="HOT") == "Amsterdam · warmtepomp · HOT"


def test_postcode_region():
    assert build_subject(region="1015AA", niche="warmtepomp", band="HOT") == "1015AA · warmtepomp · HOT"


def test_band_uppercase_enforced():
    assert build_subject(region="Utrecht", niche="airco", band="warm") == "Utrecht · airco · WARM"


def test_niche_lowercase_enforced():
    assert build_subject(region="Utrecht", niche="WARMTEPOMP", band="HOT") == "Utrecht · warmtepomp · HOT"


def test_unknown_band_raises():
    with pytest.raises(ValueError, match="band must be one of"):
        build_subject(region="Amsterdam", niche="warmtepomp", band="WARMTE")


def test_unknown_niche_raises():
    with pytest.raises(ValueError, match="niche must be one of"):
        build_subject(region="Amsterdam", niche="onbekend", band="HOT")


def test_no_brand_prefix():
    subject = build_subject(region="Amsterdam", niche="warmtepomp", band="HOT")
    assert "Lead Radar" not in subject and "[" not in subject


def test_no_emoji():
    subject = build_subject(region="Amsterdam", niche="warmtepomp", band="HOT")
    for emoji in ["🔥", "⏰", "⚠️", "🚨"]:
        assert emoji not in subject
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/subject.py`**

```python
"""Subject-line builder per spec §7.2."""

from __future__ import annotations

ALLOWED_BANDS = frozenset({"HOT", "WARM", "OPP"})
ALLOWED_NICHES = frozenset({"warmtepomp", "airco", "zonnepanelen", "laadpaal", "verduurzaming"})


def build_subject(*, region: str, niche: str, band: str) -> str:
    niche_norm = niche.strip().lower()
    band_norm = band.strip().upper()
    if niche_norm not in ALLOWED_NICHES:
        raise ValueError(f"niche must be one of {sorted(ALLOWED_NICHES)}, got {niche!r}")
    if band_norm not in ALLOWED_BANDS:
        raise ValueError(f"band must be one of {sorted(ALLOWED_BANDS)}, got {band!r}")
    region_norm = region.strip()
    if not region_norm:
        raise ValueError("region must be non-empty")
    return f"{region_norm} · {niche_norm} · {band_norm}"
```

- [ ] **Step 4: Confirm pass** — Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/subject.py tests/delivery/test_subject.py
git commit -m "feat(delivery): subject-line builder per spec §7.2"
```

---

### Task 7: Pre-header builder

**Files:**
- Create: `delivery/preheader.py`
- Create: `tests/delivery/test_preheader.py`

- [ ] **Step 1: Failing tests**

```python
import pytest

from delivery.preheader import build_preheader, reviewer_first_name


def test_canonical_template():
    line = build_preheader(reviewer_first="Marieke", platform="Tweakers", region="Amsterdam")
    assert line == "Marieke reviewde een Tweakers-post uit regio Amsterdam."


def test_platform_titlecase_enforced():
    line = build_preheader(reviewer_first="Marieke", platform="reddit", region="Utrecht")
    assert line == "Marieke reviewde een Reddit-post uit regio Utrecht."


def test_postcode_region_preserved():
    line = build_preheader(reviewer_first="Marieke", platform="Facebook", region="1015AA")
    assert line == "Marieke reviewde een Facebook-post uit regio 1015AA."


def test_no_marketing_phrases():
    line = build_preheader(reviewer_first="Marieke", platform="Tweakers", region="Amsterdam")
    assert "Open snel" not in line
    assert "nieuwe lead" not in line


def test_reviewer_first_name_helper():
    assert reviewer_first_name("Marieke de Vries") == "Marieke"
    assert reviewer_first_name("Jan-Willem ter Hoeven") == "Jan-Willem"
    assert reviewer_first_name("Anne") == "Anne"


def test_reviewer_first_name_empty_raises():
    with pytest.raises(ValueError):
        reviewer_first_name("")
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/preheader.py`**

```python
"""Pre-header builder per spec §7.3 + reviewer_first_name helper."""

from __future__ import annotations


def reviewer_first_name(full_name: str) -> str:
    cleaned = full_name.strip()
    if not cleaned:
        raise ValueError("reviewer name must be non-empty")
    return cleaned.split()[0]


def build_preheader(*, reviewer_first: str, platform: str, region: str) -> str:
    platform_norm = platform.strip().title()
    region_norm = region.strip()
    return f"{reviewer_first} reviewde een {platform_norm}-post uit regio {region_norm}."
```

- [ ] **Step 4: Confirm pass** — Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/preheader.py tests/delivery/test_preheader.py
git commit -m "feat(delivery): pre-header builder + reviewer first-name helper"
```

---

### Task 8: Opening line builder

**Files:**
- Create: `delivery/opening.py`
- Create: `tests/delivery/test_opening.py`

- [ ] **Step 1: Failing tests**

```python
import pytest

from delivery.opening import build_opening


def test_canonical_opening():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    expected = (
        "Hallo Jeroen,\n"
        "\n"
        "Onderstaande post kwam binnen vanuit Tweakers. Ik heb hem\n"
        "beoordeeld en band HOT toegekend. Reden staat onder de bron."
    )
    assert out == expected


def test_platform_titlecase():
    out = build_opening(installer_first="Jeroen", platform="reddit", band="WARM")
    assert "vanuit Reddit." in out
    assert "band WARM toegekend" in out


def test_no_smileys():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    for ch in [":)", ":(", "😊", "🙂"]:
        assert ch not in out


def test_first_person_singular():
    out = build_opening(installer_first="Jeroen", platform="Tweakers", band="HOT")
    assert "Ik heb hem" in out
    assert "Ons team" not in out


def test_invalid_band_raises():
    with pytest.raises(ValueError):
        build_opening(installer_first="Jeroen", platform="Tweakers", band="WARMTE")
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/opening.py`**

```python
"""Opening-line builder per spec §7.4. First person singular, no smileys, no exclamation."""

from __future__ import annotations

from .subject import ALLOWED_BANDS

_TEMPLATE = (
    "Hallo {installer_first},\n"
    "\n"
    "Onderstaande post kwam binnen vanuit {platform}. Ik heb hem\n"
    "beoordeeld en band {band} toegekend. Reden staat onder de bron."
)


def build_opening(*, installer_first: str, platform: str, band: str) -> str:
    band_norm = band.strip().upper()
    if band_norm not in ALLOWED_BANDS:
        raise ValueError(f"band must be one of {sorted(ALLOWED_BANDS)}")
    return _TEMPLATE.format(
        installer_first=installer_first.strip(),
        platform=platform.strip().title(),
        band=band_norm,
    )
```

- [ ] **Step 4: Confirm pass** — Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/opening.py tests/delivery/test_opening.py
git commit -m "feat(delivery): opening-line builder per spec §7.4 (first person, no smileys)"
```

---

## Phase 3 — Models and renderers

### Task 9: Dataclass models (ReviewedLead, Installer, RoutedLead, Receipt)

**Files:**
- Create: `delivery/model.py`
- Create: `tests/delivery/test_model.py`

- [ ] **Step 1: Failing tests**

```python
from datetime import datetime, timezone

import pytest

from delivery.model import Installer, Receipt, ReviewedLead, RoutedLead

UTC = timezone.utc


def make_rl(**overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur voor een warmtepomp.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=datetime(2026, 5, 18, 10, 0, 0, tzinfo=UTC),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon.",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return ReviewedLead(**base)


def test_reviewed_lead_constructs_with_required_fields():
    rl = make_rl()
    assert rl.lead_id == "L-001"
    assert rl.confidence_band == "HOT"
    assert rl.archive_url is None


def test_reviewed_lead_uppercases_band():
    rl = make_rl(confidence_band="hot")
    assert rl.confidence_band == "HOT"


def test_reviewed_lead_rejects_invalid_band():
    with pytest.raises(ValueError, match="confidence_band"):
        make_rl(confidence_band="WARMTE")


def test_reviewed_lead_rejects_empty_snippet():
    with pytest.raises(ValueError, match="snippet"):
        make_rl(snippet="")


def test_reviewed_lead_rejects_invalid_source_url():
    with pytest.raises(ValueError, match="source_url"):
        make_rl(source_url="not-a-url")


def test_reviewed_lead_rejects_invalid_reviewer_email():
    with pytest.raises(ValueError, match="reviewer_email"):
        make_rl(reviewer_email="not-an-email")


def test_installer_from_csv_row():
    inst = Installer.from_csv_row({
        "installer_id": "I-001",
        "company_name": "Visser Installaties",
        "contact_name": "Jeroen Visser",
        "email": "jeroen@visserinstallaties.nl",
        "phone": "+31 20 1234567",
        "city": "Amsterdam",
        "regions": "Amsterdam|Amstelveen|Haarlem",
        "niches": "warmtepomp|zonnepanelen",
        "active": "true",
        "notes": "",
    })
    assert inst.installer_id == "I-001"
    assert "Amsterdam" in inst.regions
    assert "warmtepomp" in inst.niches
    assert inst.active is True


def test_installer_inactive_when_active_field_false():
    inst = Installer.from_csv_row({
        "installer_id": "I-002",
        "company_name": "X", "contact_name": "Y", "email": "y@x.nl",
        "phone": "", "city": "", "regions": "", "niches": "",
        "active": "false", "notes": "",
    })
    assert inst.active is False


def test_routed_lead_combines_reviewed_and_installer():
    rl = make_rl()
    inst = Installer(
        installer_id="I-001", company_name="Visser", contact_name="Jeroen Visser",
        email="jeroen@visserinstallaties.nl", phone="", city="Amsterdam",
        regions=["Amsterdam"], niches=["warmtepomp"], active=True, notes="",
    )
    routed = RoutedLead(reviewed_lead=rl, installer=inst, case_id="LR-2026-05-18-0042")
    assert routed.case_id == "LR-2026-05-18-0042"


def test_receipt_holds_rendered_payloads():
    receipt = Receipt(
        case_id="LR-2026-05-18-0042",
        subject="Amsterdam · warmtepomp · HOT",
        preheader="Marieke reviewde een Tweakers-post uit regio Amsterdam.",
        from_display="Marieke de Vries — Lead Radar",
        from_address="marieke@lead-radar.nl",
        to_display="Jeroen Visser",
        to_address="jeroen@visserinstallaties.nl",
        body_text="(plain text)",
        body_html="<p>(html)</p>",
    )
    assert receipt.subject.startswith("Amsterdam")
    assert receipt.from_address == "marieke@lead-radar.nl"
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/model.py`**

```python
"""Dataclass models for the delivery layer.

ReviewedLead   — input from operator console / approved.jsonl
Installer      — installer registry row (from data/installers.csv)
RoutedLead     — reviewed_lead + installer + case_id
Receipt        — fully rendered payload ready for SMTP
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from .subject import ALLOWED_BANDS, ALLOWED_NICHES

_URL_RE = re.compile(r"^https?://[^\s]+$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ALLOWED_PLATFORMS = frozenset({
    "tweakers", "reddit", "facebook", "bouwinfo", "klusidee", "ouders", "other",
})


def _require(value, name: str):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{name} must be non-empty")


@dataclass
class ReviewedLead:
    lead_id: str
    snippet: str
    source_url: str
    source_platform: str
    captured_at: datetime
    region: str
    niche: str
    confidence_band: str
    band_reason: str
    reviewer_name: str
    reviewer_email: str
    reviewed_at: datetime
    archive_url: Optional[str] = None
    subject_override: Optional[str] = None
    opening_override: Optional[str] = None

    def __post_init__(self):
        for name in ("lead_id", "snippet", "source_url", "source_platform",
                     "region", "niche", "confidence_band", "band_reason",
                     "reviewer_name", "reviewer_email"):
            _require(getattr(self, name), name)
        if not _URL_RE.match(self.source_url):
            raise ValueError(f"source_url must be http(s) URL, got {self.source_url!r}")
        if not _EMAIL_RE.match(self.reviewer_email):
            raise ValueError(f"reviewer_email must be valid email, got {self.reviewer_email!r}")
        self.source_platform = self.source_platform.strip().lower()
        if self.source_platform not in _ALLOWED_PLATFORMS:
            raise ValueError(f"source_platform {self.source_platform!r} not in {sorted(_ALLOWED_PLATFORMS)}")
        self.niche = self.niche.strip().lower()
        if self.niche not in ALLOWED_NICHES:
            raise ValueError(f"niche {self.niche!r} not in {sorted(ALLOWED_NICHES)}")
        self.confidence_band = self.confidence_band.strip().upper()
        if self.confidence_band not in ALLOWED_BANDS:
            raise ValueError(f"confidence_band {self.confidence_band!r} not in {sorted(ALLOWED_BANDS)}")
        if self.archive_url is not None and not _URL_RE.match(self.archive_url):
            raise ValueError(f"archive_url must be http(s) URL, got {self.archive_url!r}")

    @classmethod
    def from_dict(cls, raw: Dict[str, object]) -> "ReviewedLead":
        captured = raw["captured_at"]
        reviewed = raw["reviewed_at"]
        return cls(
            lead_id=str(raw["lead_id"]),
            snippet=str(raw["snippet"]),
            source_url=str(raw["source_url"]),
            source_platform=str(raw["source_platform"]),
            captured_at=captured if isinstance(captured, datetime) else datetime.fromisoformat(str(captured)),
            region=str(raw["region"]),
            niche=str(raw["niche"]),
            confidence_band=str(raw["confidence_band"]),
            band_reason=str(raw["band_reason"]),
            reviewer_name=str(raw["reviewer_name"]),
            reviewer_email=str(raw["reviewer_email"]),
            reviewed_at=reviewed if isinstance(reviewed, datetime) else datetime.fromisoformat(str(reviewed)),
            archive_url=str(raw["archive_url"]) if raw.get("archive_url") else None,
            subject_override=str(raw["subject_override"]) if raw.get("subject_override") else None,
            opening_override=str(raw["opening_override"]) if raw.get("opening_override") else None,
        )


@dataclass
class Installer:
    installer_id: str
    company_name: str
    contact_name: str
    email: str
    phone: str
    city: str
    regions: List[str]
    niches: List[str]
    active: bool
    notes: str = ""

    @classmethod
    def from_csv_row(cls, row: Dict[str, str]) -> "Installer":
        def split(value: str) -> List[str]:
            v = (value or "").strip()
            if not v:
                return []
            for sep in ("|", ","):
                if sep in v:
                    return [part.strip() for part in v.split(sep) if part.strip()]
            return [v]

        active_raw = (row.get("active") or "").strip().lower()
        return cls(
            installer_id=row["installer_id"].strip(),
            company_name=row.get("company_name", "").strip(),
            contact_name=row.get("contact_name", "").strip(),
            email=row.get("email", "").strip(),
            phone=row.get("phone", "").strip(),
            city=row.get("city", "").strip(),
            regions=split(row.get("regions", "")),
            niches=split(row.get("niches", "")),
            active=active_raw in {"1", "true", "yes", "y"},
            notes=row.get("notes", "").strip(),
        )


@dataclass
class RoutedLead:
    reviewed_lead: ReviewedLead
    installer: Installer
    case_id: str


@dataclass
class Receipt:
    case_id: str
    subject: str
    preheader: str
    from_display: str
    from_address: str
    to_display: str
    to_address: str
    body_text: str
    body_html: str
```

- [ ] **Step 4: Confirm pass** — Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/model.py tests/delivery/test_model.py
git commit -m "feat(delivery): dataclass models (ReviewedLead/Installer/RoutedLead/Receipt)"
```

---

### Task 10: Plain-text canonical renderer (§7.5, §7.9)

**Files:**
- Create: `delivery/render_text.py`
- Create: `tests/delivery/test_render_text.py`

- [ ] **Step 1: Failing tests**

```python
from datetime import datetime, timezone, timedelta

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_text import render_text

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _routed(**lead_overrides):
    base = dict(
        lead_id="L-001",
        snippet=(
            "Ik zoek een installateur in regio Amsterdam voor een "
            "lucht/water warmtepomp + buffervat. Budget rond 12-15k, "
            "wil deze zomer plaatsen."
        ),
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=NOW - timedelta(hours=4),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon (deze zomer).",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=NOW - timedelta(hours=2),
    )
    base.update(lead_overrides)
    rl = ReviewedLead(**base)
    inst = Installer(
        installer_id="I-001", company_name="Visser Installaties",
        contact_name="Jeroen Visser", email="jeroen@visserinstallaties.nl",
        phone="", city="Amsterdam", regions=["Amsterdam"], niches=["warmtepomp"],
        active=True, notes="",
    )
    return RoutedLead(reviewed_lead=rl, installer=inst, case_id="LR-2026-05-18-0042")


def test_opening_uses_installer_first_name():
    assert "Hallo Jeroen," in render_text(_routed(), now=NOW)


def test_snippet_is_verbatim_quoted():
    out = render_text(_routed(), now=NOW)
    assert "Ik zoek een installateur in regio Amsterdam" in out


def test_source_platform_titlecased():
    out = render_text(_routed(), now=NOW)
    assert "vastgelegd vanuit Tweakers" in out


def test_relative_time_visible():
    out = render_text(_routed(), now=NOW)
    assert "4 uur geleden" in out


def test_open_bron_with_host():
    out = render_text(_routed(), now=NOW)
    assert "open bron ↗" in out
    assert "(tweakers.net)" in out


def test_band_glyph_hot():
    out = render_text(_routed(), now=NOW)
    assert "band:  ●  HOT" in out


def test_band_glyph_warm():
    out = render_text(_routed(confidence_band="WARM"), now=NOW)
    assert "band:  ○  WARM" in out


def test_band_glyph_opp():
    out = render_text(_routed(confidence_band="OPP"), now=NOW)
    assert "band:  ·  OPP" in out


def test_reason_visible():
    out = render_text(_routed(), now=NOW)
    assert "Expliciet budget en tijdshorizon (deze zomer)." in out


def test_signature_row():
    out = render_text(_routed(), now=NOW)
    assert "Marieke de Vries" in out
    assert "marieke@lead-radar.nl" in out
    assert "2 uur geleden" in out


def test_exclusivity_sentence():
    out = render_text(_routed(), now=NOW)
    assert "uitsluitend naar u verzonden" in out
    assert "5 werkdagen" in out


def test_dispute_strip_names_reviewer():
    out = render_text(_routed(), now=NOW)
    assert "Marieke beoordeelt persoonlijk binnen één werkdag." in out


def test_sign_off_first_name_only():
    lines = [ln.strip() for ln in render_text(_routed(), now=NOW).splitlines() if ln.strip()]
    assert "Marieke" in lines


def test_case_id_in_footer():
    assert "LR-2026-05-18-0042" in render_text(_routed(), now=NOW)


def test_brand_footer_appears_once():
    assert render_text(_routed(), now=NOW).count("Lead Radar") == 1


def test_decayed_source_shows_archive():
    routed = _routed(
        captured_at=NOW - timedelta(days=10),
        archive_url="https://archive.org/snapshot/abc",
    )
    out = render_text(routed, now=NOW)
    assert "open snapshot (gearchiveerd)" in out
    assert "DECAYED" in out
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/render_text.py`**

```python
"""Plain-text canonical renderer per spec §7.5 + §7.9.

Element order is doctrine (02.1 + 04.5). Spacing matches the spec example.
"""

from __future__ import annotations

from datetime import datetime

from .decay import is_decayed
from .model import RoutedLead
from .opening import build_opening
from .preheader import reviewer_first_name
from .time_fmt import relative_time

BAND_GLYPH = {"HOT": "●", "WARM": "○", "OPP": "·"}

_SEPARATOR = "─" * 57

_EXCLUSIVITY_PARAGRAPH = (
    "Deze lead is uitsluitend naar u verzonden. De casus blijft\n"
    "toegewezen zolang u reageert; bij geen reactie binnen 5\n"
    "werkdagen vervalt het toegewezen-zijn."
)

_DISPUTE_TEMPLATE = (
    "Onjuist iets aan deze lead? Antwoord op deze e-mail.\n"
    "{first} beoordeelt persoonlijk binnen één werkdag.\n"
    "Bij gegrond dispuut: credit op uw account."
)

_BRAND_FOOTER = "Lead Radar  ·  case {case_id}"


def _installer_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0] if parts else "installateur"


def _bron_line(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    if is_decayed(rl.captured_at, now=now) and rl.archive_url:
        return "open snapshot (gearchiveerd) ↗  · DECAYED"
    host = rl.source_url.split("://", 1)[-1].split("/", 1)[0]
    return f"open bron ↗  ({host})"


def render_text(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    inst = routed.installer

    reviewer_first = reviewer_first_name(rl.reviewer_name)
    installer_first = _installer_first_name(inst.contact_name)
    platform_titled = rl.source_platform.title()
    captured_rel = relative_time(rl.captured_at, now=now)
    reviewed_rel = relative_time(rl.reviewed_at, now=now)
    band = rl.confidence_band
    glyph = BAND_GLYPH[band]
    bron = _bron_line(routed, now=now)

    opening = rl.opening_override or build_opening(
        installer_first=installer_first,
        platform=rl.source_platform,
        band=band,
    )

    return (
        f"{opening}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f'  "{rl.snippet}"\n'
        "\n"
        f"  vastgelegd vanuit {platform_titled}, {captured_rel}\n"
        f"  {bron}\n"
        "\n"
        f"  band:  {glyph}  {band}\n"
        f"  reden: {rl.band_reason}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"gereviewd door  {rl.reviewer_name}  ·  {reviewed_rel}\n"
        f"                {rl.reviewer_email}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"{_EXCLUSIVITY_PARAGRAPH}\n"
        "\n"
        f"{_DISPUTE_TEMPLATE.format(first=reviewer_first)}\n"
        "\n"
        f"{reviewer_first}\n"
        "\n"
        f"{_SEPARATOR}\n"
        "\n"
        f"{_BRAND_FOOTER.format(case_id=routed.case_id)}\n"
    )
```

- [ ] **Step 4: Confirm pass** — Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/render_text.py tests/delivery/test_render_text.py
git commit -m "feat(delivery): plain-text canonical renderer (§7.5, §7.9)"
```

---

### Task 11: HTML alternative renderer (inline CSS, restrained)

**Files:**
- Create: `delivery/render_html.py`
- Create: `tests/delivery/test_render_html.py`

HTML mirrors element order. Constraints (spec §5): inline styles only, no `<style>` block, three colour roles (tinted neutral background, single accent for HOT, muted gray for OPP), no images, no scripts, no Tailwind classes.

- [ ] **Step 1: Failing tests**

```python
import re
from datetime import datetime, timezone, timedelta

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_html import render_html

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _routed(**lead_overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur in regio Amsterdam voor een warmtepomp.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=NOW - timedelta(hours=4),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon (deze zomer).",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=NOW - timedelta(hours=2),
    )
    base.update(lead_overrides)
    inst = Installer(
        installer_id="I-001", company_name="Visser Installaties",
        contact_name="Jeroen Visser", email="jeroen@visserinstallaties.nl",
        phone="", city="Amsterdam", regions=["Amsterdam"], niches=["warmtepomp"],
        active=True, notes="",
    )
    return RoutedLead(reviewed_lead=ReviewedLead(**base), installer=inst, case_id="LR-2026-05-18-0042")


def test_returns_well_formed_html_document():
    html = render_html(_routed(), now=NOW).lstrip()
    assert html.startswith("<!doctype html>") or html.startswith("<!DOCTYPE html>")
    assert "<html" in html and "</html>" in html


def test_no_style_or_script_tags():
    html = render_html(_routed(), now=NOW)
    assert "<style" not in html.lower()
    assert "stylesheet" not in html.lower()
    assert "<script" not in html.lower()


def test_no_tailwind_classnames():
    html = render_html(_routed(), now=NOW)
    assert not re.search(r'class="[^"]*\b(?:bg-|text-(?:sm|lg|xl)|p-\d|m-\d)\b', html)


def test_snippet_appears_verbatim():
    html = render_html(_routed(), now=NOW)
    assert "Ik zoek een installateur in regio Amsterdam voor een warmtepomp." in html


def test_source_link_target_blank_noopener():
    html = render_html(_routed(), now=NOW)
    assert 'href="https://tweakers.net/threads/12345"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener"' in html


def test_no_tracking_pixel_no_images():
    html = render_html(_routed(), now=NOW)
    assert "<img" not in html.lower()
    assert "open=" not in html


def test_band_label_and_glyph():
    html = render_html(_routed(), now=NOW)
    assert "●" in html and "HOT" in html


def test_reviewer_signature_present():
    html = render_html(_routed(), now=NOW)
    assert "Marieke de Vries" in html
    assert "marieke@lead-radar.nl" in html


def test_case_id_in_footer():
    html = render_html(_routed(), now=NOW)
    assert "LR-2026-05-18-0042" in html


def test_exclusivity_paragraph_present():
    html = render_html(_routed(), now=NOW)
    assert "uitsluitend naar u verzonden" in html


def test_one_case_id_per_email():
    html = render_html(_routed(), now=NOW)
    assert html.count("LR-2026-05-18-0042") == 1
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/render_html.py`**

```python
"""HTML alternative renderer.

Inline styles only (email-client safety). Three colour roles:
  background:    tinted near-white
  accent (HOT):  warm operational red-orange
  muted (OPP):   neutral gray

No images, no scripts, no <style> block, no Tailwind classnames.
"""

from __future__ import annotations

from datetime import datetime
from html import escape

from .decay import is_decayed
from .model import RoutedLead
from .opening import build_opening
from .preheader import reviewer_first_name
from .time_fmt import relative_time

_BAND_GLYPH = {"HOT": "●", "WARM": "○", "OPP": "·"}
_BAND_COLOR = {
    "HOT": "#b04a2f",
    "WARM": "#8a6a3b",
    "OPP": "#6e6e6e",
}

_BG = "#faf9f7"
_INK = "#1a1a1a"
_DIM = "#6e6e6e"
_RULE = "#d4d4d0"
_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif"
_MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def _style(rules: dict) -> str:
    return ";".join(f"{k}:{v}" for k, v in rules.items())


def _installer_first(full: str) -> str:
    parts = full.strip().split()
    return parts[0] if parts else "installateur"


def render_html(routed: RoutedLead, *, now: datetime) -> str:
    rl = routed.reviewed_lead
    inst = routed.installer
    band = rl.confidence_band
    band_color = _BAND_COLOR[band]
    glyph = _BAND_GLYPH[band]

    captured_rel = relative_time(rl.captured_at, now=now)
    reviewed_rel = relative_time(rl.reviewed_at, now=now)
    platform_titled = rl.source_platform.title()
    reviewer_first = reviewer_first_name(rl.reviewer_name)
    installer_first = _installer_first(inst.contact_name)
    host = rl.source_url.split("://", 1)[-1].split("/", 1)[0]

    decayed = is_decayed(rl.captured_at, now=now) and rl.archive_url
    if decayed:
        source_href = rl.archive_url
        source_label = "open snapshot (gearchiveerd)"
        source_extra = f" <span style=\"{_style({'color':_DIM,'margin-left':'8px'})}\">DECAYED</span>"
    else:
        source_href = rl.source_url
        source_label = "open bron"
        source_extra = ""

    opening = rl.opening_override or build_opening(
        installer_first=installer_first,
        platform=rl.source_platform,
        band=band,
    )

    body_style = _style({
        "font-family": _SANS, "background": _BG, "color": _INK,
        "line-height": "1.55", "margin": "0", "padding": "32px 24px",
    })
    wrapper = _style({"max-width": "640px", "margin": "0 auto"})
    rule = _style({"border": "0", "border-top": f"1px solid {_RULE}", "margin": "24px 0"})
    quote = _style({
        "font-size": "17px", "line-height": "1.6", "padding": "0 8px", "margin": "0 0 16px 0",
    })
    meta = _style({"font-size": "14px", "color": _DIM, "margin": "0"})
    band_row = _style({"font-size": "15px", "margin": "16px 0 0 0"})
    band_mark = _style({"color": band_color, "font-size": "16px", "margin-right": "8px"})
    sig = _style({"font-size": "14px", "color": _INK, "margin": "0"})
    case_style = _style({"font-family": _MONO, "font-size": "13px", "color": _DIM})
    link = _style({"color": _INK, "text-decoration": "underline"})

    snippet_html = escape(rl.snippet)
    reason_html = escape(rl.band_reason)
    opening_html = escape(opening).replace("\n", "<br>")

    return (
        "<!doctype html>"
        "<html lang=\"nl\"><head>"
        "<meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{escape(routed.case_id)}</title>"
        "</head>"
        f"<body style=\"{body_style}\">"
        f"<div style=\"{wrapper}\">"
        f"<p style=\"{_style({'margin':'0 0 16px 0'})}\">{opening_html}</p>"
        f"<hr style=\"{rule}\">"
        f"<blockquote style=\"{quote}\">&ldquo;{snippet_html}&rdquo;</blockquote>"
        f"<p style=\"{meta}\">vastgelegd vanuit {escape(platform_titled)}, {escape(captured_rel)}<br>"
        f"<a href=\"{escape(source_href)}\" target=\"_blank\" rel=\"noopener\" style=\"{link}\">{escape(source_label)} ↗</a> "
        f"<span style=\"{_style({'color':_DIM})}\">({escape(host)})</span>{source_extra}</p>"
        f"<p style=\"{band_row}\">band: <span style=\"{band_mark}\">{glyph}</span>{escape(band)}<br>"
        f"<span style=\"{_style({'color':_DIM})}\">reden:</span> {reason_html}</p>"
        f"<hr style=\"{rule}\">"
        f"<p style=\"{sig}\">gereviewd door <strong>{escape(rl.reviewer_name)}</strong> &middot; {escape(reviewed_rel)}<br>"
        f"<a href=\"mailto:{escape(rl.reviewer_email)}\" style=\"{link}\">{escape(rl.reviewer_email)}</a></p>"
        f"<hr style=\"{rule}\">"
        f"<p style=\"{meta}\">Deze lead is uitsluitend naar u verzonden. De casus blijft toegewezen zolang u reageert; bij geen reactie binnen 5 werkdagen vervalt het toegewezen-zijn.</p>"
        f"<p style=\"{_style({'margin':'16px 0','font-size':'14px'})}\">Onjuist iets aan deze lead? Antwoord op deze e-mail. {escape(reviewer_first)} beoordeelt persoonlijk binnen één werkdag. Bij gegrond dispuut: credit op uw account.</p>"
        f"<p style=\"{_style({'margin':'24px 0 0 0','font-size':'14px'})}\">{escape(reviewer_first)}</p>"
        f"<hr style=\"{rule}\">"
        f"<p style=\"{case_style}\">Lead Radar &middot; case {escape(routed.case_id)}</p>"
        "</div></body></html>"
    )
```

- [ ] **Step 4: Confirm pass** — Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/render_html.py tests/delivery/test_render_html.py
git commit -m "feat(delivery): HTML alternative renderer (inline-CSS, three colour roles)"
```

---

## Phase 4 — Routing and config

### Task 12: Installer router (region + niche match, exclusivity guard)

**Files:**
- Create: `delivery/route.py`
- Create: `tests/delivery/test_route.py`

- [ ] **Step 1: Failing tests**

```python
from datetime import datetime, timezone, timedelta
from pathlib import Path

from delivery.model import ReviewedLead
from delivery.route import load_installers, pick_installer

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def make_rl(**overrides):
    base = dict(
        lead_id="L-001", snippet="x", source_url="https://x.example/p",
        source_platform="tweakers", captured_at=NOW - timedelta(hours=4),
        region="Amsterdam", niche="warmtepomp", confidence_band="HOT",
        band_reason="r", reviewer_name="M de Vries", reviewer_email="m@x.nl",
        reviewed_at=NOW - timedelta(hours=2),
    )
    base.update(overrides)
    return ReviewedLead(**base)


def _write_installers(tmp_path: Path, rows):
    p = tmp_path / "installers.csv"
    header = "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
    p.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def _write_log(tmp_path: Path, lines):
    p = tmp_path / "lead_log.csv"
    header = "at,lead_id,from_state,to_state,actor,reason\n"
    p.write_text(header + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


def test_load_installers_parses_pipe_separated_lists(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,Jeroen Visser,j@v.nl,,Amsterdam,Amsterdam|Haarlem,warmtepomp|airco,true,",
    ])
    installers = load_installers(csv)
    assert installers[0].regions == ["Amsterdam", "Haarlem"]
    assert installers[0].niches == ["warmtepomp", "airco"]


def test_picks_first_active_match(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,J,j@v.nl,,Amsterdam,Utrecht,warmtepomp,true,",
        "I-002,Bakker,B,b@b.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        "I-003,Klaas,K,k@k.nl,,Amsterdam,Amsterdam,airco,true,",
    ])
    log = _write_log(tmp_path, [])
    picked = pick_installer(make_rl(), load_installers(csv), log_path=log)
    assert picked is not None and picked.installer_id == "I-002"


def test_skips_inactive(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,false,",
        "I-002,Bakker,B,b@b.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    log = _write_log(tmp_path, [])
    picked = pick_installer(make_rl(), load_installers(csv), log_path=log)
    assert picked.installer_id == "I-002"


def test_returns_none_when_no_match(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,J,j@v.nl,,Rotterdam,Rotterdam,warmtepomp,true,",
    ])
    log = _write_log(tmp_path, [])
    assert pick_installer(make_rl(), load_installers(csv), log_path=log) is None


def test_respects_exclusivity_already_delivered(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    log = _write_log(tmp_path, [
        "2026-05-17T08:00:00+00:00,L-001,APPROVED,DELIVERED,m@x,prior",
    ])
    picked = pick_installer(make_rl(lead_id="L-001"), load_installers(csv), log_path=log)
    assert picked is None


def test_missing_log_treated_as_empty(tmp_path):
    csv = _write_installers(tmp_path, [
        "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    picked = pick_installer(make_rl(), load_installers(csv), log_path=tmp_path / "does-not-exist.csv")
    assert picked is not None
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/route.py`**

```python
"""Installer routing.

V0 algorithm:
  1. Filter installers by active=True
  2. Filter by region (case-insensitive substring match against installer.regions)
  3. Filter by niche (exact match against installer.niches)
  4. Pick first remaining in CSV order
  5. Before returning: confirm lead_id has no prior DELIVERED transition
     in data/lead_log.csv — exclusivity (doctrine 04.3).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Optional, Union

from .model import Installer, ReviewedLead

DEFAULT_LOG_PATH = Path("data/lead_log.csv")


def load_installers(path: Union[str, Path]) -> List[Installer]:
    installers: List[Installer] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("installer_id"):
                continue
            installers.append(Installer.from_csv_row(row))
    return installers


def _already_delivered(lead_id: str, log_path: Path) -> bool:
    if not log_path.exists():
        return False
    with log_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("lead_id") == lead_id and row.get("to_state") == "DELIVERED":
                return True
    return False


def pick_installer(
    reviewed_lead: ReviewedLead,
    installers: List[Installer],
    *,
    log_path: Union[str, Path] = DEFAULT_LOG_PATH,
) -> Optional[Installer]:
    log_path = Path(log_path)
    if _already_delivered(reviewed_lead.lead_id, log_path):
        return None

    region_norm = reviewed_lead.region.strip().lower()
    niche_norm = reviewed_lead.niche.strip().lower()

    for inst in installers:
        if not inst.active:
            continue
        regions = [r.strip().lower() for r in inst.regions]
        niches = [n.strip().lower() for n in inst.niches]
        if region_norm not in regions:
            continue
        if niche_norm not in niches:
            continue
        return inst
    return None
```

- [ ] **Step 4: Confirm pass** — Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/route.py tests/delivery/test_route.py
git commit -m "feat(delivery): installer routing + exclusivity guard against lead_log"
```

---

### Task 13: Env-driven config

**Files:**
- Create: `delivery/config.py`
- Create: `tests/delivery/test_config.py`
- Modify: `.env.example` (append new env vars)

- [ ] **Step 1: Failing tests**

```python
import pytest

from delivery.config import DeliveryConfig, load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("DELIVERY_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("DELIVERY_SMTP_PORT", "587")
    monkeypatch.setenv("DELIVERY_SMTP_USER", "marieke@lead-radar.nl")
    monkeypatch.setenv("DELIVERY_SMTP_PASSWORD", "secret")
    monkeypatch.setenv("DELIVERY_SMTP_USE_TLS", "true")
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "false")
    cfg = load_config()
    assert isinstance(cfg, DeliveryConfig)
    assert cfg.smtp_host == "smtp.example.com"
    assert cfg.smtp_port == 587
    assert cfg.smtp_user == "marieke@lead-radar.nl"
    assert cfg.smtp_use_tls is True
    assert cfg.reply_domain == "lead-radar.nl"
    assert cfg.dry_run is False


def test_dry_run_default_true_when_unset(monkeypatch):
    for var in ("DELIVERY_DRY_RUN",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    cfg = load_config()
    assert cfg.dry_run is True


def test_missing_reply_domain_raises(monkeypatch):
    monkeypatch.delenv("DELIVERY_REPLY_DOMAIN", raising=False)
    with pytest.raises(ValueError, match="DELIVERY_REPLY_DOMAIN"):
        load_config()


def test_smtp_required_when_not_dry_run(monkeypatch):
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "false")
    monkeypatch.delenv("DELIVERY_SMTP_HOST", raising=False)
    monkeypatch.delenv("DELIVERY_SMTP_USER", raising=False)
    monkeypatch.delenv("DELIVERY_SMTP_PASSWORD", raising=False)
    with pytest.raises(ValueError, match="SMTP"):
        load_config()
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/config.py`**

```python
"""Env-driven delivery config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


@dataclass
class DeliveryConfig:
    reply_domain: str
    dry_run: bool = True
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    decay_days: int = 8
    input_path: Path = Path("data/reviewed/approved.jsonl")
    installers_path: Path = Path("data/installers.csv")
    log_path: Path = Path("data/lead_log.csv")
    audit_path: Path = Path("data/delivery_log.jsonl")


def load_config() -> DeliveryConfig:
    reply_domain = os.environ.get("DELIVERY_REPLY_DOMAIN", "").strip()
    if not reply_domain:
        raise ValueError("DELIVERY_REPLY_DOMAIN must be set")

    dry_run = _bool("DELIVERY_DRY_RUN", default=True)
    smtp_host = os.environ.get("DELIVERY_SMTP_HOST")
    smtp_user = os.environ.get("DELIVERY_SMTP_USER")
    smtp_password = os.environ.get("DELIVERY_SMTP_PASSWORD")

    if not dry_run:
        if not (smtp_host and smtp_user and smtp_password):
            raise ValueError(
                "SMTP credentials (DELIVERY_SMTP_HOST/USER/PASSWORD) required when DELIVERY_DRY_RUN=false"
            )

    return DeliveryConfig(
        reply_domain=reply_domain,
        dry_run=dry_run,
        smtp_host=smtp_host,
        smtp_port=int(os.environ.get("DELIVERY_SMTP_PORT", "587")),
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        smtp_use_tls=_bool("DELIVERY_SMTP_USE_TLS", default=True),
        decay_days=int(os.environ.get("DELIVERY_DECAY_DAYS", "8")),
        input_path=Path(os.environ.get("DELIVERY_INPUT_PATH", "data/reviewed/approved.jsonl")),
        installers_path=Path(os.environ.get("DELIVERY_INSTALLERS_PATH", "data/installers.csv")),
        log_path=Path(os.environ.get("DELIVERY_LOG_PATH", "data/lead_log.csv")),
        audit_path=Path(os.environ.get("DELIVERY_AUDIT_PATH", "data/delivery_log.jsonl")),
    )
```

- [ ] **Step 4: Append env block to `.env.example`**

```bash
cat >> "/Users/claudebot/Lead generator/lead-radar/.env.example" <<'EOF'

# --- Receipt delivery (Receipt Artifact v0) ---
DELIVERY_REPLY_DOMAIN=lead-radar.nl
DELIVERY_DRY_RUN=true
DELIVERY_SMTP_HOST=
DELIVERY_SMTP_PORT=587
DELIVERY_SMTP_USER=
DELIVERY_SMTP_PASSWORD=
DELIVERY_SMTP_USE_TLS=true
DELIVERY_DECAY_DAYS=8
DELIVERY_INPUT_PATH=data/reviewed/approved.jsonl
DELIVERY_INSTALLERS_PATH=data/installers.csv
DELIVERY_LOG_PATH=data/lead_log.csv
DELIVERY_AUDIT_PATH=data/delivery_log.jsonl
EOF
```

- [ ] **Step 5: Confirm pass** — Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add delivery/config.py tests/delivery/test_config.py .env.example
git commit -m "feat(delivery): env-driven config + .env.example block"
```

---

## Phase 5 — Send and dispatcher

### Task 14: SMTP sender (stdlib smtplib + EmailMessage)

**Files:**
- Create: `delivery/send.py`
- Create: `tests/delivery/test_send.py`

- [ ] **Step 1: Failing tests**

```python
from email.message import EmailMessage

from delivery.config import DeliveryConfig
from delivery.send import build_email_message, send_smtp


def make_config(dry_run=False):
    return DeliveryConfig(
        reply_domain="lead-radar.nl",
        dry_run=dry_run,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="marieke@lead-radar.nl",
        smtp_password="secret",
        smtp_use_tls=True,
    )


def test_build_message_sets_required_headers():
    msg = build_email_message(
        subject="Amsterdam · warmtepomp · HOT",
        preheader="Marieke reviewde een Tweakers-post uit regio Amsterdam.",
        from_display="Marieke de Vries — Lead Radar",
        from_address="marieke@lead-radar.nl",
        to_display="Jeroen Visser",
        to_address="jeroen@visserinstallaties.nl",
        body_text="hello",
        body_html="<p>hello</p>",
        case_id="LR-2026-05-18-0042",
    )
    assert msg["From"].startswith("Marieke de Vries")
    assert msg["From"].endswith("<marieke@lead-radar.nl>")
    assert msg["To"] == "Jeroen Visser <jeroen@visserinstallaties.nl>"
    assert msg["Reply-To"] == "marieke@lead-radar.nl"
    assert msg["Subject"] == "Amsterdam · warmtepomp · HOT"
    assert msg["X-LeadRadar-Case-ID"] == "LR-2026-05-18-0042"


def test_build_message_has_text_and_html_alternatives():
    msg = build_email_message(
        subject="s", preheader="p", from_display="F", from_address="f@x.nl",
        to_display="T", to_address="t@x.nl", body_text="plain", body_html="<p>h</p>",
        case_id="LR-2026-05-18-0001",
    )
    payloads = msg.get_payload()
    assert isinstance(payloads, list) and len(payloads) == 2
    types = {p.get_content_type() for p in payloads}
    assert types == {"text/plain", "text/html"}


def test_send_smtp_calls_smtplib(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port):
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, user, pw):
            captured["login"] = (user, pw)

        def send_message(self, msg):
            captured["subject"] = msg["Subject"]

    import delivery.send as send_mod
    monkeypatch.setattr(send_mod.smtplib, "SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["From"] = "Marieke <marieke@lead-radar.nl>"
    msg["To"] = "Jeroen <jeroen@x.nl>"
    msg["Subject"] = "test"
    send_smtp(msg, make_config(dry_run=False))

    assert captured["host"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["starttls"] is True
    assert captured["login"] == ("marieke@lead-radar.nl", "secret")
    assert captured["subject"] == "test"


def test_send_smtp_skips_when_dry_run(monkeypatch):
    called = {"smtp": False}

    class FakeSMTP:
        def __init__(self, *a, **kw):
            called["smtp"] = True

    import delivery.send as send_mod
    monkeypatch.setattr(send_mod.smtplib, "SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["From"] = "a@x"
    msg["To"] = "b@x"
    msg["Subject"] = "t"
    assert send_smtp(msg, make_config(dry_run=True)) == "dry-run"
    assert called["smtp"] is False
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/send.py`**

```python
"""SMTP sender (stdlib smtplib + EmailMessage).

Plain-text is the primary content; HTML is the alternative.
No tracking pixel, no attachments V0, no auto-bcc.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from .config import DeliveryConfig


def build_email_message(
    *,
    subject: str,
    preheader: str,
    from_display: str,
    from_address: str,
    to_display: str,
    to_address: str,
    body_text: str,
    body_html: str,
    case_id: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{from_display} <{from_address}>"
    msg["To"] = f"{to_display} <{to_address}>"
    msg["Reply-To"] = from_address
    msg["Subject"] = subject
    msg["X-LeadRadar-Case-ID"] = case_id
    msg["Message-ID"] = make_msgid(domain=from_address.split("@", 1)[-1])
    msg.set_content(f"{preheader}\n\n{body_text}")
    msg.add_alternative(body_html, subtype="html")
    return msg


def send_smtp(message: EmailMessage, config: DeliveryConfig) -> str:
    if config.dry_run:
        return "dry-run"
    with smtplib.SMTP(config.smtp_host, config.smtp_port) as client:
        if config.smtp_use_tls:
            client.starttls()
        client.login(config.smtp_user, config.smtp_password)
        client.send_message(message)
    return str(message["Message-ID"])
```

- [ ] **Step 4: Confirm pass** — Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/send.py tests/delivery/test_send.py
git commit -m "feat(delivery): SMTP sender (stdlib smtplib + plain/HTML alternatives)"
```

---

### Task 15: Dispatcher orchestrator

**Files:**
- Create: `delivery/dispatcher.py`
- Create: `tests/delivery/test_dispatcher.py`

- [ ] **Step 1: Failing tests**

```python
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from delivery.config import DeliveryConfig
from delivery.dispatcher import DispatchSummary, dispatch

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def write_approved(path: Path, leads):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for lead in leads:
            f.write(json.dumps(lead) + "\n")


def write_installers(path: Path, rows):
    header = "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def base_lead(**overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur voor warmtepomp + buffervat.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=(NOW - timedelta(hours=4)).isoformat(),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon.",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=(NOW - timedelta(hours=2)).isoformat(),
    )
    base.update(overrides)
    return base


@pytest.fixture
def config(tmp_path: Path):
    return DeliveryConfig(
        reply_domain="lead-radar.nl",
        dry_run=True,
        smtp_host=None, smtp_user=None, smtp_password=None,
        decay_days=8,
        input_path=tmp_path / "reviewed.jsonl",
        installers_path=tmp_path / "installers.csv",
        log_path=tmp_path / "lead_log.csv",
        audit_path=tmp_path / "delivery_log.jsonl",
    )


def test_dispatch_dry_run_routes_and_audits(config):
    write_approved(config.input_path, [base_lead()])
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen Visser,jeroen@visserinstallaties.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert isinstance(summary, DispatchSummary)
    assert summary.total == 1 and summary.delivered == 1
    audit_lines = config.audit_path.read_text(encoding="utf-8").strip().splitlines()
    row = json.loads(audit_lines[0])
    assert row["status"] == "delivered"
    assert row["case_id"].startswith("LR-2026-05-18-")
    assert row["installer_email"] == "jeroen@visserinstallaties.nl"
    assert row["dry_run"] is True


def test_dispatch_writes_pcs_transition_when_not_dry_run(config, monkeypatch):
    config.dry_run = False
    config.smtp_host = "smtp.x"
    config.smtp_user = "marieke@lead-radar.nl"
    config.smtp_password = "x"
    write_approved(config.input_path, [base_lead()])
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen Visser,jeroen@visserinstallaties.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    sent = {"count": 0}
    monkeypatch.setattr("delivery.dispatcher.send_smtp", lambda msg, cfg: (sent.__setitem__("count", sent["count"] + 1) or "msg-1"))
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 1 and sent["count"] == 1
    log_text = config.log_path.read_text(encoding="utf-8")
    assert "DELIVERED" in log_text and "L-001" in log_text


def test_dispatch_skips_when_no_installer_match(config):
    write_approved(config.input_path, [base_lead(region="Groningen")])
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.unrouted == 1
    audit_row = json.loads(config.audit_path.read_text(encoding="utf-8").strip())
    assert audit_row["status"] == "unrouted"


def test_dispatch_skips_when_vocab_violation(config):
    lead = base_lead(band_reason="qualified lead from Amsterdam")
    write_approved(config.input_path, [lead])
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.vocab_violations == 1


def test_dispatch_respects_exclusivity_via_log(config):
    write_approved(config.input_path, [base_lead(lead_id="L-001")])
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    config.log_path.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-17T08:00:00+00:00,L-001,APPROVED,DELIVERED,m@x,prior\n",
        encoding="utf-8",
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.unrouted == 1


def test_dispatch_respects_limit(config):
    leads = [base_lead(lead_id=f"L-{i:03d}") for i in range(5)]
    write_approved(config.input_path, leads)
    write_installers(config.installers_path, [
        "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
    ])
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config, limit=2)
    assert summary.total == 2 and summary.delivered == 2
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/dispatcher.py`**

```python
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
                _append_audit(config.audit_path, {
                    "at": now.isoformat(timespec="seconds"),
                    "status": "input_invalid",
                    "error": str(exc),
                    "raw": raw_line[:500],
                    "dry_run": config.dry_run,
                })
                continue

            installer = pick_installer(reviewed_lead, installers, log_path=config.log_path)
            if installer is None:
                summary.unrouted += 1
                _append_audit(config.audit_path, {
                    "at": now.isoformat(timespec="seconds"),
                    "status": "unrouted",
                    "lead_id": reviewed_lead.lead_id,
                    "region": reviewed_lead.region,
                    "niche": reviewed_lead.niche,
                    "dry_run": config.dry_run,
                })
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

            violations = check_no_banned_terms(subject + "\n" + body_text)
            if violations:
                summary.vocab_violations += 1
                _append_audit(config.audit_path, {
                    "at": now.isoformat(timespec="seconds"),
                    "status": "vocab_violation",
                    "lead_id": reviewed_lead.lead_id,
                    "case_id": case_id,
                    "violations": [{"kind": v.kind, "matched": v.matched, "start": v.start} for v in violations],
                    "dry_run": config.dry_run,
                })
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
                _append_audit(config.audit_path, {
                    "at": now.isoformat(timespec="seconds"),
                    "status": "smtp_error",
                    "lead_id": reviewed_lead.lead_id,
                    "case_id": case_id,
                    "error": str(exc),
                    "dry_run": config.dry_run,
                })
                continue

            if not config.dry_run:
                pcs.append_transition(
                    lead_id=reviewed_lead.lead_id,
                    from_state="APPROVED",
                    to_state="DELIVERED",
                    actor=reviewed_lead.reviewer_email,
                    reason=f"sent to {installer.email}; case_id={case_id}",
                    log_path=config.log_path,
                )

            summary.delivered += 1
            _append_audit(config.audit_path, {
                "at": now.isoformat(timespec="seconds"),
                "status": "delivered",
                "lead_id": reviewed_lead.lead_id,
                "case_id": case_id,
                "installer_id": installer.installer_id,
                "installer_email": installer.email,
                "subject": subject,
                "message_id": message_id,
                "dry_run": config.dry_run,
            })

    return summary
```

- [ ] **Step 4: Confirm pass** — Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/dispatcher.py tests/delivery/test_dispatcher.py
git commit -m "feat(delivery): dispatcher orchestrator (route → render → lint → send → log)"
```

---

## Phase 6 — CLI, golden anti-pattern suite

### Task 16: CLI entrypoint (`python -m delivery dispatch`)

**Files:**
- Create: `delivery/cli.py`
- Create: `tests/delivery/test_cli.py`

- [ ] **Step 1: Failing tests**

```python
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

UTC = timezone.utc


@pytest.fixture
def env_setup(tmp_path: Path, monkeypatch):
    reviewed = tmp_path / "reviewed.jsonl"
    installers = tmp_path / "installers.csv"
    log = tmp_path / "lead_log.csv"
    audit = tmp_path / "delivery_log.jsonl"
    reviewed.write_text(json.dumps({
        "lead_id": "L-001",
        "snippet": "Ik zoek een installateur voor warmtepomp.",
        "source_url": "https://tweakers.net/p/1",
        "source_platform": "tweakers",
        "captured_at": datetime(2026, 5, 18, 10, tzinfo=UTC).isoformat(),
        "region": "Amsterdam",
        "niche": "warmtepomp",
        "confidence_band": "HOT",
        "band_reason": "Expliciet budget en tijdshorizon.",
        "reviewer_name": "Marieke de Vries",
        "reviewer_email": "marieke@lead-radar.nl",
        "reviewed_at": datetime(2026, 5, 18, 12, tzinfo=UTC).isoformat(),
    }) + "\n", encoding="utf-8")
    installers.write_text(
        "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
        "I-001,Visser,Jeroen Visser,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "true")
    monkeypatch.setenv("DELIVERY_INPUT_PATH", str(reviewed))
    monkeypatch.setenv("DELIVERY_INSTALLERS_PATH", str(installers))
    monkeypatch.setenv("DELIVERY_LOG_PATH", str(log))
    monkeypatch.setenv("DELIVERY_AUDIT_PATH", str(audit))
    return {"audit": audit, "log": log}


def test_cli_dispatch_subcommand_runs(env_setup, monkeypatch, capsys):
    from delivery.cli import main
    monkeypatch.setattr(sys, "argv", ["delivery", "dispatch", "--limit", "1"])
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "delivered=1" in out
    assert env_setup["audit"].exists()


def test_cli_help_lists_dispatch(monkeypatch, capsys):
    from delivery.cli import main
    monkeypatch.setattr(sys, "argv", ["delivery", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "dispatch" in captured
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement `delivery/cli.py`**

```python
"""CLI: python -m delivery dispatch [--dry-run] [--limit N]."""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from .config import load_config
from .dispatcher import dispatch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="delivery", description="Lead Radar receipt dispatcher")
    sub = parser.add_subparsers(dest="command", required=True)
    p_dispatch = sub.add_parser("dispatch", help="Dispatch one batch of approved receipts")
    p_dispatch.add_argument("--limit", type=int, default=None, help="Max receipts to send")
    p_dispatch.add_argument("--dry-run", action="store_true", help="Override DELIVERY_DRY_RUN")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "dispatch":
        config = load_config()
        if args.dry_run:
            config.dry_run = True
        summary = dispatch(config, limit=args.limit)
        print(
            f"total={summary.total} delivered={summary.delivered} "
            f"unrouted={summary.unrouted} vocab_violations={summary.vocab_violations} "
            f"errors={summary.errors} dry_run={config.dry_run}"
        )
        return 0 if summary.errors == 0 else 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Confirm pass** — Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add delivery/cli.py tests/delivery/test_cli.py
git commit -m "feat(delivery): CLI entrypoint (python -m delivery dispatch)"
```

---

### Task 17: Golden anti-pattern suite + sample fixture + .gitignore

**Files:**
- Create: `delivery/fixtures/reviewed_sample.jsonl`
- Create: `tests/delivery/test_anti_patterns_golden.py`
- Modify: `.gitignore` (add `data/reviewed/`, `data/delivery_log.jsonl`)

- [ ] **Step 1: Create fixture**

`delivery/fixtures/reviewed_sample.jsonl`:

```
{"lead_id":"L-S01","snippet":"Ik zoek een installateur in regio Amsterdam voor een lucht/water warmtepomp + buffervat. Budget rond 12-15k, wil deze zomer plaatsen. Wie heeft ervaring met Vaillant aroTHERM plus?","source_url":"https://tweakers.net/threads/sample-1","source_platform":"tweakers","captured_at":"2026-05-18T10:00:00+00:00","region":"Amsterdam","niche":"warmtepomp","confidence_band":"HOT","band_reason":"Expliciet budget, expliciete tijdshorizon (deze zomer), model genoemd, regio genoemd.","reviewer_name":"Marieke de Vries","reviewer_email":"marieke@lead-radar.nl","reviewed_at":"2026-05-18T12:00:00+00:00"}
{"lead_id":"L-S02","snippet":"Iemand ervaring met airco-installatie in een rijtjeshuis uit de jaren 70? Geluidsniveau en plaatsing buitenunit zijn mijn grootste vragen.","source_url":"https://reddit.com/r/duurzaamwonen/comments/sample-2","source_platform":"reddit","captured_at":"2026-05-18T08:00:00+00:00","region":"Utrecht","niche":"airco","confidence_band":"WARM","band_reason":"Onderzoeksfase, geen tijdshorizon genoemd, geen budget.","reviewer_name":"Marieke de Vries","reviewer_email":"marieke@lead-radar.nl","reviewed_at":"2026-05-18T11:00:00+00:00"}
{"lead_id":"L-S03","snippet":"Ben benieuwd hoeveel mensen in deze groep al zonnepanelen hebben. Welk merk hebben jullie?","source_url":"https://facebook.com/groups/duurzaam/posts/sample-3","source_platform":"facebook","captured_at":"2026-05-18T06:00:00+00:00","region":"Rotterdam","niche":"zonnepanelen","confidence_band":"OPP","band_reason":"Indirecte interesse, geen tijdshorizon, geen platform-vraag.","reviewer_name":"Marieke de Vries","reviewer_email":"marieke@lead-radar.nl","reviewed_at":"2026-05-18T09:00:00+00:00"}
```

- [ ] **Step 2: Failing tests**

```python
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from delivery.model import Installer, ReviewedLead, RoutedLead
from delivery.render_html import render_html
from delivery.render_text import render_text
from delivery.vocab_lint import check_no_banned_terms

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def _installer():
    return Installer(
        installer_id="I-X", company_name="Visser", contact_name="Jeroen Visser",
        email="jeroen@x.nl", phone="", city="X",
        regions=["Amsterdam", "Utrecht", "Rotterdam"],
        niches=["warmtepomp", "airco", "zonnepanelen"],
        active=True, notes="",
    )


def _load_fixtures():
    fixture = Path(__file__).resolve().parents[2] / "delivery" / "fixtures" / "reviewed_sample.jsonl"
    leads = []
    with fixture.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            leads.append(ReviewedLead.from_dict(json.loads(line)))
    return leads


@pytest.fixture
def routed_samples():
    return [
        RoutedLead(reviewed_lead=rl, installer=_installer(), case_id=f"LR-2026-05-18-{i+1:04d}")
        for i, rl in enumerate(_load_fixtures())
    ]


def test_fixture_loads_three_samples(routed_samples):
    assert len(routed_samples) == 3
    assert {r.reviewed_lead.confidence_band for r in routed_samples} == {"HOT", "WARM", "OPP"}


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_plain_text_passes_vocab_lint(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    violations = check_no_banned_terms(body)
    assert violations == [], f"violations: {violations}"


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_html_passes_vocab_lint(routed_samples, idx):
    html = render_html(routed_samples[idx], now=NOW)
    violations = check_no_banned_terms(html)
    assert violations == [], f"violations: {violations}"


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_five_canonical_fields_present(routed_samples, idx):
    routed = routed_samples[idx]
    body = render_text(routed, now=NOW)
    assert routed.reviewed_lead.snippet in body
    assert "vastgelegd vanuit" in body
    assert "open bron ↗" in body
    assert routed.reviewed_lead.confidence_band in body
    assert routed.reviewed_lead.band_reason in body
    assert routed.reviewed_lead.reviewer_name in body
    assert routed.reviewed_lead.reviewer_email in body
    assert "uitsluitend naar u verzonden" in body
    assert routed.case_id in body


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_html_has_no_style_or_tailwind(routed_samples, idx):
    html = render_html(routed_samples[idx], now=NOW)
    assert "<style" not in html.lower()
    assert "<script" not in html.lower()
    assert "<img" not in html.lower()
    assert not re.search(r'class="[^"]*\b(?:bg-|text-(?:sm|lg|xl)|p-\d|m-\d)\b', html)


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_brand_appears_exactly_once_in_plain_text(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    assert body.count("Lead Radar") == 1


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_sign_off_first_name_only(routed_samples, idx):
    body = render_text(routed_samples[idx], now=NOW)
    lines = [ln.rstrip() for ln in body.splitlines()]
    assert "Marieke" in lines
```

- [ ] **Step 3: Update `.gitignore`**

```bash
cat >> "/Users/claudebot/Lead generator/lead-radar/.gitignore" <<'EOF'

# Receipt delivery — runtime data
data/reviewed/
data/delivery_log.jsonl
EOF
```

- [ ] **Step 4: Run delivery tests**

Run: `cd "/Users/claudebot/Lead generator/lead-radar" && python -m pytest tests/delivery/ -v`
Expected: all delivery tests pass.

- [ ] **Step 5: Run full repo test suite (regression check)**

Run: `cd "/Users/claudebot/Lead generator/lead-radar" && python -m pytest -q`
Expected: existing tests still pass + new tests pass.

- [ ] **Step 6: Commit**

```bash
git add delivery/fixtures/reviewed_sample.jsonl tests/delivery/test_anti_patterns_golden.py .gitignore
git commit -m "feat(delivery): golden anti-pattern suite + three-band sample fixture"
```

- [ ] **Step 7: Push**

```bash
git push
```

---

## Self-review (plan author)

**1. Spec coverage:**

| Spec section | Implementing task(s) |
|---|---|
| §2.1 information hierarchy | Tasks 10 (render_text), 11 (render_html), 17 (golden) |
| §2.5 never-in-receipt list | Tasks 5 (vocab_lint), 17 (golden) |
| §3.1 snippet treatment | Tasks 9 (model validation), 10 (renderer keeps verbatim) |
| §3.2 source affordance | Tasks 10, 11 |
| §3.3 captured_at relative/absolute | Task 3 (time_fmt) |
| §3.4 band rendering | Tasks 10, 11 (BAND_GLYPH + reden line) |
| §3.5 vocabulary discipline | Tasks 5 (vocab_lint), 17 (golden) |
| §4.2 explicit exclusivity sentence | Tasks 10, 11 (verbatim text) |
| §4.3 lifecycle signals | Task 10 (footer dispute strip) |
| §4.4 dispute-strip | Tasks 10, 11 |
| §5.1 operational vs SaaS grammar | Task 11 (three colour roles, no Tailwind) |
| §6.4 reviewer signature row | Tasks 10, 11 |
| §7.1 sender identity | Tasks 5 (vocab_lint catches noreply), 15 (dispatcher uses reviewer_email) |
| §7.2 subject line | Tasks 6 (subject), 15 (dispatcher builds) |
| §7.3 pre-header | Tasks 7 (preheader), 14 (build_email_message) |
| §7.4 opening line | Tasks 8 (opening), 10 (renderer embeds) |
| §7.5 citation block | Task 10 |
| §7.6 exclusivity + dispute footer | Task 10 |
| §7.7 sign-off (first name only) | Task 10 |
| §7.8 threading (no ticket prefix) | Task 14 |
| §7.9 full V0 example | Tasks 17 (golden uses fixture matching example) |
| §8 anti-patterns | Tasks 5 (vocab_lint), 17 (golden) |
| §9 "looks expensive" mechanisms | Tasks 10/11 + Task 17 invariants |
| §10 out of scope | No tasks (intentional — keeps scope tight) |
| §11 founder-decisions Q1–Q4 | Q1=A: Task 14 SMTP only; Q2=A: Task 10/11 no photo; Q3=A: Task 2 + Task 10/11 footer; Q4=A: Task 10/11 explicit zin |
| §12 implementation contract | Tasks 2–17 jointly; Task 17 golden re-asserts |

No spec gaps.

**2. Placeholder scan:** No "TBD", no "implement later", no "similar to Task N", no bare "handle edge cases". All steps contain complete code blocks.

**3. Type consistency:** `ReviewedLead`, `Installer`, `RoutedLead`, `Receipt`, `DispatchSummary`, `Violation`, `DeliveryConfig`, `BAND_GLYPH`, `ALLOWED_BANDS`, `ALLOWED_NICHES`, `reviewer_first_name`, `relative_time`, `is_decayed`, `generate_case_id`, `next_sequence_for_date`, `pick_installer`, `load_installers`, `build_subject`, `build_preheader`, `build_opening`, `render_text`, `render_html`, `check_no_banned_terms`, `build_email_message`, `send_smtp`, `dispatch`, `main` — all defined once, referenced consistently.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-18-receipt-artifact-v0.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
