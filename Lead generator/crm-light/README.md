# CRM-Light — CSV Pipeline Beheer

> Volledig CSV-based CRM. Geen accounts, geen database, geen API. Alle data lokaal in `data/leads.csv` en `data/activities.csv`.

## Wanneer wel / niet

**Gebruik dit als:**
- Je <500 leads hebt
- Solo werkt of met 1-2 mensen
- Snel wil starten zonder accounts
- Volledige data ownership wil

**Stap over naar HubSpot/Close als:**
- Je >500 leads beheert
- Met team werkt
- Email-tracking, calling, automation nodig hebt

Migratie: `python crm.py export hubspot.csv` → import in HubSpot.

## Quickstart

```bash
# 1. Importeer leads uit lead-radar output
python crm.py import ../lead-radar/data/leads_warmtepomp_amsterdam_*.csv

# 2. Bekijk pipeline
python dashboard.py

# 3. Toon top leads in 'new' stage
python crm.py list --stage new --limit 20

# 4. Lead detail
python crm.py show lr_00001

# 5. Move lead naar volgende stage
python crm.py move lr_00001 contacted

# 6. Voeg notitie toe
python crm.py note lr_00001 "Belt morgen 10u terug"

# 7. Log een email
python crm.py log lr_00001 --type email_sent --content "Cold email v1 verstuurd"

# 8. Search
python crm.py search "warmtepomp"

# 9. Stats
python crm.py stats
```

## Pipeline stages

```
new -> contacted -> replied -> meeting_booked -> qualified -> negotiating -> won
                                                                         \-> lost
```

| Stage | Wat |
|---|---|
| `new` | Nieuwe lead, nog geen contact |
| `contacted` | Eerste cold email verstuurd |
| `replied` | Lead heeft gereageerd |
| `meeting_booked` | Discovery call gepland |
| `qualified` | Past binnen ICP, interesse bevestigd |
| `negotiating` | Voorstel/contract uitgewisseld |
| `won` | Klant geworden |
| `lost` | Niet doorgegaan |

## Activity types

| Type | Wanneer |
|---|---|
| `email_sent` | Cold email of follow-up verstuurd |
| `email_received` | Reply ontvangen |
| `call` | Telefoongesprek gevoerd |
| `linkedin_msg` | LinkedIn DM verstuurd |
| `meeting` | Discovery/sales call |
| `demo` | Demo gegeven |
| `note` | Algemene notitie |
| `stage_change` | (auto-gelogd bij move) |

## Bestandsstructuur

```
crm-light/
├── crm.py                 ← CLI
├── dashboard.py           ← terminal dashboard
├── README.md
└── data/
    ├── leads.csv          ← alle leads + status
    └── activities.csv     ← log van alle interacties
```

## Data schema — leads.csv

| Kolom | Voorbeeld |
|---|---|
| lead_id | `lr_00001` |
| company_name | `Voorbeeld Installatie BV` |
| domain | `voorbeeld-installatie.nl` |
| url | `https://voorbeeld-installatie.nl` |
| email | `info@voorbeeld-installatie.nl` |
| contact_name | `Jan de Vries` |
| phone | `+31 20 1234567` |
| address | `Hoofdweg 1, 1011 AB Amsterdam` |
| city | `Amsterdam` |
| country | `NL` |
| niche | `warmtepomp` |
| source | `duckduckgo` |
| intent_score | `72` |
| score_breakdown | `{"keyword_density": 27, ...}` |
| scraped_at | `2026-04-25T17:42:11+00:00` |
| stage | `new` / `contacted` / ... |
| last_contacted_at | `2026-04-25T17:42:11+00:00` |
| next_action_at | `2026-04-28T10:00:00+00:00` |
| owner | `me` |
| notes | `Belt morgen terug` |
| custom_tags | `hot,nl,solo` |

## Data schema — activities.csv

| Kolom | Voorbeeld |
|---|---|
| activity_id | `act_1745601234` |
| lead_id | `lr_00001` |
| type | `email_sent` |
| timestamp | `2026-04-25T17:42:11+00:00` |
| content | `Cold email v1` |
| outcome | `bounced` |

## Backup & versioning

Plain CSV → gewoon committen:

```bash
cd "/Users/claudebot/Lead generator"
git add crm-light/data/
git commit -m "CRM update: $(date +%Y-%m-%d)"
git push
```

## Tips

- **Dagelijks** — `python dashboard.py` als eerste check
- **Per outreach** — `crm.py log <id> --type email_sent` na verzenden
- **Per reply** — `crm.py move <id> replied`
- **Wekelijks** — `git commit` voor backup
- **Auto-refresh** — `python dashboard.py --refresh 30` op 2e monitor

## Troubleshooting

| Probleem | Fix |
|---|---|
| `Lead niet gevonden` | Check ID met `crm.py list` |
| `Onbekend type` | Geldige types staan in error |
| Excel breekt CSV | Open met UTF-8 import, scheidingsteken `,` |
| Verloren data | `git log -- crm-light/data/` |
