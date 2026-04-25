# MVP START HERE — Gratis AI Lead Gen Stack (NL/BE HVAC)

> **Doel:** Binnen 2 uur een werkend lead-gen systeem voor warmtepomp/HVAC installateurs in NL/BE — zonder accounts, zonder betaalde tools, zonder API keys.

---

## Wat dit is

Een **volledig gratis, modulaire** lead generation stack die parallel draait aan de Apollo/HubSpot setup elders in deze repo. Gebruik dit als je:
- Eerst gratis wil testen voordat je betaalt
- Geen budget hebt voor Apollo/Clay/Phantombuster
- Volledige controle wil over je data
- Niet afhankelijk wil zijn van platform ToS

## Wat dit NIET is

- Geen vervanging van Apollo qua schaal (Apollo = 250M contacts, dit = je eigen scrapes)
- Geen automatisering van email *verzending* (je verstuurt zelf vanuit eigen mailbox)
- Geen agressieve scraping (alleen publieke bronnen, met rate limiting)

---

## De 4 modules

| Module | Wat het doet | Input → Output |
|---|---|---|
| `lead-radar/` | Vindt installatiebedrijven via DuckDuckGo, KVK, Reddit, websites | Niche + locatie → CSV met leads |
| `crm-light/` | Lead pipeline beheer (CSV-based, terminal dashboard) | CSV → status tracking |
| `outreach/` | Personaliseert email/DM templates met lead data | CSV + template → klare berichten |
| `automation/` | Eind-tot-eind pipeline runner | Eén commando → volledige run |

---

## Snelstart (15 minuten — eerste leads in CSV)

### 1. Python deps installeren

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
pip install -r requirements.txt
```

### 2. Eerste scrape draaien

```bash
python run.py --niche warmtepomp --location amsterdam --max-results 25
```

Output: `data/leads_warmtepomp_amsterdam_YYYYMMDD.csv`

### 3. Bekijk de output

```bash
head -20 data/leads_warmtepomp_amsterdam_*.csv
```

### 4. Importeer in CRM-light

```bash
cd ../crm-light
python crm.py import ../lead-radar/data/leads_warmtepomp_amsterdam_*.csv
python dashboard.py
```

### 5. Genereer eerste outreach batch

```bash
cd ../outreach
python personalize.py \
  --leads ../crm-light/data/leads.csv \
  --template templates/email/warmtepomp_v1.txt \
  --output outbox/batch_$(date +%Y%m%d).txt
```

Output: tekst-bestand met alle gepersonaliseerde emails, klaar om te kopiëren naar je mail-tool.

---

## Snelstart MAX (volledige pipeline, 1 commando)

```bash
cd "/Users/claudebot/Lead generator/automation"
./daily.sh warmtepomp amsterdam 50
```

Doet: scrape → enrich → score → import in CRM → genereer email batch → toont dashboard.

---

## Dagelijkse workflow (30-60 min)

| Tijd | Stap | Commando |
|---|---|---|
| 0-5min | Pipeline starten voor 1 nieuwe stad | `./automation/daily.sh warmtepomp utrecht 50` |
| 5-15min | Top-25 leads handmatig reviewen in dashboard | `python crm-light/dashboard.py` |
| 15-30min | Email batch personaliseren + handmatig finaal aanpassen | `python outreach/personalize.py ...` |
| 30-45min | Versturen vanuit je eigen Gmail/Outlook (max 30/dag/mailbox) | (handmatig) |
| 45-60min | Replies bekijken, status updates in CRM | `python crm-light/crm.py update <id> --stage replied` |

---

## Wat is gratis vs wat kost geld

### 100% gratis (nu)
- Lead scraping (DuckDuckGo HTML, Reddit JSON, KVK publiek)
- Website email extraction
- Intent scoring (heuristisch, geen LLM)
- CRM-light (CSV files)
- Personalisatie engine (template + replace)
- Email versturen via je eigen Gmail/Outlook (gratis tier)

### Optioneel betaald (later opschalen)
- Apollo ($49+/maand) — voor 10x meer leads, zie `apollo/`
- Maildoso ($15-25/mailbox) — voor cold email infra, zie `dns/`
- HubSpot/Close ($0-99/maand) — voor team CRM, zie `crm/`
- n8n cloud ($20+/maand) — voor 24/7 automation, zie `n8n/`

---

## Volgorde van uitbreiding

1. **Week 1 (deze week):** alleen MVP — bewijs of het werkt
2. **Week 2:** als 5+ replies → koop 1 cold-email domein + Maildoso
3. **Week 3:** als eerste klant → switch naar HubSpot Free / Close starter
4. **Maand 2:** als 3+ klanten → Apollo voor meer volume

---

## Bestandsmap

```
Lead generator/
├── MVP-START-HERE.md          ← dit bestand
├── lead-radar/                 ← gratis lead scraper (Python)
│   ├── README.md
│   ├── requirements.txt
│   ├── config.yaml
│   ├── keywords.yaml
│   ├── run.py                  ← entry point
│   ├── scrapers/               ← per-bron scrapers
│   ├── scoring/                ← intent scoring
│   ├── output/                 ← CSV/JSON export
│   ├── utils/                  ← helpers
│   └── data/                   ← scrape output
├── crm-light/                  ← CSV-based CRM
│   ├── README.md
│   ├── crm.py
│   ├── dashboard.py
│   └── data/
├── outreach/                   ← personalisatie + templates
│   ├── README.md
│   ├── personalize.py
│   └── templates/
│       ├── email/
│       └── dm/
├── automation/                 ← end-to-end pipelines
│   ├── README.md
│   ├── daily.sh
│   └── pipeline.py
│
├── (bestaande mappen voor later wanneer je naar betaalde tools gaat)
├── apollo/                     ← Apollo configuraties (betaald)
├── crm/                        ← HubSpot/Close pipelines (betaald-tier)
├── dns/                        ← cold-email DNS infrastructuur
├── email-sequences/            ← email templates (markdown formaat)
├── landingspagina/             ← lead capture landing page
└── n8n/                        ← workflow automation (zelf-hosted)
```

---

## Eerste 2 uur — concrete checklist

- [ ] **0-15 min:** Python 3.10+ check (`python3 --version`), pip install
- [ ] **15-30 min:** `cd lead-radar && python run.py --niche warmtepomp --location amsterdam --max-results 50`
- [ ] **30-45 min:** Output CSV bekijken, 5 top-leads handmatig openen om te valideren
- [ ] **45-75 min:** `cd ../crm-light && python crm.py import ../lead-radar/data/*.csv`, dashboard openen
- [ ] **75-105 min:** `cd ../outreach && python personalize.py ...` → 25 emails klaar
- [ ] **105-120 min:** Eerste 5 emails handmatig verfijnen, opslaan in Drafts in Gmail

**Resultaat na 2 uur:** 5-10 hoogwaardige leads + klaar-om-te-versturen emails. Geen account aangemaakt, niets betaald.

---

## Hulp nodig?

Lees de README.md per module:
- `lead-radar/README.md` — hoe werkt de scraper, troubleshooting
- `crm-light/README.md` — hoe je leads beheert
- `outreach/README.md` — template syntax, placeholder lijst
- `automation/README.md` — pipeline configuratie

**Belangrijk:** alle code draait zonder API keys. Als je later wil opschalen, voeg dan keys toe aan `lead-radar/config.yaml` en de scrapers gebruiken ze automatisch.
