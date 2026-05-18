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
- Domain endpoints: `/analyze-lead`, `/generate-outreach`, `/review-scrape`
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
| POST | `/api/council/query` | Generic prompt → full council output |
| POST | `/api/council/query/stream` | Same, SSE |
| POST | `/api/council/analyze-lead` | Qualify a lead (ICP score, signals, next action) |
| POST | `/api/council/generate-outreach` | Draft email / LinkedIn / SMS outreach |
| POST | `/api/council/review-scrape` | QA report on a scraped sample |

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

### Example: analyze a lead

```bash
curl -s -X POST http://localhost:8001/api/council/analyze-lead \
  -H 'Content-Type: application/json' \
  -d '{
    "lead": {
      "name": "Jane Cooper",
      "company": "Acme Solar BV",
      "title": "CFO",
      "location": "Amsterdam",
      "domain": "acme-solar.nl",
      "notes": "Expanded into NL last quarter, hired 4 engineers."
    },
    "objective": "qualify for a 30-min discovery call about lead-radar",
    "locale": "nl"
  }' | jq
```

### Example: draft outreach

```bash
curl -s -X POST http://localhost:8001/api/council/generate-outreach \
  -H 'Content-Type: application/json' \
  -d '{
    "lead": {"company": "Acme Solar", "title": "CFO", "name": "Jane Cooper"},
    "angle": "lead-radar saves them 40% on cold list-building",
    "channel": "email",
    "tone": "professional, direct, friendly",
    "locale": "nl",
    "max_length_chars": 900
  }' | jq
```

### Example: review a scrape

```bash
curl -s -X POST http://localhost:8001/api/council/review-scrape \
  -H 'Content-Type: application/json' \
  -d '{
    "source_name": "facebook-groups-installers-NL",
    "criteria": "Solar installer companies in NL/BE with >1 employee",
    "sample": [
      {"name": "...", "company": "...", "email": "..."},
      {"name": "...", "company": "...", "email": "..."}
    ]
  }' | jq
```

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
│   └── council.py       # generic + analyze/outreach/review
├── services/
│   ├── openrouter.py    # async OpenRouter client + streaming
│   ├── council.py       # 3-stage orchestration + lead-gen prompts
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
