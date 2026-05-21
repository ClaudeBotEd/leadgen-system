# Consumer Pipeline Operational Procedures

Use these procedures when validating the consumer pipeline after config changes, parser repairs, or before bootstrapping launchd.

## Single-niche smoke test

Minimal dry-run for warmtepomp × 4 sources with pre-flight dedup verification.

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

### Expected signals

- **Exit code:** 0
- **CSV output:** `data/leads/consumer/leads_warmtepomp_<date>.csv` exists with ≥1 lead
- **Dedup-store growth:** `data/leads/consumer/dedup_store.jsonl` and `data/leads/consumer/author_signature.jsonl` increase by 2+ lines
- **Source attribution:** At least 2 of the 4 requested sources contribute leads

### Cross-run dedup validation

Run the same command a second time immediately (same day). Second run should produce 0 leads if Layer 2 dedup is working:

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

Expected: lead count is significantly lower (usually 0 if run within minutes of the first run).

If run 2 returns the same lead count as run 1: Layer 2 fuzzy MinHash dedup is not recording post entries. Check `data/leads/consumer/dedup_store.jsonl` line count growth and investigate `is_cross_run_duplicate` integration in `_process_post`.

## Full-daily smoke test

Complete run across all configured niches × sources × locations.

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
scripts/run_consumer_only.sh
```

Expected behavior:
- Exit code 0
- Runtime: 5–20 minutes depending on niche × source × location combinations
- Output CSVs in `data/leads/consumer/leads_<niche>_<date>.csv`
- Sheets HOT/ALL/OPP tabs receive new rows (if `--sheets` not disabled)
- Telegram digest message arrives (one per run, if `--telegram` not disabled)

### Partial run (single niche, all sources)

If you need to test one niche without touching Sheets or Telegram:

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py \
  --niche <niche> \
  --location <location> \
  --no-sheets --no-telegram \
  --min-score 30
```

Example for isolating a parser issue:

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py \
  --niche warmtepomp \
  --location nederland \
  --sources bouwinfo_forum \
  --no-sheets --no-telegram \
  --min-score 30 2>&1 | tee /tmp/debug_bouwinfo.log
```

Then inspect `/tmp/debug_bouwinfo.log` for source-specific errors or filtering details.

## Troubleshooting

### No leads produced (0 from raw posts)

Check filtering breakdown in final summary line. If `low=<high>`, increase `--min-score` temporarily or verify intent-scoring logic. If `hardblock=<high>`, a parser or URL filter is too aggressive.

### Only 1 source contributing leads

Yellow flag. Logs should show fetch counts per source before filtering. Compare raw fetch count to final lead count. If a source shows 0 fetches, its API configuration or URL may be broken. If a source shows N fetches but 0 final leads, its parser may be too strict.

Example: if marktplaats shows `-> 10 posts` but contributes 0 leads:

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
source .env
.venv/bin/python run_consumer.py \
  --niche warmtepomp \
  --location nederland \
  --sources marktplaats \
  --limit 3 \
  --no-sheets --no-telegram \
  --min-score 0 2>&1 | head -100
```

Lower min-score to 0 and limit to 3 to see raw parsing output quickly.

### Dedup stores not growing

Layer 2 dedup recording is not being called. Verify that `_process_post` calls `is_cross_run_duplicate` and that the MinHash memoization is persisting writes to `data/leads/consumer/dedup_store.jsonl` and (for Reddit/forum) `author_signature.jsonl`.

Check that the `.jsonl` files are writable:

```bash
ls -la "/Users/claudebot/Lead generator/lead-radar/data/leads/consumer"/*.jsonl
```

If files don't exist, first run should create them. If they exist but don't grow, check Python exception logs in the console output for file I/O or JSON serialization errors.

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

After editing, run a single-niche dry-run (see "Consumer pipeline — manual dry-run" section above) to confirm queries don't break parsers.

## Bootstrapped launchd agents

Three agents are loaded after Plan B Task 7 bootstrap:

| Agent | Trigger | Wrapper | Logs |
|---|---|---|---|
| `com.leadradar.fbapify` | 08:00 / 12:00 / 17:00 / 21:00 | `scripts/run_apify_pipeline.sh` | `logs/apify.log` |
| `com.leadradar.consumer` | 08:30 / 13:00 / 18:00 | `scripts/run_consumer_only.sh` | `logs/consumer.log` |
| `com.leadradar.heartbeat` | 00:15 / 04:15 / 10:15 / 14:15 / 19:15 / 22:30 | `scripts/heartbeat.sh` | `logs/heartbeat.log` |

### Verify agents are loaded

```bash
launchctl list | grep leadradar
```

Expected: 3 lines, recent exit code 0 (or a single non-zero from a transient failure that the next trigger will clear).

### Manually trigger an agent (smoke test)

```bash
launchctl start com.leadradar.consumer
launchctl start com.leadradar.heartbeat
```

`launchctl start` is fire-and-forget. Tail the corresponding log to watch progress.

### Reload an agent after editing its plist

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
- `.env` file moved or deleted → wrapper exits 2 with `FATAL: .env missing`.
- `LEAD_RADAR_SPREADSHEET_ID` removed from `.env` → consumer wrapper exits 2 with the fail-fast env-check.
- venv python deleted → wrapper exits 2 with `FATAL: venv python not found`.
- venv missing a dependency (e.g. `datasketch` after Plan A landed) → wrapper exits with `ModuleNotFoundError`. Fix: `.venv/bin/pip install -r requirements.txt`.
- macOS sleep extended over a scheduled trigger → launchd auto-fires after wake.
- Telegram-vars missing in `.env` → heartbeat reports OK/ALERT to stdout but cannot send Telegram (exits 1 silently). Add `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` to `.env` to enable alerts.
