# Lead Radar — Gratis Lead Scraper voor NL/BE HVAC

> Vindt installatiebedrijven (warmtepomp, airco, zonnepanelen, HVAC) via DuckDuckGo en publieke bronnen — geen API keys, geen accounts, geen betaalde tools.

## 🔗 Context

- Onderdeel van [[lead-radar/index]]
- Gerelateerd: [[automation/index]], [[crm-light/index]], [[outreach/index]]

## Wat het doet

```
[niche + locatie]
       │
       ▼
[DuckDuckGo search] → [URL list]
       │
       ▼
[Filter blacklist + dedup]
       │
       ▼
[Bezoek elke website] → [Email/phone/adres extractie]
       │
       ▼
[Intent scoring 0-100]
       │
       ▼
[CSV/JSON export]   ← data/leads_<niche>_<location>_YYYYMMDD.csv
```

## Installatie

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Gebruik

```bash
python run.py --niche warmtepomp --location amsterdam --max-results 25
```

Output: `data/leads_warmtepomp_amsterdam_YYYYMMDD.csv`

### Alle opties

| Flag | Wat | Default |
|---|---|---|
| `--niche` | warmtepomp \| airco \| zonnepanelen \| hvac_generiek | (vereist) |
| `--location` | plaatsnaam | (vereist) |
| `--country` | nl \| be | nl |
| `--max-results` | max resultaten per query | 25 |
| `--no-enrich` | skip website bezoeken (sneller) | false |
| `--min-score` | filter onder deze score (0-100) | 30 |
| `--format` | csv \| json \| both | csv |
| `--master` | append aan data/leads_master.csv | false |

### Voorbeelden

```bash
# Belgische airco markt
python run.py --niche airco --location antwerpen --country be

# Veel resultaten, lage threshold (research mode)
python run.py --niche warmtepomp --location utrecht --max-results 50 --min-score 0

# Snelle scan zonder website enrichment
python run.py --niche hvac_generiek --location rotterdam --no-enrich
```

## Configuratie

- **`config.yaml`** — niches, queries, blacklist domains, scoring weights, rate limits
- **`keywords.yaml`** — high/mid/low intent keywords, industry terms, location variants

## Output schema

Alle leads hebben deze velden in CSV:

```
lead_id, company_name, domain, url, email, contact_name, phone,
address, city, country, niche, source, intent_score, score_breakdown,
scraped_at, kvk_number, kbo_number, btw_number,
has_contact, has_about, has_portfolio, has_https,
title, snippet, query
```

`scraped_at` = ISO 8601 UTC (`2026-04-25T17:42:11+00:00`).

## Architectuur

```
lead-radar/
├── run.py                  ← entry point
├── config.yaml             ← settings
├── keywords.yaml           ← keyword library
├── requirements.txt
│
├── scrapers/
│   ├── ddg_search.py       ← DuckDuckGo HTML
│   ├── website_scraper.py  ← homepage + emails
│   ├── reddit_search.py    ← Reddit JSON API
│   └── kvk_search.py       ← KVK/KBO dorks
│
├── scoring/
│   └── intent_scorer.py    ← heuristisch (geen LLM)
│
├── output/
│   └── exporter.py         ← CSV/JSON writer
│
├── utils/
│   ├── email_extractor.py
│   └── rate_limiter.py
│
└── data/                   ← output (.csv/.json)
```

## Hoe scoring werkt

| Criterium | Max | Wat |
|---|---|---|
| keyword_density | 30 | Niche keywords op homepage |
| contact_quality | 20 | Named email > info@ > geen |
| page_quality | 15 | contact + about + portfolio |
| location_match | 15 | Stad in adres |
| company_size | 10 | KVK/KBO + niet te groot |
| website_modern | 10 | HTTPS + content |

Score-breakdown staat in elke CSV row zodat je ziet WAAR de score vandaan komt.

## Standalone module gebruik

Elk script werkt los:

```bash
python utils/email_extractor.py        # smoke test extractor
python scrapers/ddg_search.py          # smoke test DDG
python scrapers/reddit_search.py       # smoke test Reddit
python scoring/intent_scorer.py        # smoke test scorer
```

## Troubleshooting

| Probleem | Fix |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `Geen resultaten` | Verlaag `--min-score 0`, of probeer andere stad |
| `403 / rate limit` | Verhoog `request_delay` naar 5.0 in config.yaml |
| `Geen emails` | Sommige sites zetten geen email op web — gebruik phone of contact form |

## Wat dit NIET doet

- Geen LinkedIn scraping (gesloten platform — gebruik Sales Navigator)
- Geen Facebook scraping (gesloten platform)
- Geen email verificatie (gebruik mailtester.com of Hunter.io free tier)
- Geen automatische verzending — outreach blijft handmatig

## Volgende stappen

1. `python run.py --niche warmtepomp --location amsterdam`
2. `head -5 data/leads_*.csv` — bekijk output
3. `cd ../crm-light && python crm.py import ../lead-radar/data/leads_*.csv` — importeer
4. `cd ../outreach && python personalize.py ...` — genereer berichten

---

## Moderation layer (llm-council integration)

Lead Radar's `moderation/` package is a *trust and provenance moderation*
layer that sits between a forum/social scraper and the installateur. It
is **not** an AI lead-generation engine. See
[specs/doctrine/trust-provenance-moderation.md](specs/doctrine/trust-provenance-moderation.md).

When enabled and the input rows look like captured public posts
(`source_url` + `snippet` + `captured_at`), the exporter:

1. POSTs each captured post to **`POST /api/council/moderate-lead`**.
2. The council returns a structured `LeadReview` — `lead_temperature`
   (HOT / WARM / OPP), `confidence_band`, `provenance_status`,
   `signal_type`, `trust_flags`, `intent_summary`, `homeowner_motivation`,
   `estimated_purchase_window`, `estimated_install_value_band`,
   `verbatim_snippet`, `source_url`, `captured_at`, `review_required`,
   `duplicate_risk`, `source_quality`, `rejection_reason`, `reviewer_notes`.
3. Reviews that clear the **HOT gate** (HOT temperature + `high`
   confidence + `verified` provenance + no `trust_flags` + not
   `review_required`) are appended to **`data/moderation/approved_leads.jsonl`**.
4. The configured webhook fires `event: lead.approved` for each approved record.

The council never generates outreach. Copy is humans-only. The webhook
payload and approved store are the integration surface for n8n.

### Enable it

```bash
export LEAD_RADAR_MODERATION_ENABLED=1
export LEAD_RADAR_MODERATION_COUNCIL_URL=http://localhost:8001

# Start the llm-council backend (in another terminal):
cd ../services/llm-council && make dev

# Direct runner against captured posts (forum/social scrape output):
cd ../../lead-radar
python scripts/run_moderation_pipeline.py --input data/captured_posts.jsonl

# Or via the existing exporter for rows that already carry post-shaped
# provenance fields (otherwise the exporter is a no-op):
python run.py --niche warmtepomp --location amsterdam
```

You'll see:

```
[export] CSV: data/leads_warmtepomp_amsterdam_20260518.csv (42 leads)
[moderation] reviewed=42 approved=6 persisted=6 webhooks=6 errors=0
[moderation] temperatures={'HOT': 6, 'WARM': 17, 'OPP': 19}
```

### Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `LEAD_RADAR_MODERATION_ENABLED` | `false` | Master switch |
| `LEAD_RADAR_MODERATION_COUNCIL_URL` | `http://localhost:8001` | Base URL of the llm-council service |
| `LEAD_RADAR_MODERATION_API_TOKEN` | _(empty)_ | Bearer token if the council requires auth |
| `LEAD_RADAR_MODERATION_STRATEGY` | `fast` | `fast` (single chairman call) or `council` (3-stage) |
| `LEAD_RADAR_MODERATION_LOCALE` | `nl` | Output language for free-text fields |
| `LEAD_RADAR_MODERATION_APPROVED_TEMPERATURES` | `HOT` | Comma-list of allowed temperatures |
| `LEAD_RADAR_MODERATION_MIN_CONFIDENCE` | `high` | One of `low` / `medium` / `high` |
| `LEAD_RADAR_MODERATION_REQUIRE_PROVENANCE` | `verified` | Comma-list (e.g. `verified` or `verified,likely`) |
| `LEAD_RADAR_MODERATION_MAX_CONCURRENT` | `4` | Per-batch concurrency |
| `LEAD_RADAR_MODERATION_MAX_RETRIES` | `2` | Retries on 5xx / 429 / timeout |
| `LEAD_RADAR_MODERATION_TIMEOUT` | `60.0` | Per-request timeout, seconds |
| `LEAD_RADAR_MODERATION_APPROVED_PATH` | `data/moderation/approved_leads.jsonl` | Where approved records are appended |
| `LEAD_RADAR_MODERATION_WEBHOOK_URL` | _(empty)_ | n8n webhook for `event: lead.approved` |
| `LEAD_RADAR_MODERATION_WEBHOOK_EVENT` | `lead.approved` | Event name in the webhook payload |
| `LEAD_RADAR_MODERATION_FAIL_OPEN` | `true` | If council unreachable, skip moderation instead of crashing |

### Approved-store schema (v2)

```json
{
  "saved_at":     "2026-05-18T13:24:55.123Z",
  "candidate_id": "cap_00001",
  "candidate":    { "source_url": "https://forum.test/t/42", "snippet": "...verbatim...", "captured_at": "2026-05-18T10:00:00Z" },
  "review":       { "lead_temperature": "HOT", "confidence_band": "high", "provenance_status": "verified", "signal_type": "INTENT_DIRECT", "trust_flags": [], "review_required": false, "..." : "" },
  "approval":     { "approved": true, "reason": "approved", "approved_temperatures": ["HOT"], "min_confidence_band": "high", "require_provenance": ["verified"] },
  "metadata":     { "strategy": "fast", "model": "openai/gpt-4.1", "schema_version": 2, "elapsed_ms": 4351 }
}
```

### n8n webhook payload (v2)

```json
{
  "event": "lead.approved",
  "schema_version": 2,
  "candidate_id": "cap_00001",
  "candidate": {},
  "review":    {},
  "approval":  {},
  "metadata":  {}
}
```

### Tests

- `tests/test_moderation_client.py` — HTTP client retries, classification.
- `tests/test_moderation_pipeline.py` — approval gate, persistence, exporter hook (no network).

Run: `pytest tests/test_moderation_*.py -q`.
