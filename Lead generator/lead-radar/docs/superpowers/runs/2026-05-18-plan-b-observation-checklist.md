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

## Carry-over from PB-T6 dry-run (2026-05-18)

Pre-launchd full-daily run produced:
- 1 sellable lead (>=60 score) across 5 niches × 10 sources × 1 run
- Most posts filtered by `low` (regex score < min_threshold), `promo`, or `hardblock`
- All 10 sources executed without exceptions
- Sheets sync confirmed working (HOT/ALL/OPP tabs received rows)
- **Telegram digest path verified but did NOT send** — `CONSUMER_TELEGRAM_CHAT_ID` and `TELEGRAM_CHAT_ID` are both unset in `.env`. Add at least one before relying on the digest as a monitoring signal.

The low single-run yield is expected: this was one run at default thresholds. Over 7 days × 3 runs/day = 21 runs the yield aggregates. If Day 7 totals are still below 25 leads/day, Plan C's queries.yaml tuning (C2) and threshold lowering (C3) become the priority.
