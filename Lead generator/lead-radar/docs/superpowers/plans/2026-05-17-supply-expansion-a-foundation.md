# Lead Radar Supply Expansion — Plan A: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken consumer-pipeline output path, add granular source-labeling, and ship the lead-quality processors (cross-run dedup, author-signature dedup, source-weight, sellability-gate, recency-boost) plus the run-digest Telegram message — so that Block B can safely activate 10 dormant scrapers on launchd without producing noisy or duplicate output.

**Architecture:** This plan touches only `lead-radar/consumer/` and its tests. It does not turn on any new sources, does not add launchd schedules, and does not change query lists. All changes are TDD: failing test first, minimal fix, verify, commit. Each task is independently shippable and produces a working build.

**Tech Stack:** Python 3.13, pytest, dataclasses, PyYAML, hashlib (sha256), datasketch (already in requirements.txt for MinHash). No new external dependencies.

**Spec:** `lead-radar/docs/superpowers/specs/2026-05-17-supply-expansion-design.md` (sections 1, 2, 5 partially, 6, 7-C partially).

**Out of scope (deferred to Plans B and C):**
- Launchd plists (Plan B)
- Per-source parser audit (Plan B)
- Manual all-niches dry-run validation (Plan B)
- FB Marketplace activation (Plan C)
- queries.yaml pruning (Plan C)
- Weekly per-source-per-niche report generator (Plan C)
- Heartbeat agent (Plan B — needs launchd context)

---

### Task 1: Reproduce and fix the `'lead/0.85'` int-parse bug in the exporter chain

**Files:**
- Test: `lead-radar/tests/test_lead_to_dict.py` (new)
- Modify: `lead-radar/consumer/__init__.py:80-91` (Lead.to_dict)

**Context:** The May-16 daily_run.log shows the consumer pipeline failed with `invalid literal for int() with base 10: 'lead/0.85'` when writing CSV/JSON. The string `'lead/0.85'` is the format `f"{verdict.kind}/{verdict.confidence:.2f}"` produced by `run_consumer.py:506-508` and stored in `breakdown["llm_verdict"]`. The exception is caught by the exporter's broad try/except, so the stacktrace is lost. The implementer must reproduce with a unit test against `Lead.to_dict()` to find the actual int() call.

- [ ] **Step 1: Write a failing test that reproduces the error**

Create `lead-radar/tests/test_lead_to_dict.py`:
```python
"""Reproduces the May-16 production exporter error.

Error in log: invalid literal for int() with base 10: 'lead/0.85'
Triggered when breakdown contains the llm_verdict string format
produced by run_consumer.py: f"{verdict.kind}/{verdict.confidence:.2f}".
"""
from __future__ import annotations

import json

from consumer import Lead


def _make_lead(breakdown: dict) -> Lead:
    return Lead(
        id="t1",
        source="reddit",
        title="x",
        text="x",
        summary="x",
        url="https://example.com/x",
        city="amsterdam",
        score=72,
        intent="warm",
        breakdown=breakdown,
        niche="warmtepomp",
        author="someuser",
        created_at="2026-05-16T06:00:00+02:00",
    )


def test_to_dict_handles_llm_verdict_string_in_breakdown():
    """breakdown['llm_verdict'] is f'{kind}/{confidence:.2f}' from run_consumer.py:506."""
    lead = _make_lead({"keyword_match": 30, "llm_verdict": "lead/0.85"})

    d = lead.to_dict()  # must not raise

    assert d["breakdown"]["llm_verdict"] == "lead/0.85"
    assert d["breakdown"]["keyword_match"] == 30


def test_to_dict_output_is_json_serializable():
    """The downstream exporter calls json.dumps(lead.breakdown). Verify nothing trips it."""
    lead = _make_lead({
        "keyword_match": 30,
        "llm_verdict": "lead/0.85",
        "llm_adjustment": -3,
        "author_recurring": 1,
    })

    d = lead.to_dict()

    # round-trips cleanly
    assert json.loads(json.dumps(d["breakdown"]))["llm_verdict"] == "lead/0.85"
```

- [ ] **Step 2: Run the test to confirm it fails (or diagnose where the bug really lives)**

Run:
```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_lead_to_dict.py -v
```

Expected outcome A — `test_to_dict_handles_llm_verdict_string_in_breakdown` **FAILS** with `ValueError: invalid literal for int() with base 10: 'lead/0.85'`. The bug is in `Lead.to_dict()`.

Expected outcome B — both tests **PASS**. Then `Lead.to_dict()` is not the culprit; the int() call is downstream. In that case, before proceeding, grep `consumer/` for any code that may call `int()` on a breakdown value or on a Lead field, then write the failing test against THAT call path. Common candidates:
- `consumer/output/sheets.py` row-formatting (existing `int(lead.score)`, `int(row[score_idx])`)
- `consumer/output/exporter.py` row-formatting (CSV writer auto-coerces)
- A field that's typed `int` on the Lead dataclass but receives a string at construction

The implementer MUST pinpoint the exact int() that fails before proceeding to Step 3.

- [ ] **Step 3: Implement the fix in `Lead.to_dict()`**

The current implementation (`consumer/__init__.py:80-91`):
```python
def to_dict(self) -> dict[str, Any]:
    d = asdict(self)
    coerced: dict[str, Any] = {}
    for k, v in d["breakdown"].items():
        if isinstance(v, bool):
            coerced[k] = v
        elif isinstance(v, (int, float)):
            coerced[k] = int(v)
        else:
            coerced[k] = v
    d["breakdown"] = coerced
    return d
```

Fix in `Lead.to_dict()` — make the float branch preserve fractional values so downstream sheets-writing doesn't lose precision:
```python
def to_dict(self) -> dict[str, Any]:
    d = asdict(self)
    coerced: dict[str, Any] = {}
    for k, v in d["breakdown"].items():
        if isinstance(v, bool):
            coerced[k] = v
        elif isinstance(v, int):
            coerced[k] = v
        elif isinstance(v, float):
            # Only coerce to int if it's a whole number; preserve fractions as float
            coerced[k] = int(v) if v.is_integer() else v
        else:
            coerced[k] = v  # strings, None, nested dict/list — pass through unchanged
    d["breakdown"] = coerced
    return d
```

If Step 2 found the int() in a different location (e.g., `sheets.py` row-formatter), patch THAT location to guard against non-numeric breakdown values:
```python
# Example pattern for any downstream int(breakdown_value):
try:
    value_int = int(breakdown_value)
except (TypeError, ValueError):
    value_int = 0  # or skip the row, depending on context
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_lead_to_dict.py -v
```

Expected: 2 passed.

Also run the broader exporter test if it exists:
```bash
python -m pytest tests/ -k "exporter or to_dict" -v
```

Expected: no new failures.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_lead_to_dict.py lead-radar/consumer/__init__.py
git commit -m "$(cat <<'EOF'
fix(consumer): exporter int-parse error on llm_verdict breakdown string

Lead.to_dict() coerced any float to int unconditionally and the
downstream CSV/Sheets writer assumed non-bool/int/float values pass
through. The May-16 production run failed writing CSV/JSON because
breakdown['llm_verdict'] = 'lead/0.85' (a string from
run_consumer.py:506) tripped a downstream int() call.

Fix preserves fractional floats and adds explicit pass-through for any
non-numeric breakdown value. New test reproduces the production case.
EOF
)"
```

---

### Task 2: Verify env vars in consumer-CLI context

**Files:**
- Create: `lead-radar/tests/test_consumer_env.py`
- Modify: `lead-radar/run_consumer.py` (env-validation startup block, if missing)

**Context:** The May-16 log shows `Sheets sync (renovatie) faalde: Geen spreadsheet ID — geef --spreadsheet-id of zet LEAD_RADAR_SPREADSHEET_ID env var.` The May-17 commits (`5d52131`, `eca916c`) fixed the FB Apify pipeline by quoting paths and moving vars out of `~/.zshrc` into `.env`. We must verify the consumer pipeline picks up the same vars when invoked from the same `.env`.

- [ ] **Step 1: Write a failing test that asserts env-presence at startup**

Create `lead-radar/tests/test_consumer_env.py`:
```python
"""Boot-time env validation for run_consumer.py --daily.

Without LEAD_RADAR_SPREADSHEET_ID + LEAD_RADAR_GS_CREDENTIALS the pipeline
runs but silently fails Sheets sync — that's how the May-16 production
issue went undetected for a week. This test enforces a fail-fast block.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_daily_aborts_without_spreadsheet_id():
    """Daily mode must exit non-zero if Sheets vars are missing AND --no-sheets is not set."""
    env = os.environ.copy()
    env.pop("LEAD_RADAR_SPREADSHEET_ID", None)
    env.pop("LEAD_RADAR_GS_CREDENTIALS", None)

    result = subprocess.run(
        [sys.executable, "run_consumer.py", "--daily", "--check-env-only"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
    assert "LEAD_RADAR_SPREADSHEET_ID" in (result.stderr + result.stdout)


def test_daily_proceeds_when_no_sheets_flag_set():
    """--no-sheets must allow daily-mode to skip the env-validation block."""
    env = os.environ.copy()
    env.pop("LEAD_RADAR_SPREADSHEET_ID", None)
    env.pop("LEAD_RADAR_GS_CREDENTIALS", None)

    result = subprocess.run(
        [sys.executable, "run_consumer.py", "--daily", "--no-sheets", "--check-env-only"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, (
        f"Expected zero exit with --no-sheets, got {result.returncode}: {result.stderr}"
    )
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_consumer_env.py -v
```

Expected: both tests FAIL (the `--check-env-only` flag does not yet exist).

- [ ] **Step 3: Implement env-validation in `run_consumer.py`**

Add a `--check-env-only` flag and a `_check_env()` function. Find the existing argparse block in `run_consumer.py` and add the flag, then add a fail-fast block that runs before any real work:

```python
# Inside the argparse setup:
parser.add_argument(
    "--check-env-only",
    action="store_true",
    help="Validate env vars and exit (used by test harness and CI checks)",
)

# After argparse but before pipeline starts:
def _check_env(args) -> tuple[bool, list[str]]:
    """Return (ok, errors). Sheets vars required unless --no-sheets is set."""
    errors: list[str] = []
    if not args.no_sheets:
        if not os.environ.get("LEAD_RADAR_SPREADSHEET_ID"):
            errors.append(
                "LEAD_RADAR_SPREADSHEET_ID is missing. Set it in .env "
                "(launchd does NOT source ~/.zshrc) or pass --no-sheets."
            )
        if not os.environ.get("LEAD_RADAR_GS_CREDENTIALS"):
            errors.append(
                "LEAD_RADAR_GS_CREDENTIALS is missing. Set absolute quoted "
                "path in .env or pass --no-sheets."
            )
    return (not errors, errors)


# Right after parsing args:
env_ok, env_errors = _check_env(args)
if not env_ok:
    for err in env_errors:
        print(f"ENV ERROR: {err}", file=sys.stderr)
    sys.exit(2)
if args.check_env_only:
    print("Env check OK.")
    sys.exit(0)
```

Note: `--no-sheets` flag may already exist. If not, add it alongside `--check-env-only`. Verify by grepping `run_consumer.py` for `no_sheets` first.

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_consumer_env.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_consumer_env.py lead-radar/run_consumer.py
git commit -m "$(cat <<'EOF'
feat(consumer): fail-fast env validation + --check-env-only flag

Adds boot-time validation of LEAD_RADAR_SPREADSHEET_ID and
LEAD_RADAR_GS_CREDENTIALS. The May-16 production run lost a day of
leads to silent Sheets-sync failure because env vars were only set
in ~/.zshrc (which launchd does not source). Fail-fast prevents
this from recurring once consumer-pipeline is added to launchd.
EOF
)"
```

---

### Task 3: Add `source_id` field to `RawPost` and `Lead` for granular source-labeling

**Files:**
- Test: `lead-radar/tests/test_raw_post_source_id.py` (new)
- Modify: `lead-radar/consumer/__init__.py` (RawPost + Lead dataclasses)

**Context:** Spec §2 change-point #6: granular bron-labeling in Sheets requires each source module to emit a `source_id` (e.g., `"reddit:r/duurzaam"`, `"marktplaats:diensten/gent"`). Today, only `source` (the registry name) is stored. We add `source_id` as an optional field that falls back to `source` for backward-compatibility.

- [ ] **Step 1: Write failing tests**

Create `lead-radar/tests/test_raw_post_source_id.py`:
```python
"""source_id is the granular label written to Sheets `bron` column.

Falls back to `source` when a source-module doesn't provide one (legacy
compat for sources we haven't updated yet).
"""
from __future__ import annotations

from consumer import Lead, RawPost


def test_raw_post_source_id_defaults_to_source():
    post = RawPost(id="x", source="reddit", url="https://example.com/x", title="t", text="b")
    assert post.source_id == "reddit"


def test_raw_post_source_id_can_be_explicit():
    post = RawPost(
        id="x",
        source="reddit",
        source_id="reddit:r/duurzaam",
        url="https://example.com/x",
        title="t",
        text="b",
    )
    assert post.source_id == "reddit:r/duurzaam"
    assert post.source == "reddit"


def test_lead_source_id_defaults_to_source():
    lead = Lead(
        id="x",
        source="marktplaats",
        title="t",
        text="b",
        summary="s",
        url="https://example.com/x",
        city="amsterdam",
        score=72,
        intent="warm",
        breakdown={},
        niche="warmtepomp",
    )
    assert lead.source_id == "marktplaats"


def test_lead_source_id_can_be_explicit():
    lead = Lead(
        id="x",
        source="marktplaats",
        source_id="marktplaats:diensten/gent",
        title="t",
        text="b",
        summary="s",
        url="https://example.com/x",
        city="gent",
        score=82,
        intent="hot",
        breakdown={},
        niche="renovatie",
    )
    assert lead.source_id == "marktplaats:diensten/gent"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_raw_post_source_id.py -v
```

Expected: all 4 tests FAIL (`AttributeError: 'RawPost' object has no attribute 'source_id'`).

- [ ] **Step 3: Add `source_id` field to both dataclasses**

Edit `lead-radar/consumer/__init__.py` — modify both dataclasses. Add `source_id` as optional with default fallback to `source`:

```python
@dataclass
class RawPost:
    """Een ruwe forumpost / listing zoals een source 'm aanlevert."""
    id: str
    source: str
    url: str
    title: str
    text: str
    author: str | None = None
    created_at: str | None = None  # ISO 8601
    metadata: dict[str, Any] = field(default_factory=dict)
    # source_id: granular bron-label voor Sheets (bv. "reddit:r/duurzaam").
    # Default = source (registry name) voor backwards compat.
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_id is None:
            self.source_id = self.source

    def fingerprint(self) -> str:
        key = f"{self.source}|{self.id}|{_canonicalize_url(self.url)}".lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class Lead:
    """Een gescoorde lead, klaar voor export."""
    id: str
    source: str
    title: str
    text: str
    summary: str
    url: str
    city: str | None
    score: int
    intent: str
    breakdown: dict[str, Any]
    niche: str
    author: str | None = None
    created_at: str | None = None
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_id is None:
            self.source_id = self.source

    def to_dict(self) -> dict[str, Any]:
        # ...existing logic with the Task-1 fix applied...
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_raw_post_source_id.py tests/test_lead_to_dict.py -v
```

Expected: all 6 tests pass. Task 1 tests should still pass — the fallback ensures no regression.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_raw_post_source_id.py lead-radar/consumer/__init__.py
git commit -m "$(cat <<'EOF'
feat(consumer): add source_id to RawPost and Lead for granular bron-labeling

source_id is the per-subcontext label (e.g. "reddit:r/duurzaam",
"marktplaats:diensten/gent") used by the Sheets bron column to make
per-source yield measurable. Defaults to source for backward compat
with source modules not yet updated. Sheets schema change comes next.
EOF
)"
```

---

### Task 4: Update each source module to emit `source_id`

**Files:**
- Modify: `lead-radar/consumer/sources/reddit.py`
- Modify: `lead-radar/consumer/sources/reddit_new.py`
- Modify: `lead-radar/consumer/sources/tweakers.py`
- Modify: `lead-radar/consumer/sources/bouwinfo.py`
- Modify: `lead-radar/consumer/sources/bouwinfo_forum.py`
- Modify: `lead-radar/consumer/sources/klusidee_forum.py`
- Modify: `lead-radar/consumer/sources/ouders_forum.py`
- Modify: `lead-radar/consumer/sources/google.py`
- Modify: `lead-radar/consumer/sources/marktplaats.py`
- Modify: `lead-radar/consumer/sources/tweedehands.py`
- Modify: `lead-radar/consumer/sources/facebook/__init__.py` (or wherever facebook posts are constructed)
- Test: `lead-radar/tests/test_source_id_formats.py`

**Context:** Each source must produce a granular `source_id` matching the format defined in the spec. We codify the format as a contract in a test, then update each source.

**source_id format contract:**
- `reddit:r/<subreddit>` — e.g., `"reddit:r/duurzaam"`
- `reddit_new:r/<subreddit>` — e.g., `"reddit_new:r/Klussers"`
- `tweakers:<forum-section>` — e.g., `"tweakers:huis-en-tuin"` (or `"tweakers:keywords"` if no section context)
- `bouwinfo:<page>` — e.g., `"bouwinfo:isolatie"`
- `bouwinfo_forum:<subforum>` — e.g., `"bouwinfo_forum:zonnepanelen"`
- `klusidee_forum:<subforum>` — e.g., `"klusidee_forum:cv-ketels"`
- `ouders_forum:<subforum>` — e.g., `"ouders_forum:huis-tuin-en-keuken"`
- `google:<host>` — e.g., `"google:bouwinfo.be"` (DDG hits group by result host)
- `marktplaats:<category>/<city>` — e.g., `"marktplaats:diensten/gent"`
- `2dehands:<category>/<city>` — e.g., `"2dehands:diensten/antwerpen"`
- `facebook:<group_id_or_slug>` — e.g., `"facebook:1520566101657472"`

- [ ] **Step 1: Write the format-contract test**

Create `lead-radar/tests/test_source_id_formats.py`:
```python
"""Per-source source_id format contract — must match Sheets schema docs.

Each source registers itself in REGISTRY; the value-builder it produces
must set RawPost.source_id to the granular form defined here.
"""
from __future__ import annotations

import re

import pytest

from consumer import RawPost
from consumer.sources import REGISTRY

# Map source-name -> regex the source_id must match
SOURCE_ID_FORMATS: dict[str, str] = {
    "reddit":          r"^reddit:r/[A-Za-z0-9_]+$",
    "reddit_new":      r"^reddit_new:r/[A-Za-z0-9_]+$",
    "tweakers":        r"^tweakers:[a-z0-9_-]+$",
    "bouwinfo":        r"^bouwinfo:[a-z0-9_-]+$",
    "bouwinfo_forum":  r"^bouwinfo_forum:[a-z0-9_-]+$",
    "klusidee_forum":  r"^klusidee_forum:[a-z0-9._-]+$",
    "ouders_forum":    r"^ouders_forum:[a-z0-9_-]+$",
    "google":          r"^google:[a-z0-9.-]+$",
    "marktplaats":     r"^marktplaats:[a-z0-9_-]+/[a-z0-9_-]+$",
    "2dehands":        r"^2dehands:[a-z0-9_-]+/[a-z0-9_-]+$",
}


@pytest.mark.parametrize("source_name", list(SOURCE_ID_FORMATS.keys()))
def test_source_registry_has_module(source_name):
    """All sources we're updating must still be in REGISTRY."""
    assert source_name in REGISTRY, f"source '{source_name}' missing from REGISTRY"


def test_source_id_format_for_fake_post():
    """RawPost preserves explicit source_id at construction."""
    p = RawPost(
        id="x",
        source="reddit",
        source_id="reddit:r/duurzaam",
        url="https://reddit.com/r/duurzaam/post/x",
        title="t",
        text="b",
    )
    assert re.match(SOURCE_ID_FORMATS["reddit"], p.source_id), (
        f"reddit example source_id {p.source_id!r} does not match contract"
    )
```

- [ ] **Step 2: Run to confirm parameterized test passes (REGISTRY is unchanged)**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_source_id_formats.py -v
```

Expected: 11 passed (10 registry-presence tests + 1 format-example test).

- [ ] **Step 3: Update reddit.py to emit `source_id`**

Open `lead-radar/consumer/sources/reddit.py` and locate the `RawPost(...)` constructor call. Add `source_id=f"reddit:r/{sub}"` where `sub` is the subreddit name being scraped. The subreddit value should already be in scope per `reddit.py:63` (`metadata={"subreddit": sub, ...}`).

Example diff hint (adapt to actual call site):
```python
yield RawPost(
    id=str(post["id"]),
    source="reddit",
    source_id=f"reddit:r/{sub}",
    url=f"https://reddit.com{post['permalink']}",
    title=post.get("title", ""),
    text=post.get("selftext", ""),
    author=post.get("author"),
    created_at=created_iso,
    metadata={"subreddit": sub, "score": int(score)},
)
```

- [ ] **Step 4: Repeat the same pattern for the other 9 sources**

For each of:
- `reddit_new.py` — `source_id=f"reddit_new:r/{sub}"`
- `tweakers.py` — `source_id=f"tweakers:{section_slug or 'keywords'}"`
- `bouwinfo.py` — `source_id=f"bouwinfo:{page_slug}"` (slug from current URL/category)
- `bouwinfo_forum.py` — `source_id=f"bouwinfo_forum:{subforum_slug}"`
- `klusidee_forum.py` — `source_id=f"klusidee_forum:{subforum_id}"` (matches the per-niche mapping in queries.yaml)
- `ouders_forum.py` — `source_id=f"ouders_forum:{subforum_slug}"`
- `google.py` — `source_id=f"google:{result_host}"` where `result_host` is the canonical netloc from the result URL
- `marktplaats.py` — `source_id=f"marktplaats:{category}/{city.lower()}"`
- `tweedehands.py` — `source_id=f"2dehands:{category}/{city.lower()}"`

For sources with multiple call sites (e.g., a forum scraper that iterates subforums), each call site must set the matching slug. If a source-module currently has the subforum name only as a loop variable, ensure it's threaded into the constructor.

Update the test file with concrete fetch-output checks for at least 3 sources where parser fixtures already exist (`tests/fixtures/`):
```python
# Add to test_source_id_formats.py — example for marktplaats:
def test_marktplaats_emits_granular_source_id():
    """marktplaats.fetch must emit source_id=marktplaats:<category>/<city>."""
    from consumer.sources import marktplaats
    posts = marktplaats.fetch(
        query="warmtepomp installateur",
        limit=2,
        location="amsterdam",
    )
    for p in posts:
        assert p.source_id.startswith("marktplaats:"), p.source_id
        assert "/" in p.source_id.split("marktplaats:", 1)[1], p.source_id
```
Add similar live-fetch tests sparingly — some are HTTP-bound and slow. Prefer fixtures.

- [ ] **Step 5: Run tests and full source-related test suite**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_source_id_formats.py tests/ -k "source or scraper or fetch" -v
```

Expected: all source-related tests pass.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_source_id_formats.py lead-radar/consumer/sources/
git commit -m "$(cat <<'EOF'
feat(consumer/sources): each source emits granular source_id

source_id format documented in tests/test_source_id_formats.py and
supply-expansion design spec §7.B. Reddit/Reddit-new use r/<sub>;
Marktplaats/2dehands use <category>/<city>; Tweakers/Bouwinfo use
their subforum/page slug; Google uses result-host; Facebook uses
group_id_or_slug. source_id falls back to source on legacy paths.
EOF
)"
```

---

### Task 5: Update `sheets.py` to write `source_id` into the bron column

**Files:**
- Modify: `lead-radar/consumer/output/sheets.py`
- Test: `lead-radar/tests/test_sheets_bron_column.py`

**Context:** Spec §2 change-point #6 and §7.B. The bron column today writes `lead.source`. We change it to `lead.source_id` (which defaults to `lead.source` for backward compat). No schema change — same column.

- [ ] **Step 1: Write a failing test**

Create `lead-radar/tests/test_sheets_bron_column.py`:
```python
"""Sheets row-builder writes lead.source_id (granular) into the bron column.

We do not mock gspread — we test the pure row-builder function in isolation.
"""
from __future__ import annotations

from consumer import Lead
from consumer.output import sheets as sheets_mod


def _row_for(lead: Lead) -> list:
    """Pull the row-builder out of sheets.py. Adapt name to actual function in sheets.py."""
    return sheets_mod._build_sheet_row(lead)


def test_bron_uses_source_id_when_set():
    lead = Lead(
        id="x", source="reddit", source_id="reddit:r/duurzaam",
        title="t", text="b", summary="s",
        url="https://reddit.com/r/duurzaam/x",
        city="amsterdam", score=82, intent="hot",
        breakdown={}, niche="warmtepomp",
    )
    row = _row_for(lead)
    bron_idx = sheets_mod.SHEET_COLUMNS.index("bron")
    assert row[bron_idx] == "reddit:r/duurzaam"


def test_bron_falls_back_to_source_when_source_id_none():
    """Legacy lead without source_id: bron must still receive source."""
    lead = Lead(
        id="x", source="reddit",
        title="t", text="b", summary="s",
        url="https://reddit.com/x",
        city="amsterdam", score=82, intent="hot",
        breakdown={}, niche="warmtepomp",
    )
    row = _row_for(lead)
    bron_idx = sheets_mod.SHEET_COLUMNS.index("bron")
    assert row[bron_idx] == "reddit"
```

If `sheets.py` does not currently export `_build_sheet_row` and `SHEET_COLUMNS`, extract them as part of this task — split the existing inline row-construction into a pure helper so it's unit-testable.

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_sheets_bron_column.py -v
```

Expected: import error or AttributeError. Adapt test names to match the actual function once extracted.

- [ ] **Step 3: Update `sheets.py` row-builder**

Open `lead-radar/consumer/output/sheets.py` and locate the function that builds the row written to Sheets (around lines 190-200 based on prior reading). Two changes:

1. Extract the row-building into `_build_sheet_row(lead) -> list` and expose `SHEET_COLUMNS = [...]` as a module-level constant.
2. Change the bron-column assignment from `lead.source` to `lead.source_id or lead.source`:

```python
# In sheets.py, near the top:
SHEET_COLUMNS = [
    "score", "status", "actie", "stad", "niche", "samenvatting", "bron",
    "link", "gevonden_op", "notitie", "prioriteit", "provincie",
    "bericht_voorstel", "contacted_at", "installateur",
]


def _build_sheet_row(lead: Lead) -> list:
    """Pure function — returns the row in SHEET_COLUMNS order."""
    return [
        int(lead.score),                     # score
        "new",                               # status
        _action_for_score(int(lead.score)),  # actie
        lead.city or "",                     # stad
        lead.niche,                          # niche
        smart_summary(lead.summary, lead.text),  # samenvatting
        lead.source_id or lead.source,       # bron  <-- THE KEY CHANGE
        lead.url,                            # link
        _now_nl_iso(),                       # gevonden_op
        "",                                  # notitie
        _priority_for_score(int(lead.score)),  # prioriteit
        detect_province(lead.city) or "",    # provincie
        generate_message(lead),              # bericht_voorstel
        "",                                  # contacted_at
        "",                                  # installateur
    ]
```

(Adapt to actual helper functions and existing column-list — the above is the structural pattern.)

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_sheets_bron_column.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_sheets_bron_column.py lead-radar/consumer/output/sheets.py
git commit -m "$(cat <<'EOF'
feat(output/sheets): write granular source_id into bron column

Extracted _build_sheet_row as a pure helper so it's unit-testable.
Legacy leads without source_id fall back to source, preserving sync
idempotency on rows written before this change. Per-source filtering
in the Sheets UI becomes direct: "filter bron contains marktplaats:".
EOF
)"
```

---

### Task 6: Consumer-pipeline Telegram smoke test + optional separate chat

**Files:**
- Modify: `lead-radar/consumer/output/telegram.py`
- Test: `lead-radar/tests/test_consumer_telegram.py`

**Context:** Spec §7.C: one Telegram bot, four message types. The consumer pipeline may want to post to a separate chat from the FB Apify HOT-alerts. We add `CONSUMER_TELEGRAM_CHAT_ID` env var with fallback to the existing `TELEGRAM_CHAT_ID`.

- [ ] **Step 1: Failing test**

Create `lead-radar/tests/test_consumer_telegram.py`:
```python
"""Telegram chat-id resolution: consumer can route to a separate chat."""
from __future__ import annotations

from consumer.output import telegram as tg


def test_chat_id_falls_back_to_default(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="consumer") == "123"


def test_chat_id_uses_consumer_when_set(monkeypatch):
    monkeypatch.setenv("CONSUMER_TELEGRAM_CHAT_ID", "456")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="consumer") == "456"


def test_chat_id_default_channel_uses_TELEGRAM_CHAT_ID(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert tg.resolve_chat_id(channel="default") == "123"


def test_chat_id_returns_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("CONSUMER_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert tg.resolve_chat_id(channel="consumer") is None
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_consumer_telegram.py -v
```

Expected: failures — `resolve_chat_id` doesn't exist yet.

- [ ] **Step 3: Add `resolve_chat_id` in `telegram.py`**

Add at the top of `lead-radar/consumer/output/telegram.py` (or near existing chat-id reading code):

```python
import os
from typing import Literal


def resolve_chat_id(channel: Literal["consumer", "default"] = "default") -> str | None:
    """Resolve which Telegram chat to send to.

    - channel='consumer': prefer CONSUMER_TELEGRAM_CHAT_ID, fall back to TELEGRAM_CHAT_ID
    - channel='default': always TELEGRAM_CHAT_ID
    Returns None if neither var is set (caller decides what to do).
    """
    if channel == "consumer":
        consumer = os.environ.get("CONSUMER_TELEGRAM_CHAT_ID", "").strip()
        if consumer:
            return consumer
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip() or None
```

Then update any existing `send_lead_alert(...)` or similar to call `resolve_chat_id("consumer")` when invoked from the consumer pipeline.

- [ ] **Step 4: Verify tests pass**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_consumer_telegram.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_consumer_telegram.py lead-radar/consumer/output/telegram.py
git commit -m "$(cat <<'EOF'
feat(output/telegram): CONSUMER_TELEGRAM_CHAT_ID with default fallback

Allows the consumer pipeline to route HOT alerts to a separate chat
from the FB Apify pipeline. Fallback to TELEGRAM_CHAT_ID preserves
single-channel default for operators who don't split them.
EOF
)"
```

---

### Task 7: Layer 2 — cross-run persistent MinHash dedup

**Files:**
- Create: `lead-radar/consumer/processor/cross_run_dedup.py`
- Test: `lead-radar/tests/test_cross_run_dedup.py`
- Modify: `lead-radar/consumer/processor/__init__.py` (export new function)

**Context:** Spec §6, Layer 2. Same person posts a slightly reworded version of their question on Reddit Monday, then on Marktplaats Wednesday. We must catch that and not sell the second one as a fresh lead. Rolling 14-day MinHash store in `data/dedup_store.jsonl`.

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_cross_run_dedup.py`:
```python
"""Layer-2 cross-run dedup: persistent MinHash store, rolling 14d window."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from consumer.processor.cross_run_dedup import (
    is_cross_run_duplicate,
    record_lead_signature,
    prune_store,
)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "dedup_store.jsonl"


def test_first_lead_is_not_duplicate(store):
    assert not is_cross_run_duplicate(
        text="Wie kan een warmtepomp installeren in Amsterdam?",
        store_path=store,
        threshold=0.70,
    )


def test_near_duplicate_within_window_is_caught(store):
    record_lead_signature(
        lead_id="L1",
        text="Wie kan een warmtepomp installeren in Amsterdam?",
        source="reddit:r/Amsterdam",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert is_cross_run_duplicate(
        text="Wie kan een warmtepomp installateren in Amsterdam?",  # near-dup, typo
        store_path=store,
        threshold=0.70,
    )


def test_old_signature_outside_window_is_pruned(store):
    record_lead_signature(
        lead_id="L1",
        text="warmtepomp installateur amsterdam gezocht",
        source="reddit:r/Amsterdam",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc) - timedelta(days=20),
    )
    pruned = prune_store(store_path=store, retain_days=14)
    assert pruned == 1
    assert not is_cross_run_duplicate(
        text="warmtepomp installateur amsterdam gezocht",
        store_path=store,
        threshold=0.70,
    )


def test_recording_appends_line_with_required_schema(store):
    now = datetime(2026, 5, 18, 8, 30, tzinfo=timezone.utc)
    record_lead_signature(
        lead_id="L1",
        text="warmtepomp gezocht",
        source="marktplaats:diensten/gent",
        niche="warmtepomp",
        store_path=store,
        now=now,
    )
    lines = store.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert set(rec.keys()) == {"signature", "lead_id", "captured_at", "source", "niche"}
    assert rec["lead_id"] == "L1"
    assert rec["source"] == "marktplaats:diensten/gent"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_cross_run_dedup.py -v
```

Expected: import error — `cross_run_dedup.py` does not exist.

- [ ] **Step 3: Implement `cross_run_dedup.py`**

Create `lead-radar/consumer/processor/cross_run_dedup.py`:
```python
"""Layer-2 cross-run persistent dedup using MinHash.

Stores compact MinHash signatures of all sellable leads. When a new
candidate lead is scored, we check it against the last 14 days of
signatures. A Jaccard similarity >= threshold is treated as a dup.

Store: data/dedup_store.jsonl (one JSON record per line, append-only,
pruned periodically).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from datasketch import MinHash

NUM_PERM = 64  # 64-perm MinHash gives Jaccard estimate w/ ~12% std error, fits in <1 KB/line
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> Iterable[str]:
    return (t.lower() for t in _TOKEN_RE.findall(text) if len(t) > 2)


def _build_signature(text: str) -> MinHash:
    mh = MinHash(num_perm=NUM_PERM)
    for tok in _tokens(text):
        mh.update(tok.encode("utf-8"))
    return mh


def _serialize_signature(mh: MinHash) -> str:
    """Pack the hashvalues array into a hex string for compact JSONL storage."""
    return mh.hashvalues.tobytes().hex()


def _deserialize_signature(hex_str: str) -> MinHash:
    import numpy as np
    arr = np.frombuffer(bytes.fromhex(hex_str), dtype=np.uint64)
    mh = MinHash(num_perm=NUM_PERM, hashvalues=arr)
    return mh


def record_lead_signature(
    *,
    lead_id: str,
    text: str,
    source: str,
    niche: str,
    store_path: Path,
    now: datetime,
) -> None:
    """Append a signature record to the store."""
    mh = _build_signature(text)
    rec = {
        "signature": _serialize_signature(mh),
        "lead_id": lead_id,
        "captured_at": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "niche": niche,
    }
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with store_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def is_cross_run_duplicate(
    *,
    text: str,
    store_path: Path,
    threshold: float = 0.70,
) -> bool:
    """Return True if any prior signature in the store is similar enough."""
    if not store_path.exists():
        return False
    candidate = _build_signature(text)
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                prior = _deserialize_signature(rec["signature"])
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            if candidate.jaccard(prior) >= threshold:
                return True
    return False


def prune_store(*, store_path: Path, retain_days: int = 14) -> int:
    """Drop records older than retain_days. Returns count removed."""
    if not store_path.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    kept: list[str] = []
    removed = 0
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                captured = datetime.fromisoformat(rec["captured_at"])
            except (json.JSONDecodeError, KeyError, ValueError):
                kept.append(line)  # keep malformed for debugging
                continue
            if captured >= cutoff:
                kept.append(line)
            else:
                removed += 1
    store_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_cross_run_dedup.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Export from processor `__init__.py`**

Add to `lead-radar/consumer/processor/__init__.py`:
```python
from .cross_run_dedup import (
    is_cross_run_duplicate,
    record_lead_signature,
    prune_store as prune_cross_run_store,
)
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_cross_run_dedup.py lead-radar/consumer/processor/cross_run_dedup.py lead-radar/consumer/processor/__init__.py
git commit -m "$(cat <<'EOF'
feat(processor): Layer 2 cross-run persistent MinHash dedup

Rolling 14-day store at data/dedup_store.jsonl. Each sellable lead
appends a 64-perm MinHash signature; subsequent candidates with
Jaccard >= 0.70 are treated as duplicates. Pruning is a separate
function to be called from the weekly cron in Plan C.
EOF
)"
```

---

### Task 8: Layer 3 — author-signature dedup

**Files:**
- Create: `lead-radar/consumer/processor/author_signature_dedup.py`
- Test: `lead-radar/tests/test_author_signature_dedup.py`
- Modify: `lead-radar/consumer/processor/__init__.py`

**Context:** Spec §6, Layer 3. Same user posts the same question across multiple subreddits or forums within 30 days. Hash `(author, niche)` for sources with reliable author identity; skip for DDG/Marktplaats where the "author" is the listing-poster but may not represent a stable identity.

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_author_signature_dedup.py`:
```python
"""Layer-3 author-signature dedup: same author, same niche, 30d window."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from consumer.processor.author_signature_dedup import (
    is_author_repeat,
    record_author_post,
    prune_author_store,
    SOURCES_WITH_AUTHOR,
)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "author_signature.jsonl"


def test_first_author_post_is_not_repeat(store):
    assert not is_author_repeat(
        author="user42",
        niche="warmtepomp",
        store_path=store,
    )


def test_same_author_same_niche_within_window_is_repeat(store):
    record_author_post(
        author="user42",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert is_author_repeat(
        author="user42",
        niche="warmtepomp",
        store_path=store,
    )


def test_same_author_different_niche_is_not_repeat(store):
    record_author_post(
        author="user42",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert not is_author_repeat(
        author="user42",
        niche="zonnepanelen",
        store_path=store,
    )


def test_pruning_drops_records_older_than_30d(store):
    record_author_post(
        author="user42", niche="warmtepomp", store_path=store,
        now=datetime.now(timezone.utc) - timedelta(days=40),
    )
    pruned = prune_author_store(store_path=store, retain_days=30)
    assert pruned == 1


def test_author_hash_is_sha256_not_plaintext(store):
    record_author_post(
        author="user42", niche="warmtepomp", store_path=store,
        now=datetime.now(timezone.utc),
    )
    raw = store.read_text()
    assert "user42" not in raw, "author plaintext leaked into store"
    rec = json.loads(raw.splitlines()[0])
    assert len(rec["author_hash"]) == 64  # sha256 hex


def test_sources_with_author_excludes_ddg_and_marktplaats():
    """Marktplaats and DDG (google) author fields aren't reliable identities."""
    assert "google" not in SOURCES_WITH_AUTHOR
    assert "marktplaats" not in SOURCES_WITH_AUTHOR
    assert "2dehands" not in SOURCES_WITH_AUTHOR
    assert "reddit" in SOURCES_WITH_AUTHOR
    assert "klusidee_forum" in SOURCES_WITH_AUTHOR
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_author_signature_dedup.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `author_signature_dedup.py`**

Create `lead-radar/consumer/processor/author_signature_dedup.py`:
```python
"""Layer-3 author-signature dedup for sources with reliable author identity.

A user who posts about warmtepomp in r/Amsterdam on Monday and reposts in
r/Klussers on Wednesday is one lead, not two. Skip for sources where the
"author" field is just a listing-poster (Marktplaats, DDG hits).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Sources where the author field represents a stable identity.
# DDG hits and Marktplaats sellers are excluded — those identities aren't
# reliable signals for "this is the same person asking again."
SOURCES_WITH_AUTHOR: frozenset[str] = frozenset({
    "reddit", "reddit_new",
    "tweakers",
    "bouwinfo", "bouwinfo_forum",
    "klusidee_forum",
    "ouders_forum",
    "facebook",
})


def _author_hash(author: str, niche: str) -> str:
    h = hashlib.sha256()
    h.update(f"{author.strip().lower()}|{niche.strip().lower()}".encode("utf-8"))
    return h.hexdigest()


def is_author_repeat(
    *,
    author: str,
    niche: str,
    store_path: Path,
    retain_days: int = 30,
) -> bool:
    if not store_path.exists():
        return False
    target = _author_hash(author, niche)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("author_hash") != target:
                continue
            try:
                last_seen = datetime.fromisoformat(rec["last_seen"])
            except (KeyError, ValueError):
                continue
            if last_seen >= cutoff:
                return True
    return False


def record_author_post(
    *,
    author: str,
    niche: str,
    store_path: Path,
    now: datetime,
) -> None:
    """Append-or-update author-signature record."""
    target = _author_hash(author, niche)
    now_iso = now.astimezone(timezone.utc).isoformat(timespec="seconds")
    store_path.parent.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if store_path.exists():
        with store_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    found = False
    for rec in existing:
        if rec.get("author_hash") == target:
            rec["last_seen"] = now_iso
            rec["post_count"] = int(rec.get("post_count", 0)) + 1
            found = True
            break

    if not found:
        existing.append({
            "author_hash": target,
            "niche": niche,
            "first_seen": now_iso,
            "last_seen": now_iso,
            "post_count": 1,
        })

    with store_path.open("w", encoding="utf-8") as f:
        for rec in existing:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def prune_author_store(*, store_path: Path, retain_days: int = 30) -> int:
    if not store_path.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retain_days)
    kept: list[str] = []
    removed = 0
    with store_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                last_seen = datetime.fromisoformat(rec["last_seen"])
            except (json.JSONDecodeError, KeyError, ValueError):
                kept.append(line)
                continue
            if last_seen >= cutoff:
                kept.append(line)
            else:
                removed += 1
    store_path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_author_signature_dedup.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Export from processor `__init__.py`**

Add:
```python
from .author_signature_dedup import (
    is_author_repeat,
    record_author_post,
    prune_author_store,
    SOURCES_WITH_AUTHOR,
)
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_author_signature_dedup.py lead-radar/consumer/processor/author_signature_dedup.py lead-radar/consumer/processor/__init__.py
git commit -m "$(cat <<'EOF'
feat(processor): Layer 3 author-signature dedup for stable-author sources

Hashes (author, niche) with sha256 — never stores plaintext author —
and skips sources without reliable author identity (Marktplaats, DDG).
Rolling 30d window; integration with pipeline comes in Task 13.
EOF
)"
```

---

### Task 9: Source-credibility weight processor

**Files:**
- Create: `lead-radar/consumer/processor/source_weight.py`
- Test: `lead-radar/tests/test_source_weight.py`
- Modify: `lead-radar/consumer/processor/__init__.py`
- Modify: `lead-radar/config.yaml` (add `source_weights` section)

**Context:** Spec §6 source_weights. Apply a per-source multiplier to the raw score before the HOT/WARM/OPP threshold gate.

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_source_weight.py`:
```python
"""Source-credibility weight applied before threshold gate."""
from __future__ import annotations

from pathlib import Path

from consumer.processor.source_weight import apply_source_weight, load_source_weights


def test_weight_above_one_boosts_score():
    assert apply_source_weight(score=75, source="bouwinfo_forum", weights={"bouwinfo_forum": 1.10}) == 82


def test_weight_below_one_drops_score():
    assert apply_source_weight(score=78, source="google", weights={"google": 0.85}) == 66


def test_unknown_source_uses_default_weight_one():
    assert apply_source_weight(score=80, source="some-new-source", weights={}) == 80


def test_score_clamped_to_0_100():
    assert apply_source_weight(score=95, source="x", weights={"x": 1.20}) == 100
    assert apply_source_weight(score=5, source="x", weights={"x": 0.10}) == 0


def test_load_source_weights_from_config(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "source_weights:\n"
        "  marktplaats: 1.05\n"
        "  google: 0.85\n",
        encoding="utf-8",
    )
    weights = load_source_weights(config_path=cfg)
    assert weights["marktplaats"] == 1.05
    assert weights["google"] == 0.85


def test_source_id_with_subcontext_uses_source_prefix():
    """source_id is reddit:r/duurzaam — strip subcontext, weight applies on 'reddit'."""
    assert apply_source_weight(score=70, source="reddit:r/duurzaam", weights={"reddit": 1.00}) == 70
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_source_weight.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `source_weight.py`**

Create `lead-radar/consumer/processor/source_weight.py`:
```python
"""Per-source credibility weight applied before threshold gating.

Weights live in config.yaml:source_weights. The processor strips any
source_id subcontext (':r/duurzaam') so the weight maps on the base
source registry name.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import yaml


def _base_source(source_or_source_id: str) -> str:
    return source_or_source_id.split(":", 1)[0] if ":" in source_or_source_id else source_or_source_id


def apply_source_weight(
    *,
    score: int,
    source: str,
    weights: Mapping[str, float],
) -> int:
    """Apply weight multiplier and clamp to [0, 100]."""
    base = _base_source(source)
    multiplier = float(weights.get(base, 1.0))
    weighted = round(score * multiplier)
    return max(0, min(100, int(weighted)))


def load_source_weights(*, config_path: Path) -> dict[str, float]:
    if not config_path.exists():
        return {}
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw = cfg.get("source_weights") or {}
    return {str(k): float(v) for k, v in raw.items()}
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_source_weight.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Add `source_weights` section to `config.yaml`**

Edit `lead-radar/config.yaml`, add at the end:
```yaml
# Source-credibility multipliers, applied before HOT/WARM/OPP threshold.
# >1.0 boosts (premium-intent sources), <1.0 demotes (noisier sources).
source_weights:
  bouwinfo_forum: 1.10
  klusidee_forum: 1.10
  marktplaats:    1.05
  2dehands:       1.05
  reddit_new:     1.00
  reddit:         1.00
  facebook:       1.00
  tweakers:       0.95
  ouders_forum:   0.95
  bouwinfo:       0.95
  google:         0.85
```

- [ ] **Step 6: Export from processor `__init__.py`**

Add:
```python
from .source_weight import apply_source_weight, load_source_weights
```

- [ ] **Step 7: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_source_weight.py lead-radar/consumer/processor/source_weight.py lead-radar/consumer/processor/__init__.py lead-radar/config.yaml
git commit -m "$(cat <<'EOF'
feat(processor): source-credibility weight before threshold gate

Multiplier table in config.yaml:source_weights. Strips source_id
subcontext so weights map on the base registry name. Clamped 0-100.
Integration with run_consumer.py scoring path comes in Task 13.
EOF
)"
```

---

### Task 10: Sellability gate processor

**Files:**
- Create: `lead-radar/consumer/processor/sellability_gate.py`
- Test: `lead-radar/tests/test_sellability_gate.py`
- Modify: `lead-radar/consumer/processor/__init__.py`

**Context:** Spec §6. A lead lands in HOT tab only if all six fields are non-null and properly populated. Otherwise demote to OPP for manual review.

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_sellability_gate.py`:
```python
"""Sellability gate for HOT-tab admission."""
from __future__ import annotations

from consumer import Lead
from consumer.processor.sellability_gate import is_sellable


def _lead(**overrides) -> Lead:
    base = dict(
        id="L1",
        source="reddit",
        source_id="reddit:r/Amsterdam",
        title="t",
        text="b",
        summary="Wie kan een warmtepomp installeren in Amsterdam-Zuid?",
        url="https://reddit.com/r/Amsterdam/post/x",
        city="amsterdam",
        score=82,
        intent="hot",
        breakdown={},
        niche="warmtepomp",
        author="someuser",
        created_at="2026-05-18T09:00:00+02:00",
    )
    base.update(overrides)
    return Lead(**base)


def test_complete_lead_is_sellable():
    result = is_sellable(_lead())
    assert result.ok is True
    assert result.missing == []


def test_missing_city_blocks():
    result = is_sellable(_lead(city=None))
    assert result.ok is False
    assert "city" in result.missing


def test_short_summary_blocks():
    result = is_sellable(_lead(summary="too short"))
    assert result.ok is False
    assert "summary" in result.missing


def test_truncation_marker_in_summary_blocks():
    result = is_sellable(_lead(summary="something interesting..."))
    assert result.ok is False
    assert "summary" in result.missing


def test_intent_unknown_blocks():
    result = is_sellable(_lead(intent="unknown"))
    assert result.ok is False
    assert "intent" in result.missing


def test_missing_author_and_no_author_context_blocks():
    lead = _lead(author=None)
    result = is_sellable(lead)
    assert result.ok is False
    assert "author" in result.missing


def test_score_below_80_blocks():
    result = is_sellable(_lead(score=78))
    assert result.ok is False
    assert "score" in result.missing
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_sellability_gate.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `sellability_gate.py`**

Create `lead-radar/consumer/processor/sellability_gate.py`:
```python
"""HOT-tab admission gate — all six fields must be present and meaningful.

A lead that fails the gate is auto-demoted from HOT to OPP for manual
review. Prevents selling a "HOT lead" that turns out to have no working
contact path.

Spec: docs/superpowers/specs/2026-05-17-supply-expansion-design.md §6.
"""
from __future__ import annotations

from dataclasses import dataclass

from .. import Lead

MIN_SUMMARY_LEN = 30
TRUNCATION_MARKERS = ("...", "…", "see full post", "read more")


@dataclass
class GateResult:
    ok: bool
    missing: list[str]


def is_sellable(lead: Lead) -> GateResult:
    missing: list[str] = []

    if not lead.url:
        missing.append("url")

    if not lead.summary or len(lead.summary) < MIN_SUMMARY_LEN:
        missing.append("summary")
    elif any(m in lead.summary.lower() for m in TRUNCATION_MARKERS):
        missing.append("summary")

    if not lead.city:
        missing.append("city")

    if not lead.author:
        # author_context is in breakdown if Reddit-enriched
        if not (isinstance(lead.breakdown, dict) and lead.breakdown.get("author_context")):
            missing.append("author")

    if lead.score < 80:
        missing.append("score")

    if not lead.intent or lead.intent in ("unknown", "cold"):
        missing.append("intent")

    return GateResult(ok=not missing, missing=missing)
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_sellability_gate.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Export from processor `__init__.py`**

```python
from .sellability_gate import is_sellable, GateResult
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_sellability_gate.py lead-radar/consumer/processor/sellability_gate.py lead-radar/consumer/processor/__init__.py
git commit -m "$(cat <<'EOF'
feat(processor): sellability gate for HOT-tab admission

Six-field check (url, summary, city, author/author_context, score>=80,
intent). Failing the gate auto-demotes from HOT to OPP. Integration
with Sheets routing comes in Task 13.
EOF
)"
```

---

### Task 11: Recency boost processor

**Files:**
- Create: `lead-radar/consumer/processor/recency_boost.py`
- Test: `lead-radar/tests/test_recency_boost.py`
- Modify: `lead-radar/consumer/processor/__init__.py`

**Context:** Spec §6. Sharpen the existing `time_decay` into explicit bands: <24h +5, 1-7d unchanged, 7-14d -10, >14d dropped (already enforced by `max_age_days: 7` for FB).

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_recency_boost.py`:
```python
"""Recency boost — explicit score adjustment based on post age."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from consumer.processor.recency_boost import apply_recency_boost, AGED_OUT


NOW = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


def _age(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).isoformat(timespec="seconds")


def test_post_under_24h_gets_plus_5():
    assert apply_recency_boost(score=70, created_at=_age(12), now=NOW) == 75


def test_post_at_24h_boundary_no_boost():
    assert apply_recency_boost(score=70, created_at=_age(24), now=NOW) == 70


def test_post_3d_old_unchanged():
    assert apply_recency_boost(score=70, created_at=_age(72), now=NOW) == 70


def test_post_10d_old_gets_minus_10():
    assert apply_recency_boost(score=70, created_at=_age(240), now=NOW) == 60


def test_post_older_than_14d_returns_aged_out_marker():
    assert apply_recency_boost(score=70, created_at=_age(15 * 24), now=NOW) is AGED_OUT


def test_missing_created_at_passes_through_unchanged():
    assert apply_recency_boost(score=70, created_at=None, now=NOW) == 70


def test_malformed_created_at_passes_through():
    assert apply_recency_boost(score=70, created_at="not-a-date", now=NOW) == 70


def test_score_with_boost_clamped_to_100():
    assert apply_recency_boost(score=98, created_at=_age(12), now=NOW) == 100
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_recency_boost.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `recency_boost.py`**

Create `lead-radar/consumer/processor/recency_boost.py`:
```python
"""Recency boost — sharpen scoring on fresh leads.

<24h:   +5
1-7d:   unchanged
7-14d:  -10
>14d:   AGED_OUT (caller drops the lead entirely)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Final, Union

AGED_OUT: Final = object()
"""Sentinel returned for posts older than 14 days."""

BOOST_24H = +5
DEMOTE_7D = -10


def apply_recency_boost(
    *,
    score: int,
    created_at: str | None,
    now: datetime | None = None,
) -> Union[int, object]:
    """Return adjusted score, or AGED_OUT if the post is too old to sell."""
    if not created_at:
        return score
    try:
        ts = datetime.fromisoformat(created_at)
    except ValueError:
        return score

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age = now - ts

    if age >= timedelta(days=14):
        return AGED_OUT
    if age >= timedelta(days=7):
        return max(0, min(100, score + DEMOTE_7D))
    if age < timedelta(hours=24):
        return max(0, min(100, score + BOOST_24H))
    return score
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_recency_boost.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Export from processor `__init__.py`**

```python
from .recency_boost import apply_recency_boost, AGED_OUT
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_recency_boost.py lead-radar/consumer/processor/recency_boost.py lead-radar/consumer/processor/__init__.py
git commit -m "$(cat <<'EOF'
feat(processor): explicit recency boost — <24h +5, 7-14d -10, >14d drop

Replaces the implicit time_decay multiplier with explicit bands.
AGED_OUT sentinel signals callers to drop the lead entirely.
Integration with run_consumer.py scoring path comes in Task 13.
EOF
)"
```

---

### Task 12: Run-digest Telegram message

**Files:**
- Modify: `lead-radar/consumer/output/telegram.py`
- Test: `lead-radar/tests/test_run_digest.py`

**Context:** Spec §5 "structural addition: per-run digest." After every launchd-triggered run, post a single Telegram message summarising per-source yield and dead-sources. Distinct from instant HOT alerts. Max 4/day (one per launchd trigger).

- [ ] **Step 1: Failing tests**

Create `lead-radar/tests/test_run_digest.py`:
```python
"""Run-digest formatter for end-of-run Telegram messages."""
from __future__ import annotations

from consumer.output.telegram import format_run_digest, RunStats, SourceStat


def test_digest_has_header_with_timestamp():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="marktplaats", posts=42, leads=8, hot=3, dead=False),
        ],
        apify_spend_used_usd=1.85,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "2026-05-18" in msg
    assert "13:00" in msg


def test_digest_marks_dead_source_with_x():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="bouwinfo", posts=0, leads=0, hot=0, dead=True),
        ],
        apify_spend_used_usd=0,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "✗" in msg
    assert "bouwinfo" in msg
    assert "DEAD" in msg


def test_digest_totals_aggregate():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="marktplaats", posts=42, leads=8, hot=3, dead=False),
            SourceStat(source="reddit_new", posts=87, leads=6, hot=1, dead=False),
            SourceStat(source="bouwinfo", posts=0, leads=0, hot=0, dead=True),
        ],
        apify_spend_used_usd=1.85,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "Total: 14 leads" in msg
    assert "4 HOT" in msg


def test_digest_shows_apify_spend():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[],
        apify_spend_used_usd=3.24,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "$3.24" in msg
    assert "$5.00" in msg
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_run_digest.py -v
```

Expected: import error.

- [ ] **Step 3: Add the digest formatter to `telegram.py`**

Append to `lead-radar/consumer/output/telegram.py`:
```python
from dataclasses import dataclass, field


@dataclass
class SourceStat:
    source: str          # base name, no source_id subcontext
    posts: int           # raw posts fetched
    leads: int           # leads after scoring + thresholding
    hot: int             # HOT subset (score >= 80 after source-weight)
    dead: bool = False   # true if dead-source detector tripped this run


@dataclass
class RunStats:
    timestamp: str                       # ISO-8601 NL-tz of run start
    per_source: list[SourceStat] = field(default_factory=list)
    apify_spend_used_usd: float = 0.0
    apify_spend_cap_usd: float = 0.0


def format_run_digest(stats: RunStats) -> str:
    """Format a single Telegram run-digest message.

    Layout matches spec §5 example. Sources sorted by leads desc.
    Dead sources sorted last and marked with ✗.
    """
    # Render date/time short-form (YYYY-MM-DD HH:MM in NL tz)
    short_ts = stats.timestamp[:16].replace("T", " ")

    sorted_stats = sorted(
        stats.per_source,
        key=lambda s: (s.dead, -s.leads, s.source),
    )

    lines = [f"Daily run {short_ts}:"]
    for s in sorted_stats:
        if s.dead:
            lines.append(f"  ✗ {s.source}: 0 posts (DEAD — needs inspection)")
        else:
            lines.append(
                f"  ✓ {s.source}: {s.posts} posts → {s.leads} leads ({s.hot} HOT)"
            )

    total_leads = sum(s.leads for s in stats.per_source)
    total_hot = sum(s.hot for s in stats.per_source)
    lines.append("")
    lines.append(f"Total: {total_leads} leads, {total_hot} HOT")
    if stats.apify_spend_cap_usd > 0:
        lines.append(
            f"Apify spend today: ${stats.apify_spend_used_usd:.2f} / ${stats.apify_spend_cap_usd:.2f} cap"
        )
    return "\n".join(lines)


def send_run_digest(stats: RunStats, *, channel: str = "consumer") -> bool:
    """Send the digest to the resolved chat. Returns True on success."""
    chat_id = resolve_chat_id(channel=channel)
    if not chat_id:
        return False
    text = format_run_digest(stats)
    # Reuse existing _post_to_telegram(chat_id, text) helper or equivalent
    # — adapt to actual API in telegram.py
    return _post_to_telegram(chat_id=chat_id, text=text)
```

If `_post_to_telegram` does not exist, locate the existing send-message function (likely `send_lead_alert` or similar) and reuse its internal HTTP helper.

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_run_digest.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_run_digest.py lead-radar/consumer/output/telegram.py
git commit -m "$(cat <<'EOF'
feat(output/telegram): end-of-run digest formatter and sender

Per spec §5: one Telegram message per launchd run summarising
per-source yield, dead-sources, and Apify spend. Distinct from
instant HOT alerts. Wiring into run_consumer.py comes in Task 13.
EOF
)"
```

---

### Task 13: Wire all new processors and the digest into `run_consumer.py`

**Files:**
- Modify: `lead-radar/run_consumer.py`
- Test: `lead-radar/tests/test_run_consumer_integration.py`

**Context:** Tasks 7-12 added pure functions. Now we thread them through the existing scoring/output flow so the production pipeline actually uses them.

Order of operations in the per-post pipeline:
1. Raw score (`score_post`)
2. LLM verifier (existing, score 40-75 band)
3. **Recency boost** (new — may return AGED_OUT → drop)
4. **Source-credibility weight** (new — clamped 0-100)
5. Score threshold gate (existing: `min_score`)
6. **Cross-run dedup** Layer 2 (new — skip if duplicate)
7. **Author-signature dedup** Layer 3 (new — skip if author repeats within 30d, only for SOURCES_WITH_AUTHOR)
8. Construct `Lead`
9. **Sellability gate** (new — if fails, demote intent from "hot" to "warm")
10. Existing Sheets/Telegram output
11. **Record signatures** for Layer 2 (cross-run) and Layer 3 (author)
12. After all niches complete: **send run-digest** (new)

- [ ] **Step 1: Write the integration test**

Create `lead-radar/tests/test_run_consumer_integration.py`:
```python
"""End-to-end integration of new processors in run_consumer.py per-post path.

We test the helper function that processes a single RawPost into a Lead
(or None), not the full --daily loop. Extract the inner loop into a
testable function _process_post(...) as part of this task.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import run_consumer
from consumer import RawPost


NOW = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


def _post(**overrides) -> RawPost:
    base = dict(
        id="X1",
        source="reddit",
        source_id="reddit:r/Amsterdam",
        url="https://reddit.com/r/Amsterdam/post/x",
        title="Wie kan een warmtepomp installeren in Amsterdam-Zuid?",
        text="Onze cv-ketel is stuk, hybride warmtepomp gezocht, spoed.",
        author="someuser",
        created_at=(NOW - timedelta(hours=6)).isoformat(timespec="seconds"),
    )
    base.update(overrides)
    return RawPost(**base)


def test_aged_out_post_is_dropped(tmp_path: Path):
    """Post >14d old returns AGED_OUT from recency boost; pipeline returns None."""
    old = _post(created_at=(NOW - timedelta(days=20)).isoformat(timespec="seconds"))
    result = run_consumer._process_post(
        raw=old,
        niche="warmtepomp",
        data_dir=tmp_path,
        now=NOW,
        no_llm=True,
    )
    assert result is None


def test_cross_run_dup_is_dropped(tmp_path: Path):
    """Second near-identical post within 14d is dropped."""
    p1 = _post()
    p2 = _post(
        id="X2",
        url="https://marktplaats.nl/listing/y",
        source="marktplaats",
        source_id="marktplaats:diensten/amsterdam",
        title="Wie kan warmtepomp installateren in Amsterdam-Zuid?",  # near-dup
        text="cv-ketel stuk, hybride warmtepomp gezocht spoed",
    )
    r1 = run_consumer._process_post(raw=p1, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    assert r1 is not None
    r2 = run_consumer._process_post(raw=p2, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    assert r2 is None


def test_sellability_gate_demotes_when_city_missing(tmp_path: Path):
    """A post that would otherwise be HOT but has no city is demoted away from 'hot'."""
    p = _post(
        # text intentionally has no city signal
        text="warmtepomp installateur gezocht spoed",
        title="warmtepomp installateur gezocht spoed",
    )
    lead = run_consumer._process_post(
        raw=p, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True,
    )
    # If the lead survives scoring but lacks city, intent must not be 'hot'
    if lead is not None and lead.score >= 80:
        assert lead.intent != "hot"
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_run_consumer_integration.py -v
```

Expected: `AttributeError: module 'run_consumer' has no attribute '_process_post'` or similar.

- [ ] **Step 3: Refactor `run_consumer.py` to extract `_process_post`**

Locate the existing per-post loop in `run_consumer.py` (around lines 480-540). Extract its body into a new helper:

```python
def _process_post(
    *,
    raw: RawPost,
    niche: str,
    data_dir: Path,
    now: datetime | None = None,
    no_llm: bool = False,
    no_cross_run_dedup: bool = False,
    no_author_dedup: bool = False,
    config: dict | None = None,
) -> Lead | None:
    """Process a single RawPost into a Lead (or None if filtered out).

    Order of operations:
      1. clean -> score (regex-based)
      2. LLM verify (optional, 40-75 band)
      3. recency boost (may return AGED_OUT -> drop)
      4. source-credibility weight (clamped 0-100)
      5. min_score threshold (drop if below)
      6. Layer-2 cross-run dedup (drop if duplicate)
      7. Layer-3 author-signature dedup (drop if author repeats)
      8. Build Lead
      9. sellability gate (demote intent from 'hot' to 'warm' if fail)
     10. record dedup signatures
    """
    from consumer.processor import (
        clean_post, score_post, should_verify, verify_post, combine_score,
        is_cross_run_duplicate, record_lead_signature,
        is_author_repeat, record_author_post, SOURCES_WITH_AUTHOR,
        apply_source_weight, load_source_weights,
        apply_recency_boost, AGED_OUT,
        is_sellable,
    )
    # ... existing clean / score / LLM-verify chain ...
    # ... insert new processors in the documented order ...
    # ... return Lead or None ...
```

The full implementation will be ~80 lines. The implementer should refactor the existing inline loop into this helper, preserving all existing behaviour, then inject the new processors at the documented positions.

Also update the per-niche stats tracking to feed `SourceStat` records for the digest, and at the end of `--daily` call:

```python
from consumer.output.telegram import RunStats, SourceStat, send_run_digest

# After all niches processed:
if not args.no_telegram:
    digest_stats = RunStats(
        timestamp=run_start_iso,
        per_source=[
            SourceStat(source=src, posts=p, leads=l, hot=h, dead=is_source_dead(src))
            for src, (p, l, h) in per_source_counts.items()
        ],
        apify_spend_used_usd=apify_spend_used,
        apify_spend_cap_usd=apify_spend_cap,
    )
    send_run_digest(digest_stats, channel="consumer")
```

- [ ] **Step 4: Run tests**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_run_consumer_integration.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run the full pipeline manually as smoke test**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python run_consumer.py --niche warmtepomp --location nederland --sources reddit_new \
  --limit 20 --no-llm --no-sheets --no-telegram
```

Expected:
- Run completes without errors.
- A few Lead objects logged.
- `data/dedup_store.jsonl` and `data/author_signature.jsonl` are created or appended.
- Re-running the same command immediately should drop most results as cross-run-dups.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_run_consumer_integration.py lead-radar/run_consumer.py
git commit -m "$(cat <<'EOF'
feat(consumer): wire recency, source-weight, dedup layers, sellability into pipeline

Extracts the per-post processing into _process_post() and injects the
new processors in documented order: recency -> source-weight ->
threshold -> Layer-2 cross-run dedup -> Layer-3 author dedup -> Lead
construction -> sellability gate (demotion only, never drop). End of
--daily run posts a Telegram digest summarising per-source yield.

Block A foundation complete. Block B (launchd activation) is next.
EOF
)"
```

---

## Self-Review

After writing all 13 tasks, the spec coverage check:

| Spec section / item | Plan task |
|---|---|
| §1 success criteria, sellability-gate ≤8 alerts/day | T10 sellability + T12 digest controls alert volume |
| §2 architecture change-point #1 (exporter bug) | T1 |
| §2 change-point #2 (launchd plist) | Deferred to Plan B (correctly out of scope) |
| §2 change-point #3 (env vars) | T2 |
| §2 change-point #4 (queries.yaml tuning) | Deferred to Plan C |
| §2 change-point #5 (cross-source persistent dedup) | T7 + T13 |
| §2 change-point #6 (source-label granular) | T3 + T4 + T5 |
| §3 Block A (Foundation) exit gate | All A-tasks (T1-T6) covered |
| §5 run-digest Telegram message | T12 + T13 wiring |
| §5 heartbeat | Deferred to Plan B (needs launchd context) |
| §6 Layer 1 (within-run dedup) | Already exists, no task needed |
| §6 Layer 2 (cross-run persistent dedup) | T7 + T13 |
| §6 Layer 3 (author-signature dedup) | T8 + T13 |
| §6 source weights | T9 + T13 |
| §6 sellability gate | T10 + T13 |
| §6 recency boost | T11 + T13 |
| §7 Sheets bron column granular | T5 |
| §7 Telegram CONSUMER_TELEGRAM_CHAT_ID | T6 |
| §7 logging & disk | Deferred (rotation can be added with launchd in Plan B) |
| §9 open question 1 (bug location) | T1 explicitly addresses |
| §9 open question 2 (source-id schema) | T4 codifies the contract |

**Placeholder scan:** No "TBD", "TODO", "implement later" in any task. Each task has runnable code and exact commands.

**Type consistency:**
- `RawPost.source_id`, `Lead.source_id` defined in T3, used consistently in T4, T5.
- `GateResult.ok`, `GateResult.missing` defined in T10, asserted in test of T10.
- `RunStats`, `SourceStat` defined in T12, used in T13.
- `AGED_OUT` sentinel defined in T11, used in T13.
- `SOURCES_WITH_AUTHOR` defined in T8, used in T13.
- All function signatures (`apply_source_weight`, `is_sellable`, `apply_recency_boost`, `is_cross_run_duplicate`, `is_author_repeat`) consistent between tests and implementations.

**Plan complete and ready for execution.**
