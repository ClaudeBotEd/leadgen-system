# Lead Radar — Autonomy Architecture Design (Noord-Ster)

**Status:** Awaiting founder review (na brainstorming-sessie 2026-05-18)
**Auteur:** Claude Opus 4.7 (i.s.m. founder, sessie 2026-05-18)
**Datum:** 2026-05-18
**Branch:** `feat/facebook-scraper`
**Relateerd aan:** `2026-05-17-supply-expansion-design.md` (upstream-spec voor supply; deze spec definieert de bovenliggende intelligence-operations laag)
**Type:** Noord-Ster operating-system ontwerp — *niet* implementatie-spec voor één feature, maar het control-systeem waaraan alle toekomstige sub-specs zich verantwoorden.

---

## 0 — Context

Lead Radar is operationeel een consumer-pipeline die publieke signalen scrapet, scoort, en classificeert tot leads. Per 2026-05-18 zijn de volgende onderdelen live in productie:

- 10+ ingestie-bronnen (Facebook via Apify, Reddit, Tweakers, fora, marktplaatsen)
- Sellability-gate, fuzzy dedup, LLM-verificatie
- Launchd-orchestratie (3× daags), heartbeat-monitoring, Telegram run-digests
- Google Sheets sync, source-attribution per niche
- Een minimale lifecycle-primitief (`pcs.py`) met 6 states: `NEW / APPROVED / DELIVERED / OUTCOME / REJECTED / EXPIRED`

De supply-uitbreiding (Plan A + Plan B) is afgerond; 7-daagse observatie-window loopt tot 2026-05-25.

Wat ontbreekt is **niet meer supply** — wat ontbreekt is het **operating system** dat menselijke en agent-beslissingen op een schaalbare, veilige, *en* leerbare manier laat samenleven. Dat operating system is de scope van deze spec.

### Wat deze spec IS

Het ontwerp van de **autonomy architectuur** — het control-systeem dat bepaalt:

- Welke beslissingen in Lead Radar door mensen worden genomen, welke door agents, en hoe die verdeling evolueert
- Onder welke voorwaarden een beslissing van menselijk naar (semi-)autonoom mag promoveren
- Hoe de architectuur zichzelf beschermt tegen drift, schade, governance-bloat, en operator-overload
- Hoe leersnelheid expliciet wordt gemeten en beschermd
- Welke datasets door het systeem *zelf* worden gegenereerd en hoe die de moat vormen

### Wat deze spec NIET is

- Geen implementatie-spec voor de Operator Intelligence Console (volgende deliverable)
- Geen ontwerp van de uitgebreide lifecycle-state-machine (volgt als sub-spec)
- Geen ontwerp van scoring-, routing- of classificatie-algoritmes (worden gegeven workflows die *binnen* deze architectuur opereren)
- Geen ontwerp van installateur-onboarding flow
- Geen ontwerp voor BE-FR / DE / EU markten (uitgesteld tot na pilot)

Deze spec definieert de **regels van het spel**. Andere specs definiëren de spelers en zetten.

---

## 1 — Strategische intentie

Lead Radar wordt een **intelligence operations company**, niet een AI SaaS. Concreet betekent dat:

| Wat we bouwen | Wat we expliciet *niet* bouwen |
|---|---|
| Operationele intelligentie-infrastructuur | Generic AI-workflow automation |
| Mission-critical control systems | Dashboard theater |
| Operator-gecalibreerde besluitvorming | "Set and forget" autonomie |
| Proprietary datasets door operationele discipline | Veronderstelde moats op basis van openbare data |
| Vertrouwens-systemen (installateurs, leads) | Marketplace bidding mechanics |

### Founder-principes (philosophical bedrock)

Deze vijf principes vormen de niet-onderhandelbare ondergrond:

1. **Quality > volume.** Lead-yield optimalisatie mag nooit ten koste van vertrouwen of dataset-integriteit gaan.
2. **Operational trust > automation hype.** Een operator die "ja" tegen een lead zegt draagt verantwoordelijkheid. Een agent doet dat niet.
3. **Intelligence > dashboards.** Dashboards rapporteren over werkelijkheid; intelligence verandert hem.
4. **Human review > premature AI decisions.** Agents zijn assistenten tot proprietary bewijs het anders aantoont — niet op basis van algemene model-benchmarks.
5. **Conversion learning > growth metrics.** Het enige getal dat fundamenteel meetelt is: hebben we een installatie veroorzaakt? Alles daarboven is afgeleide.

### Strategische uitkomst

Een operating system dat:

- Schaalt van 30 tot 300 leads/dag zonder her-architectuur
- Bewijs accumuleert tot een moat (per beslissings-categorie, per workflow)
- Tegelijk weerstand biedt tegen *governance theater* én tegen *roekeloze autonomie*
- Zelf-bewust is over zijn eigen trade-offs (Safety × Simplicity × Learning Velocity)
- Een proprietary dataset opbouwt die concurrenten niet kunnen kopiëren omdat ze geen operator-laag hebben

---

## 2 — Operationele variabelen (vastgelegd in brainstorming 2026-05-18)

Vijf vars vormen de calibratie van het ontwerp:

| Variabele | Waarde | Implicatie |
|---|---|---|
| **Staffing horizon** | 3-5 person ops team binnen 12 maanden | Echte multi-operator architectuur, role-based access, escalatie wel definiëren maar niet bouwen V0 |
| **Volume target** | Quality-first, volume emergent (ontwerp elastisch tussen ~30 en ~300 leads/dag) | Schaal-afhankelijke componenten expliciet markeren |
| **Exclusiviteitsmodel** | "Effectief exclusief" met expliciete reroute-gates (TIMED-OUT, REJECTED-by-installer) | Lifecycle moet reroute-edges modelleren; audit moet bewijzen dat nooit twee installateurs gelijktijdig claimen |
| **Build/buy posture** | Build de moat, buy de rest. **Onze DB is van ons. Tools lezen daaruit; ze ZIJN niet onze DB.** | Workflow Profile, decision-log, attribution-chain in owned Postgres; Retool/Metabase/Sentry/Linear/Telegram als commodity-laag |
| **Geografische scope** | NL + BE-NL alleen | BE-FR/DE/EU zijn separate toekomstige specs |
| **Agent-decisie filosofie** | Agent-assisted by default; agent-decided promotie ALLEEN met proprietary-dataset bewijs | Replaces "automate-or-not" framing — verfijnt naar promotion-with-evidence |

---

## 3 — Out of scope (expliciet uitgesloten in dit document)

- Implementatie van de Operator Intelligence Console (volgende ontwerpcyclus)
- Specifieke scoring-prompts en classificatie-modellen
- Sales / outreach-flow naar installateurs
- Installateur-onboarding flow
- Aanpassingen aan bestaande consumer-pipeline-code (deze is "gegeven")
- Lifecycle-state-machine uitbreiding (subsequent sub-spec na console v0)
- Pricing-architectuur en commerciële flows
- Cross-locale ondersteuning (BE-FR, DE, EU)

---

## 4 — Definition of done (op architectuur-niveau)

Dit document is "done" wanneer:

1. De V0-inventaris (Sectie 12) implementeerbaar is door een development team zonder verdere architecturele vragen
2. De deferred-inventaris (Sectie 13) een duidelijke trigger-conditie heeft per component
3. De Operator Intelligence Console v0 ontwerp-sessie kan starten vanuit deze spec als contract
4. Founder heeft expliciet akkoord gegeven op alle vier delen (1, 1B, 1C, 2)

Niet vereist voor "done":

- Implementatie zelf (volgt via writing-plans skill)
- Console UI ontwerp (volgt na deze spec)
- Numerieke kalibratie van thresholds (waarden in deze spec zijn vertrekpunten, te tunen tegen echte data — zie Sectie 14)

---

## 5 — Deel 1: Autonomy Tiers, Risk Classes, Promotion/Demotion

### 5.1 Autonomy Tiers (T0-T4)

Vijf trappen van besluit-autonomie. Elke beslissing in het systeem zit op precies één tier, per moment, per workflow.

| Tier | Naam | Wie beslist | Wat agent doet | Sampling | Reversibiliteits-eis |
|---|---|---|---|---|---|
| **T0** | Human-only | Mens leest brondata direct | Niets — agent mag mens niet "primen" | n.v.t. | n.v.t. |
| **T1** | Agent-assisted | Mens met agent-aanbeveling | Classificeert, scoort, vat samen, schrijft concept | 100% (elke beslissing logged) | Vrij of goedkoop |
| **T2** | Agent-decided, verplichte steekproef | Agent autonoom, mens reviewt sample | Volledige beslissing | 10-20% blind random, geen exceptie | Goedkoop |
| **T3** | Agent-decided, exception-only | Agent autonoom, mens bij low-confidence of downstream alert | Volledige beslissing + zelfeval | 1-5% random + alle exceptions | Goedkoop |
| **T4** | Volautonoom met passieve monitoring | Agent autonoom | Volledige beslissing | <1% random, voornamelijk drift-driven | Vrij/goedkoop |

**Kritische clausule:** T4 is *aspirationeel*. De meeste workflows hebben een **terminal tier** lager dan T4 — ze mogen niet promoveren ongeacht het bewijs. Welke workflows terminal-T1 of terminal-T2 zijn wordt expliciet vastgelegd via risk class (5.2) en CoF circuit breaker (6.1).

### 5.2 Decision Risk Classes (met max-tier plafond)

Niet elke beslissing mag dezelfde trap volgen. Classificatie in een risk class is een hard plafond.

| Risk Class | Voorbeelden | Plafond | Waarom |
|---|---|---|---|
| **Existential** | Prijs, contractvoorwaarden, refund-policy, brandkeuzes | **T1 forever** | Eén fout = bedrijf in gevaar. Statistiek redt dit niet. |
| **Trust-load-bearing** | Lead-levering aan installateur, installateur-trust-score, dispute-resolutie, source-onboarding | **T2 max** | Fout = relatie of reputatie beschadigd, deels onomkeerbaar. Verplichte steekproef voor altijd. |
| **Dataset-defining** | Conversie-registratie, outcome-attributie | **T1 forever** | Dit is de bron van de proprietary dataset. Agent-decided hier = dataset-corruptie = vergiftiging van het hele moat-mechanisme. |
| **Quality-load-bearing** | Signaal-classificatie, intent-scoring, source-credibility-update, niche-detectie | **T3 max** | Fout = kwaliteitsdegradatie, doorgaans herstelbaar. Drift moet altijd zichtbaar zijn. |
| **Routine factual** | Dedup matching, taaldetectie, geo-extractie, normalisatie | **T4 toegestaan** | Fout = goedkoop herstelbaar, deterministisch verifieerbaar tegen grondwaarheid. |

**Niet-promoteerbaar:** *Dataset-defining* en *Existential* zijn de twee non-promoteerbare klassen. Geen hoeveelheid bewijs verhoogt hun plafond. Dit is de ethische bedrock.

### 5.3 Promotion Policy — 8 gates met AND-logica

Een workflow promoveert van T_n naar T_{n+1} alleen als **alle** van het volgende waar zijn:

1. **Sample size**: ≥ N beslissingen geobserveerd in huidige tier (T1→T2: N=500; T2→T3: N=2.000; T3→T4: N=10.000)
2. **Agreement rate**: agent-mens agreement ≥ θ% over rollende 30 dagen (T2: θ=98; T3: θ=99; T4: θ=99.5) — *thresholds worden parameteriseerd door CoF in 6.5*
3. **Time-at-tier**: ≥ T dagen op huidige tier (T2: 30d; T3: 90d; T4: 180d) — *ook CoF-geparameteriseerd*
4. **Drift stability**: agreement rate vertoont geen significante daling over laatste D dagen (T2: 14d; T3: 30d; T4: 60d)
5. **Reversibility check**: hoogste reversal-cost in workflow is ≤ klasse-plafond
6. **Rollback drill**: rollback-procedure is recent getest in een drill (≤90 dagen)
7. **Incident-free**: geen open of recent incident (≤30 dagen) in deze workflow
8. **Lead-operator sign-off**: founder of senior ops tekent expliciet af. **De promotie-beslissing zelf is een T0-beslissing.**

### 5.4 Demotion Policy — automatisch op één van

- Agreement rate daalt ≥ X% over rollende 7 dagen (X = CoF-geparameteriseerd, default 1.0%)
- Drift-detector vuurt N keer in T dagen
- Operator override-rate stijgt > baseline + X%
- Manual kill-switch ingedrukt
- Downstream outcome (conversie, installateur-klacht, refund-rate) degradeert > X%

**Demotion is altijd één tier per keer.** Geen "T3 → T0" sprong behalve via globale kill-switch. Reden: één-tier-per-keer voorkomt overcorrectie en houdt de operator in de loop tijdens incident-respons.

### 5.5 Wat deze sectie uitsluit

| Discipline | Sluit uit |
|---|---|
| AND-logica op 8 gates | "We hebben 98% accuracy dus promotie" |
| Lead-operator sign-off als T0 | Geautomatiseerde promotie ook bij groene metrics |
| Tier-plafond per risk class | "Goede metrics op classificatie dus we promoten installateur-scoring ook" |
| Conversie-registratie permanent terminal-T1 | Ontstaan van de dataset via de agent zelf |
| Automatische demotion | "We wachten op de meeting volgende week" tijdens drift |

---

## 6 — Deel 1B: CoF Vector, Latency Class, OCL Budget, Workflow Profile

### 6.1 Cost of Failure (CoF) — 5-component vector per workflow

CoF vervangt de scalaire "reversibility" uit Deel 1. Elke beslissing krijgt een **CoF-vector**, niet één getal.

| Component | Wat het meet | Voorbeelden van hoog | Hoe gemeten |
|---|---|---|---|
| **CoF.financial** | Directe euro-kost van een fout | Refund €75-€500, infra-doorberekening | Eurobudget per fout |
| **CoF.installer** | Relatieschade × LTV-installateur | Slechte lead = churn = €10k+ LTV verlies | P(churn) × LTV |
| **CoF.exclusivity** | Brand-promise schade | Twee installateurs claimen dezelfde lead | Aantal exclusiviteit-breaches |
| **CoF.dataset** | Corruptie van proprietary dataset | Foutieve conversie-registratie → vergiftigt promotion-evidence van álle workflows | Cascade-multiplier |
| **CoF.ops_cascade** | Downstream operationele kost | Verkeerde classificatie → verkeerde routing → klacht → refund-handling | Operator-uren per fout |

**Architecturele consequenties:**

1. **CoF-gewogen agreement-drempels** vervangen de vaste 98/99/99.5%:

   `θ_required = θ_base + (max(CoF_vector) − CoF_baseline) × k`

   Concreet: workflow met `CoF.exclusivity=hoog` vereist 99.7% agreement voor T2-promotie; workflow met alles laag mag op 96%.

2. **CoF-aware sampling**: T2-workflow met hoge CoF krijgt 30-50% sample; lage CoF 10-20%. Sampling is een **CoF-functie**, geen constante.

3. **CoF circuit breaker**: zodra één CoF-component "catastrophic" scoort (dataset-corruptie of exclusiviteits-breuk), wordt de workflow **gepind op T1 of lager**, ongeacht risk class. Dit is een hard override op het risk-class plafond.

4. **Demotion-gevoeligheid** schaalt met CoF: 0.5% drift triggert demotion voor hoge-CoF; 2% voor lage-CoF.

### 6.2 Latency Class & Fallback Policy

Vier latency-budgetten:

| Latency Class | Budget | Voorbeelden |
|---|---|---|
| **L0** | <60s | Abuse-detection (signaal lijkt adversarial → block intake) |
| **L1** | <1u | High-intent inbound ("zoek installateur voor volgende week") |
| **L2** | <24u | Routine HOT/WARM lead-levering, dispute-respons |
| **L3** | <7d | Source-credibility tuning, conversie-registratie, installateur-score-review |

**Verplichte Fallback Policy per workflow** met Tier ≤ T1 én Latency < L3:

- **F-A: Managed Overflow** — tijdelijk auto-promotie naar volgende tier met verhoogde sample-rate (bijv. T1 → T2 met 30%). **Pre-authorization door lead operator vereist.**
- **F-B: Degraded-SLA Queue** — workflow blijft op huidige tier, "achterstallig" gemarkeerd, alert naar volgende-laag operator.
- **F-C: Conservative-Default** — bij geen operator: kies de niet-doen optie (lead NIET leveren, dispute NIET resolven). Default-naar-veilig.

**Latency × CoF interactie:** workflows met L0/L1 én hoge CoF vereisen 24/7 oncall (geen F-A toegestaan) en latency-aware kill-switch: workflow pauzeert automatisch buiten kantooruren in plaats van fallback-naar-autonomie.

**Forbidden rationale:** "we halen de latency niet" mag NOOIT promotie-reden zijn. Bij latency-druk: capacity toevoegen of Fallback-Policy invoeren, niet architectuur laxer maken.

### 6.3 Operator Cognitive Load (OCL) Budget

Modellering van operationele realiteit:

| Review-complexiteit | Tijd/review | Sustained throughput | Voorbeeld |
|---|---|---|---|
| **Routine** | 5-15s | 1.000-1.500/dag | Lead-levering approval op HOT-scores >85 |
| **Medium** | 30s-2min | 200-400/dag | Borderline classificatie, dispute-respons |
| **Complex** | 10-30min | 30-80/dag | Installateur-score wijziging, conversie-registratie |

Met 3-5 ops-team + 20-30% context-switch overhead: **effectieve dagcapaciteit ≈ 2.500-5.000 routine OR 500-1.200 medium OR 80-250 complex per dag**, niet additief.

**Architecturele consequenties:**

1. **OCL-budget per workflow** in Workflow Profile (max-operator-minuten/dag)
2. **Operational Headroom Monitor** (cross-workflow): groen <60%, geel 60-80%, oranje 80-100%, rood 100% met forced action
3. **Fatigue-weighted agreement scoring**: review-evidence is fatigue-gewogen (laatste uur shift: 0.6×; weekend-avond: 0.4×; fresh-morning: 1.0×). Voorkomt promotie op basis van vermoeide bevestigingen.
4. **Alert precision discipline**: alert-queue moet ≥70% precision halen (>30% false alerts → alert-blindness); auto-aanscherping bij onderschrijding
5. **Decision-repetition fatigue**: bij ≥5 vergelijkbare cases/operator/dag → UI-signaal "5e vergelijkbare case vandaag" + auto-batch
6. **Weekend/off-hours policy per workflow**: hoog-CoF pauzeert standaard met F-C; lage-CoF mag F-A draaien

### 6.4 Workflow Profile — het bindende artefact

Elke workflow heeft een formeel **Workflow Profile** (YAML/JSON in owned database, versioned). Dit is het document dat de autonomy-architectuur leest om te weten hoe te handelen.

```yaml
workflow_id: lead_delivery_routing
description: "Operator beslist welke installateur een goedgekeurde lead krijgt"

profile_level: standard                  # light | standard | critical
risk_class: trust_load_bearing           # → T2 max
current_tier: T1
terminal_tier: T2                        # nooit hoger

cof_vector:
  financial: low                         # €75 refund max
  installer_relationship: high           # P(churn) × €10k LTV
  exclusivity: high                      # core brand promise
  dataset_corruption: medium             # routing data informeert installateur-scoring
  ops_cascade: medium

cof_circuit_breakers:                    # als deze afgaan: forceer T1
  - exclusivity_breach_risk_per_decision > 0.1%

latency_class: L2                        # sub-day budget
sla_budget_minutes: 240                  # 4u operator-respons-doel
fallback_policy: F-B                     # degraded-SLA queue + alert
out_of_hours_policy: pause               # nooit fallback-naar-autonomie buiten kantooruren

ocl_budget:
  per_operator_minutes_per_day: 30
  complexity: medium
  expected_volume_per_day: 50

promotion_thresholds:                    # parameterized van defaults
  agreement_rate: 0.997                  # verhoogd vanwege CoF.exclusivity=high
  sample_size: 800
  time_at_tier_days: 60
  drift_window_days: 21

demotion_triggers:
  agreement_drift_pct: 0.5
  override_rate_baseline_delta_pct: 1.0

simplicity_audit:
  last_governance_review: 2026-05-18
  controls_under_review: []
  candidate_for_simplification: false

learning_targets:
  days_to_confidence_target_days: 45
  unresolved_ambiguity_pct_trend: decreasing
  taxonomy_evolution_per_quarter_min: 1

sandbox_links:
  current_experiments: []

owner: founder
last_reviewed: 2026-05-18
```

Workflow Profiles zijn **zelf data**, niet documentatie. Wijzigingen zijn versie-gecontroleerd, vereisen lead-operator sign-off, en zijn zelf T0-beslissingen.

### 6.5 Geparameteriseerde promotion/demotion thresholds

De 8 gates uit 5.3 staan, maar drie zijn nu CoF/Latency/OCL-geparameteriseerd:

| Gate | Origineel | Nu geparameteriseerd |
|---|---|---|
| #2 Agreement rate | Vast 98/99/99.5% | `θ_base + f(CoF_max)` |
| #3 Time-at-tier | Vast 30/90/180d | Schaalt met CoF |
| #4 Drift stability | Vast window | Korter window voor hogere CoF |
| **#9 Headroom (nieuw)** | n.v.t. | Workflow ≤80% van OCL-budget — anders capacity-actie, geen promotie |
| **#10 Fatigue (nieuw)** | n.v.t. | Promotion-evidence is fatigue-gewogen, niet rauwe agreement-count |

Demotion-triggers krijgen er twee bij:
- **OCL-overflow**: >100% van budget over ≥3 dagen → forceer Managed Overflow of capacity-actie
- **Alert precision drop**: alert-queue precisie zakt onder 70% → workflow auto-pause tot operator-actie

### 6.6 Drie concrete voorbeeld-workflows

**Voorbeeld 1: Lead-levering routing** (Trust-load-bearing, CoF.exclusivity=high)

```
Risk Class: Trust-load-bearing → T2 max
CoF circuit breaker: exclusivity-breach → T1 gepind
Effectief plafond: T1 forever (zolang exclusiviteit kernbelofte blijft)

Latency: L2 (sub-day)
Fallback: F-B (degraded queue, alert)
Out-of-hours: pause

OCL: medium complexity, ~30 min/operator/dag bij 50 leads/dag
Headroom-check: 3-pers team = 90 min/dag totaal → ruim binnen budget tot ~150 leads/dag

Operator flow: lead arriveert in Retool queue → agent toont
  - voorgesteld installateur (rangorde van 3)
  - distance, fit, capaciteit-status, recente conversie-rate
  - draft notificatie-email
Operator klikt "Approve" of "Kies andere" → audit log → lead gaat de deur uit
```

**Voorbeeld 2: Signaal-classificatie heat-pump intent** (Quality-load-bearing, CoF medium)

```
Risk Class: Quality-load-bearing → T3 max
CoF vector: alle componenten medium → promotie tot T3 mogelijk

Latency: L1 (sub-hour ideal, L2 acceptabel)
Fallback: F-A (managed overflow naar T2 met 30% sample tijdens piek)
Out-of-hours: F-A toegestaan, CoF medium

OCL: complex (1-3min per ambigue review)
  - T1 100% review = 500 signalen × 1.5min = 12.5u/dag → onhaalbaar voor klein team
  - Implicatie: T1 mag alleen voor ambigue-band (confidence 40-75), niet voor alle signalen
  - High-confidence (>90%): route naar T2 vanaf dag 1
  - Ambigue band: T1, dit is waar leer-evidentie groeit

Operator flow: agent classificeert → alleen 40-75 band in Retool queue
  → operator ziet brontekst + 3 kandidaat-categorieën + agent-onderbouwing
  → klikt categorie of "geen intent"
  → audit log met agent-aanbeveling, operator-keuze, agreement Y/N
```

**Voorbeeld 3: Conversie-registratie** (Dataset-defining, terminal T1)

```
Risk Class: Dataset-defining → T1 forever
CoF.dataset = catastrophic → cascading corruptie risk

Latency: L3 (weken)
Fallback: niet van toepassing
Out-of-hours: pause

OCL: complex (operator stuurt installateur mail, parseert antwoord, registreert)
  - ~15min per conversie-event
  - Volume: bij €75/lead en 100 leads/maand en 30% conversie = 30 events/maand = ~7.5u/maand

Operator flow: 14 dagen na lead-levering → agent stuurt automatische follow-up draft
  → operator reviewt draft, klikt "Send"
  → installateur antwoordt
  → agent parseert antwoord, pre-vult conversie-formulier
  → operator verifieert + klikt "Save"
  → audit log = grondwaarheid voor promotion-evidence van alle andere workflows

Bron-van-waarheid die ALLE andere promoties valideert.
Agent mag hier nooit "decided" worden, ook niet bij 99.99% agreement.
```

### 6.7 Wat deze sectie uitsluit

| Discipline | Sluit uit |
|---|---|
| CoF als 5-vector | Eén-getal "reversibility" verbergt component-specifieke risk |
| CoF circuit breaker | "Goede metrics dus promotie" als exclusiviteit op het spel staat |
| Latency-pressure ≠ promotion-reason | Architectuur laxer maken om SLA te halen |
| Fatigue-weighted evidence | Promotie op vermoeide bevestigingen |
| Workflow Profile als versioned data | Stille architectuur-wijzigingen in prompt/code |
| Out-of-hours pause voor hoog-CoF | Stille degradatie buiten zicht van het team |
| Conservative-default als fallback | "Default-naar-doorgaan" — altijd default-naar-veilig |

---

## 7 — Deel 1C: Simpliciteit, Sandbox, Learning Velocity

### 7.1 Simplicity Pressure — governance moet verdiend worden

**Kern-principe:** *Default to the lightest governance that still preserves trust and reversibility. Heavier controls must be earned by demonstrated risk.*

**7.1.1 Workflow Profile-niveaus:**

| Niveau | Wanneer | Bevat |
|---|---|---|
| **Profile-Light** | Nieuwe workflows, lage CoF, <50 beslissingen/dag | workflow_id, risk_class, owner, current_tier, lead_operator |
| **Profile-Standard** | Trigger: CoF.any ≥ medium, volume >50/dag, incident in laatste 90d | Volledige Workflow Profile uit 6.4 |
| **Profile-Critical** | Trigger: CoF.any = catastrophic, Trust-load-bearing in productie, terminal-T1 dataset-defining | Profile-Standard + on-call rotatie + 24/7 anomaly-monitoring + verplichte maandelijkse drills |

**Bevorderingsregel:** profile-niveau gaat alleen omhoog wanneer trigger feitelijk vuurt — niet preventief.

**7.1.2 Inverse promotion (governance-simplificatie):**

- Workflow ≥12 maanden incident-vrij + sample-rate-evidence consistent boven θ → mag sample-rate verlagen (binnen risk-class minima)
- Control niets gevangen in 6 maanden → kandidaat voor retirement (T0-beslissing)
- Profile-Critical → Profile-Standard mag na 18 maanden stabiel + lead-operator-akkoord

Simplificatie is **zelf een T0-beslissing** met dezelfde rigor als promotie.

**7.1.3 Governance Drift Detector** (kwartaal-cadans):

Voor elke control vraagt het: *"Heeft deze control in de laatste 90 dagen iets gevangen, voorkomen, of geïnformeerd?"*

- Ja → behouden
- Nee, workflow in risk-window → behouden, observeer langer
- Nee, workflow buiten risk-window → flag voor retirement-review

Geen automatische verwijderaar — een forcing function tegen accumulerende legacy.

**7.1.4 YAGNI-toetsvraag bij elke nieuwe control:**

> "Voorkomt dit een specifieke schade die de lichtere alternatief niet kan voorkomen, met een waarschijnlijkheid die de operationele kosten rechtvaardigt?"

Geen concreet schade-scenario = geen toevoeging.

### 7.2 Experimental Autonomy Sandboxes

Productie mag niet het enige leeroppervlak zijn.

**7.2.1 Vijf sandbox-modi:**

| Modus | Wat het doet | Productie-impact |
|---|---|---|
| **Shadow** | Agent beslist parallel met operator op productie-traffic; agent-beslissing alleen logged | Geen |
| **Replay** | Nieuwe agent/prompt op historische beslissingen, vergelijk met operator | Geen |
| **Synthetic** | Adversariële + zeldzame cases gegenereerd, agent en operator beoordelen | Geen |
| **Parallel A/B** | Slice van traffic via alternatief agent/prompt, vergelijk downstream-outcomes | Klein, opzettelijk |
| **Promotion Drill** | Workflow draait simultaan in target-tier (volle veiligheidsmechanismen), output naar drill-kanaal | Geen tot drill slaagt |

**7.2.2 Sandbox-governance is opzettelijk licht:**

- Geen 8-gate promotie-policy binnen sandbox
- Geen Workflow Profile vereist (alleen experiment-record)
- Operators mogen experimenten starten zonder lead-operator-sign-off
- Sandbox-output bereikt nooit installateurs, leads, of productie-dataset
- Sandbox beslissingen worden wél volledig logged

**7.2.3 Sandbox-naar-productie gates (5 gates voor T0/sandbox → T1):**

1. Shadow-mode accumuleerde ≥ N beslissingen op echte productie-traffic
2. Shadow-vs-operator agreement ≥ θ over voldoende dagen
3. Geen catastrofale CoF-component-overtreding in sandbox
4. Promotion drill uitgevoerd zonder incidenten
5. Lead operator sign-off (T0)

**7.2.4 Kritisch: nieuw agent reset ALTIJD naar T1**, zelfs als de workflow op T2/T3 zit. Promotie-bewijs hoort bij het *specifieke* agent, niet bij de workflow-abstractie.

### 7.3 Learning Velocity Metrics

Tegenwicht voor safety-metrics. Een veilig-maar-stilstaand systeem is geen intelligence company.

| Metric | Definitie | Gezond signaal | Ongezond signaal |
|---|---|---|---|
| **Days-to-confidence** | Mediane dagen sandbox-entry → T1 productie | Trend dalend of stabiel | Trend stijgend |
| **Operator correction convergence** | Variantie in overrides op vergelijkbare inputs over tijd | Dalend | Stabiel-hoog |
| **Taxonomy evolution rate** | Nieuwe categorieën/subcategorieën per kwartaal | 1-5 per kwartaal | Nul OF zeer hoog |
| **Signal novelty rate** | % signalen die niet vertrouwd in bestaande klassen passen | Stabiel of licht dalend | Snel stijgend |
| **% unresolved ambiguity** | % beslissingen in operator-review band | Trend dalend | Trend stabiel/stijgend |
| **Routing-learning velocity** | Convergentie installateur-fit voorspelling met conversie | 3-6 maanden per installateur | Geen convergentie |
| **New pattern discovery frequency** | Door operators geïdentificeerde patronen die taxonomie-update triggeren per kwartaal | Niet-nul | Nul OF zeer hoog |
| **Knowledge half-life per bron** | Hoe lang blijft source-credibility-data accuraat | Lang voor stabiele bronnen | Onverwacht kort op stabiele bronnen |

**Interpretatie-regels:**

- **Targets zijn trend-aware**, niet absoluut
- **Stalling triggert investigatie**, geen demotion (demotion is voor veiligheid; leer-stilstand is een groei-alert)
- **Stagnatie + safety-metrics groen = paradox-signaal**: of we hebben ambigue cases verkeerd geclassificeerd als trivial, of de wereld is werkelijk stabiel (kandidaat voor promotie + simplificatie)
- **Hoge novelty + lage taxonomy-evolution = rode vlag**: wereld verandert, ons begrip niet

**Learning Velocity Dashboard:** naast Safety Dashboard, zelfde zichtbaarheid. Lead operator review-cadans: maandelijks. De vraag: *"Leren we snel genoeg om over 12 maanden nog steeds beter te zijn dan wat concurrenten kunnen kopiëren?"*

### 7.4 De Spanningsdriehoek — meta-principe

Drie krachten trekken tegen elkaar:

```
                  Safety
                 /      \
                /        \
       Simplicity ──── Learning Velocity
```

| Hoek | Wil | Risico bij dominantie |
|---|---|---|
| **Safety** | Meer gates, meer review, strengere promotie | Operational drag, governance theater |
| **Simplicity** | Minder controls, minder overhead | Catastrofale fout door ontbrekende safeguard |
| **Learning Velocity** | Sneller iteratie, meer sandbox | Drift, onstabiele dataset, overhaaste promoties |

**Architecture-review cadans (kwartaal):** lead operator beantwoordt expliciet:

1. Welke hoek heeft dit kwartaal het meeste gewonnen?
2. Is dat de juiste hoek geweest voor dit moment?
3. Welke specifieke beslissingen hebben de drift veroorzaakt?
4. Welke control of ritueel moet vereenvoudigd, geschrapt, of toegevoegd om de balans te herstellen?

### 7.5 Wat deze sectie uitsluit

| Discipline | Sluit uit |
|---|---|
| Profile-levels (Light/Standard/Critical) | One-size-fits-all governance overhead |
| Inverse promotion + Governance Drift Detector | Accumulerende legacy-controls |
| YAGNI-toetsvraag bij elke control | "Voor de zekerheid" controls zonder schade-scenario |
| Sandbox als eerste-klas omgeving | Productie als enige leeroppervlak |
| Nieuw agent reset altijd naar T1 | Promotie-bewijs verwarren met workflow-historie |
| Learning Dashboard naast Safety Dashboard | Optimaliseren puur op veiligheid zonder evolutie-snelheid |
| Kwartaal-review op Spanningsdriehoek | Onbewust drijven naar één hoek |
| Stalling triggert investigatie, geen demotion | Learning-stilstand verkeerd diagnosticeren als safety-probleem |

---

## 8 — Deel 2: Safety Architecture (V0-disciplined)

Voor elk onderdeel: het concept, V0 minimale versie, en uitgesteld tot operationele evidence.

### 8.1 Audit Log als Dataset

**Concept:** Eén onveranderlijk decision-log per beslissing. Geen "compliance feature" — **de proprietary dataset zelf**.

**V0 schema:**

```sql
CREATE TABLE decisions (
  decision_id          UUID PRIMARY KEY,
  workflow_id          TEXT NOT NULL,
  profile_version      INT NOT NULL,
  tier_at_decision     TEXT NOT NULL,         -- T0..T4
  inputs_hash          TEXT NOT NULL,
  inputs_payload       JSONB NOT NULL,
  agent_id             TEXT,                  -- model+prompt versie, nullable bij T0
  agent_recommendation JSONB,
  agent_confidence     FLOAT,
  agent_reasoning_ref  TEXT,                  -- link naar LLM trace (S3/disk)
  reviewer_id          TEXT,                  -- nullable: alleen T0/T1/T2-sample
  reviewer_decision    JSONB,
  agreement            TEXT,                  -- Y / N / NA
  override_reason      TEXT,
  override_category    TEXT,                  -- taxonomy_miss | too_strict | too_lax | context_missing | other
  decided_at           TIMESTAMPTZ NOT NULL,
  time_to_decide_ms    INT,
  outcome              JSONB                  -- gevuld later via feedback
);
```

**V0 niet-onderhandelbaar:**
- Append-only (geen UPDATE/DELETE behalve outcome-vulling — gehandhaafd via app-laag of trigger)
- Offsite backup vanaf dag 1
- Retentie indefinitive
- Postgres in eigen beheer (geen managed-DB-as-service met onduidelijk dataeigendom)

**Uitgesteld (V1+):** OpenTelemetry-integratie, gespecialiseerde tijdseries-store, partitionering.

### 8.2 Drift Detection — 4 signal-types, gefaseerd

| Signaal | Wat het detecteert | V0 viable? |
|---|---|---|
| **Input drift** | Signal-novelty rate, woordenschat-shifts | **V0** |
| **Confidence drift** | Agent-confidence distributie shift t.o.v. baseline | V0 baseline-collectie, V1 detector |
| **Decision drift** | Agent-human agreement-verandering per niche/source/operator | V1 |
| **Outcome drift** | Conversie/refund/klacht-rate shift | V1+ |

**V0 build:**
- Input-drift: dagelijkse novelty-rate berekening; 7-daagse rolling baseline; alert bij >2σ afwijking
- Confidence-distributie logging start vanaf dag 1 (verzamel-modus, geen detector)

**Uitgesteld:** Decision-drift en outcome-drift detectoren. Schema is er, detector volgt zodra volume past.

### 8.3 Kill-Switch Systeem — drie niveaus, één V0

| Niveau | Effect | V0? |
|---|---|---|
| **Workflow** | Eén workflow → forceer T0/T1, alle beslissingen naar operator | **V0** |
| **Tier-wide** | Alle T3+ workflows → T2 | V1 |
| **Globaal** | Alles → T0/T1 | V1 |

**V0 implementatie:**

```sql
CREATE TABLE workflow_kill_state (
  workflow_id   TEXT PRIMARY KEY,
  killed_until  TIMESTAMPTZ,
  reason        TEXT NOT NULL,
  set_by        TEXT NOT NULL,
  set_at        TIMESTAMPTZ NOT NULL
);
```

Workflow-code checkt aan begin van elke beslissing. Killed = route naar operator queue ongeacht tier. Reactivatie = expliciete T0-handeling.

**Uitgesteld:** Tier-wide en globale switches komen er wanneer meerdere autonome workflows tegelijk in productie zijn.

### 8.4 Escalation Tree — gedefinieerd, niet gebouwd

| Niveau | Rol | V0 reality |
|---|---|---|
| **L1** | Workflow operator (routine queue) | = founder |
| **L2** | Senior operator (ambigue cases, sign-off) | = founder |
| **L3** | Lead operator (promotie/demotie/kill-switch autoriteit) | = founder |
| **L4** | Incident commander | = founder |

**V0 stand:** Rollen gedefinieerd in architectuur zodat ze klaarstaan wanneer persoon 2 arriveert. Geen escalation-routing tooling. Telegram aan founder volstaat zolang team één is.

**Uitgesteld:** Multi-persoon escalatie-routing, role-based access in Retool, on-call rotatie tooling.

### 8.5 Rollback Orchestration — 4 niveaus, 3 V0

| Niveau | Wat het herstelt | V0? |
|---|---|---|
| **Decision** | Eén beslissing terugdraaien | **V0** |
| **Agent** | Vorige agent/prompt versie | **V0** |
| **Profile** | Workflow Profile vorige versie | **V0** (gratis als versioned) |
| **Workflow-tier** | Workflow naar lagere tier | V0 via demotion mechaniek |

**V0 build:**
- Decision-rollback: nieuwe `decision_rollback` rij wijst naar originele, met reden en nieuwe operator-beslissing
- Agent-rollback: agents zijn semver-getagged in DB; deploy is roll-forward met de mogelijkheid tot revert-to-tag
- Profile-rollback: profiles zijn versioned rows; "revert to K" = nieuwe versie K+1 met inhoud van K-1

**Verplichte V0 drill:** rollback-procedure één keer uitvoeren tegen een test-decision binnen 14 dagen na launch.

**Uitgesteld:** Geautomatiseerde quarterly drills, rollback-cascade-tests, multi-decision-batch-rollback.

### 8.6 Anomaly Handling — threshold V0

**Verschil met drift:** drift is geleidelijk, anomaly is plotseling.

**V0 detectoren:**

| Anomaly | Detectie | Actie |
|---|---|---|
| Signaal-volume-spike per bron | >3× 7-d gemiddelde | Alert, niet auto-pause |
| Geo-cluster anomalie | >N leads uit één postcode in 24u | Alert + voorlopige hold |
| Operator override-spike | >2× baseline van die operator in 24u | Alert lead operator |
| Agent-confidence-collapse | Mediane confidence daalt >X% over 24u | Auto-pause workflow, lead operator alert |

**Uitgesteld:** Statistische anomaly-detectie, multi-variate detectoren, adversarial-input detectie.

### 8.7 Operator Override Mechanics

**V0 build:**
- Verplichte `override_reason` (vrije tekst) + `override_category` (5 opties) bij elke afwijking
- Reasons en categorieën gelogd; geen UI voor pattern-analyse V0
- Maandelijks: lead operator leest doorlopend de overrides (raw table reading) — geen dashboard bij <100 overrides/week

**Uitgesteld:** Pattern-detectie UI, operator-calibration dashboards, geautomatiseerde "5 vergelijkbare cases" UI-signalen.

### 8.8 Sandbox Replay/Simulation — 2 modi V0

Van de 5 sandbox-modi uit 7.2:

| Modus | V0? |
|---|---|
| Shadow | **V0** |
| Replay | **V0** |
| Synthetic | V1 |
| Parallel A/B | V1 |
| Promotion Drill | V1 |

**V0 implementatie:**
- Sandbox = `decisions_sandbox` tabel die productie-schema mirrort
- Shadow: productie-decision wordt ook doorgegeven aan sandbox-agent; resultaat in `decisions_sandbox`
- Replay: scriptable harness die historische `decisions` rijen door een nieuwe agent draait

### 8.9 Trust-Preserving Controls — twee niet-onderhandelbaar V0

| Control | V0? | Rationale |
|---|---|---|
| **Exclusivity Monitor** | **V0** | Beschermt kernbelofte. Real-time check: kan twee installateurs simultaan een claim hebben? Antwoord *onmogelijk* by design. |
| **Conversion Attribution Chain** | **V0** | Beschermt moat-dataset. Signal → lead → delivery → outcome → conversion herconstrueerbaar via FK's. |
| **Installer-facing transparency** | V1 | Data is V0 aanwezig in audit log; UI/export pas bij eerste installateur-vraag |
| **"Show your work" voor trust-load-bearing** | **V0** | Elke T1/T2 trust-load-bearing logt human-readable agent-reasoning. Al gedekt door audit-log schema. |

**V0 Exclusivity Monitor:**

```sql
-- Illustratief; concrete state-namen worden vastgelegd door de lifecycle sub-spec.
-- De *vorm* van de constraint is verplicht: UNIQUE op lead_id voor de set van states
-- die een "actieve claim" representeren.
CREATE UNIQUE INDEX one_active_claim_per_lead
  ON deliveries (lead_id)
  WHERE state IN (<active_claim_states>);
```

Applicatie-level check pre-routing: assert geen actieve claim bestaat. Verplicht audit-log van re-route gebeurtenissen.

> **Dependency note:** de exacte states die "actieve claim" representeren worden gedefinieerd in de toekomstige Lifecycle sub-spec. `pcs.py` v0 heeft op dit moment alleen `DELIVERED` als kandidaat-state. De Lifecycle sub-spec breidt dit waarschijnlijk uit met intermediate states (bijv. een "wacht op installateur-respons" state). De Exclusivity Monitor wordt feitelijk geactiveerd zodra de Lifecycle sub-spec deze states heeft vastgelegd.

**V0 Attribution Chain:**

- Lead-tabel FK's: `source_signal_id → lead_id → delivery_id → outcome_id → conversion_id`
- Reconstructie-query: "geef de volledige keten voor lead X" = één SQL-query

### 8.10 Wat deze sectie uitsluit

| Discipline | Sluit uit |
|---|---|
| Audit log = proprietary dataset | Loggen als afterthought; logs in SaaS we niet bezitten |
| V0 vs uitgesteld markering | Bouwen voor verbeelding |
| Exclusivity Monitor als DB-constraint | Brand-belofte als beleid in plaats van enforced systeem |
| Geen multi-tier kill-switch V0 | Bouwen voor parallel-productie die niet bestaat |
| Geen pattern-analyse UI V0 | Dashboards bouwen vóór patronen bekend |
| Geen escalation-tooling V0 | Multi-persoon infrastructuur in één-persoons team |
| "Show your work" voor trust-load-bearing | Verborgen reasoning achter trust-dragende beslissingen |

---

## 9 — Onveilige vs veilige autonomie — illustratieve voorbeelden

**Onveilig:**

- Promotie van classificatie naar T3 omdat agreement-rate 95% is, terwijl de operator-population klein was (selectie-bias)
- Auto-promotie op basis van één metric (agreement-rate) zonder reversibility-check
- Agent autonoom installateur-scoring laten doen (relatie-context is onherstelbaar)
- Auto-registratie van conversies omdat installateur "ja" zei tegen de agent (dataset-corruptie)
- Workflow promoveren omdat operator-queue achterloopt op SLA (latency-pressure als promotion-reden)
- Sample-rate verlagen "omdat het al maanden goed gaat" zonder Governance Drift Detector check
- Profile-Critical → Profile-Light overslaan in één stap

**Veilig:**

- Auto-classificatie van high-confidence (>90%) signalen met 1% sampling, na 6 maanden T1 baseline
- Auto-deduplicatie via deterministische MinHash (geen agent-beslissing, deterministisch verifieerbaar)
- Auto-extractie van geo uit publieke signalen (well-bounded, fact-extracting, reversibel)
- Template-formatting met installateur-naam (deterministisch, geen "beslissing")
- T1 promotie van nieuwe agent na 7d shadow + 14d productie-T1 met agreement >97% en lead operator sign-off
- Sample-rate-verlaging van 20% naar 15% na 12 maanden incident-vrij met expliciete Governance Drift Detector akkoord en T0 sign-off

---

## 10 — Failure-scenarios + verdedigingsmechaniek

| Scenario | Hoe het misgaat | V0 defense | V1 defense |
|---|---|---|---|
| **Drift gaat onopgemerkt** | Agreement-rate stabiel maar agent shiftte op één niche | n.v.t. — geen decision-drift detector V0 | Per-niche decision-drift detector |
| **Operator skews dataset** | Eén operator approve't alles → agent leert laksheid | Maandelijkse override-pattern leesronde door lead operator | Per-operator agreement tracking + calibratie |
| **Model-update verandert gedrag stil** | GPT-N update → classificaties verschuiven overnight | Agent-version semver + audit-log per agent_id | Automatische re-baseline op model-update |
| **Adversariële signalen** | Iemand realiseert dat onze classifier triggert op zin X → floods | Volume-anomaly detector (8.6) | Multi-variate adversarial detection |
| **Catastrofale kill-switch faalt** | Kill-switch flipped maar workflow draait door via cache | Workflow-code checkt kill-state per beslissing, geen cache | Drill verifieert real-time effect |
| **Conversie-dataset corruptie via agent** | Agent registreert conversies autonoom → vergiftigt promotion-evidence | Conversie-registratie permanent T1, geen agent-decided pad mogelijk | n.v.t. — protected by architectural rule |
| **Exclusiviteits-breuk** | Twee installateurs claimen dezelfde lead simultaan | UNIQUE index op active-claim state | Real-time monitor + audit |
| **Operator overload onder volume-spike** | OCL >100%, queue groeit, fouten | Operational Headroom Monitor + Managed Overflow F-A policy | Auto-capacity-scaling alerting |
| **Stille governance-bloat** | Controls accumuleren, niemand schrapt | Governance Drift Detector kwartaal-cadans (V0) | Geautomatiseerde retirement-recommendations |
| **Learning stagnatie verkleed als safety** | Demote workflow ipv leerprobleem onderzoeken | "Stalling triggert investigatie, geen demotion" regel | Learning Dashboard + maand-cadans |

---

## 11 — Hoe dit een lange-termijn moat wordt

De autonomy-architectuur is zelf een moat omdat:

1. **De owned dataset van agent-vs-human decisions** is uniek. Geen openbare bron heeft deze. Concurrenten die "full AI" gaan kunnen 'm niet bouwen omdat ze geen operator-laag hebben.

2. **Operator-gecalibreerde promotion criteria** encoderen tacit business knowledge. Een nieuwe speler kan de prompts kopiëren maar niet de drempels — die komen uit honderden operator-beslissingen.

3. **Drift-detectoren specifiek voor Lead Radar's signals** kunnen niet gekloond worden. Ze zijn getrained op onze input-distributie.

4. **Trust-of-the-installateur** is gebouwd op het feit dat een mens verantwoordelijk is voor de beslissingen die ertoe doen. Dat is geen technische moat — dat is een relationele moat.

5. **Conversion-feedback dataset** is de primaire grondwaarheid. Concurrenten die op publieke benchmarks trainen kunnen onze accuracy niet matchen op *onze* signal-distributie.

6. **De Workflow Profile als versioned data** maakt de architectuur introspecteerbaar en aanpasbaar zonder code-deploys. Operators kunnen het systeem evolueren.

Concurrenten kunnen "AI lead-gen" doen. Ze kunnen geen *intelligence operations company* zijn zonder de operator-jaren en het dataset-fundament.

---

## 12 — V0 Inventaris (build now)

Wat we feitelijk bouwen na akkoord van deze spec:

| # | Component | Sectie | Laag |
|---|---|---|---|
| 1 | `decisions` Postgres tabel met volle schema, append-only, offsite backup | 8.1 | DB |
| 2 | Input-drift detector (novelty-rate + woordenschat-shift, dagelijks) | 8.2 | Drift |
| 3 | Confidence-distributie logging (baseline-collectie, geen detector) | 8.2 | Drift |
| 4 | `workflow_kill_state` config-tabel + runtime-check in alle workflows | 8.3 | Control |
| 5 | Escalation rollen gedefinieerd (geen tooling — alle rollen = founder) | 8.4 | Documentatie |
| 6 | Decision/Agent/Profile rollback mechaniek (gratis via versioning) | 8.5 | DB |
| 7 | Eén rollback drill binnen 14 dagen na launch | 8.5 | Process |
| 8 | 4 threshold-based anomaly detectoren | 8.6 | Drift |
| 9 | Override logging met categorie (vrije tekst + 5 categorieën) | 8.7 | Audit |
| 10 | Sandbox: Shadow + Replay modi (sandbox-tabel + script-harness) | 8.8 | Sandbox |
| 11 | Exclusivity Monitor (UNIQUE index + applicatie-check) | 8.9 | Trust |
| 12 | Conversion Attribution Chain (FK-keten + 1-query reconstructie) | 8.9 | Schema |
| 13 | "Show your work" logging voor trust-load-bearing T1/T2 | 8.9 | Audit |
| 14 | Workflow Profile schema in DB, versioned, met initial profiles voor de eerste 2-3 workflows | 6.4 | Config |
| 15 | Operational Headroom Monitor V0 (Profile-Standard workflows alleen) | 6.3 | Dashboard-light |
| 16 | Governance Drift Detector kwartaal-script (handmatig gedraaid V0) | 7.1.3 | Process |
| 17 | Learning Velocity Metrics queries voor handmatige maandelijkse review | 7.3 | Reporting |

Bijbehorende eerste 3 workflows die V0 actief worden (initieel profiles):

- `lead_delivery_routing` — terminal T1 vanwege CoF.exclusivity circuit breaker
- `signal_classification_ambiguous_band` — start T1, target T2/T3
- `conversion_registration` — terminal T1, dataset-defining

Andere workflows wachten tot deze drie operationele ervaring leveren.

---

## 13 — Uitgesteld Inventaris (build when operational evidence justifies)

| Component | Sectie | Trigger voor activatie |
|---|---|---|
| OpenTelemetry-integratie | 8.1 | Audit-log volume > ~10k decisions/dag |
| Statistische confidence-drift detector | 8.2 | Baseline-data ≥ 30d verzameld |
| Decision-drift detector per niche/source/operator | 8.2 | Eerste workflow op T2 actief ≥ 14d |
| Outcome-drift detector | 8.2 | Eerste conversie-events geregistreerd, N ≥ 30 |
| Tier-wide kill-switch | 8.3 | 2+ workflows op T3+ tegelijk in productie |
| Globale kill-switch | 8.3 | Incident vereiste 't OF Profile-Critical workflow actief |
| Multi-persoon escalation tooling | 8.4 | Tweede operator hire |
| Geautomatiseerde rollback drills (quarterly) | 8.5 | Eerste handmatige drill aantoonbaar te zwaar |
| Statistische anomaly-detectie | 8.6 | Threshold-detectoren miss-rate > 20% |
| Adversarial-input detectie | 8.6 | Eerste bevestigde adversarial poging |
| Pattern-analyse UI voor overrides | 8.7 | >100 overrides/week wordt rauw lezen onmogelijk |
| Operator-calibration dashboards | 8.7 | Tweede operator hire |
| Sandbox Synthetic-modus | 8.8 | Edge-case coverage knelt aantoonbaar |
| Sandbox Parallel A/B-modus | 8.8 | Eerste stable T2/T3 agent met iteratie-pad |
| Sandbox Promotion Drill-modus | 8.8 | Eerste reële T1→T2 promotie aanstaande |
| Installer-facing transparency UI | 8.9 | Eerste installateur die het vraagt |
| Real-time exclusivity-monitor dashboard | 8.9 | >2 installateurs in productie |

---

## 14 — Kalibratie-aantekening

**Belangrijk voor toekomstige revisies:**

Alle numerieke waarden in deze spec (thresholds, percentages, tijdvensters, sample sizes) zijn **vertrekpunten, geen grondwaarheden**. Voorbeelden van kandidaat-bijstelling:

- Sample size N=500 voor T1→T2 — kan blijken te laag of te hoog
- Agreement-rate θ=98% voor T2 — kan blijken niet streng genoeg voor onze CoF-profielen
- Drift-window D=14d voor T2 — kan blijken te kort of te lang
- OCL-budgets per workflow — afhankelijk van werkelijke operator-snelheid
- CoF k-factor in agreement-formule — moet getuned tegen aanvankelijke false-positive/negative rate

**Versioning-discipline:** elke toekomstige revisie van deze spec krijgt versie-metadata met:
- "Calibrated against N decisions over D days"
- Welke thresholds zijn aangepast en op welke evidence
- Welke uitgestelde componenten zijn geactiveerd en waarom

De architectuur-*structuur* (tiers, risk classes, gates, CoF/Latency/OCL dimensies, sandbox-modi, Spanningsdriehoek) is wat load-bearing is. De numerieke calibratie is wat we *gaan* leren.

---

## 15 — Transitie naar Operator Intelligence Console v0

### Wat de volgende ontwerpsessie behandelt

Deze spec definieert het regel-systeem. De volgende sessie definieert de **werkomgeving** waarin operators dat regel-systeem dagelijks gebruiken: de **Operator Intelligence Console v0**.

Founder-principes voor de Console (vastgelegd in deze sessie 2026-05-18):

- **Niet als enterprise software** — geen modale wizards, geen rolverwarring
- **Niet als dashboard theater** — metrics ondersteunen werkflows, ze zijn niet het werk
- **Niet als analytics overload** — alleen wat de huidige beslissing dient
- **Wel: dagelijkse intelligence workstation** — de plek waar de operator letterlijk leeft
- **Wel: snelle operator workflows** — meeste beslissingen <30 seconden
- **Wel: minimale cognitieve belasting** — één beslissing per scherm, geen context-switching
- **Wel: hoge inspecteerbaarheid** — elke beslissing leesbaar via audit-trail in twee klikken
- **Wel: snelle review-loops** — sample-reviews en overrides in dezelfde view
- **Wel: fast correction** — override + reason + recategorize in één flow
- **Wel: trust-preserving operations** — exclusivity-state altijd zichtbaar, attribution-chain altijd reconstrueerbaar

### Wat Console v0 omvat

De V0 console laadt en gebruikt:

- **Operator queues** voor de drie startworkflows (delivery routing, ambigue classificatie, conversie-registratie)
- **Audit views** — lees-only access tot decisions-tabel via filterbare interface
- **Override flows** — verplichte category-keuze + free text reason
- **Conversion logging UI** — formulier-flow gevoed door agent-parse van installateur-antwoord
- **Exclusivity handling UI** — visuele weergave van active-claim state per lead
- **Workflow Profile loading** — console leest profiles om te weten welke tier/CoF/etc geldt
- **Basic sandbox replay/shadow support** — operator kan zien wat agent zou hebben gedaan in shadow

### Wat Console v0 NIET omvat

- Multi-operator role-based access (rollen gedefinieerd; toegang V0 = single founder login)
- Patroon-analyse dashboards (V1)
- Geautomatiseerde alert-routing (Telegram volstaat V0)
- Real-time dashboards voor metrics die niet beslissings-relevant zijn
- Pattern-detectie UI voor overrides (V1)
- Installer-facing portal (separate spec, separate timeline)

### Volgende stap

Na founder review en akkoord van deze spec: nieuwe ontwerpsessie voor **Operator Intelligence Console v0**, resulterend in een eigen spec en daarna een implementatie-plan via writing-plans.

Geen verdere architectuur-uitbreiding totdat operationele realiteit aanwijst wat werkelijk nodig is.

---

## Appendix A — Glossarium

| Term | Betekenis in deze spec |
|---|---|
| **Tier (T0-T4)** | Autonomie-niveau van een specifieke beslissing in een specifieke workflow op een specifiek moment |
| **Workflow** | Een klasse van repeterende beslissingen met gedeelde inputs, outputs, en governance (bijv. "lead delivery routing") |
| **Workflow Profile** | Versioned data-record dat de configuratie van een workflow definieert (risk class, CoF vector, latency class, OCL budget, thresholds, eigenaar) |
| **Risk Class** | Categorisering van een beslissings-type met een hard tier-plafond (Existential, Trust-load-bearing, Dataset-defining, Quality-load-bearing, Routine factual) |
| **CoF** | Cost of Failure — 5-component vector: financial, installer, exclusivity, dataset, ops_cascade |
| **OCL** | Operator Cognitive Load — budget van operator-aandacht per workflow per dag |
| **Profile Level** | Light / Standard / Critical — niveau van governance-zwaarte per workflow |
| **Latency Class** | L0/L1/L2/L3 — tijd-budget voor beslissingen in een workflow |
| **Fallback Policy** | F-A (Managed Overflow) / F-B (Degraded SLA Queue) / F-C (Conservative Default) — gedrag wanneer normaal beslis-pad niet haalbaar is |
| **Sandbox Modus** | Shadow / Replay / Synthetic / Parallel A/B / Promotion Drill — vijf experimenteer-omgevingen |
| **Drift Signal** | Input / Confidence / Decision / Outcome — vier orthogonale drift-detectie signalen |
| **Kill-Switch** | Workflow / Tier-wide / Globaal — drie niveaus van autonomie-noodstop |
| **Rollback Niveau** | Decision / Agent / Profile / Workflow-tier — vier herstel-niveaus |
| **Override Category** | taxonomy_miss / too_strict / too_lax / context_missing / other — vijf categorieën van operator-afwijking |
| **Operator** | Mens die beslissingen neemt in het systeem. V0 = founder. V1+ = founder + 2-4 anderen met gedefinieerde rollen |
| **Agent** | Specifieke versie van model + prompt + tools dat een aanbeveling of beslissing produceert |
| **Spanningsdriehoek** | Het meta-principe dat Safety, Simplicity, en Learning Velocity tegen elkaar trekken en kwartaal-review vereisen |

---

**Einde spec.**

Versie 1.0 — 2026-05-18.
Volgende revisie wanneer operationele realiteit aantoont welke calibraties moeten verschuiven.
