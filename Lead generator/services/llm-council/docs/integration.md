# Integration cookbook

How to consume `services/llm-council` from the rest of the Lead generator
ecosystem (n8n, CRM, outreach, lead-radar scoring).

## Base URL

- **Local dev**: `http://localhost:8001`
- **Docker compose**: `http://llm-council-backend:8001` (from another compose
  service on the same network), or `http://host.docker.internal:8001` from
  containers elsewhere.

## Authentication

By default the service is open (suitable for `localhost` only). For shared
deployments set `LLM_COUNCIL_API_TOKEN` and have callers send:

```
Authorization: Bearer <token>
```

The same token is also used as the rate-limit bucket key, so each consumer
(one token per system) gets its own quota.

## Error contract

Every non-2xx response uses:

```json
{
  "error": {
    "code": "validation_error|http_error|conversation_not_found|upstream_model_error|rate_limited|internal_error",
    "message": "human-readable",
    "details": { "...": "..." }
  }
}
```

## Endpoints at a glance

| Use case | Endpoint |
| --- | --- |
| Generic council reasoning | `POST /api/council/query` |
| Streamed generic query | `POST /api/council/query/stream` (SSE) |
| Lead qualification (ICP score, signals, next action) | `POST /api/council/analyze-lead` |
| Outbound message draft | `POST /api/council/generate-outreach` |
| Scrape QA report | `POST /api/council/review-scrape` |
| Persistent chat (UI flows) | `POST /api/conversations/{id}/message` |

## n8n recipes

### 1. Score a lead inside an n8n workflow

```
HTTP Request node
  Method:  POST
  URL:     http://llm-council-backend:8001/api/council/analyze-lead
  Headers: Authorization: Bearer {{$env.LLM_COUNCIL_API_TOKEN}}
  Body (JSON):
    {
      "lead": {{$json.lead}},
      "objective": "qualify for outbound, score 0-100",
      "locale": "nl"
    }
```

Downstream: pipe `body.stage3.response` into the CRM `note` field, or
extract the ICP score via a Function node:

```js
const text = $input.first().json.stage3.response;
const m = text.match(/ICP\s*score[^\d]*(\d{1,3})/i);
return [{ json: { score: m ? parseInt(m[1], 10) : null, raw: text } }];
```

### 2. Draft an email when a deal moves to "Engage"

```
HTTP Request node
  Method:  POST
  URL:     http://llm-council-backend:8001/api/council/generate-outreach
  Body:
    {
      "lead": {
        "name":    "{{$json.contact.name}}",
        "company": "{{$json.contact.company}}",
        "title":   "{{$json.contact.title}}"
      },
      "angle": "lead-radar saves them ~40% on cold list-building",
      "channel": "email",
      "tone": "professional, direct, friendly",
      "locale": "nl",
      "max_length_chars": 900
    }
```

### 3. QA a scrape from Facebook Groups

```
HTTP Request node
  Method:  POST
  URL:     http://llm-council-backend:8001/api/council/review-scrape
  Body:
    {
      "source_name": "facebook-groups-installers-NL",
      "criteria":    "Solar installer companies in NL/BE with >1 employee",
      "sample":      {{$json.sample}}
    }
```

A complete example workflow is in
[`docs/examples/n8n_lead_qualifier.json`](examples/n8n_lead_qualifier.json).

## CRM integration

The lightweight `crm-light/` and the full `crm/` flows can attach council
output to a contact note. A minimal Python helper:

```python
import httpx

LLM_COUNCIL = "http://localhost:8001"

async def qualify(lead: dict, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            f"{LLM_COUNCIL}/api/council/analyze-lead",
            headers=headers,
            json={"lead": lead, "objective": "qualify for outbound"},
        )
        r.raise_for_status()
        return r.json()
```

## Outreach automation

Use `/api/council/generate-outreach` in your daily batch job to produce
council-graded copy. Tip: persist `metadata.aggregate_rankings` alongside
each draft so you can audit which model dominated which decision.

## Streaming clients (SSE)

```js
const r = await fetch("/api/council/query/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "..." }),
});

const reader = r.body.getReader();
const decoder = new TextDecoder();
let buf = "";
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  buf += decoder.decode(value, { stream: true });
  const lines = buf.split("\n");
  buf = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.startsWith("data:")) continue;
    const event = JSON.parse(line.slice(5).trim());
    // event.type: stage1_start | stage1_complete | stage2_* | stage3_* | complete | error
    console.log(event.type, event.data);
  }
}
```

## Operational guidance

- **Cost**: defaults route 90% of tokens through cheap small models;
  only the chairman pays for `gpt-4.1`. Override
  `LLM_COUNCIL_MODELS` / `LLM_COUNCIL_CHAIRMAN_MODEL` per environment.
- **Resilience**: any council member can fail without breaking a request.
  Inspect `metadata.label_to_model` to see who actually contributed.
- **Throughput**: bump `LLM_COUNCIL_RATE_LIMIT_PER_MINUTE` for trusted
  internal consumers, or set per-consumer tokens so they don't share an IP
  bucket.
- **Storage**: switch to Postgres with one env var when you outgrow SQLite.
