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

## Troubleshooting

- **Reddit 429**: `request_delay` omhoog in `consumer/utils.py`.
- **Tweakers/Bouwinfo geen resultaten**: HTML structuur kan veranderd
  zijn. Voeg een selector toe in `_parse(...)` van die source.
- **Marktplaats geeft 0**: meestal anti-bot challenge. Run zonder
  marktplaats: `--sources reddit,tweakers,bouwinfo,google`.
- **Geen leads boven min-score**: verlaag `--min-score` (bv 20) of
  breid `queries.yaml` uit met meer varianten.
