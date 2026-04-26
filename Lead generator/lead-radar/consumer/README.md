# Consumer Lead Radar

Vindt high-intent **eindklanten** voor installateurs in NL/BE — mensen die
nu actief op zoek zijn naar een installateur of offerte voor:

- **warmtepomp**, **airco**, **zonnepanelen**, **cv**, **renovatie**

Geen automatische outreach. Alleen discovery → filteren → scoring → CSV/JSON.

## Bronnen

| Source | Methode | Auth |
|---|---|---|
| `reddit` | Publieke JSON API (`reddit.com/r/<sub>/search.json`) | nee |
| `tweakers` | Forum search HTML (`gathering.tweakers.net/forum/find`) | nee |
| `bouwinfo` | BE forum search HTML (`bouwinfo.be`) | nee |
| `google` | DuckDuckGo via `duckduckgo_search` (geen Google captcha-risk) | nee |
| `marktplaats` | Publieke listings (`marktplaats.nl/q/...`) | nee |
| `facebook` | **Niet** scrapen — handmatig posts kopieren in tekst-file | n.v.t. |

## Snelstart

```bash
cd lead-radar

# Eenmalig: install dependencies
pip install -r requirements.txt

# Run
python run_consumer.py --niche warmtepomp --location nederland --limit 50
```

Output:
```
lead-radar/data/leads/consumer/
  leads_warmtepomp_2026-04-26.csv
  leads_warmtepomp_2026-04-26.json
  seen_hashes.json   ← cross-run dedup
```

## CLI opties

```bash
python run_consumer.py \
  --niche warmtepomp \                    # warmtepomp|airco|zonnepanelen|cv|renovatie
  --location amsterdam \                   # optioneel — stad of "nederland"/"belgie"
  --limit 50 \                             # max posts per source-query
  --sources reddit,tweakers,google \       # optioneel — default = alles
  --min-score 30 \                         # cut-off voor output (default 30)
  --facebook-file fb_posts.txt \           # optioneel — handmatige FB analyse
  --verbose
```

## Scoring (0–100)

| Factor | Punten | Triggert op |
|---|---:|---|
| Locatie aanwezig | +20 | Stad uit NL/BE-lijst of postcode |
| Urgentie | +25 | "zsm", "spoed", "deze maand", "asap", … |
| Vraagt installateur | +25 | "installateur", "monteur", "vakman", "aannemer" |
| Woning/situatie | +15 | "huis", "rijtjeshuis", "m2", "bouwjaar", "dak" … |
| Budget/offerte | +15 | "euro", "€", "offerte", "kosten", … |
| Off-topic penalty | −30 | Niche keyword komt **niet** voor in tekst |

**Intent**: ≥70 = `hot` · 40-69 = `warm` · <40 = `cold`.

Vóór scoring filtert de classifier expliciete promo-posts en pure
info-vragen weg (regex-rules in `processor/intent_classifier.py`).

## Dagelijks gebruik

Een typische dag-routine die je 5-10 leads per niche oplevert:

```bash
# 1) Run alle vijf niches voor heel NL/BE
for n in warmtepomp airco zonnepanelen cv renovatie; do
  python run_consumer.py --niche $n --location nederland --limit 30
done

# 2) Open de CSV in Numbers/Excel — sorteer op score desc
open data/leads/consumer/leads_warmtepomp_$(date +%F).csv

# 3) Bekijk de hot leads, kopieer URL, ga naar de bron, en reageer zelf
#    (geen automatische outreach — dat doe jij persoonlijk)

# 4) Optioneel: FB groep posts kopieren naar fb_posts.txt en analyseren
python run_consumer.py --niche warmtepomp --facebook-file fb_posts.txt
```

Cross-run dedup zorgt dat je elke dag alleen *nieuwe* posts ziet.
Verwijder `seen_hashes.json` om alles weer te zien.

## Facebook handmatig

Per spec geen automatische scraping. Workflow:

1. Open een FB-groep ("Warmtepomp Nederland", "Airco-installatie", etc.)
2. Kopieer interessante posts in een tekstbestand, gescheiden door `---`
   of een blanke regel:
   ```
   Wie heeft tip voor warmtepomp installateur regio Utrecht?
   Ik heb een rijtjeshuis van 110m2 en wil binnenkort overstappen.

   ---

   Mijn cv-ketel is kapot, zoek met spoed iemand in Antwerpen.
   ```
3. Run met `--facebook-file fb_posts.txt`.

Of programmatisch:
```python
from consumer.sources.facebook import analyze_manual_posts
leads = analyze_manual_posts([
    "Wie heeft tip voor warmtepomp installateur Utrecht?",
    "CV kapot, zoek monteur in Antwerpen, deze week.",
], niche_keywords=["warmtepomp", "cv"])
for l in leads:
    print(l.score, l.intent, l.city, l.summary[:80])
```

## Architectuur

```
lead-radar/
  consumer/
    __init__.py            ← RawPost / Lead / intent_from_score
    queries.yaml           ← per-niche zoekqueries
    utils.py               ← PoliteSession, SeenStore
    sources/
      __init__.py          ← REGISTRY {name: fetch_fn}
      reddit.py            ← Reddit JSON API
      tweakers.py          ← Tweakers GoT scraper
      bouwinfo.py          ← Bouwinfo scraper
      google.py            ← DDG search lib
      marktplaats.py       ← MP /q/<query>/ scraper
      facebook.py          ← analyze_manual_posts() — geen scraping
    processor/
      cleaner.py           ← HTML strip, city detect, summary
      intent_classifier.py ← lead vs promo vs info
      scorer.py            ← 0-100 score + breakdown
    output/
      exporter.py          ← CSV + JSON writer
  run_consumer.py          ← CLI
```

Pipeline:

```
  fetch (per source × per query)
    → RawPost
    → seen_hashes.json dedup (cross-run)
    → cleaner.clean_post()
    → intent_classifier.is_potential_lead()    (filter promo/info)
    → scorer.score_post()                       (0-100)
    → keep if score >= min_score
    → exporter.export_leads()                  (CSV + JSON)
```

## Wat je later kan verbeteren

- **Reddit auth**: vervang public JSON door PRAW met read-only OAuth
  (verhoogt rate limit van ~60/min naar 600/min).
- **LLM-based scoring**: vervang regex-scorer door Claude/GPT-call —
  betere recall op atypische phrasings. Kost euro per 1000 posts; doe
  alleen op posts met score ≥ 40.
- **Meer sources**: HVAC-Forum.nl, `r/HVAC`, `r/heatpumps`, 2dehands.be.
- **Notification webhook**: nieuwe hot leads → Telegram/Slack push.
- **Tijd-gewogen score**: posts ouder dan 30 dagen krijgen malus.
- **Smart dedup**: nu op (source, id) — fuzzy text-match cross-platform.
- **Auteur-verrijking**: scrape Reddit-auteur's laatste posts om
  recurring vragers (lage waarde) te onderscheiden van nieuwe leads.
- **Streamlit dashboard** over de CSV met "mark contacted" knop.

## Google Sheets sync

Na elke run kunnen de leads automatisch in een Google Sheet komen. Twee tabs:
**ALL LEADS** (alles) en **TOP LEADS** (score ≥ 70). Idempotent — dubbele
leads worden niet opnieuw toegevoegd. Gesorteerd op score (HOT bovenaan).

### 1. Google Cloud project + API aanzetten

1. Ga naar https://console.cloud.google.com/
2. Maak een project (bv "Lead Radar"), of kies een bestaand project.
3. Open **APIs & Services → Library**, zoek en enable:
   - **Google Sheets API**
   - **Google Drive API**

### 2. Service account aanmaken + JSON-key downloaden

1. **APIs & Services → Credentials → "+ Create Credentials" → Service account**
2. Naam: `lead-radar-bot`. Klik door tot "Done".
3. Klik op de zojuist aangemaakte service account → tab **Keys**
   → **Add Key → Create new key → JSON**.
4. Er wordt een `<project>-xxxxx.json` gedownload. Verplaats die naar:
   ```
   lead-radar/.credentials/google_sheets.json
   ```
   (Map staat al in `.gitignore` — wordt nooit gecommit.)

### 3. Sheet aanmaken + toegang geven

1. Maak een nieuwe Google Sheet (https://sheets.new). Geef een titel,
   bv "Lead Radar — Consumer Leads".
2. Kopieer het **spreadsheet ID** uit de URL. De URL ziet er zo uit:
   `https://docs.google.com/spreadsheets/d/`**`<DIT_DEEL_IS_HET_ID>`**`/edit`
3. Open `lead-radar/.credentials/google_sheets.json`, kopieer de waarde
   van `client_email` (iets als `lead-radar-bot@<project>.iam.gserviceaccount.com`).
4. In je Sheet: **Share** knop rechtsboven → plak het service-account email
   → rol **Editor** → Send. (Geen melding nodig — vink "Notify people" uit.)

### 4. Configureer + run

Eénmalig — geef de spreadsheet-ID door via env var (handigst):
```bash
export LEAD_RADAR_SPREADSHEET_ID="<jouw_id>"
```
Of zet het in `~/.zshrc` zodat het na elke nieuwe shell beschikbaar is.

Run met sync:
```bash
python run_consumer.py --niche warmtepomp --location nederland --limit 25 --sheets
```

Of expliciet (zonder env):
```bash
python run_consumer.py --niche warmtepomp --sheets \
   --spreadsheet-id "<jouw_id>" \
   --credentials .credentials/google_sheets.json
```

### Sheet structuur

Tabs **ALL LEADS** en **TOP LEADS** worden auto-aangemaakt met deze kolommen:

| score | status | stad | niche | samenvatting | actie | bron | link |
|---|---|---|---|---|---|---|---|
| 85 | HOT | utrecht | warmtepomp | Wie heeft tip warmtepomp installateur? CV kapot, deze maand offerte… | CONTACT | reddit | https://… |

Status-mapping: ≥70 → HOT, 40-69 → WARM, <40 → COLD.
Actie-mapping: HOT → CONTACT, WARM → LATER, COLD → SKIP.

### Daily cron

Bv elke ochtend automatisch alle 5 niches naar Sheets:
```bash
# crontab -e
0 8 * * *  cd "$HOME/Lead generator/lead-radar" && \
   for n in warmtepomp airco zonnepanelen cv renovatie; do \
     python3 run_consumer.py --niche $n --location nederland --limit 25 --sheets; \
   done >> /tmp/leadradar.log 2>&1
```

### Troubleshooting Sheets

- **"Service-account JSON niet gevonden"**: check pad bovenstaand.
- **"Kon spreadsheet … niet openen"**: vergat je het service-account
  email als Editor te sharen?
- **`SpreadsheetNotFound`**: ID klopt niet — kopieer opnieuw uit URL.
- **`PermissionDenied: Drive API not enabled`**: stap 1 — enable Drive API.

## Troubleshooting

- **Reddit 429**: `request_delay` omhoog in `consumer/utils.py`.
- **Tweakers/Bouwinfo geen resultaten**: HTML structuur kan veranderd
  zijn. Voeg een selector toe in `_parse(...)` van die source.
- **Marktplaats geeft 0**: meestal anti-bot challenge. Run zonder
  marktplaats: `--sources reddit,tweakers,bouwinfo,google`.
- **Geen leads boven min-score**: verlaag `--min-score` (bv 20) of
  breid `queries.yaml` uit met meer varianten.
