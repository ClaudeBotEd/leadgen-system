# Lead Radar — Facebook als primaire lead-bron (Design)

**Status:** Awaiting founder review (na brainstorming-sessie 2026-05-19)
**Auteur:** Claude Opus 4.7 (i.s.m. founder Sem Vijn, sessie 2026-05-19)
**Datum:** 2026-05-19
**Branch:** TBD — gesuggereerd: `feat/facebook-primary-source` (huidige werk-branch is `feat/trust-hardening-sprint`)
**Doctrine-impact:** Vereist bump naar `trust-provenance-moderation.md` v0.2 — zie §8.
**Type:** Implementatie-design voor een verschuiving in primaire ingestiebron, niet een nieuw control-systeem. Inrichting valt onder de bestaande autonomy-architectuur (zie `2026-05-18-autonomy-architecture-design.md`).

---

## 0 — Context

Per 2026-05-19 draait Lead Radar al een gemengde ingestie-pipeline: Reddit (5+ subs), Tweakers, fora, marktplaatsen, en een Apify-cloud Facebook-scraper voor publieke groepen + Marketplace + pages. PCS-v0 lifecycle (`pcs.py`) staat operationeel. De `data/lead_log.csv` is per vandaag leeg — er is nog geen betalende installateur.

De founder stelt vast dat **veruit de meeste reëel-bruikbare RFQ-intent op Facebook leeft**, met name in closed groups die Apify niet zonder ingelogde sessie kan benaderen. De huidige publieke-only configuratie laat ~60-70% van het potentiële volume liggen.

### Wat deze spec IS

Het volledige ontwerp om Facebook te promoveren tot **primaire ingestiebron** voor Lead Radar, inclusief:

- Architectuur voor parallel Apify-cloud + burner-Playwright ingestie
- Setup, warming-up, ban-detection en recovery voor een dedicated burner-account
- Provenance-discipline voor closed-group leads (doctrine-bump vereist)
- Review-throughput automation om de hogere volume binnen PCS-v0 founder-cap te houden
- Lead-inventory + decay tracking voor het "supply-first, demand-later" pad
- Demo-tool om bestaande supply zichtbaar te maken aan kandidaat-installateurs
- Doctrine v0.2 met member-resolvable URL als geldige provenance-modaliteit
- Testing-strategie inclusief mockable burner-fixtures

### Wat deze spec NIET is

- Geen vervanging van de Apify-route (die blijft voor publieke surfaces)
- Geen ontwerp van installateur-onboarding of betaalflows (uit `lead-radar-site/`)
- Geen herziening van de scoring/classification engine (ongewijzigd)
- Geen meerdere-burner-army (afgekeurd — zie §10)
- Geen geautomatiseerde lead-matching (Sem assigned handmatig)
- Geen scoring-UX wijzigingen (doctrine A8 blijft)

---

## 1 — Strategische intentie

| Wat we bouwen | Wat we expliciet niet bouwen |
|---|---|
| Facebook als grootste single source | Marketplace-bidding op FB-leads |
| Closed-group toegang via member-burner | Scrape van Sem's eigen FB-profiel (account-risico) |
| Demo-tool voor kandidaat-installateurs | Real-time auto-match installateur ↔ lead |
| Doctrine v0.2 met member-resolvable URL | Verzwakking van archive-discipline (juist uitbreiding) |
| LLM-pre-screen om review-burden laag te houden | Vervanging van menselijke approval-stap (A19) |

**Founder-keuzes tijdens brainstorming (2026-05-19):**

- Operationeel doel: maximaal geautomatiseerd, beste resultaat → **single dedicated burner + Apify hybrid (Approach A)**.
- Demand-side timing: **supply-first, demand-kant later** → leads worden harvest+approved zonder directe DELIVERED-stap, leven in een inventory-pool.

---

## 2 — Architectuur

**Twee parallelle ingestie-paden, één downstream pipeline.**

```
[Apify cloud actors]                  [Burner Playwright runner]
  ├── publieke groepen                  ├── closed groups (member-only)
  ├── Marketplace queries               ├── high-value publieke groepen
  └── page-comments                     │   die Apify niet goed dekt
        │                               │
        ▼                               ▼
   data/fb_queue/apify-*.jsonl    data/fb_queue/burner-*.jsonl
        │                               │
        └───────┬───────────────────────┘
                ▼
       run_consumer._drain_fb_queue_once()
                │
                ▼
   bestaande pipeline: classifier → scorer → moderation
                │
                ▼
        APPROVED → inventory pool (NIEUW)
```

### 2.1 Wat blijft ongewijzigd

- `consumer/sources/facebook/apify_groups.py`, `apify_client.py`, `onboard.py`
- Apify-targets in `config/facebook_targets.yaml` (publieke groepen + Marketplace + pages)
- launchd plist `com.leadradar.fbapify.plist`
- Downstream pipeline (classifier, scorer, moderation, PCS state machine)
- RawPost dict-shape — burner-runner produceert byte-compatibele output

### 2.2 Nieuwe modules

| Module | Doel |
|---|---|
| `consumer/sources/facebook/burner_runner.py` | Headless Playwright runner met session-cookie persistence, scrape per groep, output naar `data/fb_queue/burner-*.jsonl` |
| `consumer/sources/facebook/burner_session.py` | Login, cookie-save/load, health-check (captcha/checkpoint detection) |
| `consumer/sources/facebook/burner_targets.py` | Read+parse van `config/facebook_burner_targets.yaml` |
| `config/facebook_burner_targets.yaml` | Closed-group target lijst (apart van Apify-targets) |
| `data/burner_state/cookies.json` | Persistente session cookies (gitignored) |
| `data/burner_state/heartbeat.csv` | Per-cycle health-check + ban-detection log |
| `com.leadradar.fbburner.plist` | launchd schedule op anti-pattern tijden |

### 2.3 Inventory-pool

Omdat supply-first betekent dat APPROVED-leads niet meteen DELIVERED worden, krijgen ze een aparte inventory-state:

- Nieuwe CSV `data/lead_inventory.csv`. Veld-schema in §6.
- Aparte CSV (niet uitbreiding van `lead_log.csv`) omdat het concept "warme voorraad" anders is dan workflow-state.
- Inventory wordt gevoed door de bestaande PCS APPROVED-transitie, niet vervanging.

### 2.4 Twee yaml-files voor targets

Bewust gescheiden: `facebook_targets.yaml` (Apify) en `facebook_burner_targets.yaml` (burner). Reden: per-groep is duidelijk welk pad hem benadert, en de burner-targets vragen extra metadata (membership-aanvraag-status, admin-vragen-template, last-active-check).

---

## 3 — Burner account: setup, warming, ban-detection, recovery

### 3.1 Eenmalige setup (~3-4 uur over 2 dagen)

1. **Gmail-account** — geen verwijzing naar Sem in naam/profiel. Nederlandse spelling, plausibele leeftijd 25-40.
2. **Virtueel NL telefoonnummer** — via SMSPVA / SMS-man (~€5/maand). Geen VoIP (FB blokkeert). Eenmalig voor registratie + 2FA-setup.
3. **FB-registratie** vanaf residential IP (Sem's thuis-IP in Amersfoort). Profielfoto via thispersondoesnotexist.com. Plaats: NL, taal: NL.
4. **Stockprofiel** — 5-10 friend-requests naar willekeurige publieke NL-profielen (~1-2 accepts verwacht), 3-5 page-likes (lokale dingen, Nederlandse media).

**Restrictie:** burner-account moet vanuit dezelfde IP-range (Amersfoort) blijven inloggen. Geen VPN-jumps, geen mobiele-data-switches. FB detecteert IP-pattern-breaks meedogenloos.

### 3.2 Warming-up (2-4 weken, organische ramp-up)

| Week | Activiteit |
|------|-----------|
| 1 | Dagelijks 10-15 min handmatig scrollen. 1-2 reacties op publieke posts. 0 group-joins. |
| 2 | 2-3 group-joins/dag (publiek of low-bar). Blijf handmatig scrollen. Beantwoord eventuele admin-vragen. |
| 3 | 5-7 group-joins/dag, inclusief closed groups met admin-aanvraag (warmtepomp-niches, regionale verbouwgroepen). Authentieke antwoorden op admin-vragen. |
| 4 | Playwright-automation start op **lage frequentie** (1×/dag). Verhoog naar 4×/dag pas na een week zonder rate-limit/captcha. |

**Schedule launchd-plist v1 (na week 4):**
- Tijden: 09:15, 13:45, 18:20, 22:05 (NIET symmetrisch met Apify's 08/12/17/21 om patroon te vermijden).
- Per cycle: max 3 groepen scrape, met 30-90s random sleep tussen groepen. Cap op 25 posts per groep per cycle.

### 3.3 Ban-detection (continu, automated)

Iedere scrape-cycle roept `burner_session.health_check()` aan. Faal-indicatoren:

- Cookie verlopen / sessie ongeldig
- Captcha-element in DOM
- "Checkpoint required" redirect
- HTTP 429 of rate-limit-banner
- Posts-count voor laatste 3 cycles = 0 (vroege indicator)

**State machine:**
- `OK` — normaal
- `WARNING` — één faalde check (continue, maar log)
- `LOCKED` — drie consecutive faalde checks (stop scraping, Telegram-alert naar Sem)

Heartbeat-CSV `data/burner_state/heartbeat.csv` schema:
```
at, status, posts_fetched, captcha_seen, rate_limited, cycle_duration_s, notes
```

### 3.4 Recovery (bij ban)

- Niet proberen door te scrapen — versnelt detectie.
- launchd-job pauzeert automatisch (`com.leadradar.fbburner.plist` disabled via wrapper-script).
- **Optie 1 — cooldown:** 3-7 dagen volledig idle, daarna handmatig inloggen. Werkt soms voor soft-limits.
- **Optie 2 — nieuwe burner:** 2-4 weken warming-up downtime. Apify-pad blijft draaien voor publieke surfaces, dus nooit volledige FB-blackout.

---

## 4 — Closed-group provenance (doctrine-collisie)

### 4.1 Het probleem

Doctrine v0.1 §00.2 eist dat `source_url` "publicly resolvable" is. Closed-group post-URLs zijn alleen resolvable voor leden van die groep. Dit breekt v0.1.

### 4.2 De oplossing — drie compenserende disciplines

**A) Verplichte archive-bundle bij approval (uitbreiding §01.3)**

Bij elke closed-group lead wordt op approval-time:
1. Volledige post-DOM gedumpt naar `data/archives/<lead_id>.html` (bestaand pattern)
2. Screenshot van de post-rendering naar `data/archives/<lead_id>.png` (NIEUW — Playwright maakt deze in dezelfde sessie)
3. SHA-256 hash van beide bestanden naar `archive_manifest.csv` met velden: `lead_id, captured_at, html_sha256, png_sha256`

**Fail-closed:** als één van de archieven ontbreekt → lead kan NIET DELIVERED worden. Doctrine A32 (nieuw).

**B) Group provenance metadata in delivery (uitbreiding §02.3)**

Bij elke closed-group lead-delivery ziet de installateur expliciet:
- "Bron: Closed Facebook-groep `<groep-naam>` (`<aantal-leden>` leden, jij bent geen lid)"
- Verifieerbaarheid-disclaimer: "URL alleen voor leden zichtbaar. Op verzoek leveren wij een archief-snapshot met SHA-256 hash binnen 24u na delivery."
- Verbatim citaat blijft verplicht (ongewijzigd).

Geen marketing-camouflage. De installateur moet kunnen zien dat het een member-only bron is.

**C) Reviewer-attestation per closed-group lead (uitbreiding §00.5)**

`reviewer_name` (Sem) wordt aangevuld met `reviewer_attestation`: vrije tekst die Sem invult bij approval, in eigen woorden:
- Voorbeeld: "Gezien in groep 'Hybride warmtepomp' op 19 mei 2026, OP is actieve groepslid sinds 2024."
- Opgeslagen in `lead_inventory.csv`, gerendered in delivery-mail.
- Vrije tekst (geen boilerplate) om A19 (rubber-stamping) te respecteren.
- Kost ~10 sec extra per approval — aanvaardbaar binnen review-throughput budget.

### 4.3 Vocab-lint uitbreiding (§02.3)

`dispatcher.py` lint-regels krijgen source-class-bewustzijn:
- Bij `source_class = burner_closed`: delivery-content mag NIET de term "publieke bron" / "publicly available" / "openbare post" claimen.
- Bij élke source-class: term "AI lead" blijft banned (bestaand).

### 4.4 Doctrine-update — formele wijzigingen

Zie §8 voor de volledige doctrine-revisielijst.

---

## 5 — Review throughput

### 5.1 Realistisch volume

Initiële schatting tijdens brainstorming was te hoog (200/dag). Realistische cijfers na correctie:

| Stap | Realistisch volume per dag |
|------|---------------------------|
| Closed groups in scope (NL, 6 niches uitgebreid) | 15-30 groepen totaal |
| Ruw scraped posts/dag totaal | ~50-200 |
| Na hard-block / fuzzy dedup / classifier | ~15-40 candidates |
| Na pre-screen (auto_present + needs_human) | ~10-30 leads voor review |
| Apify-route candidates (parallel) | ~10-30 |
| **Totaal review-burden voor Sem** | **~15-45 leads/dag** |
| Tijd-equivalent (gemengd één-voor-één) | **~15-25 min/dag** |

Binnen PCS-v0 60-min founder-cap.

### 5.2 LLM pre-screen (twee-categorisch)

Nieuwe module `consumer/processor/prescreen.py`:

- Input: lead die laag-1-filters overleeft
- Output: `prescreen_class` in `{auto_present, needs_human}`
- Prompt-categorie `auto_present`: verbatim citaat heeft expliciete RFQ-intent + regio + niche-fit ÉN één van: offerte-zoeken, installateur-zoeken, prijs-vraag, timing-indicatie
- Default-categorie `needs_human`: alles wat geen `auto_present` triggert
- Reden voor twee-categorisch ipv vierwaardig: bij realistische volumes (15-45 leads/dag) is fijnmazig classificeren overbodig
- Doctrine A8 ✓ — geen numerieke score
- Sem ziet beide categorieën in dezelfde console-view; `auto_present` staat bovenaan met snel-approve-pad

### 5.3 Console-aanpassing

`lead-radar-console/` krijgt nieuwe view `/inventory/review`:
- Default filter: `prescreen_class = auto_present`, sorted by `captured_at desc`
- Eén-voor-één review (geen batch — A19)
- Verbatim citaat + groep-bron + attestation-tekstveld verplicht zichtbaar
- Filters: per niche, per regio, per source-class
- Approve-knop disabled tot attestation-tekstveld ≥ 20 karakters bevat

### 5.4 Pre-screen kwaliteits-monitor

Nieuwe CSV `data/prescreen_metrics.csv`:
```
at, lead_id, prescreen_class, sem_decision, override_flag, override_reason
```

Wekelijks rapport: override-rate per klasse. Als `auto_present` → `sem_rejected` rate > 20%, prompt wordt herzien. Observability voor de LLM-classifier, niet stille drift.

### 5.5 LLM-kosten

~30 leads/dag × ~1500 tokens prompt+response × pricing voor lokaal Anthropic-model = **~$0.50-1/dag**. Acceptabel.

---

## 6 — Lead inventory + decay-tracking

### 6.1 Inventory CSV

`data/lead_inventory.csv` schema:

| veld | beschrijving |
|------|-------------|
| `lead_id` | join naar bestaande pipeline |
| `niche` | warmtepomp / isolatie / etc. |
| `region_nl` | provincie + plaatsnaam genormaliseerd |
| `captured_at` | wanneer harvest plaatsvond (van RawPost) |
| `approved_at` | wanneer Sem approve klikte |
| `expires_at` | `captured_at + decay_window[niche]` |
| `source_class` | `apify_public` / `burner_closed` / `paste` |
| `reviewer_attestation` | Sem's vrije tekst voor closed-group leads |
| `delivered_to` | installer_id zodra DELIVERED, anders leeg |
| `demo_used_at` | timestamp dat lead in een installateur-demo werd getoond |
| `still_warm_checked_at` | laatste hercheck door Sem |

### 6.2 Decay-windows per niche

Initiële waarden — operator kan tunen via `config.yaml`:

| Niche | Window |
|-------|--------|
| warmtepomp, airco, zonnepanelen, laadpaal | 14 dagen |
| isolatie, ventilatie, kozijnen | 21 dagen |
| dakwerk | 10 dagen |
| renovatie, cv | 7 dagen |

Window-overschrijding → state `EXPIRED` automatisch via `pcs.py` transition. Append-only event log blijft authoritative.

### 6.3 Still-warm recheck (optioneel)

Dagelijkse cron checkt leads tussen 7-14 dagen oud die nog niet `DELIVERED` zijn. Voor closed-group leads waar de burner nog steeds toegang heeft: scrape OP's recente posts in dezelfde groep. Als opvolg-post "ik heb iemand gevonden" zegt → state `EXPIRED` met reason `op_resolved`.

Initieel uit. Aanzetten als pool > 100 leads bevat.

### 6.4 Realistische pool-grootte

- ~7-15 APPROVED/dag × gemiddelde 14-dagen-window = **peak inventory ~100-200 leads**.
- Bij 0 installateurs (huidige situatie): pool groeit tot ~150-250 leads en stabiliseert door expiries.
- Snelle drop-off als delivery start: ~30-40% binnen 7 dagen DELIVERED bij actieve installateur-side.

### 6.5 Wat dit NIET wordt

- Geen ranking-algoritme over de pool (A8 — geen scores)
- Geen "trending leads" widget (§02.2 — feiten, niet aanbevelingen)
- Geen automatische match installateur ↔ lead (Sem handmatig)

---

## 7 — Demo-tool: "kijk wat we hebben in jouw regio"

### 7.1 Doel

Kandidaat-installateur ziet hoeveel verse, gerelevante leads er in zijn niche + regio liggen — zonder dat hij ze al kan lezen. Bewijst supply zonder weggeven van het product.

### 7.2 Drie niveaus

**Niveau 1 — Geaggregeerde teaser (publiek, geen auth)**

- Pagina: `lead-radar-site/src/app/pilot/zien-wat-er-is/page.tsx`
- Installateur kiest niche + regio (provincie + straal: 25/50/100 km)
- Toont: "**23 actieve leads** in jouw scope. Bron-verdeling: 14 closed FB-groepen, 6 publieke groepen + Marketplace, 3 Reddit. Oudste: 4 dagen. Nieuwste: gisteren."
- Geen verbatim, geen URL, geen namen
- Doctrine §02.2 (feiten, geen claims) ✓

**Niveau 2 — Eén gratis lead-preview met locatie-redactie (pilot-aanvraag-flow)**

- Installateur klikt "Toon mij één voorbeeld" → moet bedrijfsnaam + KvK + e-mail invullen
- Toont één willekeurige `auto_present` lead uit zijn scope met:
  - Verbatim citaat (max 200 chars)
  - Niche-fit + intent-typering (categorisch)
  - Regio op gemeente-niveau (geen straat, geen postcode)
  - Bron-klasse: "Closed FB-groep — naam van groep zichtbaar"
  - Captured + age in dagen
- Geen contactgegevens, geen volledige post-URL, geen archief-bundle
- Eén-per-installateur-per-week (rate-limit op KvK)

**Niveau 3 — Volledige lead = betaalde PPL pilot (€0 voor eerste 5, €75/lead daarna)**

Bestaande pricing-flow in `lead-radar-site/src/content/pricing.ts`.

### 7.3 Technisch

- Nieuwe Next.js-route `lead-radar-site/src/app/pilot/zien-wat-er-is/page.tsx`
- API-laag: `lead-radar-console/src/app/api/inventory/aggregate/route.ts` retourneert counts (geen content)
- Region-resolution: `lead-radar/utils/regions.py` met provincie + plaats mapping
- Geen postcode-API in v1

### 7.4 Wat dit NIET wordt in v1

- Geen real-time dashboard "mijn leads" voor de installateur (komt later, na pilot bewijst)
- Geen auto-match (Sem handmatig)
- Geen scoring-slider, geen sorteren (A8)
- Geen "vergelijkbare leads" recommendations

### 7.5 Conversie-pad

1. Sem benadert installateur cold/warm via LinkedIn/koud-mail
2. Stuurt link naar geaggregeerde teaser: "23 leads in jouw scope, kijk hier zelf"
3. Installateur klikt door, ziet counts, klikt "voorbeeld"
4. Installateur ziet één redacted HOT-lead, voelt "dit is echt"
5. Vraagt pilot-flow aan (5 gratis), betaalt vanaf lead 6

**Conversie-metric voor bewijslast:** teaser-view → preview-aanvraag → pilot-aanvraag funnel.

---

## 8 — Doctrine v0.2 deltas

**Bron-document:** `lead-radar/specs/doctrine/trust-provenance-moderation.md`

Version bump v0.1 → v0.2 vereist (section change = bump per revision rules).

### 8.1 Wijzigingen sectie-inhoud

| Sectie | Wijziging |
|--------|-----------|
| §00.2 | Uitgebreid: resolvable URL is óf (a) publicly resolvable, óf (b) member-resolvable met verplichte archive-bundle + reviewer-attestation per §00.2.b |
| §00.2.b | NIEUW: Definitie closed-group provenance (groep-naam, ledenaantal, member-only disclaimer, archive-bundle binnen 24u op verzoek) |
| §00.5 | Ongewijzigd inhoudelijk — reviewer-attestation is uitbreiding van accountable reviewer-name pattern |
| §01.3 | Uitgebreid: archive-capture krijgt screenshot toegevoegd voor closed-group leads |
| §02.3 | Vocab-lint krijgt source-class-aware regels — `burner_closed` mag niet "publieke bron" claimen |

### 8.2 Appendix-wijzigingen

| Item | Wijziging |
|------|-----------|
| A32 | NIEUW: "Closed-group lead delivered zonder volledige archive-bundle (HTML + screenshot + hash) = MAG NOOIT. Fail-closed." |
| B.1 | Uitbreiding canonical term: "verifiable member-witnessed intent" als sub-categorie van "verifiable public intent" voor closed-group bron |
| B.2 | Geen nieuwe banned terms; bestaande lint-regels worden source-class-aware (zie §02.3) |

### 8.3 Changelog-entry

Verplicht onderaan doctrine-document:
```
## v0.2 — 2026-05-XX
Member-resolvable URL toegevoegd als geldige provenance-modaliteit voor closed
Facebook groups. Drie compenserende disciplines: verplichte archive-bundle,
group provenance metadata in delivery, reviewer-attestation. Appendix A32
toegevoegd (fail-closed bij ontbrekende archive-bundle). Vocab-lint source-
class-aware. Geen breuk in §00.5 accountable reviewer pattern.
```

---

## 9 — Testing-strategie

### 9.1 Unit tests (`lead-radar/tests/`)

| Bestand | Wat |
|---------|-----|
| `test_burner_session.py` | Cookie persistence, expiry-check, health-check DOM-parsing |
| `test_burner_runner.py` | RawPost shape conformance (byte-compatibel met Apify-output), groep-filter logica, rate-limit-respect, random-sleep distribution |
| `test_lead_inventory.py` | CSV schema, expiry-window-berekening per niche, append-only EXPIRED state-transitions |
| `test_prescreen_classifier.py` | Twee-categorisch output, override-rate monitoring, prompt-stabiliteit (snapshot test) |
| `test_demo_aggregate.py` | Count-only API retourneert geen verbatim/URL, regio-resolutie, KvK rate-limit |

### 9.2 Integration tests

| Bestand | Wat |
|---------|-----|
| `test_fb_dual_path_pipeline.py` | Apify-queue én burner-queue beide gemockt, drain merged, downstream produceert verwachte APPROVED-leads |
| `test_closed_group_provenance.py` | Closed-group lead zonder archive-bundle → DELIVERED faalt (fail-closed). Met volledige bundle → gaat door |
| `test_doctrine_v02_vocab_lint.py` | Closed-group delivery-content die "publieke bron" claimt wordt geblokkeerd |

### 9.3 End-to-end (Playwright, `lead-radar-console/tests/`)

| Bestand | Wat |
|---------|-----|
| `inventory-review.spec.ts` | Sem opent `/inventory/review`, ziet één-voor-één UI met verbatim + bron + attestation-tekstveld, approves één lead. Verifieert dat batching disabled is en attestation verplicht ≥20 karakters |
| `demo-aggregate.spec.ts` | Bezoeker kiest niche+regio op publieke pilot-pagina, ziet count-aggregaten zonder verbatim/URL |

### 9.4 Manuele test-protocol (geen automation mogelijk)

- **Burner warming-up:** dagelijks `heartbeat.csv` review eerste 4 weken. Success-criterion: "no captcha gezien, no rate-limit gezien" gedurende 7 consecutive dagen voor automation aan gaat
- **Closed-group archive-bundle visual review:** één per week handmatig HTML + screenshot openen, bevestigen dat ze bruikbaar zijn voor eventuele disclosure-aanvraag

### 9.5 Wat we expliciet NIET testen

- Geen integratie-test tegen live FB (ToS-risico, non-deterministische output, ban-risico)
- Geen load-test op burner-pipeline (volume is laag, ~50-200 posts/dag)
- Geen scoring-correctness test (scoring engine ongewijzigd)

---

## 10 — Non-goals

Expliciet uit scope:

- **Meerdere burners (army)** — afgekeurd in brainstorming. Te grote operationele overhead, 6-9u opzet, 8 weken voor full operationeel. Single burner voldoende.
- **Volledig FB-only (Apify droppen)** — afgekeurd. Apify-route blijft als veilige fallback voor publieke surfaces.
- **Auto-match installateur ↔ lead** — Sem assigned handmatig. Doctrine "één lead → één installateur" intact.
- **Real-time dashboard voor installateurs** — uitgesteld tot na pilot conversie-bewijs.
- **BE-FR / DE / EU markten** — uit scope, NL-only.
- **Profile-scraping op FB** — alleen group-feed posts + post-comments. Profiel-inspectie triggert FB-review.
- **Proxy-rotatie binnen sessie** — FB detecteert IP-jumps direct.
- **Auto-like / auto-comment via burner** — versnelt detectie.

---

## 11 — Open vragen

Zaken die deze spec NIET beslist, en die tijdens implementatie of operatie opgelost moeten worden:

1. **Burner-account naam + persona-details** — wordt eenmalig bepaald door Sem bij setup. Niet in deze spec gefixeerd.
2. **Exacte target-lijst closed groups** — `config/facebook_burner_targets.yaml` wordt door Sem opgebouwd over warming-up periode. Initieel: 15-30 groepen, gespreid over 6 niches.
3. **KvK rate-limit-strategie voor demo-tool** — IP-based als KvK ontbreekt? Beslissen tijdens implementatie.
4. **Tijd-zone-handling regio-resolutie** — alleen NL of ook BE in v1? Doctrine zegt NL/BE-markt, codebase ondersteunt beide. Beslissen tijdens implementatie demo-tool.
5. **Notificatie-pad bij burner LOCKED-state** — Telegram-alert is default; e-mail-fallback nodig? Te beslissen tijdens implementatie burner-runner.

### 11.1 Reeds besloten (geen open vraag)

- **Doctrine v0.2 commit-timing:** geconfirmeerd als eerste implementatie-task. Doctrine moet gemerged zijn voor de eerste burner-lead approve-flow draait. Anders breekt fail-closed in moderatie/delivery.
- **Scope-check (informatief voor writing-plans):** deze spec dekt 6 logisch verbonden sub-implementaties (doctrine, burner-runner, archive-discipline, pre-screen+console, inventory+decay, demo-tool). Te groot voor één plan; verwacht dat `superpowers:writing-plans` dit phaseert in 3-4 sub-plannen.

---

## 12 — Definition of Done

De spec is geïmplementeerd wanneer:

1. ✅ Doctrine v0.2 gecommit en gemerged in main
2. ✅ `consumer/sources/facebook/burner_*.py` modules unit-tested en geïntegreerd
3. ✅ `config/facebook_burner_targets.yaml` aangemaakt met minimaal 5 closed groups
4. ✅ launchd plist `com.leadradar.fbburner.plist` geïnstalleerd op Sem's Mac
5. ✅ Burner-account 4 weken warming-up gepasseerd, automation aan
6. ✅ Eerste closed-group lead succesvol APPROVED met volledige archive-bundle
7. ✅ `lead_inventory.csv` operationeel met decay-windows per niche
8. ✅ LLM pre-screen `auto_present` / `needs_human` werkend met < 20% override-rate na eerste 50 leads
9. ✅ Demo-tool publiek bereikbaar op `lead-radar-site/pilot/zien-wat-er-is`
10. ✅ Eerste betaalde installateur of pilot-aanvraag binnengekomen via demo-tool funnel

Items 1-9 zijn implementatie-deliverables. Item 10 is de business-validatie waar dit allemaal voor staat.

---

**Volgende stap na founder-review:** invocatie van `superpowers:writing-plans` om een gefaseerd implementatie-plan op te stellen.
