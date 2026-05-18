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
