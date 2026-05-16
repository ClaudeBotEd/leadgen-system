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
python3 -m consumer.sources.facebook.runner apify --niche warmtepomp
```

Verwacht:

```
INFO Apify groups run done: 73 posts, $0.18 total (queue: data/fb_queue/apify-groups-...jsonl)
INFO   OK  warmtepomp/1520566101657472: posts=18 cost=$0.0420
INFO   OK  warmtepomp/1430530037683847: posts=15 cost=$0.0380
...
```

Daarna draait de gewone pipeline de queue leeg:

```bash
python3 run_consumer.py --niche warmtepomp
```

## 4. Productie-schedule

Vervang in je launchd plist (`com.leadradar.fbscrape.plist`) of crontab
de `scrape` subcommand door `apify`:

```bash
# crontab voorbeeld — 4× per dag alle niches
0 8,12,17,21 * * * cd ~/Lead\ generator/lead-radar && python3 -m consumer.sources.facebook.runner apify --niche all >> logs/apify.log 2>&1
```

Geen `--account-id` meer nodig. `com.leadradar.fbquota.plist`
(midnight quota reset) is ook overbodig in Apify-modus — die telde
self-hosted account-quota; Apify rekent server-side af.

## 5. Wat doe je met de oude self-hosted setup?

* **Niets weggooien.** De Playwright code, burner-state in
  `data/fb_state/`, en de groups/marketplace/pages surfaces blijven
  bruikbaar voor diepte-runs of als fallback.
* **launchd plist uitschakelen** (zie sectie 4 hierboven) zodat ze niet
  parallel draaien tegen dezelfde queue.

## 6. Kosten verwachten

`apify/facebook-groups-scraper` rekent doorgaans
$0.30–0.50 per 1000 posts. Bij de huidige config (16 groepen × 20 posts
= 320 posts/run, 4 runs/dag) = ~$0.20–0.30 per dag. Houd `data/apify_spend.json`
in de gaten — als het ledger ineens omhoog schiet zonder dat targets
zijn veranderd, heeft Apify de pricing aangepast.

## 7. Niet-Groups surfaces

* **Marketplace** en **Pages** zitten al in
  `config/facebook_targets.yaml` maar worden nog niet via Apify
  gescrapet — de mapper voor `apify/facebook-marketplace-scraper` en
  `apify/facebook-pages-scraper` is volgende uitrol-stap.
* Tot die er is, kun je marketplace/pages via de self-hosted scraper
  blijven draaien (`runner scrape`) en alleen groups via Apify
  (`runner apify`). Beide schrijven naar dezelfde queue.
