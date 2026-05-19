# LLM Council — multi-LLM orchestration service

Internal **AI orchestration & analysis service** for the Lead generator monorepo.
A FastAPI backend + React/Vite UI that runs any prompt — or a lead-generation
task — through a 3-stage council of LLMs (proposal → peer ranking → chairman
synthesis), all routed through one OpenRouter key.

Originally based on [karpathy/llm-council](https://github.com/karpathy/llm-council);
hardened and extended for production use inside this monorepo:

- pydantic-settings + typed config / env validation
- Async SQLAlchemy storage (SQLite → Postgres swap is a one-env-var change)
- SSE streaming for both the chat and the lead-gen endpoints
- structlog structured logging (dev console / prod JSON)
- Rate limiting + optional bearer-token auth for n8n / CRM consumers
- Central error contract `{error:{code,message,details}}`
- Health / liveness / readiness endpoints
- Moderation endpoint: `/api/council/moderate-lead` + source-quality `/review-scrape`
- Balanced cost model defaults (gpt-4.1-mini + gemini-2.5-flash + claude-3.5-haiku, chair: gpt-4.1)
- Dockerfile + docker-compose + Makefile + smoke script

---

## Quick start

```bash
cd services/llm-council
make install              # uv sync + npm install
cp .env.example .env.local && $EDITOR .env.local   # set OPENROUTER_API_KEY
make dev                  # backend on :8001, frontend on :5173
```

Then open [http://localhost:5173](http://localhost:5173) for the UI or
[http://localhost:8001/docs](http://localhost:8001/docs) for the OpenAPI explorer.

---

## Configuration

All settings live in `.env.local` (gitignored). See `.env.example` for the
complete list. The most important ones:

| Variable | Default | Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | _(required)_ | https://openrouter.ai/keys |
| `LLM_COUNCIL_PORT` | `8001` | Backend port |
| `LLM_COUNCIL_MODELS` | `openai/gpt-4.1-mini, google/gemini-2.5-flash, anthropic/claude-3.5-haiku` | Council members (comma-separated) |
| `LLM_COUNCIL_CHAIRMAN_MODEL` | `openai/gpt-4.1` | Synthesis chairman |
| `LLM_COUNCIL_TITLE_MODEL` | `google/gemini-2.5-flash` | Conversation-title generator |
| `LLM_COUNCIL_DATABASE_URL` | `sqlite+aiosqlite:///./data/llm_council.db` | Set to `postgresql+asyncpg://...` for Postgres |
| `LLM_COUNCIL_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CSV list |
| `LLM_COUNCIL_RATE_LIMIT_PER_MINUTE` | `60` | Per IP / token |
| `LLM_COUNCIL_API_TOKEN` | _(empty)_ | If set, every API call must send `Authorization: Bearer <token>` |
| `LLM_COUNCIL_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LLM_COUNCIL_ENV` | `development` | Switch to `production` for JSON logs |

---

## API surface

### Health

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Full status (models, env, configured?) |
| GET | `/health/live` | Liveness — always 200 if the process is up |
| GET | `/health/ready` | Readiness — 200 only with valid runtime config |

### Conversations (UI-facing)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/conversations` | List metadata |
| POST | `/api/conversations` | Create |
| GET | `/api/conversations/{id}` | Get full conversation |
| DELETE | `/api/conversations/{id}` | Delete |
| POST | `/api/conversations/{id}/message` | Submit message, run full council |
| POST | `/api/conversations/{id}/message/stream` | Same, SSE stream |

### Council (integration surface)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/council/query` | Generic prompt → full 3-stage council output |
| POST | `/api/council/query/stream` | Same, SSE |
| POST | `/api/council/review-scrape` | Provenance / source-quality QA on a scraped sample |
| POST | `/api/council/moderate-lead` | **Structured moderation verdict** on a single captured public post |

> The B2B SaaS endpoints (`/analyze-lead`, `/generate-outreach`,
> `/score-lead`, `/generate-sequence`) were removed in the
> trust-provenance refactor. The council is a moderation and
> verification layer, not a sales automation engine.

All endpoints return:

```json
{
  "stage1": [{"model": "...", "response": "..."}],
  "stage2": [{"model": "...", "ranking": "...", "parsed_ranking": ["Response A", "Response B"]}],
  "stage3": {"model": "...", "response": "..."},
  "metadata": {
    "label_to_model": {"Response A": "openai/gpt-4.1-mini"},
    "aggregate_rankings": [{"model": "...", "average_rank": 1.5, "rankings_count": 3}]
  }
}
```

### Example: source-quality review on a scraped sample

```bash
curl -s -X POST http://localhost:8001/api/council/review-scrape \
  -H 'Content-Type: application/json' \
  -d '{
    "source_name": "gathering-of-tweakers-warmtepomp",
    "criteria": "credible upstream of homeowner-intent posts",
    "sample": [
      {"source_url": "https://forum.test/t/1", "snippet": "Ik wil een warmtepomp in Utrecht.", "captured_at": "2026-05-18T10:00:00Z"},
      {"source_url": "https://forum.test/t/2", "snippet": "Offerte aangevraagd voor warmtepomp.", "captured_at": "2026-05-18T10:01:00Z"}
    ]
  }' | jq
```

### Example: moderate a single captured post

```bash
curl -s -X POST http://localhost:8001/api/council/moderate-lead \
  -H 'Content-Type: application/json' \
  -d '{
    "candidate": {
      "candidate_id": "cap_00042",
      "source_url": "https://gathering.tweakers.test/forum/thread/42",
      "snippet": "Onze cv begeeft het, wie kan een warmtepomp plaatsen in Utrecht?",
      "captured_at": "2026-05-18T10:00:00Z",
      "posted_at": "2026-05-18T09:55:00Z",
      "source_platform": "gathering-of-tweakers",
      "region": "Utrecht",
      "snippet_lang": "nl",
      "niche": "warmtepomp"
    },
    "strategy": "fast",
    "locale": "nl"
  }' | jq
```

Returns (only HOT + verified + high + no flags + `review_required=false`
clears the human-reviewer gate downstream):

```json
{
  "candidate_id": "cap_00042",
  "review": {
    "source_url":         "https://gathering.tweakers.test/forum/thread/42",
    "verbatim_snippet":   "Onze cv begeeft het, wie kan een warmtepomp plaatsen in Utrecht?",
    "captured_at":        "2026-05-18T10:00:00Z",
    "lead_temperature":   "HOT",
    "confidence_band":    "high",
    "provenance_status":  "verified",
    "signal_type":        "INTENT_DIRECT",
    "intent_summary":     "Homeowner asks installateurs to quote replacement.",
    "homeowner_motivation": "CV is failing — needs replacement soon.",
    "estimated_purchase_window":    "<30 days",
    "estimated_install_value_band": "5-15k EUR",
    "trust_flags":         [],
    "review_required":     false,
    "duplicate_risk":      "low",
    "source_quality":      "high",
    "rejection_reason":    "",
    "reviewer_notes":      "Clear, recent, region given."
  },
  "strategy": "fast",
  "model":    "openai/gpt-4.1",
  "elapsed_ms": 4351,
  "json_parsed": true,
  "usage":  {"prompt_tokens": 250, "completion_tokens": 120, "total_tokens": 370},
  "error":  null
}
```

---

## Lead-radar integration

The `lead-radar` package consumes the moderation endpoint via
`lead-radar/moderation/`. When `LEAD_RADAR_MODERATION_ENABLED=1` is set
and the scraper produces post-shaped rows (`source_url` + `snippet` +
`captured_at`), each post is automatically moderated. Records that
clear the HOT gate (HOT + `high` confidence + `verified` provenance +
no `trust_flags` + not `review_required`) are appended to
`lead-radar/data/moderation/approved_leads.jsonl` and an
`event: lead.approved` webhook fires for downstream n8n automation.

The council never generates outreach. Copy is humans-only. See the
`lead-radar/README.md` "Moderation layer" section for env-var reference,
schema, and the doctrine at
`lead-radar/specs/doctrine/trust-provenance-moderation.md`.

---

## Architecture

```
backend/
├── main.py              # FastAPI app factory + lifespan
├── config.py            # pydantic-settings (env-driven)
├── logging.py           # structlog
├── errors.py            # CouncilError + central handlers
├── dependencies.py      # rate limiter + optional bearer auth
├── schemas.py           # pydantic request/response models
├── api/
│   ├── health.py
│   ├── conversations.py
│   └── council.py       # generic query + review-scrape + moderate-lead
├── services/
│   ├── openrouter.py    # async OpenRouter client + streaming
│   ├── council.py       # 3-stage orchestration + source-quality prompt
│   ├── lead_moderation.py  # provenance/intent moderation prompts + parsing
│   └── storage.py       # async SQLAlchemy persistence
└── db/
    ├── database.py      # engine + session factory
    └── models.py        # Conversation / Message ORM
```

---

## Development

```bash
make help             # list targets
make install          # backend + frontend deps
make dev              # run both
make backend          # backend only
make frontend         # frontend only
make test             # pytest (in-memory SQLite)
make lint             # ruff
make smoke            # curl /health on running backend
```

### Resetting local state

```bash
make clean            # caches + sqlite file
```

### Switching to Postgres

```bash
# in .env.local
LLM_COUNCIL_DATABASE_URL=postgresql+asyncpg://user:pw@host/db
```

No code changes — SQLAlchemy + async drivers do the rest. Tables auto-create on startup.

---

## Docker

```bash
make docker-build
make docker-up    # backend on :8001, frontend on :5173
make docker-down
```

See `docker-compose.yml` for env wiring. The compose file reads `.env.local`
the same way local dev does.

---

## Tests

```bash
make test
```

Tests use an in-memory SQLite database and a mocked OpenRouter client — no
network or API key required.

---

## Integration cookbook

See [`docs/integration.md`](docs/integration.md) for ready-made n8n,
CRM, and outreach-pipeline integration recipes.

---

## Debugging tips

- `LLM_COUNCIL_LOG_LEVEL=DEBUG` — see every OpenRouter call.
- `GET /openapi.json` or `/docs` — interactive route inspector.
- `make smoke` — confirm health + create + delete conversation.
- A model failing? `stage1`/`stage2` simply drop that model and continue;
  check `openrouter_http_error` log lines.
- Rate-limited? Lower request volume, increase
  `LLM_COUNCIL_RATE_LIMIT_PER_MINUTE`, or set `LLM_COUNCIL_API_TOKEN` so
  each consumer gets their own bucket.
