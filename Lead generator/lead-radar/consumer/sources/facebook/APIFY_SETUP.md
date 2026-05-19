# Apify-cloud Facebook scraper — operator setup

De Apify-route vervangt de self-hosted Playwright scraper voor Facebook
Groups. **Geen burner-accounts, geen Playwright, geen launchd-jojo's
nodig** — Apify draait server-side met hun eigen account-pool en
residential proxies. De output landt in dezelfde `data/fb_queue/*.jsonl`
shape als de self-hosted scraper, dus `run_consumer.py` merkt geen
verschil.

> De self-hosted scraper blijft in de codebase als koude backup. Je kan
> 'm altijd terugzetten als Apify een actor breekt of als je premium-
> diepte (comments, profielen) wil scrapen.

## 1. Token + budget

```bash
# In ~/.env van lead-radar (of in je shell rc):
APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxx
APIFY_DAILY_BUDGET_USD=5.00
```

Token kopiëren van: <https://console.apify.com/settings/integrations>.

De budget-cap is **hard**. Zodra de geaccumuleerde dagspend ≥ cap, weigert
de wrapper verdere actor-calls (`ApifyBudgetExceeded`). State wordt
bijgehouden in `data/apify_spend.json` (UTC dag → USD bedrag).

## 2. Dependency installeren

```bash
cd ~/Lead\ generator/lead-radar
pip install -r requirements.txt   # voegt apify-client>=1.7 toe
```

## 3. Smoke-test (één niche, monitor cost)

```bash
set -a && source .env && set +a
python3 -m consumer.sources.facebook.runner apify --niche warmtepomp
```

> **`set -a && source .env && set +a`** is verplicht — de codebase laadt
> `.env` niet automatisch. Productie launchd plist doet hetzelfde via een
> wrapper-script (zie sectie 4).

Verwacht:

```
INFO Apify groups run done: 75 posts, $0.27 total (queue: data/fb_queue/apify-groups-...jsonl)
INFO   OK  warmtepomp/1520566101657472: posts=17 cost=$0.0610
INFO   OK  warmtepomp/1430530037683847: posts=20 cost=$0.0460
...
```

Daarna draait de gewone pipeline de queue leeg:

```bash
python3 run_consumer.py --daily   # iterates over alle niches
```

## 4. Productie-schedule (macOS launchd)

We gebruiken launchd ipv cron omdat cron geen slapende Mac wekt; launchd
schedule een gemiste run zodra de Mac wakker is.

```bash
# Installeer plist + wrapper
cp consumer/sources/facebook/com.leadradar.fbapify.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.leadradar.fbapify.plist
launchctl list | grep leadradar          # verify

# Handmatig triggeren voor smoke-test
launchctl start com.leadradar.fbapify
tail -f logs/apify.log
```

Schedule: 08:00 / 12:00 / 17:00 / 21:00 lokale tijd. Logs landen in
`logs/apify.log` (stdout) en `logs/apify.err` (stderr).

> **Belangrijk:** schakel de oude self-hosted `com.leadradar.fbscrape.plist`
> uit voordat je Apify activeert — anders concurreren ze om dezelfde
> queue.

```bash
launchctl unload ~/Library/LaunchAgents/com.leadradar.fbscrape.plist 2>/dev/null
rm ~/Library/LaunchAgents/com.leadradar.fbscrape.plist
```

## 5. Wat doe je met de oude self-hosted setup?

* **Niets weggooien.** De Playwright code, burner-state in
  `data/fb_state/`, en de groups/marketplace/pages surfaces blijven
  bruikbaar voor diepte-runs of als fallback.
* **launchd plist uitschakelen** (zie sectie 4 hierboven) zodat ze niet
  parallel draaien tegen dezelfde queue.

## 6. Kosten verwachten

`apify/facebook-groups-scraper` rekent doorgaans
$0.30–0.50 per 1000 posts. Bij de huidige config:

* **per run** (alle niches): ~$0.95 voor 16 groepen → ~245 posts
* **per dag** (4 runs): ~$3.80 — past binnen de $5 cap met 30% headroom
* **per maand**: ~$115

Houd `data/apify_spend.json` in de gaten — als het ledger ineens omhoog
schiet zonder dat targets zijn veranderd, heeft Apify de pricing
aangepast.

## 7. Niet-Groups surfaces

* **Marketplace** en **Pages** zitten al in
  `config/facebook_targets.yaml` maar worden nog niet via Apify
  gescrapet — de mapper voor `apify/facebook-marketplace-scraper` en
  `apify/facebook-pages-scraper` is volgende uitrol-stap.
* Tot die er is, kun je marketplace/pages via de self-hosted scraper
  blijven draaien (`runner scrape`) en alleen groups via Apify
  (`runner apify`). Beide schrijven naar dezelfde queue.

## 8. Operator runbook

### Budget uitgeput vóór einde dag

Symptoom: log bevat `ApifyBudgetExceeded`, queue groeit niet meer.

```bash
cat data/apify_spend.json
# {"2026-05-17": 5.0123}   <- cap geraakt

# Optie A — accepteer dat run-van-vandaag overgeslagen wordt; ledger reset
# automatisch om 00:00 UTC.
# Optie B — tijdelijk cap verhogen (NIET in .env, dan blijft het permanent):
APIFY_DAILY_BUDGET_USD=10.00 \
  python3 -m consumer.sources.facebook.runner apify --niche all
# Optie C — permanent verhogen: bewerk .env, restart launchd:
launchctl unload ~/Library/LaunchAgents/com.leadradar.fbapify.plist
launchctl load -w ~/Library/LaunchAgents/com.leadradar.fbapify.plist
```

Tip: als je consistent boven cap zit, verlaag `max_posts_per_target` in
`config/facebook_targets.yaml` (default 20 → 15 scheelt ~25% cost).

### Actor down / herhaalde 5xx fouten

Symptoom: log toont `apify: <actor> call failed attempt N: <err>` op
elke groep. De wrapper retried 1× per call; bij blijvende failures
gaat de hele run alsnog door — alleen die specifieke groep ontbreekt.

```bash
# Check Apify status: https://status.apify.com/
# Check de specifieke run via console:
open "https://console.apify.com/actors/runs"
```

Als de actor permanent stuk is: switch tijdelijk terug naar self-hosted
door de oude `com.leadradar.fbscrape.plist` opnieuw te laden (zie
sectie 4 reversed).

### Queue niet drainen

Symptoom: `data/fb_queue/*.jsonl` files stapelen op, `run_consumer.py`
draait niet of finds 0 posts.

```bash
# Check of run_consumer.py daily-schedule draait (apart van Apify):
launchctl list | grep leadradar
crontab -l | grep leadradar

# Forceer drain:
python3 run_consumer.py --daily

# Files worden na consumptie verplaatst naar data/fb_queue/processed/.
ls -la data/fb_queue/processed/ | tail
```

### 0-posts groep diagnosticeren

Symptoom: log toont `groep/<id>: posts=0 cost=$0.0010` — actor returnt
niks. Meestal: PRIVATE GROUP zonder FB-login.

```bash
# Quick check via Apify API:
set -a && source .env && set +a
python3 -c "
from apify_client import ApifyClient
import os
client = ApifyClient(os.environ['APIFY_API_TOKEN'])
runs = list(client.actor('apify/facebook-groups-scraper').runs().list(limit=10).items)
cheap = [r for r in runs if r.get('usageTotalUsd', 0) < 0.01]
for r in cheap[:3]:
    log = client.log(r['id']).get()
    print(f'RUN {r[\"id\"]}:')
    for line in (log or '').split('\\n'):
        if 'PRIVATE' in line or 'ERROR' in line:
            print(f'  {line.strip()}')
"
```

Als de groep PRIVATE is: verwijder uit `config/facebook_targets.yaml`
(comment-out met reden — bewaar de ID voor archeologie).

### Monitoring: eerste 24u na go-live

```bash
# Spend tracker
watch -n 60 'cat data/apify_spend.json'

# Queue groei
watch -n 60 'ls -la data/fb_queue/*.jsonl 2>/dev/null | tail'

# Run log tail
tail -F logs/apify.log

# Daily summary (na een paar runs)
grep "Apify groups run done" logs/apify.log | tail -10
```

Verwacht patroon:

* 4 entries in `apify_spend.json` history binnen 24u — een per launchd trigger
* Queue files verschijnen om 08:01, 12:01, 17:01, 21:01 en zijn na ~30s door
  `run_consumer.py` verplaatst naar `processed/` (mits daily-run schedule
  ook actief is)
* Totale daily spend $3-$4 (kruis-check met `data/apify_spend.json`)

Bij afwijking >50%: zie de specifieke runbook-sectie hierboven.
