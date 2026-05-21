# Lead Radar — Supply Expansion Design

**Status:** Approved by founder 2026-05-17. Ready for implementation plan.
**Author:** Claude Opus 4.7
**Branch:** `feat/facebook-scraper` (continues here; sub-branch optional per implementation plan)

---

## 0 — Context

The Apify Facebook-groups pipeline went live 2026-05-17 and is producing ~1 HOT + 3 OPP leads per day. The founder's goal for this project is to generate income by selling exclusive intent-leads to NL/BE installer companies at €75 per lead (pilot model on the upcoming `lead-radar-site`).

At ~4 leads per day, the supply is far below what the income model requires to be viable. This sprint expands lead supply by activating dormant infrastructure that has already been built but never wired to production.

**Discovery that reframes the problem:** the `lead-radar/consumer/` package contains 11 source scrapers (FB, Reddit, Reddit-new, Tweakers, Bouwinfo, Bouwinfo-forum, Klusidee-forum, Ouders-forum, Google/DDG, Marktplaats, 2dehands.be). Only the FB Apify path runs in launchd. The other 10 are written, tested, and dormant.

The strategy is not "build new scrapers." It is "activate + fix + tune what exists, plus one strategic addition (FB Marketplace activation)."

---

## 1 — Strategic intent

Move Lead Radar from a single-source pipeline (FB Apify only) to a full multi-source production pipeline. Outcome: enough lead volume to credibly launch `lead-radar-site` with a "look what comes in" proof element and enough inventory to onboard the first 10 paying installers.

### Out of scope this sprint

- Sales/outreach to installers (separate sprint)
- DE / BE-FR geographic expansion (separate sprint, gated on €1k MRR)
- Subscription-model switch (separate sprint)
- New scraper code for any source not already in `consumer/sources/`

### Success criteria (measured over 14 days post-deploy)

| Metric | Baseline | Goal | Stretch |
|---|---|---|---|
| Leads/day (HOT+WARM+OPP) | ~4 | ≥40 | ≥80 |
| HOT leads/week (score ≥80 after source-weight) | ~7 | ≥25 | ≥50 |
| Active sources of 11 | 1 | 11 | 11 |
| Sheets sync success rate | ~50% | 100% | 100% |
| Exporter errors per run | 1-3 | 0 | 0 |
| Cross-source duplicate rate | unknown | <5% | <2% |
| Telegram alerts/day | 1-2 | ≤8 | ≤6 |
| Monthly infra cost | €90 | ≤€350 | ≤€350 |

### Definition of done

1. `python run_consumer.py --daily` runs via launchd at 08:30 / 13:00 / 18:00 daily.
2. Output reaches CSV, JSON, and Google Sheets without errors.
3. Dead-source detection produces per-run digest alerts via Telegram.
4. A per-source-per-niche weekly volume report runs every Monday.
5. All 11 sources have had at least one >0-yield run within the first 7 production days.
6. FB Marketplace queries are activated within the Apify pipeline.

---

## 2 — Architecture

### Existing data flow (no fundamental change)

```
11 sources (consumer/sources/*)
  ├── facebook (Apify)
  ├── reddit / reddit_new
  ├── tweakers
  ├── bouwinfo / bouwinfo_forum
  ├── klusidee_forum
  ├── ouders_forum
  ├── google (DuckDuckGo)
  ├── marktplaats
  └── 2dehands

  → RawPost(url, title, text, author, niche, location)

processor/
  → clean → score(0-100) → LLM-verify(40-75 band, Haiku, cached)
    ├── hardblock (aggregators, OEM, energy companies)
    ├── fuzzy_dedup (MinHash, Jaccard ≥ 0.70, within-run)
    └── author_enrich (Reddit-only)

  → Lead(id, source, niche, score, intent, city, ...)

output/
  → CSV + JSON  (data/leads/consumer/leads_<niche>_<date>.{csv,json})
  → Google Sheets (HOT ≥80 / ALL ≥70 / OPPORTUNITIES 60-69)
  → Telegram (HOT instant + run digest 4×/day + weekly report)
```

### Production-ready elements (no rebuild)

- Source registry with dead-source detector (`consumer/sources/__init__.py:_source_health`)
- Hardblock filter for aggregators (Werkspot/Solvari/Bobex), OEM vendors, energy retailers (`config.yaml:filtering.blacklist_domains`)
- Fuzzy dedup with MinHash for within-run cross-source duplicate detection
- LLM verifier (Claude Haiku) for score-band 40-75 with disk cache (`.cache/llm_verifier/`)
- Idempotent Sheets sync with workflow status (`new → contacted → replied → qualified → sold`) — user fields untouched on re-sync
- NL-timezone-correct filenames and cell stamps

### Six change-points

| # | Change | Where | Why |
|---|---|---|---|
| 1 | Fix `'lead/0.85'` int-parse bug | `consumer/output/exporter.py` or upstream in `Lead.to_dict()` | Output errors block all downstream sync |
| 2 | Add launchd plist for consumer | `consumer/sources/facebook/` style → new `com.leadradar.consumer.plist` | Pipeline currently runs only manually |
| 3 | Verify env vars in consumer context | `.env` + plist `EnvironmentVariables` | FB-pipeline gotcha (zshrc not sourced, paths must be quoted) applies here too |
| 4 | Query tuning per niche | `consumer/queries.yaml` | Maximize volume; remove zero-yield queries |
| 5 | Cross-source dedup expanded from per-run to persistent rolling 14d | `consumer/processor/fuzzy_dedup.py` + new `data/dedup_store.jsonl` | Same person posting across sources within a week becomes 1 lead, not 3 |
| 6 | Source-label granularity in Sheets | `sheets.py` + each source module | `"reddit:r/duurzaam"` instead of `"reddit"` → per-source yield measurable |

### Two architecture decisions

**A. Cadence.** Consumer pipeline runs **3×/day** (08:30 / 13:00 / 18:00). FB Apify stays 1×/day (cost-throttled by daily-spend cap). Rationale: 3×/day quadruples fresh-catch range on free HTML sources at near-zero marginal cost.

**B. Storage.** Keep current CSV/JSON + Sheets 3-tab layout. No new database. Sufficient for 1k+ leads/month, and Sheets is already the operator CRM frontend.

---

## 3 — Phased rollout

Three sequential blocks, each with a hard exit-gate. Within a block, parallel work is allowed.

### Block A — Foundation (7-9h dev)

**Exit gate:** consumer-pipeline runs cleanly for one niche manually, leads land in Sheets HOT/ALL/OPP tabs without errors, source-label is granular.

| ID | Task | Estimate | Sequential? |
|---|---|---|---|
| A1 | Reproduce `'lead/0.85'` int-parse bug, locate in `Lead.to_dict()` or `breakdown` path, fix + test | 2-3h | Yes (blocker) |
| A2 | Verify `LEAD_RADAR_SPREADSHEET_ID` + `LEAD_RADAR_GS_CREDENTIALS` work in consumer CLI context | 1h | After A1 |
| A3 | Source-label granularity in Sheets `bron` column: `"reddit:r/duurzaam"`, `"marktplaats:diensten/gent"`. Small change in `sheets.py` + each source module passes a `source_id` | 3-4h | After A1, parallel with A2 |
| A4 | Telegram bot smoke-test for consumer-pipeline (may want separate `CONSUMER_TELEGRAM_CHAT_ID`, fallback to existing) | 30min | Parallel |

### Block B — Activate (13-15h dev + 1 week observation)

**Exit gate:** `com.leadradar.consumer.plist` runs 3×/day for 7 days. All 11 sources have produced >0 leads at least once. Sheets receives leads without duplicates or errors.

| ID | Task | Estimate | Sequential? |
|---|---|---|---|
| B1 | Single-niche dry-run: `python run_consumer.py --niche warmtepomp --sources <all>` — validate Sheets, no output errors | 1h | First |
| B2 | All-niches manual `--daily` run, validate every (niche × source) combo produces output | 2h | After B1 |
| B3 | Cross-source dedup audit on B2 results, tune `fuzzy_threshold` if needed | 2-3h | After B2 |
| B4 | Audit per-source parser health: 11 sources × ~5min = check HTML parsers still match current site DOM, especially marktplaats / 2dehands / bouwinfo / klusidee (external sites may have drifted) | 4-5h | Parallel with A complete |
| B5 | Create `com.leadradar.consumer.plist`, schedule 08:30 / 13:00 / 18:00 | 2h | After B2 |
| B6 | Launchd smoke test (`launchctl unload && load`), validate one real cron trigger, check `consumer.log` | 1h | After B5 |
| B7 | Update `OPERATOR_SETUP.md` with consumer-pipeline section (env vars, dead-source reset, queries tuning) | 1h | After B6 |

### Block C — Tune (14-18h dev, spread 1-2 weeks)

**Begins only after Block B has run 7 days** — otherwise we tune on too little data.

**Exit gate:** per-source-per-niche volume report shows where leads come from, zero-yield queries pruned, Telegram alerts manageable (≤8/day), Marketplace queries activated.

| ID | Task | Estimate | Trigger |
|---|---|---|---|
| C1 | Per-source-per-niche weekly volume report (Python script + `SOURCE STATS` Sheets tab) | 3-4h | After 7 prod days |
| C2 | `queries.yaml` audit: zero-yield queries removed, strong queries broadened (city permutations, synonyms) | 2-3h | After C1 |
| C3 | Telegram threshold tuning (HOT 80→85 if too noisy; switch to daily-digest if needed) | 1h | During week-1 prod |
| C4 | Activate FB Marketplace queries in `apify_groups.py` pipeline — config exists, code path missing | 4-5h | After B6 |
| C5 | `dead_threshold` tuning per source (Marktplaats can tolerate 5 consecutive 0-yields, Reddit stricter) | 1h | After C1 |
| C6 | Optional: parallel-runner if serial wall-clock > 30min | 3-4h | Only if needed |

### Volume evolution

| Milestone | Expected leads/day |
|---|---|
| End of Block A | 0 (no volume change) |
| End of Block B | 25-56 (all sources active, unoptimized) |
| End of Block C | 50-100+ (Marketplace added, queries pruned, weights applied) |

**Total: ~35-42h dev across ~4 weeks wall-clock.**

---

## 4 — Per-source decisions

| # | Source | Decision | Expected yield/day | Tuning note |
|---|---|---|---|---|
| 1 | facebook (Apify) | Keep + extend with Marketplace (C4) | 1-3 → 3-8 | FB Pages stays off (vendor broadcast, low intent) |
| 2 | reddit (search) | Activate | 3-6 | Location-aware. Queries.yaml has 20+ subs. Add `r/Klussers`, `r/Offertes`, `r/DIYNL` if missing |
| 3 | reddit_new (feed) | Activate | 2-4 | High-intent subs (Klussers/Offertes/DIYNL). Skips keyword filter — catches leads missing exact term |
| 4 | tweakers | Activate | 1-2 | NL tech-savvy. Strong for warmtepomp + zonnepanelen. Premium quality, low volume |
| 5 | bouwinfo | Activate | 1-3 | BE national, no city routing |
| 6 | bouwinfo_forum | Activate | 2-4 | BE forum, high intent |
| 7 | klusidee_forum | Activate | 3-6 | XenForo NL DIY. Per-niche subforum mapping in queries.yaml. Strongest non-FB NL source for intent |
| 8 | ouders_forum | Activate | 1-2 | Low volume, high intent (families, homeowners with budget). Community moderation = low spam |
| 9 | google (DDG) | Activate with cap | 3-8 | Location-aware. `max_results=30/query` cap. Otherwise explodes with low-relevance hits |
| 10 | marktplaats | Activate | 5-12 | NL "Diensten en Vakmensen" — highest intent density of all sources. City permutations matter |
| 11 | 2dehands (BE) | Activate | 3-6 | BE-equivalent. Covers Flanders primarily |

**Expected aggregate at Block B end:** 25-56 leads/day (unoptimized).
**Expected after Block C:** 50-100+ leads/day.

### Deliberate deprioritizations

- **FB Pages:** stays off. Vendor broadcast content, low signal-ratio doesn't justify Apify cost.
- **Reddit author_enrich:** stays optional (`--no-author-enrich` flag). Default on during dry-run; can turn off if latency degrades at 3×/day cadence.

### Niche coverage matrix

Every niche has ≥6 strong sources after activation. No coverage gap.

|  | warmtepomp | airco | zonnepanelen | cv | renovatie |
|---|---|---|---|---|---|
| facebook | ✓ | ✓ | ✓ | (via warmtepomp) | ✓ |
| reddit + reddit_new | ✓ | ✓ | ✓ | ✓ | ✓ |
| tweakers | ✓ | ✓ | ✓ | weak | weak |
| bouwinfo / bouwinfo_forum | ✓ | ✓ | ✓ | ✓ | ✓ |
| klusidee_forum | weak | ✓ | ✓ | ✓ | ✓ |
| ouders_forum | ✓ | ✓ | ✓ | ✓ | weak |
| google (DDG) | ✓ | ✓ | ✓ | ✓ | ✓ |
| marktplaats | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2dehands | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 5 — Failure-mode policy

Four categories. Each failure has detection, reaction, and alert decision.

### A — Source-level failures

| Failure | Detection | Reaction | Alert |
|---|---|---|---|
| HTML parser breaks (DOM drift) | Dead-source detector (3× consecutive 0-yield) | Skip rest of run; mark dead; no retry until operator resets | Yes — daily digest shows `"<source> DEAD"` |
| Rate-limit (429) | `PoliteSession` retry layer | Exponential backoff, max 3 retries, then skip | No (normal) |
| Site outage (5xx) | HTTP failure | Skip source this run, not mark dead | No (transient) |
| Login wall appears (public→auth) | Parser returns 0 / HTML without posts | Dead-source kicks in | Yes (same as parser break) |
| Captcha challenge | Captcha regex markers in HTML | Skip + mark dead | Yes — likely structural |

### B — Output-path failures

| Failure | Detection | Reaction | Alert |
|---|---|---|---|
| Sheets auth expired | gspread exception | Retry 1×, then CSV-only fallback | Yes — critical |
| Sheets rate-limit | gspread retry-after | Wait-and-retry up to 3× | No |
| CSV/JSON write fail | OSError | Log error, continue run | Yes |
| Telegram bot down | requests timeout | Log + skip, non-critical | No |
| LLM verifier timeout | 12s timeout (built-in) | Score without verifier for this post | No |

### C — Scheduling failures

| Failure | Detection | Reaction | Alert |
|---|---|---|---|
| launchd should fire 13:00 but no run-log | **Heartbeat plist**, runs every 4h, checks last run-log < 12h old | Telegram alert | Yes — otherwise pipeline can die silently for weeks |
| Apify daily-cap hit | `data/apify_spend.json` ledger | Skip FB run, other sources continue | Yes (informational) |
| Disk full | OSError on log-write | Hard fail | Yes |

### D — Data-quality failures

| Failure | Detection | Reaction | Alert |
|---|---|---|---|
| Hardblock lets aggregator through | Manual review sample | Add to `filtering.blacklist_domains` | No (learnings loop) |
| Author-enrich fails (deleted user) | Reddit API 404 | Skip enrichment, post-only score | No |
| LLM verifier false positive | Operator flags `actie='skip'` in Sheets | Manual; no automated action | No |
| Duplicate across 2 runs | Sheets link-dedup | Auto-skipped by Sheets sync | No |

### Structural addition: per-run digest

After each launchd run, post a Telegram digest:

```
Daily run 2026-05-18 13:00:
  ✓ marktplaats:   42 posts → 8 leads (3 HOT)
  ✓ reddit_new:    87 posts → 6 leads (1 HOT)
  ✗ bouwinfo:      0 posts (DEAD — needs inspection)
  ✓ klusidee:      28 posts → 4 leads (0 HOT)
  ...
  Total: 31 leads, 6 HOT
  Apify spend today: $1.85 / $5.00 cap
```

Separate from instant HOT-alerts. Max 4/day (per launchd trigger). Without this, you cannot detect a quietly broken source for days.

---

## 6 — Dedup & lead quality

### Three dedup layers

**Layer 1 — Within-run (existing).** MinHash Jaccard ≥ 0.70 on `title + text`, per-run. Catches same post returned by two sources in one run. Keep as-is.

**Layer 2 — Cross-run, persistent (new).** Sheets `link`-dedup catches exact URL re-finds (existing, idempotent). Add persistent MinHash store in `data/dedup_store.jsonl` with rolling 14-day window. Each new lead's text checked against store. Catches same person, lightly reworded post, on different source within the week. Implementation: ~2-3h in `processor/fuzzy_dedup.py`.

`data/dedup_store.jsonl` schema (one JSON object per line):
```
{
  "signature": "<minhash-hex>",
  "lead_id": "<uuid>",
  "captured_at": "<ISO-8601 with NL tz offset>",
  "source": "<source_id e.g. marktplaats:diensten/gent>",
  "niche": "<warmtepomp|airco|zonnepanelen|cv|renovatie>"
}
```

**Layer 3 — Author-signature (new, heuristic).** For sources with author identity (Reddit, FB groups, forums): hash `(author, niche)` → if same user posts about same niche within 30 days, dedup. Skip for sources without reliable author (DDG, Marktplaats). Implementation: ~3-4h, store in `data/author_signature.jsonl`.

`data/author_signature.jsonl` schema (one JSON object per line):
```
{
  "author_hash": "<sha256-hex>",
  "niche": "<niche>",
  "first_seen": "<ISO-8601 with NL tz offset>",
  "last_seen":  "<ISO-8601 with NL tz offset>",
  "post_count": <int>
}
```

### Existing quality controls (keep)

- Hardblock: aggregators, OEM vendors, energy companies (`config.yaml:filtering.blacklist_domains`)
- Min-score gate: nothing below 60 reaches Sheets
- LLM verifier: Haiku double-check for 40-75 score band, cached
- Author enrichment: Reddit-only — user history → real person vs spambot

### New quality controls

**Source-credibility weights** (in `config.yaml`):

```yaml
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

Applied **before** threshold check. Reorients volume toward sources whose leads convert best.

**Sellability gate** for HOT tab. A lead lands in HOT only if all six fields are non-null:
1. `url` (working source URL)
2. `summary` (≥30 chars, no truncation markers)
3. `city` (NL/BE municipality, filled)
4. `author` or `author_context`
5. `score ≥ 80` (after source-weight)
6. `intent` (explicit, not "unknown")

Missing any → auto-demote to OPP tab for manual review. Prevents selling a "HOT lead" that has no working contact path.

**Recency boost** (sharpen existing `time_decay: true`):
- Post < 24h: +5 score
- Post 1-7d: unchanged
- Post 7-14d: -10 score
- Post > 14d: dropped (`max_age_days: 7` already enforces for FB)

Reinforces fresh = premium.

---

## 7 — Operational setup

### A — Launchd schedules

| Plist | Trigger | Purpose | Status |
|---|---|---|---|
| `com.leadradar.fbapify.plist` | 08:00 daily | FB Apify groups + Marketplace (post-C4) | Existing |
| `com.leadradar.consumer.plist` | 08:30 / 13:00 / 18:00 daily | All 10 non-FB sources, all 5 niches | **New** (B5) |
| `com.leadradar.heartbeat.plist` | Every 4h | Check last run-log < 12h old; Telegram alert if not | **New** (A4/B7) |
| `com.leadradar.fbquota.plist` | 00:00 daily | Reset Apify daily-cap counter | Existing |
| `com.leadradar.weekly.plist` | Mon 09:00 | Per-source-per-niche yield report | **New** (C1) |

### B — Google Sheets schema

Three existing tabs unchanged: HOT / ALL / OPPORTUNITIES. Two additions:

1. **`bron` column granular** (A3): `"reddit:r/duurzaam"`, `"marktplaats:diensten/gent"`. Per-source filtering in Sheets becomes direct.
2. **New tab `SOURCE STATS`** (C1, weekly auto-update, dump-and-rewrite):
   ```
   week | source | niche | posts_seen | leads | hot | dead_count | last_success
   ```

The 15 existing columns are unchanged. User-status fields (status / contacted_at / notitie / installateur) remain untouched on re-sync.

### C — Telegram channels (one bot, four message types)

| Type | When | Frequency |
|---|---|---|
| HOT instant alert | Per HOT lead (≥80 after source-weight) | ~5-15/day |
| Run digest | End-of-run summary | 4×/day (per launchd trigger) |
| Heartbeat alert | No run > 12h | Only on failure |
| Weekly report | Per-source yield, dead sources, KPIs | Mon 09:00 |

### D — Logging & disk

- Logs in `lead-radar/logs/`: `apify.log`, `apify.err`, `consumer.log` (new), `consumer.err` (new), `heartbeat.log` (new), `weekly.log` (new)
- Rotation: daily roll at start-of-run, suffix `.YYYYMMDD`, 30-day retention via `TimedRotatingFileHandler` + monthly cron cleanup
- `data/leads/consumer/` archived monthly to `data/archive/<YYYY-MM>/`
- `data/dedup_store.jsonl` rolling 14d, trimmed in weekly cron
- All logs local; no cloud upload

### E — Environment variables

```bash
# Apify (FB only)
APIFY_TOKEN="..."
APIFY_DAILY_SPEND_CAP_USD="5.00"

# Google Sheets (all pipelines)
LEAD_RADAR_SPREADSHEET_ID="1CwtxxS1XPWzz54nLV3ndVuHPrwidocXCpZG1h9_yEOU"
LEAD_RADAR_GS_CREDENTIALS="/Users/claudebot/Lead generator/secrets/gs-creds.json"

# Anthropic (LLM verifier)
ANTHROPIC_API_KEY="..."

# Telegram
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."

# Optional: consumer-pipeline can use a separate chat
CONSUMER_TELEGRAM_CHAT_ID=""   # falls back to TELEGRAM_CHAT_ID
```

**launchd reminders (from `.env.example`, already fixed in May 17 commit):**
- launchd does NOT source `~/.zshrc` — all env vars must be in `.env` or plist `EnvironmentVariables`
- Paths with spaces must be quoted

### F — `OPERATOR_SETUP.md` updates (B7)

Add a consumer-pipeline section covering:
- How to install the consumer launchd agent (`launchctl bootstrap gui/$UID com.leadradar.consumer.plist`)
- How to reset a dead source (CLI flag wrapping `reset_source_health(source_name)`)
- How to safely tune `queries.yaml` without pipeline breakage
- How to read the weekly report and which metric drives which decision

---

## 8 — Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| HTML parsers drifted since last run (May 16 was last consumer run) | Medium | Medium | Block B4 audits all 11 parsers against live HTML before launchd |
| 3×/day Reddit/DDG triggers rate-limit ban | Low-Medium | Medium | PoliteSession already implements polite delays; dead-source detector contains blast radius |
| Telegram noise overwhelms operator | Medium | Low | Digest-format default, HOT threshold tunable in C3 |
| Cross-source dedup misses near-dupes | Medium | Medium | Layer 2 persistent MinHash + Layer 3 author-signature; threshold tunable in B3 |
| LLM cost spike with 11 sources × 5 niches × 3 runs | Low | Low | Existing cache + 40-75 band only; estimate <€10/month |
| Sheets API rate limit at 3×/day × 11 sources | Low | Low | gspread already batches; existing retry-after handling |
| Operator burnout from 8 HOT alerts/day | Medium | Medium | Sellability-gate prevents low-quality HOT; weekly digest is the primary signal |

---

## 9 — Open questions for plan phase

These do not block design approval but must be resolved during the writing-plans phase:

1. **Bug location for A1**: where does `'lead/0.85'` originate? Likely in a `breakdown` dict value being parsed as int somewhere downstream. Need to grep.
2. **Source-id schema for A3**: exact format per source — `"marktplaats:<category>/<city>"` vs `"marktplaats/<city>/<category>"`. One format must be chosen.
3. **Heartbeat-agent implementation**: shell script vs Python? The threshold differs per pipeline — FB Apify runs 1×/day so threshold ~30h, consumer runs 3×/day so threshold ~8h. Two heartbeats or one with per-target thresholds?
4. **FB Marketplace activation (C4)**: does the existing Apify actor support Marketplace queries, or do we need a different actor? Verify with Apify console.
5. **Parallel runner (C6)**: only needed if serial wall-clock exceeds 30min. Benchmark in B2.

---

## 10 — Approval

Sections 1-7 approved by founder via interactive brainstorming on 2026-05-17. This document supersedes any prior informal plan for supply expansion.

Next step: invoke `writing-plans` skill to produce a numbered implementation plan with TDD-shaped tasks, mapped to Blocks A / B / C.
