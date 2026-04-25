# Lead Radar — Gratis Lead Scraper voor NL/BE HVAC

> Vindt installatiebedrijven (warmtepomp, airco, zonnepanelen, HVAC) via DuckDuckGo en publieke bronnen — geen API keys, geen accounts, geen betaalde tools.

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
