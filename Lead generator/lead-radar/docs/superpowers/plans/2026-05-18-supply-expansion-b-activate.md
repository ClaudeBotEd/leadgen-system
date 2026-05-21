# Lead Radar Supply Expansion — Plan B: Activate

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the 10 dormant consumer-pipeline scrapers from "code-complete" into "production on launchd 3× daily for 7 days", with parser-health audits, a heartbeat agent that alerts when the pipeline goes silent, and a verified end-to-end smoke run before scheduling.

**Architecture:** Two new launchd agents (`com.leadradar.consumer.plist` at 08:30 / 13:00 / 18:00; `com.leadradar.heartbeat.plist` every 4h), one new wrapper script (`scripts/run_consumer_only.sh`), and per-source parser-health fixtures to catch silent breakage before launchd takes over. No code-level architecture changes to the consumer-pipeline itself — Plan A already shipped all the processors. Plan B is operational.

**Tech Stack:** macOS launchd, bash 3.2+ (system default), Python 3.13 + pytest, Telegram Bot API via `curl`. No new dependencies.

**Spec:** `lead-radar/docs/superpowers/specs/2026-05-17-supply-expansion-design.md` (sections 3 Block B, 5, 7-A, 7-D, 7-F).

**Out of scope (deferred to Plan C):**
- FB Marketplace activation (Plan C task C4)
- queries.yaml zero-yield pruning (Plan C task C2)
- Weekly per-source-per-niche volume report + `SOURCE STATS` Sheets tab (Plan C task C1)
- Telegram threshold tuning (Plan C task C3)
- Dead-source threshold tuning per source (Plan C task C5)

**Carried over from Plan A review (4 yellow followups, none ship-blocking):**
- Track raw-post counters per base source (not just leads) for accurate digest signal
- Per-skip-reason attribution in `_process_post` (currently all `None` → `skipped_low`)
- Legacy `--enrich-authors` ordering quirk (penalty applied after gates)
- Hardcoded `0.70` Jaccard threshold in cross-run dedup (should follow `args.dedup_threshold`)

These are addressed inline where they become visible during Plan B validation (Task 5 and Task 6 will surface attribution gaps; the parser-health audit in Task 1 verifies no new sources broke).

---

## File Structure

**New files:**
- `lead-radar/tests/test_parser_health.py` — fixture-driven parser-health tests per source
- `lead-radar/tests/fixtures/parser_health/<source>/*.html|json` — captured HTML/JSON fixtures for offline parser validation
- `lead-radar/scripts/run_consumer_only.sh` — shell wrapper that launches `run_consumer.py --daily` excluding the FB-Apify path
- `lead-radar/scripts/heartbeat.sh` — checks log mtime, sends Telegram alert if too stale
- `lead-radar/scripts/reset_dead_source.py` — CLI to clear the dead-source flag for a source
- `lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist` — launchd agent at 08:30 / 13:00 / 18:00
- `lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist` — launchd agent every 4h

**Files modified:**
- `lead-radar/OPERATOR_SETUP.md` — add consumer-pipeline section + heartbeat docs + runbooks
- `lead-radar/.env.example` — document the `--sources` exclusion gotcha if discovered in Task 5

---

## Task 1: Parser-health audit harness with per-source fixtures

**Files:**
- Create: `lead-radar/tests/test_parser_health.py`
- Create: `lead-radar/tests/fixtures/parser_health/<source>/sample.{html,json}` (10 files, one per non-FB source)

**Context:** All 10 non-FB sources have parsers that were last validated when written (varying dates from May 14-16). HTML on Marktplaats / 2dehands / Bouwinfo / Klusidee may have drifted. Before we put them on launchd 3×/day, each parser must demonstrate it can still extract a `RawPost` from a recent live sample. The audit runs offline using captured fixtures so CI can re-run it.

Sources to audit (10): `reddit`, `reddit_new`, `tweakers`, `bouwinfo`, `bouwinfo_forum`, `klusidee_forum`, `ouders_forum`, `google`, `marktplaats`, `2dehands` (FB Apify is already production-validated, skip).

- [ ] **Step 1: Write the parameterized parser-health test**

Create `lead-radar/tests/test_parser_health.py`:
```python
"""Per-source parser-health audit.

Each source ships with a captured live-sample fixture in
tests/fixtures/parser_health/<source>/. The parser must extract at
least one RawPost with the required fields populated.

If a fixture is missing, the test fails with instructions for capturing
one. See the URL pattern in each source module's top-of-file docstring.

Run subset:
    python -m pytest tests/test_parser_health.py -v
    python -m pytest tests/test_parser_health.py -v -k reddit
"""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.sources import REGISTRY

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parser_health"

SOURCES_TO_AUDIT: list[str] = [
    "reddit", "reddit_new", "tweakers",
    "bouwinfo", "bouwinfo_forum",
    "klusidee_forum", "ouders_forum",
    "google", "marktplaats", "2dehands",
]


@pytest.mark.parametrize("source_name", SOURCES_TO_AUDIT)
def test_source_registered(source_name):
    """Sanity — source must still be in REGISTRY for Plan B to activate it."""
    assert source_name in REGISTRY, f"Source {source_name!r} missing from REGISTRY"


@pytest.mark.parametrize("source_name", SOURCES_TO_AUDIT)
def test_parser_health_fixture_exists(source_name):
    """Each audited source must have a captured fixture for offline validation."""
    source_dir = FIXTURES_DIR / source_name
    if not source_dir.exists() or not any(source_dir.iterdir()):
        pytest.fail(
            f"Missing parser-health fixture for {source_name!r}.\n"
            f"Capture one with:\n"
            f"    mkdir -p {source_dir}\n"
            f"    # then save a recent HTML/JSON sample from the source's "
            f"live URL to {source_dir}/sample.html (or .json)\n"
            f"    # See module docstring in consumer/sources/{source_name}.py "
            f"for the URL pattern."
        )


def _load_fixture(source_name: str, ext: str = "html") -> str:
    path = FIXTURES_DIR / source_name / f"sample.{ext}"
    if not path.exists():
        pytest.skip(f"Fixture not captured: {path}")
    return path.read_text(encoding="utf-8")


def test_reddit_parser_extracts_post():
    """Reddit JSON listing parses to at least one RawPost with required fields."""
    from consumer.sources import reddit as src
    import json
    data = json.loads(_load_fixture("reddit", "json"))
    posts = src._parse_listing(data)
    assert posts, "Reddit fixture must contain at least one listing"
    p = posts[0]
    assert p.source == "reddit"
    assert p.source_id.startswith("reddit:r/")
    assert p.url.startswith("https://")
    assert p.id


def test_reddit_new_parser_extracts_post():
    """Reddit /new JSON parses via shared helper, source overridden to reddit_new.

    reddit_new wraps reddit's _parse_listing then rewrites source/source_id.
    Test the wrap behavior by invoking through a public entry point if available;
    otherwise skip with a TODO note for module refactor.
    """
    from consumer.sources import reddit_new as src
    if not hasattr(src, "fetch_from_json"):
        pytest.skip(
            "reddit_new needs a fetch_from_json(data, sub=...) helper for "
            "offline testing; see Task 1 step 4 implementation notes."
        )
    import json
    data = json.loads(_load_fixture("reddit_new", "json"))
    posts = src.fetch_from_json(data, sub="DIYNL")
    assert posts
    p = posts[0]
    assert p.source == "reddit_new"
    assert p.source_id == "reddit_new:r/DIYNL"


def test_tweakers_parser_extracts_post():
    from consumer.sources import tweakers as src
    if not hasattr(src, "_parse_search"):
        pytest.skip("tweakers needs a _parse_search(html) helper")
    html = _load_fixture("tweakers", "html")
    posts = src._parse_search(html)
    assert posts, "Tweakers fixture must yield >=1 post"
    assert all(p.source == "tweakers" for p in posts)
    assert all(p.source_id.startswith("tweakers:") for p in posts)


def test_bouwinfo_parser_extracts_post():
    from consumer.sources import bouwinfo as src
    if not hasattr(src, "_parse_search"):
        pytest.skip("bouwinfo needs a _parse_search(html) helper")
    html = _load_fixture("bouwinfo", "html")
    posts = src._parse_search(html)
    assert posts, "Bouwinfo fixture must yield >=1 post"
    assert all(p.source == "bouwinfo" for p in posts)


def test_bouwinfo_forum_parser_extracts_post():
    from consumer.sources import bouwinfo_forum as src
    if not hasattr(src, "_parse_category_page"):
        pytest.skip("bouwinfo_forum needs a _parse_category_page helper")
    html = _load_fixture("bouwinfo_forum", "html")
    posts = src._parse_category_page(html, subforum_slug="zonnepanelen")
    assert posts, "Bouwinfo-forum fixture must yield >=1 post"
    assert all(p.source == "bouwinfo_forum" for p in posts)
    assert all(p.source_id == "bouwinfo_forum:zonnepanelen" for p in posts)


def test_klusidee_forum_parser_extracts_post():
    from consumer.sources import klusidee_forum as src
    if not hasattr(src, "_parse_subforum"):
        pytest.skip("klusidee_forum needs a _parse_subforum helper")
    html = _load_fixture("klusidee_forum", "html")
    posts = src._parse_subforum(html, subforum_id="cv-ketels-gaskachels-en-geisers.33")
    assert posts, "Klusidee fixture must yield >=1 post"
    assert all(p.source == "klusidee_forum" for p in posts)
    assert all(p.source_id.startswith("klusidee_forum:") for p in posts)


def test_ouders_forum_parser_extracts_post():
    from consumer.sources import ouders_forum as src
    if not hasattr(src, "_parse_subforum_page"):
        pytest.skip("ouders_forum needs a _parse_subforum_page helper")
    html = _load_fixture("ouders_forum", "html")
    posts = src._parse_subforum_page(html, subforum_slug="huis-tuin-en-keuken")
    assert posts, "Ouders forum fixture must yield >=1 post"
    assert all(p.source == "ouders_forum" for p in posts)


def test_google_ddg_parser_extracts_post():
    from consumer.sources import google as src
    if not hasattr(src, "_parse_results"):
        pytest.skip("google needs a _parse_results helper")
    html = _load_fixture("google", "html")
    posts = src._parse_results(html)
    assert posts, "DDG fixture must yield >=1 result"
    assert all(p.source == "google" for p in posts)
    assert all(p.source_id.startswith("google:") for p in posts)


def test_marktplaats_parser_extracts_post():
    from consumer.sources import marktplaats as src
    if not hasattr(src, "_parse_html"):
        pytest.skip("marktplaats needs a _parse_html(html, source_id_prefix, source_name) helper")
    html = _load_fixture("marktplaats", "html")
    posts = src._parse_html(
        html,
        source_id_prefix="marktplaats:diensten/amsterdam",
        source_name="marktplaats",
    )
    assert posts, "Marktplaats fixture must yield >=1 listing"
    assert all(p.source == "marktplaats" for p in posts)
    assert all(p.source_id.startswith("marktplaats:") for p in posts)


def test_tweedehands_parser_extracts_post():
    """2dehands.be (Belgium) uses the same parser as marktplaats with a different source_name."""
    from consumer.sources import marktplaats as src
    if not hasattr(src, "_parse_html"):
        pytest.skip("marktplaats needs a _parse_html helper for 2dehands")
    html = _load_fixture("2dehands", "html")
    posts = src._parse_html(
        html,
        source_id_prefix="2dehands:diensten/antwerpen",
        source_name="2dehands",
    )
    assert posts, "2dehands fixture must yield >=1 listing"
    assert all(p.source == "2dehands" for p in posts)
    assert all(p.source_id.startswith("2dehands:") for p in posts)
```

If a per-source private helper has a different name in the actual module than what's asserted above, ADAPT the test to the actual helper name (or extract a thin wrapper). The contract is: "given a captured fixture, the parser yields >=1 RawPost with matching `source` and `source_id` format". Do not invent helpers — if a module truly has no parse-from-string entry point (e.g. only an HTTP-bound `fetch()`), refactor it to expose one OR mark that single test as `pytest.skip` with the specific reason.

- [ ] **Step 2: Run the test to confirm failures (no fixtures yet)**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_parser_health.py -v
```

Expected: 10 `test_source_registered` PASS, 10 `test_parser_health_fixture_exists` FAIL with helpful capture instructions, 10 per-source `test_*_parser_extracts_post` SKIP (fixture-not-captured) or FAIL (helper missing).

- [ ] **Step 3: Capture one fixture per source from a live sample**

For each source, fetch a real recent page and save it under `tests/fixtures/parser_health/<source>/sample.{html|json}`. Use the URL patterns each module's docstring documents.

Example for Reddit (JSON):
```
mkdir -p "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/reddit"
curl -sS -A "Mozilla/5.0 lead-radar parser-health" \
    "https://www.reddit.com/r/DIYNL/search.json?q=warmtepomp&restrict_sr=on&limit=10" \
    > "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/reddit/sample.json"
```

For Reddit-new (JSON):
```
mkdir -p "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/reddit_new"
curl -sS -A "Mozilla/5.0 lead-radar parser-health" \
    "https://www.reddit.com/r/DIYNL/new.json?limit=10" \
    > "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/reddit_new/sample.json"
```

For Marktplaats (HTML):
```
mkdir -p "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/marktplaats"
curl -sS -A "Mozilla/5.0 lead-radar parser-health" \
    "https://www.marktplaats.nl/q/warmtepomp+installateur+amsterdam/" \
    > "/Users/claudebot/Lead generator/lead-radar/tests/fixtures/parser_health/marktplaats/sample.html"
```

Repeat for the other 7 sources. The URL pattern for each is documented in the source module's top-of-file docstring. If a source has rate-limiting that blocks `curl`, open the URL in a browser and use "Save Page As → Webpage, HTML only".

**Redaction policy:** if any captured fixture contains identifying user content (emails, phone numbers, full names), redact with `sed -i '' 's/<pattern>/[REDACTED]/g' <fixture>` before committing. Public forum titles + body text are fine. Add a `tests/fixtures/parser_health/README.md` documenting the policy.

- [ ] **Step 4: Extract per-source parser helpers where missing**

For any source where the test was forced to SKIP because the parse-from-string helper doesn't exist, refactor the source module to extract one. Example for `reddit_new.py`:

Currently `fetch(query, sub, ...)` does HTTP + parsing inline. Extract:
```python
def fetch_from_json(data: dict, *, sub: str) -> list[RawPost]:
    """Parse a /r/<sub>/new.json response into RawPosts (testable offline)."""
    raw = _reddit_search._parse_listing(data)
    return [
        RawPost(
            id=p.id, source="reddit_new", source_id=f"reddit_new:r/{sub}",
            url=p.url, title=p.title, text=p.text,
            author=p.author, created_at=p.created_at, metadata=p.metadata,
        )
        for p in raw
    ]


def fetch(query, *, limit, location=None, subreddits=None, **kw):
    # ... existing HTTP fetch ...
    data = json.loads(response.text)
    return fetch_from_json(data, sub=current_sub)[:limit]
```

Apply the same pattern to any other source missing a parse-from-string helper. Keep behavior identical — this is a refactor, not a logic change.

- [ ] **Step 5: Run all parser-health tests**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_parser_health.py -v
```

Expected: 30 tests pass (10 registry + 10 fixture-exists + 10 parser-extracts).

If a per-source parser test FAILS (not skips): the parser has drifted vs current HTML and needs repair. The fix lives in the source module. Repair, re-capture the fixture if it was malformed, re-run. Document the repair in the commit message.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_parser_health.py "lead-radar/tests/fixtures/parser_health/"
# Also stage any source-module refactors from step 4:
git add lead-radar/consumer/sources/
git commit -m "$(cat <<'EOF'
test(consumer/sources): parser-health audit with fixtures for 10 sources

Captured live samples per source; offline-runnable test verifies each
parser still yields >=1 RawPost with correct source / source_id format.
Will be CI-runnable and re-runnable when a source's DOM changes.

Extracted parse-from-string helpers for sources that were HTTP-coupled:
  - <list per actual refactors>

Found and repaired parser drift in:
  - <list any sources that needed repair OR note: "no drift detected">

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Consumer-only shell wrapper script

**Files:**
- Create: `lead-radar/scripts/run_consumer_only.sh`

**Context:** The existing `scripts/run_apify_pipeline.sh` calls FB-Apify collect → `run_consumer.py --daily`. The new consumer launchd agent must run only the 10 non-FB sources, so a separate wrapper is needed. Mirrors the existing script's structure: load `.env`, walk to repo root, invoke venv python with `--sources <non-fb>`.

**The `--sources` exclusion question:** verify whether `run_consumer.py --daily` defaults to running all REGISTRY sources or only the FB queue. Read the args block and the `--sources` default value.

- [ ] **Step 0: Verify default --sources behavior**

```
cd "/Users/claudebot/Lead generator/lead-radar"
grep -n -- "--sources\|args.sources\|ALL_SOURCES\|sources_to_run\|NATIONAL_SOURCES" run_consumer.py | head -20
```

Decide based on the default:
- If `--daily` defaults to ALL_SOURCES → consumer wrapper passes `--sources reddit,reddit_new,tweakers,bouwinfo,bouwinfo_forum,klusidee_forum,ouders_forum,google,marktplaats,2dehands` (10 non-FB).
- If `--daily` already excludes facebook → wrapper just calls `--daily`.

If the script supports `--exclude-sources facebook` (cleaner one-line), prefer that.

- [ ] **Step 1: Create the wrapper**

Create `lead-radar/scripts/run_consumer_only.sh`:
```bash
#!/bin/bash
# Lead Radar — consumer-pipeline-only wrapper (no FB Apify).
#
# Launchd entry point: loads .env, runs run_consumer.py --daily restricted
# to the 10 non-FB sources, logs to stdout/stderr (launchd captures via
# StandardOutPath/StandardErrorPath).
#
# Exits 0 on full success, non-zero if pipeline fails. Distinguish from
# scripts/run_apify_pipeline.sh which also drains the FB queue.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "FATAL: $REPO_ROOT/.env missing — needed for Sheets + LLM keys" >&2
  exit 2
fi

# Export every var from .env into the environment for this process.
set -a
# shellcheck disable=SC1091
source .env
set +a

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "FATAL: venv python not found at $VENV_PY" >&2
  exit 2
fi

# Non-FB sources — the FB Apify path runs under its own launchd agent.
NON_FB_SOURCES="reddit,reddit_new,tweakers,bouwinfo,bouwinfo_forum,klusidee_forum,ouders_forum,google,marktplaats,2dehands"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Consumer-only pipeline begin ==="

# Fail-fast env check (added by Plan A Task 2)
"$VENV_PY" run_consumer.py --daily --sources "$NON_FB_SOURCES" --check-env-only

echo "--- Running run_consumer.py --daily --sources ${NON_FB_SOURCES} ---"
"$VENV_PY" run_consumer.py --daily --sources "$NON_FB_SOURCES"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Consumer-only pipeline end (ok) ==="
```

Make it executable:
```bash
chmod +x "/Users/claudebot/Lead generator/lead-radar/scripts/run_consumer_only.sh"
```

- [ ] **Step 2: Smoke-test the wrapper offline**

Run it with `--no-sheets --no-telegram` injected via env (cleaner than editing the script) — or test the underlying python call manually first:

```
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py --daily \
  --sources reddit,marktplaats \
  --no-sheets --no-telegram --no-llm \
  --limit 5
```

Expected: completes without exceptions, prints per-niche summary.

If that passes, run the wrapper directly (will hit live Sheets if creds present):
```
"/Users/claudebot/Lead generator/lead-radar/scripts/run_consumer_only.sh"
```

Expected: completes in 5-20 minutes; produces `data/leads/consumer/leads_*.csv` files; logs lines to stdout (launchd will capture these later); no exceptions in output.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/scripts/run_consumer_only.sh
git commit -m "$(cat <<'EOF'
feat(scripts): consumer-only pipeline wrapper for launchd

Mirrors scripts/run_apify_pipeline.sh structure but restricted to the 10
non-FB sources. Fail-fast env-check (added by Plan A Task 2) runs before
the real pipeline so launchd marks the run as failed if Sheets vars are
missing, instead of silently producing CSV without sync.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Consumer launchd plist

**Files:**
- Create: `lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist`

**Context:** macOS launchd agent that fires the consumer-pipeline wrapper at 08:30, 13:00, 18:00 daily. Placed next to the existing FB plist for consistency.

**Schedule rationale** (per spec §7-A): offset from FB's 08:00 / 12:00 / 17:00 / 21:00 to avoid Apify-cost overlap and spread load. 08:30 catches overnight posts after FB has run. 13:00 catches morning posts. 18:00 catches afternoon posts.

- [ ] **Step 1: Create the plist**

Create `lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!--
  Lead Radar — Consumer-pipeline (non-FB) launchd agent (macOS).

  Roept scripts/run_consumer_only.sh aan, dat:
    1. .env source't (Sheets, LLM, Telegram vars)
    2. Fail-fast env check (Plan A Task 2)
    3. run_consumer.py --daily --sources <10 non-FB> draait

  Schedule: 08:30 / 13:00 / 18:00 lokale tijd (Amsterdam mits Mac op CET).
  Offset 30min van FB Apify (08:00) om Apify-cost overlap te vermijden.
  Launchd schedule een gemiste run zodra de Mac wakker is.

  Installatie:
    cp consumer/sources/facebook/com.leadradar.consumer.plist ~/Library/LaunchAgents/
    launchctl load -w ~/Library/LaunchAgents/com.leadradar.consumer.plist
    launchctl list | grep leadradar     # verify

  Handmatige trigger (smoke-test na installatie):
    launchctl start com.leadradar.consumer
    tail -f "/Users/claudebot/Lead generator/lead-radar/logs/consumer.log"

  Uitschakelen:
    launchctl unload ~/Library/LaunchAgents/com.leadradar.consumer.plist
-->
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.leadradar.consumer</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/claudebot/Lead generator/lead-radar/scripts/run_consumer_only.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/claudebot/Lead generator/lead-radar</string>

  <key>RunAtLoad</key>
  <false/>

  <!-- Schedule: 08:30, 13:00, 18:00 lokale tijd -->
  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key><integer>8</integer>
      <key>Minute</key><integer>30</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>13</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>18</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
  </array>

  <key>StandardOutPath</key>
  <string>/Users/claudebot/Lead generator/lead-radar/logs/consumer.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/claudebot/Lead generator/lead-radar/logs/consumer.err</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
  </dict>
</dict>
</plist>
```

- [ ] **Step 2: Validate the plist with `plutil`**

```
plutil "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist"
```

Expected: `... OK`. If invalid, plutil prints the line number of the syntax error.

- [ ] **Step 3: Dump the plist for visual schedule check**

```
plutil -p "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist"
```

Expected output contains `Label = "com.leadradar.consumer"`, three `StartCalendarInterval` entries with hours 8/13/18 and minutes 30/0/0 respectively, `ProgramArguments` includes the wrapper path.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist
git commit -m "$(cat <<'EOF'
feat(launchd): com.leadradar.consumer.plist — 3x daily consumer pipeline

Triggers scripts/run_consumer_only.sh at 08:30 / 13:00 / 18:00 lokale
tijd. Offset from FB Apify (08:00) to avoid cost overlap. Logs to
lead-radar/logs/consumer.log + consumer.err.

Bootstrap with:
  cp consumer/sources/facebook/com.leadradar.consumer.plist ~/Library/LaunchAgents/
  launchctl load -w ~/Library/LaunchAgents/com.leadradar.consumer.plist

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Heartbeat shell script + launchd plist

**Files:**
- Create: `lead-radar/scripts/heartbeat.sh`
- Create: `lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist`
- Create: `lead-radar/tests/test_heartbeat.py`

**Context:** Per spec §5-C and §7-A: the largest silent-failure mode in a launchd system is when it stops firing and nobody notices. A heartbeat agent runs every 4 hours, checks `lead-radar/logs/consumer.log` and `apify.log` mtimes, and sends a Telegram alert if either has been silent longer than its threshold.

Thresholds:
- FB Apify pipeline (`apify.log`): 4× daily, threshold 30 hours (1.25 × period).
- Consumer pipeline (`consumer.log`): 3× daily, threshold 8 hours (~1.6 × period of 4-5h).

- [ ] **Step 1: Write the heartbeat test harness**

Create `lead-radar/tests/test_heartbeat.py`:
```python
"""Heartbeat: detect silent pipeline failure via log-mtime check.

The heartbeat script is bash, but its core decision logic can be tested
via subprocess. Each test sets up a known mtime on a temp log file and
asserts the script's exit code + stdout indicates alert-or-OK.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT_SH = REPO_ROOT / "scripts" / "heartbeat.sh"


@pytest.fixture
def fake_logs(tmp_path):
    """Create temp log files we can age by setting mtime."""
    apify = tmp_path / "apify.log"
    consumer = tmp_path / "consumer.log"
    apify.write_text("dummy", encoding="utf-8")
    consumer.write_text("dummy", encoding="utf-8")
    return {"apify": apify, "consumer": consumer, "dir": tmp_path}


def _set_mtime_hours_ago(path: Path, hours: float) -> None:
    """Pretend the file was touched hours ago."""
    t = time.time() - hours * 3600
    os.utime(path, (t, t))


def _run_heartbeat(logs_dir: Path, dry_run: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HEARTBEAT_LOGS_DIR"] = str(logs_dir)
    env["HEARTBEAT_DRY_RUN"] = "1" if dry_run else "0"
    env["TELEGRAM_BOT_TOKEN"] = "test-token"
    env["TELEGRAM_CHAT_ID"] = "123"
    return subprocess.run(
        ["/bin/bash", str(HEARTBEAT_SH)],
        env=env, capture_output=True, text=True, timeout=10,
    )


def test_heartbeat_ok_when_both_logs_fresh(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 1)
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert result.returncode == 0, result.stderr
    assert "ALERT" not in result.stdout
    assert "OK" in result.stdout


def test_heartbeat_alerts_when_apify_too_stale(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 36)  # > 30h threshold
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "apify" in result.stdout.lower()


def test_heartbeat_alerts_when_consumer_too_stale(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 1)
    _set_mtime_hours_ago(fake_logs["consumer"], 12)  # > 8h threshold
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "consumer" in result.stdout.lower()


def test_heartbeat_alerts_when_log_missing(fake_logs):
    """A missing log file is treated as a silent failure (alert)."""
    fake_logs["apify"].unlink()
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "apify" in result.stdout.lower()


def test_heartbeat_dry_run_does_not_send_telegram(fake_logs):
    """HEARTBEAT_DRY_RUN=1 must skip the actual curl POST."""
    _set_mtime_hours_ago(fake_logs["apify"], 36)
    result = _run_heartbeat(fake_logs["dir"], dry_run=True)
    assert "DRY_RUN" in result.stdout
    # Should not contain output from a real telegram API call
    assert "https://api.telegram.org" not in result.stderr
```

- [ ] **Step 2: Run to confirm failure (script doesn't exist yet)**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_heartbeat.py -v
```

Expected: 5 tests fail (script not found).

- [ ] **Step 3: Implement `scripts/heartbeat.sh`**

Create `lead-radar/scripts/heartbeat.sh`:
```bash
#!/bin/bash
# Lead Radar — heartbeat: alert when launchd pipelines go silent.
#
# Runs every 4h via com.leadradar.heartbeat.plist. Checks mtime of:
#   - apify.log    (threshold: 30 hours)
#   - consumer.log (threshold: 8 hours)
#
# Missing log or too-old mtime triggers a Telegram alert.
#
# Env overrides (used by tests):
#   HEARTBEAT_LOGS_DIR=/path/to/logs (default: <repo>/logs)
#   HEARTBEAT_DRY_RUN=1              (skip actual curl POST)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOGS_DIR="${HEARTBEAT_LOGS_DIR:-$REPO_ROOT/logs}"
DRY_RUN="${HEARTBEAT_DRY_RUN:-0}"

# Source .env for Telegram credentials, unless they're already in env (test path).
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"
    set +a
  fi
fi

# Threshold per pipeline (hours). bash 3.2 (macOS default) doesn't have
# associative arrays in all installs — use parallel arrays.
NAMES=("apify" "consumer")
THRESHOLDS_H=(30 8)

NOW_EPOCH="$(date +%s)"
ALERTS=()

for i in 0 1; do
  name="${NAMES[$i]}"
  threshold_h="${THRESHOLDS_H[$i]}"
  threshold_s=$(( threshold_h * 3600 ))
  log_path="$LOGS_DIR/${name}.log"

  if [[ ! -f "$log_path" ]]; then
    echo "ALERT: $name log missing at $log_path"
    ALERTS+=("$name: log file missing")
    continue
  fi

  # macOS-compatible mtime in epoch seconds.
  mtime_epoch="$(stat -f %m "$log_path")"
  age_s=$(( NOW_EPOCH - mtime_epoch ))
  age_h=$(( age_s / 3600 ))

  if (( age_s > threshold_s )); then
    echo "ALERT: $name silent for ${age_h}h (threshold ${threshold_h}h)"
    ALERTS+=("$name: silent for ${age_h}h (threshold ${threshold_h}h)")
  else
    echo "OK: $name last activity ${age_h}h ago"
  fi
done

if [[ ${#ALERTS[@]} -eq 0 ]]; then
  echo "OK: all pipelines healthy"
  exit 0
fi

# Build alert message.
hostname_short="$(hostname -s 2>/dev/null || echo "mac")"
msg="🚨 Lead Radar heartbeat — pipeline silent on ${hostname_short}"$'\n\n'
for a in "${ALERTS[@]}"; do
  msg+="  • $a"$'\n'
done
msg+=$'\n'"Logs: $LOGS_DIR"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN: would send Telegram alert:"
  echo "$msg"
  exit 0
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "WARN: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing — cannot send alert" >&2
  exit 1
fi

# Plain text — no parse_mode (avoid MarkdownV2 escape hell, per Plan A fix c95cee2).
curl -sS \
  --max-time 10 \
  -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${msg}" \
  > /dev/null

echo "Heartbeat alert sent to Telegram"
exit 0
```

Make it executable:
```
chmod +x "/Users/claudebot/Lead generator/lead-radar/scripts/heartbeat.sh"
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_heartbeat.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Create the heartbeat plist**

Create `lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<!--
  Lead Radar — heartbeat launchd agent (macOS).

  Roept scripts/heartbeat.sh aan elke 4 uur. Script checkt mtime van
  apify.log + consumer.log; te oud = Telegram alert.

  Installatie:
    cp consumer/sources/facebook/com.leadradar.heartbeat.plist ~/Library/LaunchAgents/
    launchctl load -w ~/Library/LaunchAgents/com.leadradar.heartbeat.plist

  Handmatige trigger:
    launchctl start com.leadradar.heartbeat

  Uitschakelen:
    launchctl unload ~/Library/LaunchAgents/com.leadradar.heartbeat.plist
-->
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.leadradar.heartbeat</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/claudebot/Lead generator/lead-radar/scripts/heartbeat.sh</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/Users/claudebot/Lead generator/lead-radar</string>

  <key>RunAtLoad</key>
  <false/>

  <!-- Every 4 hours, offset from pipeline triggers (08:00/08:30/12:00/13:00/17:00/18:00/21:00). -->
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Hour</key><integer>0</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>4</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>19</integer><key>Minute</key><integer>15</integer></dict>
    <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>30</integer></dict>
  </array>

  <key>StandardOutPath</key>
  <string>/Users/claudebot/Lead generator/lead-radar/logs/heartbeat.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/claudebot/Lead generator/lead-radar/logs/heartbeat.err</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
  </dict>
</dict>
</plist>
```

The schedule is staggered (00:15, 04:15, 10:15, 14:15, 19:15, 22:30) to avoid colliding with pipeline runs (which start at HH:00 or HH:30).

- [ ] **Step 6: Validate the plist**

```
plutil "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist"
plutil -p "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist"
```

Expected: `OK`, dump shows 6 StartCalendarInterval entries.

- [ ] **Step 7: Smoke-test the script manually**

```
cd "/Users/claudebot/Lead generator/lead-radar"
HEARTBEAT_DRY_RUN=1 scripts/heartbeat.sh
```

Expected: lists OK/ALERT for apify and consumer based on current log mtimes. If both pipelines have run recently, both report OK. If consumer.log doesn't exist yet (pre-bootstrap), expect ALERT for consumer — that's the expected pre-bootstrap state.

- [ ] **Step 8: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_heartbeat.py lead-radar/scripts/heartbeat.sh lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist
git commit -m "$(cat <<'EOF'
feat(launchd): heartbeat agent — alerts on silent pipelines every 4h

scripts/heartbeat.sh checks mtime of apify.log (30h threshold, FB runs
4x/day) and consumer.log (8h threshold, consumer runs 3x/day). Sends
plain-text Telegram alert via curl on any threshold breach. Missing
log file = treated as alert (most extreme silent failure).

com.leadradar.heartbeat.plist runs at 6 staggered times across the day,
offset from pipeline schedules to avoid collision.

5 unit tests cover: both fresh (OK), apify stale (ALERT), consumer stale
(ALERT), log missing (ALERT), dry-run skips curl.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Live single-niche dry-run validation

**Files:**
- Modify: `lead-radar/OPERATOR_SETUP.md` (append dry-run section)

**Context:** Before bootstrapping launchd, verify the consumer pipeline produces leads end-to-end for one niche, with Sheets sync disabled. This is a checklist task — verification criteria are explicit.

- [ ] **Step 1: Run single-niche dry-run for warmtepomp**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py \
  --niche warmtepomp \
  --location nederland \
  --sources reddit,reddit_new,marktplaats,bouwinfo_forum \
  --limit 10 \
  --no-sheets --no-telegram \
  --min-score 30
```

The 4 sources chosen cover both location-aware (reddit, marktplaats) and national (reddit_new, bouwinfo_forum) so we shake out any geo-routing bug.

- [ ] **Step 2: Verify expected output signals**

Check the run completed without exceptions:
```
echo $?      # must be 0
```

Check leads were produced:
```
ls -lh "data/leads/consumer/leads_warmtepomp_$(date +%Y-%m-%d).csv"
wc -l "data/leads/consumer/leads_warmtepomp_$(date +%Y-%m-%d).csv"
```

Expected: file exists, >= 2 lines (header + at least 1 lead).

Check dedup stores were populated:
```
ls -lh data/dedup_store.jsonl data/author_signature.jsonl
wc -l data/dedup_store.jsonl data/author_signature.jsonl
```

Expected: both files exist; line counts > 0.

Check per-source attribution in the output:
```
python -c "import csv; rows = list(csv.DictReader(open('data/leads/consumer/leads_warmtepomp_$(date +%Y-%m-%d).csv'))); from collections import Counter; print(Counter(r.get('source','') for r in rows))"
```

Expected: at least 2 of the 4 requested sources appear. If only 1 source appears, that's a yellow flag — investigate which of the others is silently failing (likely parser drift; revisit Task 1).

- [ ] **Step 3: Re-run immediately and verify cross-run dedup catches dups**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
.venv/bin/python run_consumer.py \
  --niche warmtepomp \
  --location nederland \
  --sources reddit,reddit_new,marktplaats,bouwinfo_forum \
  --limit 10 \
  --no-sheets --no-telegram \
  --min-score 30  2>&1 | tee /tmp/rerun.log
```

Inspect the summary table at the end. Compare lead counts vs first run.

Expected: lead count is significantly lower (most are caught by Layer 2 cross-run MinHash dedup). If lead count is UNCHANGED, the dedup is not working — blocker before Task 6.

- [ ] **Step 4: Document the dry-run procedure in OPERATOR_SETUP.md**

Append to `lead-radar/OPERATOR_SETUP.md`:
```markdown

## Consumer pipeline — manual dry-run

Use this when validating after a config change, parser repair, or before
re-bootstrapping launchd.

### Single-niche smoke test

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py \
  --niche warmtepomp \
  --location nederland \
  --sources reddit,reddit_new,marktplaats,bouwinfo_forum \
  --limit 10 \
  --no-sheets --no-telegram \
  --min-score 30
```

Verify:
- Exit code 0
- `data/leads/consumer/leads_warmtepomp_<date>.csv` exists with >=1 lead
- `data/dedup_store.jsonl` and `data/author_signature.jsonl` grew
- At least 2 of the 4 requested sources contributed leads

### Full-daily smoke test

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
scripts/run_consumer_only.sh
```

Verify:
- Exit code 0
- Run takes 5-20 minutes depending on niches × sources × locations
- Sheets HOT/ALL/OPP tabs received new rows
- Telegram digest message arrived (one per run)
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/OPERATOR_SETUP.md
git commit -m "$(cat <<'EOF'
docs(operator): consumer-pipeline manual dry-run procedure

Documents the single-niche and full-daily smoke-test commands plus
expected verification signals (exit code, CSV output, dedup-store
growth, source attribution). Validated against a real run before
bootstrapping launchd.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Live full-daily dry-run with Sheets sync enabled

**Files:** (verification only — logs may optionally be archived)

**Context:** Run the full consumer pipeline end-to-end with Sheets sync ON. Validates Sheets routing, Telegram digest delivery, and source-attribution in the bron column. This is the LAST manual run before launchd takes over.

- [ ] **Step 1: Verify Sheets env vars are present and credentials are readable**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
echo "ID: ${LEAD_RADAR_SPREADSHEET_ID:-MISSING}"
ls -lh "${LEAD_RADAR_GS_CREDENTIALS:-/nonexistent}"
```

Expected: `ID:` followed by a real spreadsheet ID; `ls` shows a JSON credentials file (not a "No such file" error).

If either is missing: stop and fix `.env` per spec §7-E.

- [ ] **Step 2: Run the full consumer pipeline (Sheets ON)**

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
scripts/run_consumer_only.sh 2>&1 | tee "/tmp/consumer-dryrun-$(date +%Y%m%dT%H%M).log"
```

Expected: completes in 5-20 minutes; log ends with `=== ... Consumer-only pipeline end (ok) ===`. The Telegram digest message is sent at the very end of `run_consumer.py --daily` (added by Plan A Task 13).

- [ ] **Step 3: Verify Sheets received the leads with granular bron**

Open the spreadsheet (`LEAD_RADAR_SPREADSHEET_ID`) in a browser. Check:
- HOT, ALL, OPPORTUNITIES tabs exist and have rows.
- The `bron` column shows granular IDs like `reddit:r/duurzaam`, `marktplaats:warmtepomp-installateur/amsterdam`, `klusidee_forum:cv-ketels-gaskachels-en-geisers.33`.
- `status` column for new rows is `new`, `actie` is filled per score.
- No row has empty `score`, `bron`, `link`, or `samenvatting` columns.

If `bron` column shows only base names (`reddit`, `marktplaats`): the Plan A Task 5 fix didn't fully wire in. Open `consumer/output/sheets.py:_build_sheet_row` and verify `lead.source_id or lead.source`.

- [ ] **Step 4: Verify the Telegram digest arrived**

Check the Telegram chat targeted by `CONSUMER_TELEGRAM_CHAT_ID` (falls back to `TELEGRAM_CHAT_ID`). Look for a message starting with `Daily run YYYY-MM-DD HH:MM:` listing per-source results.

Expected format (one message per run):
```
Daily run 2026-05-18 13:00:
  ✓ marktplaats: 42 posts → 8 leads (3 HOT)
  ✓ reddit_new: 87 posts → 6 leads (1 HOT)
  ✗ bouwinfo: 0 posts (DEAD — needs inspection)
  ...

Total: 31 leads, 6 HOT
```

If no message arrived: check `logs/consumer.log` for `send_run_digest` errors. Most likely cause is missing `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` in `.env`.

If MarkdownV2-parse-error in logs: Plan A fix `c95cee2` regressed — restore `parse_mode=None` for digest calls.

- [ ] **Step 5: Verify the run-summary table in stdout**

The `run_consumer.py --daily` mode prints a per-niche summary at the end. Confirm:
- All 5 niches appear (warmtepomp, airco, zonnepanelen, cv, renovatie).
- Lead counts > 0 for at least 3 niches.
- HOT counts > 0 for at least 1 niche.

If 0 leads across the board: a parser is silently broken or env-config is wrong. Stop and investigate before Task 7.

- [ ] **Step 6: (Optional) Archive the verification log**

```bash
mkdir -p "/Users/claudebot/Lead generator/lead-radar/docs/superpowers/runs"
cp "/tmp/consumer-dryrun-"*.log "/Users/claudebot/Lead generator/lead-radar/docs/superpowers/runs/"
cd "/Users/claudebot/Lead generator"
git add "lead-radar/docs/superpowers/runs/"
git commit -m "$(cat <<'EOF'
docs(runs): consumer-pipeline full-daily smoke-test log

Captured stdout from the pre-launchd-bootstrap verification run.
Confirms: all 10 non-FB sources fire, Sheets receives granular bron
labels, Telegram digest delivered, no exceptions.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

(If the log contains any sensitive content, redact before committing or `.gitignore` the runs/ directory and commit a sanitized excerpt.)

---

## Task 7: Bootstrap launchd + verify first auto-run

**Files:** (no new files; operational task)

**Context:** Copy the two new plists into `~/Library/LaunchAgents/`, bootstrap them, and wait for the first scheduled run to verify launchd correctly fires the wrappers.

- [ ] **Step 1: Pre-flight check**

Confirm the existing FB Apify agent is healthy (don't break what works):
```
launchctl list | grep leadradar
tail -20 "/Users/claudebot/Lead generator/lead-radar/logs/apify.log"
```

Expected: `com.leadradar.fbapify` listed, recent log entries present.

- [ ] **Step 2: Install the new plists**

```bash
cp "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist" \
   ~/Library/LaunchAgents/

cp "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.heartbeat.plist" \
   ~/Library/LaunchAgents/

launchctl load -w ~/Library/LaunchAgents/com.leadradar.consumer.plist
launchctl load -w ~/Library/LaunchAgents/com.leadradar.heartbeat.plist

launchctl list | grep leadradar
```

Expected output lists 3 agents:
```
-  0  com.leadradar.fbapify
-  0  com.leadradar.consumer
-  0  com.leadradar.heartbeat
```

The `-  0` means "not currently running, last exit 0" (or never run). If you see a non-zero exit, see Step 4 for log inspection.

- [ ] **Step 3: Trigger a manual run of each new agent**

```bash
launchctl start com.leadradar.consumer
tail -f "/Users/claudebot/Lead generator/lead-radar/logs/consumer.log"
# Wait for "Consumer-only pipeline end (ok)" then Ctrl-C
```

Then:
```bash
launchctl start com.leadradar.heartbeat
tail -20 "/Users/claudebot/Lead generator/lead-radar/logs/heartbeat.log"
```

Expected:
- Consumer agent run completes in 5-20 minutes; final log line ends with "end (ok)".
- Heartbeat agent run completes within seconds; final log line is `OK: all pipelines healthy` (or similar).

- [ ] **Step 4: Inspect for errors**

```bash
tail -50 "/Users/claudebot/Lead generator/lead-radar/logs/consumer.err"
tail -20 "/Users/claudebot/Lead generator/lead-radar/logs/heartbeat.err"
```

Both `.err` files should be empty or contain only benign warnings.

If `consumer.err` has errors:
- Permission denied on .env or credentials → fix file permissions / paths.
- ModuleNotFoundError → venv not picked up; check the plist's `PATH` env var.
- "Sheets sync (X) faalde" → check Sheets credentials path is quoted absolute.

If `heartbeat.err` has errors:
- `stat: cannot stat`: log file path mismatch; check HEARTBEAT_LOGS_DIR.
- curl failures: check TELEGRAM_BOT_TOKEN.

- [ ] **Step 5: Wait for the first natural cron-trigger**

The next scheduled trigger is one of:
- Consumer: 08:30, 13:00, or 18:00 (next in time).
- Heartbeat: next staggered HH:15 / HH:30.

Wait for it (DO NOT manually `launchctl start` — we want to verify cron fires automatically). After the trigger:
```bash
tail -50 "/Users/claudebot/Lead generator/lead-radar/logs/consumer.log"
launchctl list | grep com.leadradar.consumer
```

Expected: log shows a NEW `=== Consumer-only pipeline begin ===` entry at the scheduled time. `launchctl list` shows last exit 0 with PID transition (PID became `-` after run completed).

- [ ] **Step 6: Snapshot launchd state in OPERATOR_SETUP.md**

Append to `lead-radar/OPERATOR_SETUP.md`:
```markdown

## Bootstrapped launchd agents

After Plan B activation, three agents are loaded:

| Agent | Trigger | Wrapper | Logs |
|---|---|---|---|
| `com.leadradar.fbapify` | 08:00 / 12:00 / 17:00 / 21:00 | `scripts/run_apify_pipeline.sh` | `logs/apify.log` |
| `com.leadradar.consumer` | 08:30 / 13:00 / 18:00 | `scripts/run_consumer_only.sh` | `logs/consumer.log` |
| `com.leadradar.heartbeat` | staggered 6×/day | `scripts/heartbeat.sh` | `logs/heartbeat.log` |

### Verify agents are loaded

```bash
launchctl list | grep leadradar
```

Expected: 3 lines, exit code 0.

### Manually trigger an agent

```bash
launchctl start com.leadradar.consumer
launchctl start com.leadradar.heartbeat
```

### Reload an agent after editing a plist

```bash
launchctl unload ~/Library/LaunchAgents/com.leadradar.consumer.plist
cp "/Users/claudebot/Lead generator/lead-radar/consumer/sources/facebook/com.leadradar.consumer.plist" \
   ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.leadradar.consumer.plist
```

### Diagnose silent failures

If a pipeline went silent and heartbeat didn't alert (or heartbeat itself is silent):

```bash
launchctl list | grep leadradar     # check for non-zero exit codes
tail -50 logs/consumer.err          # look for stack traces or env errors
tail -50 logs/heartbeat.err
```

Common causes:
- `.env` file moved or deleted → wrapper exits 2 with "FATAL: .env missing".
- `LEAD_RADAR_SPREADSHEET_ID` removed from `.env` → consumer wrapper exits 2 with the fail-fast env-check.
- venv python deleted → wrapper exits 2 with "venv python not found".
- macOS sleep extended over a scheduled trigger → launchd auto-fires after wake.
```

- [ ] **Step 7: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/OPERATOR_SETUP.md
git commit -m "$(cat <<'EOF'
docs(operator): launchd bootstrap procedure + agent overview

Documents the three loaded launchd agents (fbapify, consumer, heartbeat),
how to verify/trigger/reload them, and common silent-failure diagnostics.
Captured during the live bootstrap of Plan B agents.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Operator runbook — dead-source reset and queries tuning

**Files:**
- Modify: `lead-radar/OPERATOR_SETUP.md` (append two more sections)
- Create: `lead-radar/scripts/reset_dead_source.py`
- Create: `lead-radar/tests/test_reset_dead_source_cli.py`

**Context:** The dead-source detector (`consumer/sources/__init__.py:_source_health`) auto-skips a source after 3 consecutive 0-yield runs. To bring it back, an operator must reset it. Currently there is no CLI for this — operators have been editing internal state by hand. Task 8 adds a one-shot CLI plus documents the reset and queries-tuning runbooks.

- [ ] **Step 1: Failing test**

Create `lead-radar/tests/test_reset_dead_source_cli.py`:
```python
"""CLI for resetting dead-source health counters."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_reset_dead_source_cli_exists_and_runs():
    """The CLI must be invokable and exit 0 for a known source."""
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "reddit"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "reddit" in result.stdout


def test_reset_dead_source_cli_rejects_unknown_source():
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "nonexistent_source_xyz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "unknown" in combined.lower() or "REGISTRY" in combined


def test_reset_dead_source_cli_supports_all():
    """`--all` resets every source in REGISTRY."""
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "reset" in result.stdout.lower()
```

- [ ] **Step 2: Run to confirm failure**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_reset_dead_source_cli.py -v
```

Expected: 3 tests fail (script doesn't exist).

- [ ] **Step 3: Implement the reset CLI**

Create `lead-radar/scripts/reset_dead_source.py`:
```python
#!/usr/bin/env python3
"""Reset the dead-source health counter for one or all sources.

Usage:
    python scripts/reset_dead_source.py reddit
    python scripts/reset_dead_source.py marktplaats bouwinfo_forum
    python scripts/reset_dead_source.py --all

After 3 consecutive 0-yield runs, the dispatcher in consumer/sources/__init__.py
marks a source as dead and skips it for the rest of the current process. This
CLI clears the in-process flag — but since each launchd run starts a fresh
process, this CLI is most useful for manual --daily invocations or when
diagnosing why a source isn't producing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from consumer.sources import REGISTRY, reset_source_health  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", help="Source names to reset")
    parser.add_argument("--all", action="store_true", help="Reset all sources")
    args = parser.parse_args()

    if not args.all and not args.sources:
        parser.error("specify one or more source names, or --all")

    targets = list(REGISTRY) if args.all else args.sources

    unknown = [s for s in targets if s not in REGISTRY]
    if unknown:
        print(
            f"ERROR: unknown source(s): {', '.join(unknown)}\n"
            f"Known sources in REGISTRY: {', '.join(sorted(REGISTRY))}",
            file=sys.stderr,
        )
        return 2

    for source in targets:
        reset_source_health(source)
        print(f"reset: {source}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make it executable:
```
chmod +x "/Users/claudebot/Lead generator/lead-radar/scripts/reset_dead_source.py"
```

- [ ] **Step 4: Run tests to verify**

```
cd "/Users/claudebot/Lead generator/lead-radar"
python -m pytest tests/test_reset_dead_source_cli.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Append runbook sections to OPERATOR_SETUP.md**

```markdown

## Dead-source reset

If the daily digest reports a source as DEAD (e.g. `✗ marktplaats: 0 posts (DEAD)`):

1. **Quick check** — re-run the source manually with verbose logging:
   ```bash
   cd "/Users/claudebot/Lead generator/lead-radar"
   source .env
   .venv/bin/python run_consumer.py \
     --niche warmtepomp --location amsterdam \
     --sources marktplaats --limit 5 \
     --no-sheets --no-telegram --min-score 1
   ```

2. **If the manual run produces 0 posts**, the parser has likely drifted. Re-capture a fresh fixture and re-run the parser-health test:
   ```bash
   curl -sS -A "Mozilla/5.0" "https://www.marktplaats.nl/q/..." \
     > "tests/fixtures/parser_health/marktplaats/sample.html"
   .venv/bin/python -m pytest tests/test_parser_health.py::test_marktplaats_parser_extracts_post -v
   ```
   If the test fails, the parser needs repair.

3. **If the manual run DOES produce posts**, the dead-source flag is stale (likely from a transient network issue). Reset it:
   ```bash
   .venv/bin/python scripts/reset_dead_source.py marktplaats
   ```
   The next launchd-triggered run will re-attempt the source.

## queries.yaml tuning

`consumer/queries.yaml` lists per-niche, per-source search queries. Tuning rules:

- **Never edit the file while a pipeline run is in progress** (`launchctl list | grep com.leadradar.consumer` should show `-` PID).
- **Add city permutations** for location-aware sources (`reddit`, `google`, `marktplaats`, `2dehands`) when a city is heavily represented in your customer base.
- **Remove zero-yield queries** after the weekly report (Plan C) shows them.
- **Don't add more than 50 queries per source per niche** — overcrowds the dispatcher and triggers rate limits.

Schema reminder (see `consumer/queries.yaml` header for the full doc):

```yaml
niches:
  warmtepomp:
    keywords_required: [warmtepomp]
    queries_text:
      - "warmtepomp installateur gezocht"
      - "wie kan warmtepomp installeren {location}"
```

After editing, run a single-niche dry-run (Task 5 procedure) to confirm queries don't break parsers.
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar/tests/test_reset_dead_source_cli.py lead-radar/scripts/reset_dead_source.py lead-radar/OPERATOR_SETUP.md
git commit -m "$(cat <<'EOF'
feat(scripts): reset_dead_source.py CLI + operator runbook for dead sources

scripts/reset_dead_source.py wraps consumer.sources.reset_source_health
with positional source-name args and --all. Validates source names
against REGISTRY before resetting. 3 unit tests cover known source,
unknown source, and --all.

OPERATOR_SETUP.md adds two runbook sections:
- Dead-source diagnosis flow: manual run -> parser health test -> reset
- queries.yaml tuning rules (don't edit during a run, city permutations,
  zero-yield removal, max 50/source/niche)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 7-day observation gate

**Files:**
- Create: `lead-radar/docs/superpowers/runs/2026-05-18-plan-b-observation-checklist.md`

**Context:** Plan B's exit gate is "consumer pipeline runs 3×/day for 7 days; all 11 sources produced >0 leads at least once; Sheets sync 100%". This task is a structured checklist for the observation window. Plan C does not start until this checklist is fully green.

- [ ] **Step 1: Create the observation checklist**

Create `lead-radar/docs/superpowers/runs/2026-05-18-plan-b-observation-checklist.md`:
```markdown
# Plan B observation checklist

**Window:** 7 consecutive days starting from launchd bootstrap (Task 7).
**Goal:** Confirm Plan B's exit-gate criteria before starting Plan C.

## Day-by-day verification

For each day, after the 18:00 consumer run, verify:

### Day 1 (bootstrap day)

- [ ] All 3 scheduled consumer triggers fired (08:30, 13:00, 18:00).
- [ ] FB Apify continues to fire on its own schedule.
- [ ] Heartbeat agent ran at least once and reported `OK`.
- [ ] Telegram digest received for each consumer run.
- [ ] At least 4 of the 10 non-FB sources produced >0 leads.
- [ ] Sheets received at least 1 new row.

### Day 2-6 (steady state)

For each day:
- [ ] 3 consumer runs fired on time.
- [ ] No heartbeat ALERTs received.
- [ ] Digests received and report no DEAD sources.
- [ ] No exceptions in `logs/consumer.err`.
- [ ] At least 5 sources produced leads (cumulative across the day's 3 runs).

### Day 7 (final gate)

- [ ] Tally per-source lead count over the full 7 days from Sheets `bron` column (filter contains each source name).
- [ ] Every one of the 10 non-FB sources produced ≥1 lead during the week.
  - If a source has 0 leads after 7 days, mark it for parser audit (Task 1 procedure).
- [ ] Apify FB also produced ≥1 lead during the week.
- [ ] Cross-source duplicate rate <5% (sample 50 leads, check for near-dupes across `bron` values).
- [ ] Operator burnout check: Telegram alerts per day stayed ≤ 8 average.
- [ ] Total leads/day in Sheets averaged ≥ 25 (goal was 40; 25 is gate-pass).

## Failure modes encountered (fill during observation)

| Day | Source | Failure | Resolution |
|---|---|---|---|
| | | | |

## Exit gate decision

- [ ] All 10 non-FB sources produced ≥1 lead during 7 days
- [ ] No persistent heartbeat ALERTs
- [ ] Sheets sync 100%
- [ ] Operator alerts ≤ 8/day average

If all four are checked, **Plan B exit gate is PASSED**. Start writing Plan C.

If any is failing, **Plan B exit gate is FAILED**. Resolve before starting Plan C:
- Source with 0 leads: Task 1 parser audit + queries.yaml tuning.
- Persistent heartbeat ALERTs: investigate logs; common causes are macOS sleep eating cron triggers, or wrapper script breakage.
- Sheets sync < 100%: check `LEAD_RADAR_GS_CREDENTIALS` rotation; the service account may have lost edit access to the spreadsheet.
- Operator alerts > 8/day: raise `hot_threshold` in `config.yaml` from 80 → 85.
```

- [ ] **Step 2: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add "lead-radar/docs/superpowers/runs/2026-05-18-plan-b-observation-checklist.md"
git commit -m "$(cat <<'EOF'
docs(plan-b): 7-day observation checklist + exit-gate criteria

The observation window starts at launchd bootstrap. Each day requires
the same checks (triggers fired, digests received, sources producing).
Day 7 is the gate: every non-FB source must have produced ≥1 lead,
Sheets sync 100%, operator alerts ≤8/day average.

If gate passes, Plan C (tuning) starts. If not, the checklist's
"Failure modes" table accumulates incidents during the window.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 3: Set a calendar reminder for Day 7**

This is not a git task — operator action only. Set a reminder 7 calendar days from launchd bootstrap to execute the Day 7 verification.

---

## Self-Review

After writing all 9 tasks, spec coverage check:

| Spec section / requirement | Plan B task |
|---|---|
| §3 Block B exit gate: pipeline runs 3×/day for 7 days, all 11 sources fire ≥1× | T7 (bootstrap) + T9 (7-day observation) |
| §3 B1 single-niche dry-run | T5 |
| §3 B2 all-niches manual run | T6 |
| §3 B3 cross-source dedup audit | T5 step 3 + T9 day-7 check |
| §3 B4 per-source parser audit | T1 |
| §3 B5 create com.leadradar.consumer.plist | T3 |
| §3 B6 launchd smoke test | T7 |
| §3 B7 update OPERATOR_SETUP.md | T5 step 4, T7 step 6, T8 step 5 |
| §5 heartbeat agent (deferred from Plan A) | T4 |
| §7-A heartbeat plist every 4h | T4 |
| §7-D log rotation policy | not in this plan — Plan C |
| §7-F OPERATOR_SETUP.md consumer-pipeline section, dead-source reset, queries tuning | T8 |

**Placeholder scan:** No "TBD" / "TODO" / "fill in details" in any task. Every shell command, plist entry, and test has runnable content.

**Type consistency:**
- `HEARTBEAT_LOGS_DIR`, `HEARTBEAT_DRY_RUN` env-var names match between Task 4 test (`test_heartbeat.py`) and script (`heartbeat.sh`).
- `reset_source_health` (existing) function name matches the CLI's import (Task 8).
- `_build_run_stats` helper from Plan A's fix `7b88ea2` is referenced only conceptually here — Plan B does not import or extend it.
- All script paths (`scripts/run_consumer_only.sh`, `scripts/heartbeat.sh`, `scripts/reset_dead_source.py`) consistent between plist `ProgramArguments`, OPERATOR_SETUP.md, and the actual `Create:` file paths.

**Plan complete and ready for execution.**

## Open questions for execution time

These will be resolved during implementation and don't block design approval:

1. **Does `run_consumer.py --daily` default to all sources or just FB queue?** Verify in Task 2 step 0 by reading `args.sources` default. If default is `["facebook"]`, the wrapper's `--sources` flag is essential. If default is `ALL_SOURCES`, the wrapper could equivalently use `--exclude-sources facebook` (cleaner).

2. **Fixture redaction policy for parser-health tests (Task 1):** if a captured HTML/JSON snapshot contains PII (a user's real name, phone number), use `sed` redaction with `[REDACTED]` placeholders before committing. Add a one-line README inside `tests/fixtures/parser_health/` documenting the policy.

3. **Heartbeat schedule overlap with `com.leadradar.fbquota` (00:00 daily):** the heartbeat's 00:15 trigger fires 15 min after the FB quota reset. If they ever collide on a slow Mac, neither breaks (different scripts). No mitigation needed unless heartbeat ever needs to read the quota file.

4. **Should the consumer-pipeline log rotate daily?** Plan B doesn't rotate. After 7 days the log will be ~10-50 MB depending on verbosity. Plan C's weekly task adds a `TimedRotatingFileHandler` configuration. Plan B operator can `> logs/consumer.log` manually if it grows uncomfortable.

5. **Reddit author_enrich (`--enrich-authors`) during launchd runs:** the spec defaults it OFF for performance. Verify the consumer wrapper (Task 2) does NOT pass `--enrich-authors`. If wallclock budget permits later, Plan C can enable it as a tier-2 enhancement.
