# FB Primary — Plan D: Demo Bundle & Outreach Tooling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce een set statische HTML-pagina's + outreach-docs zodat Sem de huidige inventory en het lead-format kan tonen aan installateurs tijdens cold calls. Snelle founder-led outreach, geen platformbouw.

**Architecture:** Geen nieuwe abstrahering. Reuse `delivery/render_html.py` voor sample-receipt. Eén kleine module `demo_bundle/` voor inventory-snapshot HTML (table-driven uit `data/lead_inventory.csv`). CLI `run_render_demo.py` schrijft alles naar `output/demo/`. Outreach-docs in `docs/outreach/` als markdown.

**Tech Stack:** Python 3, stdlib (csv, html, pathlib, datetime), pytest. Hergebruik bestaand `delivery/` package. Geen template engine, geen JS, geen server.

**Depends on:** Plan A merged (uses `consumer.inventory` schema), Plan B Task 1 (`consumer.approval.approve_lead` aanwezig).

**Scope-exclusions (expliciet niet in Plan D):**
- Hosting/deploy van demo-bundle (lokaal openen tijdens calls voldoende)
- Geen integratie met `lead-radar-site` NextJS — die staat los
- Geen analytics, geen tracking, geen DB
- Geen nieuwe doctrine-secties of governance

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `lead-radar/run_inventory_show.py` | Create | CLI: print inventory table naar terminal (founder-rehearsal) |
| `lead-radar/run_seed_demo_inventory.py` | Create | CLI: seed 6-8 synthetische leads voor demo-volume |
| `lead-radar/demo_bundle/__init__.py` | Create | Package marker |
| `lead-radar/demo_bundle/inventory_page.py` | Create | Render inventory snapshot HTML |
| `lead-radar/demo_bundle/sample_receipt.py` | Create | Construct synthetic ReviewedLead + invoke `delivery.render_html` |
| `lead-radar/run_render_demo.py` | Create | CLI orchestrator: schrijf bundel naar `output/demo/` |
| `lead-radar/tests/test_inventory_show.py` | Create | Unit tests (3) |
| `lead-radar/tests/test_seed_demo_inventory.py` | Create | Unit tests (2) |
| `lead-radar/tests/test_demo_inventory_page.py` | Create | Unit tests (3) |
| `lead-radar/tests/test_demo_sample_receipt.py` | Create | Unit tests (2) |
| `lead-radar/docs/outreach/rehearsal.md` | Create | Sem's call-walkthrough script |
| `lead-radar/docs/outreach/cold-email.md` | Create | Cold-email template |
| `lead-radar/.gitignore` | Modify | Add `output/` |

---

## Pre-flight

- [ ] **Verify branch state**

```bash
cd "/Users/claudebot/Lead generator"
git branch --show-current  # expect: feat/fb-primary-b-moderation
ls lead-radar/consumer/approval.py lead-radar/consumer/inventory.py
ls lead-radar/delivery/render_html.py
```

Plan D stacks op `feat/fb-primary-b-moderation`.

---

## Task 1: Inventory show CLI

**Files:**
- Create: `lead-radar/run_inventory_show.py`
- Create: `lead-radar/tests/test_inventory_show.py`

**Goal:** `python3 run_inventory_show.py` toont huidige inventory als terminal-tabel. Founder-rehearsal tool, geen filtering.

- [ ] **Step 1.1: Schrijf falende test**

```python
"""Unit tests for run_inventory_show CLI."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.inventory import append_inventory_row
from run_inventory_show import render_inventory_table, main


@pytest.fixture
def sample_inventory(tmp_path: Path) -> Path:
    path = tmp_path / "lead_inventory.csv"
    append_inventory_row(
        path,
        lead_id="lead-001",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at="2026-05-19T08:00:00+00:00",
        approved_at="2026-05-19T09:00:00+00:00",
        expires_at="2026-06-02T08:00:00+00:00",
        source_class="apify_public",
    )
    append_inventory_row(
        path,
        lead_id="lead-002",
        niche="zonnepanelen",
        region_nl="utrecht|utrecht",
        intent_strength="WARM",
        captured_at="2026-05-18T14:00:00+00:00",
        approved_at="2026-05-18T15:00:00+00:00",
        expires_at="2026-06-01T14:00:00+00:00",
        source_class="burner_closed",
        reviewer_attestation="Lid sinds 2024",
    )
    return path


class TestRenderInventoryTable:
    def test_renders_header_and_rows(self, sample_inventory: Path):
        out = render_inventory_table(sample_inventory)
        assert "lead-001" in out
        assert "lead-002" in out
        assert "warmtepomp" in out
        assert "HOT" in out
        assert "WARM" in out
        assert "intent" in out.lower()

    def test_empty_inventory_returns_message(self, tmp_path: Path):
        out = render_inventory_table(tmp_path / "missing.csv")
        assert "Geen inventory" in out or "empty" in out.lower()

    def test_main_prints_to_stdout(
        self, sample_inventory: Path, capsys: pytest.CaptureFixture
    ):
        rc = main(["--inventory", str(sample_inventory)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "lead-001" in captured.out
```

- [ ] **Step 1.2: Run om falen te verifiëren**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 -m pytest tests/test_inventory_show.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'run_inventory_show'`.

- [ ] **Step 1.3: Implementeer `run_inventory_show.py`**

```python
"""CLI: print huidige inventory als leesbare terminal-tabel.

Voor founder-rehearsal en operational orientation. Geen filtering,
geen sorting flags V0 — alle rows in CSV-volgorde.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


_COLUMNS = [
    ("lead_id", 22),
    ("niche", 14),
    ("region_nl", 22),
    ("intent", 6),
    ("captured", 12),
    ("expires", 12),
    ("source", 14),
]


def _truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value.ljust(width)
    return (value[: width - 1] + "…").ljust(width)


def render_inventory_table(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        return "Geen inventory gevonden op " + str(path)

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return "Geen inventory rows (alleen header)."

    header = " ".join(_truncate(name, width) for name, width in _COLUMNS)
    rule = "-" * len(header)
    lines = [header, rule]
    for row in rows:
        captured = (row.get("captured_at") or "")[:10]
        expires = (row.get("expires_at") or "")[:10]
        cells = [
            _truncate(row.get("lead_id", ""), 22),
            _truncate(row.get("niche", ""), 14),
            _truncate(row.get("region_nl", ""), 22),
            _truncate(row.get("intent_strength", ""), 6),
            _truncate(captured, 12),
            _truncate(expires, 12),
            _truncate(row.get("source_class", ""), 14),
        ]
        lines.append(" ".join(cells))
    lines.append(rule)
    lines.append(f"{len(rows)} lead(s) in pool.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    args = parser.parse_args(argv)
    print(render_inventory_table(args.inventory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 1.4: Run tests + commit**

```bash
python3 -m pytest tests/test_inventory_show.py -v   # 3 passed
cd "/Users/claudebot/Lead generator"
git add lead-radar/run_inventory_show.py lead-radar/tests/test_inventory_show.py
git commit -m "feat(demo): run_inventory_show CLI for terminal-table view

Plan D Task 1. Founder-rehearsal tool — print huidige inventory
als leesbare tabel. Geen filtering, geen sorting: alle rows in
CSV-volgorde.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Demo-inventory seed script

**Files:**
- Create: `lead-radar/run_seed_demo_inventory.py`
- Create: `lead-radar/tests/test_seed_demo_inventory.py`

**Goal:** Eén commando schrijft 6-8 synthetische demo-leads naar inventory zodat de demo-bundle ook met "lege" lokale state direct gevuld is. Idempotent: skip leads waarvan lead_id al bestaat.

- [ ] **Step 2.1: Schrijf falende test**

```python
"""Unit tests for seed_demo_inventory."""
from __future__ import annotations

import csv
from pathlib import Path

from run_seed_demo_inventory import DEMO_LEADS, seed_demo_inventory


def _read_inventory(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestSeedDemoInventory:
    def test_seeds_all_demo_leads_to_empty_csv(self, tmp_path: Path):
        inventory_path = tmp_path / "lead_inventory.csv"
        decay_windows = {
            row["niche"]: {"HOT": 14, "WARM": 28} for row in DEMO_LEADS
        }
        written = seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        assert written == len(DEMO_LEADS)
        rows = _read_inventory(inventory_path)
        assert len(rows) == len(DEMO_LEADS)
        assert {r["lead_id"] for r in rows} == {l["lead_id"] for l in DEMO_LEADS}

    def test_idempotent_skips_existing_lead_ids(self, tmp_path: Path):
        inventory_path = tmp_path / "lead_inventory.csv"
        decay_windows = {
            row["niche"]: {"HOT": 14, "WARM": 28} for row in DEMO_LEADS
        }
        seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        second = seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        assert second == 0
        rows = _read_inventory(inventory_path)
        assert len(rows) == len(DEMO_LEADS)
```

- [ ] **Step 2.2: Run om falen te verifiëren**

```bash
python3 -m pytest tests/test_seed_demo_inventory.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 2.3: Implementeer `run_seed_demo_inventory.py`**

```python
"""CLI: seed synthetische demo-leads naar inventory voor founder-rehearsal.

Idempotent: leads waarvan lead_id al bestaat in inventory worden
overgeslagen. Schrijft GEEN lead_log transitions — dit is een demo-
preseed, niet een echt approve-pad.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from consumer.inventory import (
    append_inventory_row,
    compute_expires_at,
    ensure_inventory_csv,
    load_decay_windows,
)


_NOW = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)


DEMO_LEADS: list[dict] = [
    {
        "lead_id": "demo-wp-utr-001",
        "niche": "warmtepomp",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=6),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-wp-utr-002",
        "niche": "warmtepomp",
        "region_nl": "utrecht|utrecht",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=2),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-zp-utr-001",
        "niche": "zonnepanelen",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(days=1),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-zp-flv-001",
        "niche": "zonnepanelen",
        "region_nl": "flevoland|almere",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=3),
        "source_class": "burner_closed",
        "reviewer_attestation": "Lid sinds 2024; observerend account",
    },
    {
        "lead_id": "demo-iso-utr-001",
        "niche": "isolatie",
        "region_nl": "utrecht|nieuwegein",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=18),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-airco-utr-001",
        "niche": "airco",
        "region_nl": "utrecht|veenendaal",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=4),
        "source_class": "burner_closed",
        "reviewer_attestation": "Lid sinds 2023; meelees-rol",
    },
    {
        "lead_id": "demo-lp-utr-001",
        "niche": "laadpaal",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=3),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-dak-flv-001",
        "niche": "dakwerk",
        "region_nl": "flevoland|lelystad",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=2),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
]


def seed_demo_inventory(
    *,
    inventory_path: str | Path,
    decay_windows: dict[str, dict[str, int]],
) -> int:
    inventory_path = Path(inventory_path)
    ensure_inventory_csv(inventory_path)

    existing_ids: set[str] = set()
    with inventory_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            existing_ids.add(row["lead_id"])

    written = 0
    for lead in DEMO_LEADS:
        if lead["lead_id"] in existing_ids:
            continue
        captured_at = lead["captured_at"]
        expires_at = compute_expires_at(
            captured_at, lead["niche"], lead["intent_strength"], decay_windows
        )
        append_inventory_row(
            inventory_path,
            lead_id=lead["lead_id"],
            niche=lead["niche"],
            region_nl=lead["region_nl"],
            intent_strength=lead["intent_strength"],
            captured_at=captured_at.isoformat(timespec="seconds"),
            approved_at=captured_at.isoformat(timespec="seconds"),
            expires_at=expires_at.isoformat(timespec="seconds"),
            source_class=lead["source_class"],
            reviewer_attestation=lead["reviewer_attestation"],
        )
        written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    decay_windows = load_decay_windows(args.config)
    n = seed_demo_inventory(
        inventory_path=args.inventory, decay_windows=decay_windows
    )
    print(f"Seeded {n} demo lead(s) into {args.inventory}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2.4: Run tests + commit**

```bash
python3 -m pytest tests/test_seed_demo_inventory.py -v   # 2 passed
cd "/Users/claudebot/Lead generator"
git add lead-radar/run_seed_demo_inventory.py lead-radar/tests/test_seed_demo_inventory.py
git commit -m "feat(demo): seed_demo_inventory CLI for founder-rehearsal volume

Plan D Task 2. 8 synthetische leads across niches/regions/intent-
strengths. Idempotent: skip existing lead_ids. Geen lead_log
transitions — preseed only.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Inventory snapshot HTML page

**Files:**
- Create: `lead-radar/demo_bundle/__init__.py`
- Create: `lead-radar/demo_bundle/inventory_page.py`
- Create: `lead-radar/tests/test_demo_inventory_page.py`

**Goal:** Render HTML pagina met tabel van huidige inventory: niche, regio, intent badge, captured-relative, decay-countdown, source-badge. Single-file inline CSS, geen JS.

- [ ] **Step 3.1: Schrijf falende test**

```python
"""Unit tests for demo_bundle.inventory_page."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from consumer.inventory import append_inventory_row
from demo_bundle.inventory_page import render_inventory_html


@pytest.fixture
def filled_inventory(tmp_path: Path) -> Path:
    path = tmp_path / "lead_inventory.csv"
    now = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)
    append_inventory_row(
        path,
        lead_id="demo-001",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at=(now - timedelta(hours=6)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(hours=5)).isoformat(timespec="seconds"),
        expires_at=(now + timedelta(days=14)).isoformat(timespec="seconds"),
        source_class="apify_public",
    )
    append_inventory_row(
        path,
        lead_id="demo-002",
        niche="zonnepanelen",
        region_nl="utrecht|utrecht",
        intent_strength="WARM",
        captured_at=(now - timedelta(days=3)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(days=3)).isoformat(timespec="seconds"),
        expires_at=(now + timedelta(days=25)).isoformat(timespec="seconds"),
        source_class="burner_closed",
        reviewer_attestation="Lid sinds 2024",
    )
    return path


class TestRenderInventoryHtml:
    def test_contains_header_and_lead_ids(self, filled_inventory: Path):
        html = render_inventory_html(
            inventory_path=filled_inventory,
            snapshot_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        )
        assert "<html" in html.lower()
        assert "Lead-radar" in html
        assert "demo-001" in html
        assert "demo-002" in html
        assert "warmtepomp" in html
        assert "HOT" in html and "WARM" in html

    def test_escapes_html_in_attestation(self, tmp_path: Path):
        path = tmp_path / "lead_inventory.csv"
        now = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)
        append_inventory_row(
            path,
            lead_id="demo-xss",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at=now.isoformat(timespec="seconds"),
            approved_at=now.isoformat(timespec="seconds"),
            expires_at=(now + timedelta(days=14)).isoformat(timespec="seconds"),
            source_class="burner_closed",
            reviewer_attestation="<script>alert('x')</script>",
        )
        html = render_inventory_html(
            inventory_path=path,
            snapshot_at=now,
        )
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_empty_inventory_renders_placeholder(self, tmp_path: Path):
        path = tmp_path / "lead_inventory.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(
                "lead_id,niche,region_nl,intent_strength,captured_at,"
                "approved_at,expires_at,source_class,reviewer_attestation,"
                "delivered_to,demo_used_at,still_warm_checked_at\n"
            )
        html = render_inventory_html(
            inventory_path=path,
            snapshot_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        )
        assert "Geen leads" in html or "Pool is leeg" in html
```

- [ ] **Step 3.2: Run om falen te verifiëren**

```bash
python3 -m pytest tests/test_demo_inventory_page.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'demo_bundle'`.

- [ ] **Step 3.3: Implementeer `demo_bundle/__init__.py`**

```python
"""Demo bundle — static HTML artifacts voor founder-led outreach.

Geen platform. Geen server. Geen analytics. Eén commando regenereert
de bundel naar output/demo/.
"""
```

- [ ] **Step 3.4: Implementeer `demo_bundle/inventory_page.py`**

```python
"""Render inventory snapshot HTML page.

Eén pagina, single-file (inline CSS in <style>), geen JS. Tabel met
huidige inventory + decay countdown + intent badge + source badge.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html import escape
from pathlib import Path


_STYLE = """
body{font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;
  background:#faf9f7;color:#1a1a1a;margin:0;padding:32px;}
h1{font-size:22px;margin:0 0 4px;}
.snapshot{color:#6e6e6e;font-size:13px;margin-bottom:24px;}
table{border-collapse:collapse;width:100%;background:#fff;
  border:1px solid #d4d4d0;border-radius:6px;overflow:hidden;}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #ebebe7;
  font-size:14px;vertical-align:top;}
th{background:#f3f1ed;font-weight:600;font-size:12px;
  text-transform:uppercase;letter-spacing:0.04em;color:#4a4a45;}
tr:last-child td{border-bottom:none;}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;
  font-size:12px;font-weight:600;}
.hot{background:#fde6df;color:#b04a2f;}
.warm{background:#f5ecdc;color:#8a6a3b;}
.src-public{background:#e6efe6;color:#3f6b3f;}
.src-closed{background:#ece6f4;color:#5b3f8a;}
.src-paste{background:#eee;color:#555;}
.empty{padding:48px;text-align:center;color:#6e6e6e;background:#fff;
  border:1px solid #d4d4d0;border-radius:6px;}
footer{margin-top:32px;color:#6e6e6e;font-size:12px;}
"""


def _intent_badge(intent: str) -> str:
    cls = "hot" if intent == "HOT" else "warm"
    return f'<span class="badge {cls}">{escape(intent)}</span>'


def _source_badge(source: str) -> str:
    cls = {
        "apify_public": "src-public",
        "burner_closed": "src-closed",
        "paste": "src-paste",
    }.get(source, "src-paste")
    label = {
        "apify_public": "publiek",
        "burner_closed": "besloten",
        "paste": "paste",
    }.get(source, source)
    return f'<span class="badge {cls}">{escape(label)}</span>'


def _humanize_relative(
    iso_str: str, snapshot_at: datetime, *, future: bool
) -> str:
    if not iso_str:
        return "—"
    try:
        when = datetime.fromisoformat(iso_str)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        return iso_str
    delta = when - snapshot_at if future else snapshot_at - when
    secs = int(delta.total_seconds())
    if secs < 0:
        return "verlopen" if future else "—"
    days = secs // 86400
    if days >= 1:
        return f"over {days}d" if future else f"{days}d geleden"
    hours = secs // 3600
    if hours >= 1:
        return f"over {hours}u" if future else f"{hours}u geleden"
    return "nu" if future else "zojuist"


def render_inventory_html(
    *,
    inventory_path: str | Path,
    snapshot_at: datetime,
) -> str:
    inventory_path = Path(inventory_path)
    rows: list[dict] = []
    if inventory_path.exists():
        with inventory_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

    snapshot_label = snapshot_at.strftime("%d %B %Y, %H:%M UTC")
    header_html = (
        f'<h1>Lead-radar — huidige voorraad</h1>'
        f'<div class="snapshot">Snapshot: {escape(snapshot_label)}'
        f' &middot; {len(rows)} lead(s)</div>'
    )

    if not rows:
        body_html = '<div class="empty">Pool is leeg — Geen leads beschikbaar.</div>'
    else:
        cells_html = []
        for r in rows:
            cells_html.append(
                "<tr>"
                f"<td><code>{escape(r.get('lead_id', ''))}</code></td>"
                f"<td>{escape(r.get('niche', ''))}</td>"
                f"<td>{escape(r.get('region_nl', '').replace('|', ' / '))}</td>"
                f"<td>{_intent_badge(r.get('intent_strength', ''))}</td>"
                f"<td>{_humanize_relative(r.get('captured_at', ''), snapshot_at, future=False)}</td>"
                f"<td>{_humanize_relative(r.get('expires_at', ''), snapshot_at, future=True)}</td>"
                f"<td>{_source_badge(r.get('source_class', ''))}</td>"
                "</tr>"
            )
        body_html = (
            '<table>'
            '<thead><tr>'
            '<th>Lead-ID</th><th>Niche</th><th>Regio</th>'
            '<th>Intent</th><th>Gezien</th><th>Verloopt</th><th>Bron</th>'
            '</tr></thead><tbody>'
            + "".join(cells_html)
            + '</tbody></table>'
        )

    return (
        '<!doctype html><html lang="nl"><head>'
        '<meta charset="utf-8">'
        '<title>Lead-radar voorraad</title>'
        f'<style>{_STYLE}</style>'
        '</head><body>'
        + header_html
        + body_html
        + '<footer>Doctrine v0.2 &middot; provenance-gefilterd, decay-bewust.</footer>'
        '</body></html>'
    )
```

- [ ] **Step 3.5: Run tests + commit**

```bash
python3 -m pytest tests/test_demo_inventory_page.py -v   # 3 passed
cd "/Users/claudebot/Lead generator"
git add lead-radar/demo_bundle/__init__.py lead-radar/demo_bundle/inventory_page.py lead-radar/tests/test_demo_inventory_page.py
git commit -m "feat(demo): inventory_page HTML renderer

Plan D Task 3. Static single-file HTML, inline CSS, geen JS.
Inventory snapshot met intent/source badges + decay countdown.
HTML-escape voor reviewer_attestation.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Sample receipt HTML (reuse `delivery/render_html.py`)

**Files:**
- Create: `lead-radar/demo_bundle/sample_receipt.py`
- Create: `lead-radar/tests/test_demo_sample_receipt.py`

**Goal:** Render één voorbeeld-receipt HTML via bestaande `delivery.render_html` met synthetische `ReviewedLead` + `Installer` + `RoutedLead`. Geen email-send. Plak HTML in `output/demo/sample-receipt.html`.

- [ ] **Step 4.1: Schrijf falende test**

```python
"""Unit tests for demo_bundle.sample_receipt."""
from __future__ import annotations

from demo_bundle.sample_receipt import render_sample_receipt_html


class TestRenderSampleReceiptHtml:
    def test_returns_html_with_canonical_fields(self):
        html = render_sample_receipt_html()
        assert isinstance(html, str)
        assert "warmtepomp" in html.lower()
        assert "Sem" in html

    def test_renders_non_trivial_length(self):
        html = render_sample_receipt_html()
        assert len(html) > 200
```

- [ ] **Step 4.2: Run om falen te verifiëren**

```bash
python3 -m pytest tests/test_demo_sample_receipt.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 4.3: Implementeer `demo_bundle/sample_receipt.py`**

**Implementer-note**: lees eerst `delivery/model.py` voor exacte signatures van `ReviewedLead`, `Installer`, `RoutedLead`, en `delivery/render_html.py` voor de juiste rendering-functienaam. Bouw één synthetische `RoutedLead` met fictieve maar realistische gegevens en pipe door bestaande renderer.

Skeleton (aanpassen aan exacte API):

```python
"""Render sample-receipt HTML voor outreach-demo.

Reuse delivery.render_html — geen nieuwe renderer. Constructie van
één synthetische ReviewedLead + Installer + RoutedLead met fictieve
gegevens (geen echte naam/post/url).
"""
from __future__ import annotations

from datetime import datetime, timezone

from delivery.model import ReviewedLead, Installer, RoutedLead
from delivery.render_html import render_html


def _build_synthetic_routed_lead() -> RoutedLead:
    reviewed = ReviewedLead(
        lead_id="demo-receipt-sample",
        snippet=(
            "Zoek installateur voor warmtepomp; vrijstaande woning '98, "
            "Amersfoort. Vergelijking 2-3 offertes."
        ),
        source_url="https://www.facebook.com/groups/example/posts/000",
        source_platform="facebook",
        captured_at=datetime(2026, 5, 19, 8, 15, 0, tzinfo=timezone.utc),
        region="utrecht|amersfoort",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Concrete RFQ + regio-match + niche-fit.",
        reviewer_name="Sem Vijn",
        reviewer_email="sem@lead-radar.nl",
    )
    installer = Installer(
        installer_id="demo-installer",
        company_name="Voorbeeld Installatie BV",
        contact_name="Voorbeeld",
        email="voorbeeld@example.nl",
        phone="",
        city="Amersfoort",
        regions=["utrecht|amersfoort"],
        niches=["warmtepomp"],
        active=True,
        notes="",
    )
    return RoutedLead(
        reviewed_lead=reviewed,
        installer=installer,
        case_id="LR-DEMO-001",
    )


def render_sample_receipt_html() -> str:
    routed = _build_synthetic_routed_lead()
    return render_html(routed)
```

Als exacte function-name niet `render_html` is (controleer via `grep -n "^def " delivery/render_html.py`), pas aan zonder delivery-package te wijzigen.

- [ ] **Step 4.4: Run tests + commit**

```bash
python3 -m pytest tests/test_demo_sample_receipt.py -v   # 2 passed
cd "/Users/claudebot/Lead generator"
git add lead-radar/demo_bundle/sample_receipt.py lead-radar/tests/test_demo_sample_receipt.py
git commit -m "feat(demo): sample_receipt reuses delivery.render_html

Plan D Task 4. Synthetic ReviewedLead + Installer -> RoutedLead,
piped through existing delivery renderer. Geen nieuwe renderer.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Demo render orchestrator CLI

**Files:**
- Create: `lead-radar/run_render_demo.py`
- Modify: `lead-radar/.gitignore` (append `output/`)

**Goal:** Eén commando schrijft de complete bundle naar `output/demo/`:
- `output/demo/inventory.html`
- `output/demo/sample-receipt.html`
- `output/demo/README.md`

- [ ] **Step 5.1: Implementeer `run_render_demo.py`**

```python
"""CLI: render demo-bundle voor founder-led outreach.

Schrijft naar output/demo/:
  - inventory.html      — huidige inventory snapshot
  - sample-receipt.html — voorbeeld van delivered lead
  - README.md           — usage-note voor Sem

Idempotent: overschrijft bestaande files.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from demo_bundle.inventory_page import render_inventory_html
from demo_bundle.sample_receipt import render_sample_receipt_html


_README_BODY = """\
# Demo-bundle

- `inventory.html`      — huidige inventory snapshot (regenereer met `python3 run_render_demo.py`)
- `sample-receipt.html` — voorbeeld van het delivery-format

Open in browser tijdens een installateur-call.
"""


def render_demo_bundle(
    *,
    inventory_path: str | Path,
    output_dir: str | Path,
    snapshot_at: datetime | None = None,
) -> list[Path]:
    snapshot_at = snapshot_at or datetime.now(timezone.utc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    inv_path = output_dir / "inventory.html"
    inv_path.write_text(
        render_inventory_html(
            inventory_path=inventory_path,
            snapshot_at=snapshot_at,
        ),
        encoding="utf-8",
    )
    written.append(inv_path)

    receipt_path = output_dir / "sample-receipt.html"
    receipt_path.write_text(render_sample_receipt_html(), encoding="utf-8")
    written.append(receipt_path)

    readme_path = output_dir / "README.md"
    readme_path.write_text(_README_BODY, encoding="utf-8")
    written.append(readme_path)

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    parser.add_argument("--output", default="output/demo")
    args = parser.parse_args(argv)

    written = render_demo_bundle(
        inventory_path=args.inventory,
        output_dir=args.output,
    )
    print(f"Wrote {len(written)} files to {args.output}:")
    for p in written:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5.2: Append `output/` aan `.gitignore`**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
echo "output/" >> .gitignore
```

(Als `.gitignore` nog niet bestaat, create eerst.)

- [ ] **Step 5.3: Smoke test**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 run_render_demo.py
ls output/demo/
open output/demo/inventory.html
open output/demo/sample-receipt.html
```

Expected: 3 files; beide HTML pagina's laden in browser zonder errors.

- [ ] **Step 5.4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/run_render_demo.py lead-radar/.gitignore
git commit -m "feat(demo): run_render_demo orchestrator + .gitignore output/

Plan D Task 5. Eén commando regenereert demo-bundle naar
output/demo/ (inventory + sample-receipt + README).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Outreach runbook + cold-email template

**Files:**
- Create: `lead-radar/docs/outreach/rehearsal.md`
- Create: `lead-radar/docs/outreach/cold-email.md`

**Goal:** Twee korte markdown-docs die Sem kan openen tijdens (1) dry-run rehearsal en (2) live installateur-call.

- [ ] **Step 6.1: Schrijf `rehearsal.md`**

```markdown
# Rehearsal — installateur demo call

Doel: één installateur leren kennen + één lead samen doornemen.

## Voor de call

    cd lead-radar
    python3 run_seed_demo_inventory.py
    python3 run_render_demo.py
    open output/demo/inventory.html
    open output/demo/sample-receipt.html

## Volgorde op de call (<=20 min)

1. **Wie ben jij, wie zijn wij** (2 min)
   - Sem Vijn, 22, solo founder, Amersfoort
   - "We bouwen geen generiek lead-platform. We bouwen één scherpe lead-pijp voor jouw niche."

2. **Wat is een lead bij ons** (5 min)
   - Open `sample-receipt.html`
   - Loop de canonical velden langs: snippet, source, regio, niche, band
   - Benadruk: snippet is letterlijk, geen reformulering. Bron is altijd zichtbaar.

3. **Wat hebben we nu** (5 min)
   - Open `inventory.html`
   - Filter visueel op installateur's niche/regio
   - Wijs op decay-countdown ("over 13d") — vers, niet stale
   - Wijs op bron-badge (publiek vs. besloten + attestation)

4. **Wat verkopen we, wat niet** (5 min)
   - "Eén lead = één installateur. Exclusief. Geen broker-model."
   - "Wij filteren, jij belt of mailt. We doen het outbound niet voor je."
   - "Pricing: nog niet vandaag. Vandaag is alleen: wil je een pilot-week?"

5. **Vraag aan installateur** (3 min)
   - "Als ik je morgen één bruikbare lead in jouw niche/regio stuur, mag ik dan terug bellen?"

## Niet doen

- Niet over scalability, automation, of platform praten
- Geen kortingen aanbieden zonder pilot-resultaat
- Geen "AI" als verkooppunt — provenance is het verkooppunt

## Na de call

- Schrijf installateur in `data/installers.csv` als hij geïnteresseerd is
- Bevestig per email binnen 1 uur ("Bedankt voor het gesprek, ik stuur deze week één lead")
```

- [ ] **Step 6.2: Schrijf `cold-email.md`**

```markdown
# Cold-email template — installateur outreach

Eén template, gepersonaliseerd per installateur. Plain text, geen tracking, geen images.

## Subject

> Eén voorbeeldlead voor {{company_name}} — geen verkooppraatje

## Body

    Beste {{contact_name}},

    Mijn naam is Sem, 22, solo, uit Amersfoort. Ik bouw lead-radar:
    een gefilterde lead-pijp voor installateurs in {{niche}}. Niet
    generiek, niet AI-marketing — publieke posts uit FB/forums +
    besloten groepen met attestation, met bronvermelding en een
    decay-window.

    Eén voorbeeldlead voor jou:
    {{sample_receipt_link_or_text}}

    Geen factuur, geen contract. Als deze lead niets is voor je,
    kost het je 30 seconden om "nee" te zeggen.

    Als ik je deze week één bruikbare lead voor {{niche}} in
    {{region}} stuur, mag ik dan kort terugbellen?

    Met vriendelijke groet,
    Sem Vijn
    sem@lead-radar.nl

## Personalization checklist

- [ ] `{{company_name}}` ingevuld
- [ ] `{{contact_name}}` ingevuld (eerst-naam — vriendelijk)
- [ ] `{{niche}}` matcht installateur's hoofd-niche
- [ ] `{{region}}` matcht installateur's werkgebied
- [ ] `{{sample_receipt_link_or_text}}` — kopieer drie regels uit sample-receipt.html OF stuur file als bijlage

## Niet doen

- Geen "even afstemmen" / "5-minuten gesprek" jargon
- Geen reply-to noreply
- Geen mass-send tools — alle outreach is individueel
- Geen second touch zonder eerste antwoord
```

- [ ] **Step 6.3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/docs/outreach/rehearsal.md lead-radar/docs/outreach/cold-email.md
git commit -m "docs(outreach): rehearsal walkthrough + cold-email template

Plan D Task 6. Twee operationele docs: rehearsal.md (call-script)
en cold-email.md (per-installateur template, plain-text).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: End-to-end smoke + PR

- [ ] **Step 7.1: Full bundle regenereren**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 run_seed_demo_inventory.py
python3 run_inventory_show.py
python3 run_render_demo.py
open output/demo/inventory.html
open output/demo/sample-receipt.html
```

Visueel check:
- inventory.html toont 9+ leads (1 sanity + 8 seed) met intent badges + decay countdown
- sample-receipt.html toont een complete email-style receipt
- Beide laden zonder errors

- [ ] **Step 7.2: Full regression suite**

```bash
python3 -m pytest 2>&1 | tail -3
```

Expected: 1140 + 10 nieuwe tests = 1150 passed (3 skipped).

- [ ] **Step 7.3: Push branch + PR**

```bash
cd "/Users/claudebot/Lead generator"
git push origin feat/fb-primary-b-moderation
gh pr create --title "Plan B Task 1 + Plan D: approve_lead wrapper & demo-bundle" --body "$(cat <<'EOF'
## Summary
- Plan B Task 1: approve_lead() wrapper combining pcs + inventory
- Plan D: demo-bundle (inventory.html + sample-receipt.html) + outreach docs

## Test plan
- [x] approve_lead: 6 tests, all green
- [x] demo CLI's + renderers: 10 tests, all green
- [x] Full regression: 1150 passed, 3 skipped
- [ ] Visual smoke: open output/demo/*.html

🤖 Generated with Claude Code
EOF
)"
```

---

## Self-Review

**Goal coverage:**

| Doel | Tasks |
|------|-------|
| Demoability | 3, 4, 5 |
| Inventory visibility | 1, 3 |
| Installateur-conversaties | 6 |
| Operational clarity | 1, 6 |
| Snelle founder-led outreach | 6 |

**Placeholder scan:**
- Task 4 Step 4.3 heeft implementer-note over verifying exact function name in `delivery/render_html.py`. Acceptabel: implementer leest delivery module voor exacte API.
- Geen "TBD" of "implement later" elders.

**Type consistency:**
- `render_inventory_html(*, inventory_path, snapshot_at)` consistent in Tasks 3 + 5
- `render_sample_receipt_html()` consistent in Tasks 4 + 5
- `seed_demo_inventory(*, inventory_path, decay_windows)` consistent in Task 2

**Scope:** Geen analytics, geen server, geen scalability theater, geen nieuwe dependencies. Eén nieuwe package `demo_bundle/` (2 modules). Drie nieuwe CLI's. Twee markdown-docs. Reuse van bestaand `delivery/`.

---

## Execution Handoff

Plan stacks op `feat/fb-primary-b-moderation` (huidige branch). PR bevat zowel Plan B Task 1 als Plan D; bij review kan worden gesplitst als gewenst.
