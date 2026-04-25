# Automation — End-to-End Pipeline

> Een commando voor een complete dagelijkse lead-gen run: scrape -> CRM import -> outreach batch -> dashboard.

## Quickstart

```bash
cd "/Users/claudebot/Lead generator/automation"
./daily.sh warmtepomp amsterdam 50
```

Dit doet:
1. Scrape 50 leads voor warmtepomp + amsterdam via lead-radar
2. Importeer nieuwe leads in crm-light (deduped)
3. Genereer outreach email batch (max 20 emails)
4. Toon CRM dashboard

## Bestanden

```
automation/
├── daily.sh         ← bash wrapper (eenvoudig commando)
├── pipeline.py      ← Python orchestrator (alle opties)
└── README.md
```

## daily.sh

```bash
./daily.sh [niche] [location] [max] [country]
```

| Arg | Default | Voorbeeld |
|---|---|---|
| `niche` | `warmtepomp` | `airco`, `zonnepanelen`, `hvac_generiek` |
| `location` | `amsterdam` | `utrecht`, `antwerpen` |
| `max` | `25` | `50`, `100` |
| `country` | `nl` | `be` |

Env vars (optioneel):

```bash
export SIGNATURE="Jan Jansen"
export FROM_EMAIL="jan@jouwbedrijf.nl"
export FROM_COMPANY="JouwBedrijf B.V."
./daily.sh warmtepomp eindhoven 30
```

## pipeline.py (volledige opties)

```bash
python pipeline.py --help

python pipeline.py \
    --niche warmtepomp \
    --location amsterdam \
    --country nl \
    --max 50 \
    --min-score 40 \
    --signature "Jan Jansen" \
    --from-email "jan@jouwbedrijf.nl" \
    --from-company "JouwBedrijf B.V." \
    --outreach-max 20
```

| Flag | Wat |
|---|---|
| `--niche` | warmtepomp / airco / zonnepanelen / hvac_generiek |
| `--location` | plaatsnaam |
| `--country` | nl / be |
| `--max` | max scrape resultaten |
| `--min-score` | minimum intent score (0-100) |
| `--no-scrape` | skip scrape (gebruik bestaande CSV) |
| `--no-crm` | skip CRM import |
| `--no-outreach` | skip outreach batch generation |
| `--no-dashboard` | skip eind-dashboard |
| `--template` | override outreach template pad |
| `--signature` | je naam voor `{{your_name}}` |
| `--from-email` | je email voor `{{your_email}}` |
| `--from-company` | je bedrijf voor `{{your_company}}` |
| `--outreach-max` | max emails in outreach batch |

## Wat is geautomatiseerd vs handmatig

### Automatisch (de pipeline)

- Scraping van DuckDuckGo voor leads
- Filtering blacklist + dedup op domein
- Website bezoeken + email/contact extractie
- Intent scoring (0-100)
- Export naar CSV
- Import in CRM-light met dedup
- Personalisatie van email templates
- Output naar outbox tekstbestand
- Pipeline statistieken

### Handmatig (jij doet)

- Top-leads reviewen voor outreach (5 min)
- Emails verzenden vanuit eigen Gmail/Outlook (15-20 min, max 30/dag/mailbox)
- Replies bekijken en in CRM markeren (5 min)
- Sales calls plannen en voeren
- Wekelijks: git commit `crm-light/data/`

### Waarom niet alles automatisch?

1. **Email versturen** — vereist mailbox auth + warmup. Handmatig versturen is veiliger en gratis.
2. **Reply detectie** — vereist IMAP integratie. Handmatig = 5 min/dag.
3. **Sales calls** — niet te automatiseren, dat is je core skill.
4. **Quality control** — AI scrapers geven soms rare resultaten; menselijke review filtert eruit.

## Cron job (24/7 automatisering)

Voor dagelijkse automatische scrape (resultaat eindigt in CSV, jij verwerkt morgen):

```bash
# crontab -e
0 7 * * * cd "/Users/claudebot/Lead generator/automation" && ./daily.sh warmtepomp amsterdam 25 >> /tmp/lead-radar.log 2>&1
```

Of via macOS `launchd`:

```bash
# ~/Library/LaunchAgents/com.user.leadgen.daily.plist
```

## n8n integratie

Als je n8n al draait (zie `n8n/`), kan de scrape job ook daar:

```
cd /Users/claudebot/Lead\ generator/automation && python3 pipeline.py \
  --niche warmtepomp \
  --location amsterdam \
  --no-outreach
```

## Dependency management

Eerste keer:

```bash
pip3 install -r ../lead-radar/requirements.txt
```

`daily.sh` doet dit automatisch als deps niet gevonden.

## Troubleshooting

| Probleem | Fix |
|---|---|
| `permission denied: ./daily.sh` | `chmod +x daily.sh` |
| `python3: command not found` | Installeer Python 3.10+ |
| `ModuleNotFoundError` | `pip3 install -r ../lead-radar/requirements.txt` |
| Pipeline stopt op stap 2 | Check stderr; vaak DDG rate limit -> wacht 15 min |
| Geen scrape output | Check `lead-radar/data/` op fresh CSV |
| Outreach batch leeg | Check `crm-light/data/leads.csv` heeft leads in `new` stage |

## Stop / pauseer

Druk `Ctrl+C` tijdens een run. Reeds gescrape'd data blijft bewaard.

Om alleen specifieke stap opnieuw te draaien:

```bash
# Alleen CRM import (geen rescrape)
python pipeline.py --niche warmtepomp --location amsterdam --no-scrape

# Alleen outreach (van bestaande leads)
python pipeline.py --niche warmtepomp --location amsterdam --no-scrape --no-crm
```

## Master leads.csv

Pipeline schrijft ook naar `lead-radar/data/leads_master.csv` (cumulatief over ALLE runs). Handig voor:
- Cross-niche analyse: `head leads_master.csv`
- Backup naar Excel/Numbers
- Migration naar HubSpot/Close later
