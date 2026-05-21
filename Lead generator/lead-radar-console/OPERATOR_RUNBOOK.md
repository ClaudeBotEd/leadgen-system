# Operator Runbook — Lead Radar Console v0

## Daily login

1. Open http://localhost:3000 (or production URL)
2. Click "Send magic link" with your operator email
3. Open the email, click the link → lands on /triage

## Triage scan (every work-block, ~5 seconds)

The triage page shows three workflow blocks:

- **Routing** — leads waiting for installer assignment
- **Classification** — signals waiting for classification (ambiguous-band)
- **Conversion** — outcomes waiting to be registered

For each: see the queue count + 1-2 secondary signals (e.g., "1 HOT >24h", "3 taxonomy-flag").

**Action:** press `1`, `2`, or `3` to enter the workflow you'll work on first.

## Routing workflow

Per lead:
- Read lead in top section (band, score, niche, geo, post text)
- Review agent's recommended installer + 2 alternatives
- Decide:
  - `A` — approve agent's top pick, route, save, advance
  - `P` — pick alternative (then `1`/`2` to select, `Enter` to confirm)
  - `O` — override (none of the recommendations fit; specify category + reason)
  - `H` — hold (come back later)
  - `N` — skip without action

Decision-support language: installer fitness is shown as qualitative labels ("Strong regional fit", "High conversion history") — not as decimal percentages. Don't try to compute precision the agent doesn't have.

## Classification workflow

Per signal:
- Read signal source, age, user, pre-score, full post text
- Review agent's top-3 candidate categories with confidence scores
- Decide:
  - `1`/`2`/`3` — confident pick of one of the candidates
  - `U` then `1`/`2`/`3` — uncertain pick (you're picking a category but flagging "not sure")
  - `M` then `1`/`2`/`3` (primary) then `1`/`2`/`3` (secondary) — mixed intent
  - `T` — taxonomy gap (none of the candidates fit; flag for taxonomy review)
  - `N` — confident no-intent
  - `O` — override (free-form category)
  - `H` — hold

The qualifier matters: it goes into `decisions.reviewer_decision.qualifier` and feeds the learning velocity metrics. Don't force confident classifications when uncertain.

## Conversion workflow

Per conversion event:
- Read lead history + installer's reply
- Review agent's parsed fields (outcome / value band / install status / attribution)
- If parse confidence ≥80%, press `S` to enter "confirming" → `S` again to save
- If parse confidence <80%, system forces you into `E` (edit) first → adjust → `S` `S` to save
- `F` to flag dispute (e.g., installer disagrees with the lead attribution)

This is **dataset-defining** — your save is the ground truth for the proprietary dataset. The "are you sure?" prompt is intentional.

## Override flow (universal)

When `O` is pressed in any card:
1. Pick a category (1-5: taxonomy miss / too strict / too lax / context missing / other)
2. Type a brief reason (max 200 chars)
3. `Enter` to save & advance, `Esc` to cancel

Override patterns are the future intelligence-learning surface. Be specific in reasons.

## Audit inspection (`V` key)

Press `V` on any card to see the lead's full lifecycle tree inline. Click any node to expand its details (workflow, agent rec, operator decision, agreement, time-to-decide).

For infrastructure details (decision_id, profile_version, tier, agent_id, inputs_hash) → click `[A]dvanced inspect` inside the expanded node.

**Discipline:** Time-in-audit indicator appears after 60s; prompt to continue queue work after 3min. Don't disappear into investigative rabbit-holes — Esc back to your queue.

## Search (`/` key)

Press `/` from anywhere to open the universal search overlay:
- Type text to search lead/signal post text + niche
- Or type a lead-id (e.g., `lead-fixture-001`) for exact match
- Arrow keys navigate matches, `Enter` opens that lead's audit chain
- `Esc` cancels (state preserved)

## When to kill a workflow

Currently kill-state is set directly via DB (no UI in V0):

```bash
docker exec -it lead-radar-console-pg psql -U console -d lead_radar
```

```sql
INSERT INTO workflow_kill_state (workflow_id, reason, set_by, killed_until)
VALUES ('lead_delivery_routing', 'investigating drift', '<operator_id>', NULL)
ON CONFLICT (workflow_id) DO UPDATE SET reason=EXCLUDED.reason, set_by=EXCLUDED.set_by, killed_until=EXCLUDED.killed_until, set_at=now();
```

To release: `DELETE FROM workflow_kill_state WHERE workflow_id = '...';`

The triage page will show the workflow as "paused" while killed.

## Operational headroom widget (top-right)

Shows aggregate OCL budget consumption today:
- Green: <60% used — plenty of capacity
- Yellow: 60-79% — review your pace
- Orange: 80-99% — Managed Overflow options surface
- Red: 100%+ — forced action required (capacity, overflow policy, or pause)

## Troubleshooting

**Magic link doesn't arrive:** check Resend dashboard. Verify `RESEND_API_KEY` and `RESEND_FROM` in `.env`. Verify your operator email is `active=true` in DB.

**Queue empty but I expect items:** check `docker compose ps` (Postgres running?), then `pnpm db:seed-fixtures` to repopulate dev fixtures.

**Build fails on ESLint:** common cause is `any` types or unescaped quotes in JSX. Run `node_modules/.bin/next build` to see specifics.

**Tests fail with connection errors:** ensure Docker Postgres is running and `.env` has `DATABASE_URL=postgresql://console:console@localhost:5432/lead_radar`.
