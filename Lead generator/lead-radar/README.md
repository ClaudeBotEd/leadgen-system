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

## AI Intelligence Layer (llm-council integration)

Lead Radar can automatically run every scraped lead through the
`services/llm-council` AI intelligence layer. When enabled:

1. The exporter calls **POST `/api/council/score-lead`** for each lead.
2. Leads with `lead_quality_score >= threshold` (default `6`) also call
   **POST `/api/council/generate-sequence`** for cold email + LinkedIn +
   3-step follow-up + CTAs.
3. Qualified leads are appended to **`data/crm/qualified_leads.jsonl`**
   (one JSON object per line — n8n / log shippers can tail it).
4. Optionally fires an **`event: lead.qualified`** webhook to n8n.

### Enable it

```bash
export LEAD_RADAR_INTELLIGENCE_ENABLED=1
export LEAD_RADAR_INTELLIGENCE_COUNCIL_URL=http://localhost:8001

# Start the llm-council backend (in another terminal):
cd ../services/llm-council && make dev

# Run lead-radar — intelligence runs automatically inside export_leads():
cd ../../lead-radar && python run.py --niche warmtepomp --location amsterdam
```

You'll see:

```
[export] CSV: data/leads_warmtepomp_amsterdam_20260518.csv (42 leads)
[intelligence] scored=42 qualified=18 persisted=18 webhooks=18 errors=0
```

### Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `LEAD_RADAR_INTELLIGENCE_ENABLED` | `false` | Master switch; when off, exporter is unchanged |
| `LEAD_RADAR_INTELLIGENCE_COUNCIL_URL` | `http://localhost:8001` | Base URL of the llm-council service |
| `LEAD_RADAR_INTELLIGENCE_API_TOKEN` | _(empty)_ | Bearer token if the council requires auth |
| `LEAD_RADAR_INTELLIGENCE_STRATEGY` | `fast` | `fast` (single chairman call) or `council` (full 3-stage) |
| `LEAD_RADAR_INTELLIGENCE_GENERATE_SEQUENCE` | `true` | Set to `0` to score only, no outreach drafts |
| `LEAD_RADAR_INTELLIGENCE_QUALITY_THRESHOLD` | `6` | Only leads with `lead_quality_score >= N` are persisted |
| `LEAD_RADAR_INTELLIGENCE_LOCALE` | `en` | Output language for free-text fields (`en`, `nl`, …) |
| `LEAD_RADAR_INTELLIGENCE_MAX_CONCURRENT` | `4` | Per-batch concurrency (ThreadPoolExecutor size) |
| `LEAD_RADAR_INTELLIGENCE_MAX_RETRIES` | `2` | Retries on 5xx / 429 / timeout / transport error |
| `LEAD_RADAR_INTELLIGENCE_TIMEOUT` | `60.0` | Per-request timeout, seconds |
| `LEAD_RADAR_INTELLIGENCE_CRM_PATH` | `data/crm/qualified_leads.jsonl` | Where qualified leads are appended |
| `LEAD_RADAR_INTELLIGENCE_WEBHOOK_URL` | _(empty)_ | n8n webhook for `event: lead.qualified` |
| `LEAD_RADAR_INTELLIGENCE_WEBHOOK_MIN_SCORE` | `7` | Only fire webhook for leads at or above this |
| `LEAD_RADAR_INTELLIGENCE_FAIL_OPEN` | `true` | If council is unreachable, skip enrichment instead of crashing |

### CRM JSONL schema (v1)

```json
{
  "saved_at": "2026-05-18T12:34:56.123Z",
  "lead_id": "lr_00001",
  "lead":         { "...raw scraped fields...": "" },
  "intelligence": { "lead_quality_score": 7, "automation_fit_score": 8, "...": "" },
  "sequence":     { "cold_email": {}, "linkedin_opener": "", "follow_up_sequence": [], "cta_suggestions": [] },
  "metadata": {
    "threshold": 6,
    "strategy":  "fast",
    "model":     "openai/gpt-4.1",
    "score_elapsed_ms":    4351,
    "sequence_elapsed_ms": 4773,
    "schema_version": 1
  }
}
```

### n8n webhook payload (v1)

```json
{
  "event": "lead.qualified",
  "schema_version": 1,
  "lead_id": "lr_00001",
  "lead":         {},
  "intelligence": {},
  "sequence":     {},
  "metadata":     {}
}
```

### Tests

- `tests/test_intelligence_client.py` — HTTP client retries, classification, auth header.
- `tests/test_intelligence_pipeline.py` — end-to-end with a stubbed council (no network).

Run: `pytest tests/test_intelligence_*.py -q`.
