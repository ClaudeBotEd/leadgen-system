# Lead Radar — Setup Guide

Volledige setup van consumer pipeline v2 — van zero naar HOT leads in je Telegram.

## 1. Python + dependencies

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Test de installatie:

```bash
pytest tests/ -q
```

Verwachte output: `329 passed, 1 skipped`.

## 2. Google Sheets sync (verplicht voor portal-workflow)

### 2a. Service account + spreadsheet

1. https://console.cloud.google.com/ — maak project "Lead Radar"
2. APIs & Services → Library → enable **Google Sheets API** + **Google Drive API**
3. Credentials → Create credentials → Service account → naam `lead-radar-bot`
4. Service account → Keys tab → Add Key → JSON
5. Verplaats download naar `lead-radar/.credentials/google_sheets.json`
6. https://sheets.new — maak spreadsheet "Lead Radar — Consumer Leads"
7. Kopieer ID uit URL (deel tussen `/d/` en `/edit`)
8. Open `.credentials/google_sheets.json`, kopieer `client_email`
9. In Sheet: Share knop → plak email → role **Editor** → Send

### 2b. Env vars

```bash
export LEAD_RADAR_SPREADSHEET_ID="<id_uit_url>"
export LEAD_RADAR_GS_CREDENTIALS="$PWD/.credentials/google_sheets.json"
```

Of zet in `~/.zshrc` voor permanente shell-toegang.

## 3. LLM-verifier (Claude Haiku) — sterk aanbevolen

Claude geeft second-opinion op borderline scores (40-75) → recall +20-30%.

1. https://console.anthropic.com/settings/keys → Create key
2. ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

Kost ~€0.001/post in borderline-zone. ~250 posts/dag → €0,25/dag.

Skip per-run met `--no-llm`. Pipeline draait gewoon door zonder key (regex-only).

## 4. Telegram bot — real-time HOT lead push

1. Op Telegram: open chat met **@BotFather**
2. Stuur `/newbot` → kies naam → krijg `TELEGRAM_BOT_TOKEN`
3. Open chat met je nieuwe bot, stuur willekeurig bericht ("hi")
4. In browser: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Zoek `"chat":{"id":...}` → dat is `TELEGRAM_CHAT_ID`
6. ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC..."
   export TELEGRAM_CHAT_ID="987654321"
   ```

Test: `python3 -c "from consumer.output.telegram import ping_bot; print(ping_bot())"`
Verwacht: `(True, "@jouwbotnaam")`.

## 5. Eerste daily run

```bash
python3 run_consumer.py --daily
```

Doet:
1. Alle 5 niches (warmtepomp, airco, zonnepanelen, cv, renovatie)
2. 12 queries per niche-source combo (Reddit, Tweakers, Bouwinfo, Marktplaats, DDG, 2dehands)
3. Hard-block filter → fuzzy dedup → cleaner → classifier → scorer + time-decay
4. LLM second-opinion op borderline
5. Reddit author-history check
6. Sheets sync (HOT / ALL / OPPORTUNITIES tabs)
7. Telegram push voor elke HOT lead (score ≥80)

Verwachte output: `~10-30 leads/dag` waarvan ~3-8 HOT.

## 6. Productie deployment

### 6a. Hetzner CX22 VPS (€4,50/mo)

```bash
# Op de Hetzner box
ssh root@<ip>
apt update && apt install -y python3.11 python3-venv git
git clone https://github.com/<jouwacct>/leadgen-system.git
cd "leadgen-system/Lead generator/lead-radar"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 6b. Cron — 4x per dag

```bash
crontab -e
```

```cron
# Lead Radar — 4x per dag (8u/12u/16u/20u Amsterdam)
0 7,11,15,19 * * * cd "/root/leadgen-system/Lead generator/lead-radar" && \
    /root/leadgen-system/.../.venv/bin/python run_consumer.py --daily >> /var/log/leadradar.log 2>&1
```

### 6c. Structured logging + Sentry

```bash
export LEAD_RADAR_LOG_FORMAT=json
export SENTRY_DSN="https://<key>@sentry.io/<project>"
export LEAD_RADAR_ENV=production
```

JSON-logs gaan naar stderr → Grafana Loki / Hetzner journald / etc.

## 7. CLI cheatsheet

```bash
# Daily mode — alles in 1
python3 run_consumer.py --daily

# Eén niche — alleen Reddit + Tweakers
python3 run_consumer.py --niche warmtepomp --sources reddit,tweakers --limit 30

# Skip alle quality lagen (debug regex-only)
python3 run_consumer.py --niche cv --no-llm --no-fuzzy-dedup \
    --no-hardblock --no-author-enrich --no-telegram

# Verlaag LLM-zone (meer LLM-calls = hogere kost én betere recall)
python3 run_consumer.py --niche warmtepomp \
    --llm-min-score 30 --llm-max-score 80

# Andere fuzzy threshold (strenger = minder dedup)
python3 run_consumer.py --niche cv --dedup-threshold 0.85

# Verbose + JSON log
LEAD_RADAR_LOG_FORMAT=json python3 run_consumer.py --niche cv --verbose
```

## 8. Tests draaien

```bash
pytest tests/ -q                          # alles (~380 tests)
pytest tests/test_scorer.py -v             # alleen scorer
pytest tests/ -m "llm"                     # alleen live LLM (heeft API key nodig)
pytest tests/ -m "not llm and not network" # offline-only (CI mode)
```

## 8a. Production safety

```bash
# Dry-run: pipeline runt, maar geen Sheets sync en geen Telegram alerts.
# CSV/JSON exports gebeuren wel, dus operator kan output inspecteren
# zonder iets richting prod te pushen.
python3 run_consumer.py --daily --dry-run

# Kosten-vrije validatie (geen Sheets, geen Telegram, geen LLM):
python3 run_consumer.py --daily --dry-run --no-llm

# Soft cap op LLM-spend per run (cached hits tellen niet mee):
export LEAD_RADAR_LLM_BUDGET_EUR=0.50      # ~500 calls bij Haiku
python3 run_consumer.py --daily
```

De daily-run sluit af met een regel die het aantal API-calls, geschatte
kosten en cache-hit-rate toont — geen Anthropic dashboard nodig voor
spend-monitoring.

## 9. Troubleshooting

| Probleem | Fix |
|---|---|
| `ANTHROPIC_API_KEY` ontbreekt → "skipped:no_api_key" in logs | Normaal — voeg key toe of run met `--no-llm` |
| Telegram alerts komen niet aan | `ping_bot()` test eerst — check bot_token + chat_id |
| Sheets sync "PermissionError" | Service-account email heeft geen Editor-recht op spreadsheet |
| Reddit 429 (too many requests) | Verhoog `request_delay` in `consumer/utils.py`, of voeg PRAW OAuth toe |
| Lege output ondanks goede posts | `--min-score 0` om alles te zien; check `breakdown` voor penalty-redenen |
| LLM-cache groeit te groot | `rm -rf .cache/llm_verifier/` — re-vult zichzelf |

## 10. Wat erbij komt in volgende versies

- Postgres-backbone (vervangt Sheets als bron-van-waarheid)
- Next.js installateur-portal (klant accept/reject + Stripe billing)
- Vision-LLM op foto-bevattende posts
- WhatsApp Business API voor outbound
- A/B testing voor message-templates
- Active learning loop op gelabelde feedback
