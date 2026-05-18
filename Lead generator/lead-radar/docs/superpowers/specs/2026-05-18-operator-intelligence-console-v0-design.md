# Lead Radar — Operator Intelligence Console v0 Design

**Status:** Awaiting founder review (na brainstorming-sessie 2026-05-18)
**Auteur:** Claude Opus 4.7 (i.s.m. founder, sessie 2026-05-18)
**Datum:** 2026-05-18
**Branch:** `feat/facebook-scraper`
**Input contract:** `2026-05-18-autonomy-architecture-design.md` (in dezelfde directory) — deze console implementeert de operator-laag bovenop dat regelsysteem
**Type:** UI/UX + implementation-scope ontwerp voor de dagelijkse operator workstation. Geen marketing-website, geen public-facing UI. Dit is *de* werkomgeving waarin een operator letterlijk dagelijks zit.

---

## 0 — Context

Lead Radar heeft per 2026-05-18:

- Operationele consumer-pipeline (10+ bronnen, launchd-orchestratie, heartbeat, Sheets sync)
- Net-gecommit **Autonomy Architecture** spec (autonomy tiers T0-T4, risk classes, CoF/Latency/OCL, workflow profiles als versioned data, V0 inventaris van 13 safety-componenten)
- 7-daagse Plan B observatie-window lopend tot 2026-05-25

Wat ontbreekt is de **dagelijkse werkomgeving** waarin de founder (en straks 3-5 ops team) het autonomy-systeem operationeel gebruikt: leads goedkeuren, classificaties corrigeren, conversies registreren, audit inspecteren.

### Wat deze spec IS

Het ontwerp van de **Operator Intelligence Console v0** — een lean web app die het volgende doet:

- De drie V0 workflows uit de autonomy spec presenteert in operator-friendly card-stack form
- Workflow Profiles leest om te weten welke tier/CoF/policy geldt per beslissing
- Decisions wegschrijft naar het audit log (de proprietary dataset)
- Audit chains inline inspecteerbaar maakt zonder rabbit-holes
- Universal search biedt voor lead-retrieval
- Trust-preserving operations afdwingt (state, focus, single-threaded werkflow)
- Telegram als enige interrupt-surface gebruikt

### Wat deze spec NIET is

- Geen implementation-plan (volgt via writing-plans skill na founder-akkoord)
- Geen marketing- of installateur-facing UI (separate spec: `lead-radar-site/`)
- Geen design-systeem of theming-spec (V0 is one-look, zie sectie 11)
- Geen RBAC of multi-tenant ontwerp (V1+, expliciet uitgesloten)
- Geen dashboards, analytics, of reporting (architecturaal verboden V0)
- Geen mobile- of tablet-UI (laptop/desktop V0)

---

## 1 — Strategische intentie

**De console is een intelligence workstation, geen SaaS admin tool.**

| Wat we bouwen | Wat we expliciet *niet* bouwen |
|---|---|
| Dagelijkse intelligence workstation | Enterprise SaaS admin |
| Card-stack focus per beslissing | Spreadsheet/CRM-grids |
| Keyboard-first ergonomics | Mouse-heavy menus |
| Inline audit inspection | Separate analytics-pagina |
| Telegram als interrupt-surface | In-console toast/badge feed |
| Trust-preserving single-threaded flow | Multi-modal dashboard noise |
| Decision-support language | Pseudo-precise data-dressing |

### Founder-principes voor deze console (vastgelegd 2026-05-18)

1. **Operational flow boven visual polish**
2. **Minimale cognitieve belasting**
3. **Hoge inspecteerbaarheid (in <2 klikken)**
4. **Fast review/correction loops**
5. **Anti-dashboard / anti-gamification discipline**
6. **3 extreem goede workflows boven 30 half-nuttige schermen**
7. **Ontworpen voor één operator dagelijks; team-uitbreiding zonder her-architectuur**

### Strategische uitkomst

Een console die:

- 90% van de dagelijkse operator-tijd in card-stack focus-modus houdt
- Per beslissing in <30s door routine-cases gaat, in 1-3min door ambigue cases
- Audit-inspectie in <60s afhandelt zonder de queue te verliezen
- Schaalt naar 3-5 operators zonder UI- of architectuur-wijziging
- Een dataset opbouwt (de `decisions` tabel + override patterns) die de moat versterkt

---

## 2 — Operationele keuzes (vastgelegd in brainstorming)

Zes design-niveau beslissingen die het hele ontwerp dragen:

| Keuze | Waarde | Implicatie |
|---|---|---|
| **Medium** | Lean Next.js + shadcn + owned Postgres | Custom craft mogelijk, geen Retool-SaaS-feel, eigen data-pad |
| **Daily rhythm** | 2-3 gefocuste work-blocks per dag, pull-on-load | Geen websocket-infrastructuur V0, simpele page-loads |
| **Landing** | Triage-overzicht (counters per workflow + alerts) | 5-seconden situational awareness vóór dieper werk |
| **Decision UX** | Card-stack pattern, één beslissing per scherm-moment | Geen list-with-rows, geen multi-select, geen bulk |
| **Ergonomie** | Keyboard-first met single-letter shortcuts, mouse-tolerant | Power-user snelheid, nieuwe-ops leercurve laag |
| **Context awareness** | Top-strip + cluster-banner + hover-peek (geen permanente rail) | Awareness zonder focus-state breken |

### Niet-onderhandelbare disciplines

| Discipline | Sluit uit |
|---|---|
| Auto-save op actie | "Save"-knoppen, verlies-bij-vergeten patterns |
| Keyboard-first | Hover-only menus, deep-submenu UX |
| Inline audit | Separate audit-pagina, modal-stacking voor inspect |
| One-look V0 | Theming, dark-mode, customization |
| Telegram-only notifications V0 | In-console toast/badge feeds |
| Single notificatie-surface | Email + Slack + in-app + Telegram alle vier |
| Single-threaded focus | Multi-window-sync, parallel inbox-views |
| Anti-gamification | Operator-performance metrics in UI |

---

## 3 — Out of scope

Expliciet uitgesloten van V0 (versie-1-onderhandelbaar, met trigger-conditie voor latere activatie):

| Categorie | Wat NIET V0 | V1+ trigger |
|---|---|---|
| Multi-tenant | Organisatie-scheiding | Tweede klant (n.v.t. — Lead Radar is one-tenant) |
| RBAC | Role-gating in UI | Tweede operator hire |
| Mobile | Responsive UI, mobile views | Geen V0 |
| Theming | Dark mode, customization | Aanvraag van operator/team |
| i18n | Vertaling | Internationale ops-team |
| Real-time | Websockets, live updates | Multi-operator coordination friction |
| In-console notifications | Toasts/badges/bell-icons | Real-time tier bereikt |
| Keyboard customization | Configurable shortcuts | Operator-aanvraag, geen standaard |
| Saved searches | Bookmarks/favorites | Search-frequency rechtvaardigt het |
| Bulk acties | Multi-select, bulk-approve | Aantoonbaar workflow-bottleneck |
| Export | CSV/PDF download | Compliance/installateur-aanvraag |
| Public API | Externe integraties | Aantoonbaar externe consument |
| Operator analytics | Performance-metrics in UI | Anti-gamification permanent |
| Performance dashboards | Reporting KPI-views | Anti-dashboard permanent |
| Calendar | Shift-planning | Multi-operator shift-coordinatie |
| File upload | Bijlagen | Workflow vraagt het aantoonbaar |
| Multi-window sync | Tab-coordination | Multi-operator parallel werken |
| Undo-stack | UI-level undo | Rollback uit autonomy spec dekt dit |
| Custom card layouts | Per-workflow UI-tweaks | Standaard-shell V0 |
| A/B testing UI | Varianten | Geen multi-variant tooling V0 |
| Onboarding tour | Tooltips/gidsen | Solo operator V0 |

---

## 4 — Definition of done (op design-niveau)

Dit document is "done" wanneer:

1. De componenten-inventaris (Sectie 12) zonder verdere ontwerpvragen door writing-plans omgezet kan worden in een uitvoerbaar plan
2. Founder heeft akkoord gegeven op alle vijf design-secties (medium/rhythm, decision-UX, cards, override+audit+search, auth/notif/scope)
3. De input-contracts met de autonomy spec (workflow profiles, decisions tabel, kill-state, override-categorieën) zijn helder gespecificeerd
4. De NIET-V0 lijst is gecontracteerd als V1+ scope

**Niet vereist voor "done":**

- Pixel-perfect mockups (one-look V0 wordt in build-fase gepolished)
- Exacte styling-keuzes (typography/density wordt implementation discipline, sectie 11)
- Database migration scripts (writing-plans output)
- Test-suite ontwerp (writing-plans output)

---

## 5 — Architectuur op hoog niveau

### 5.1 Stack

- **Frontend**: Next.js (App Router), React, TypeScript
- **UI components**: shadcn/ui (gestyled met Tailwind)
- **Auth**: NextAuth of vergelijkbaar (magic-link via SMTP/Resend)
- **Database**: owned Postgres (geen managed-as-a-service zonder data-eigendom)
- **Deployment**: keuze in implementation-plan (Vercel of self-hosted Hetzner zijn beide redelijke V0-opties)

### 5.2 Drie screens

1. **Triage Overview** (landing) — counters per workflow + alerts
2. **Card-Stack Queue** (één card-shell, drie workflow-specifieke bodies)
3. **Audit Chain View** (inline binnen card-shell, geen page-navigation)

Geen verdere screens V0. Auth-flow is een mini-screen (login) maar telt niet als operator-werkomgeving.

### 5.3 Data model — tabellen die console gebruikt

**Bestaand (uit autonomy spec, V0 inventaris):**

- `decisions` — append-only audit log, console schrijft hier alle operator-acties naartoe
- `workflow_profiles` — versioned, console leest profile bij elke decision (welke tier? welke CoF? welke fallback-policy?)
- `workflow_kill_state` — console checkt per pageload + per decision-fetch
- `override_categories` — console renderet de actieve categorieën uit deze tabel (sectie 9.2)

**Nieuw (console-eigen, V0):**

```sql
CREATE TABLE operators (
  operator_id   UUID PRIMARY KEY,
  name          TEXT NOT NULL,
  email         TEXT NOT NULL UNIQUE,
  role          TEXT NOT NULL CHECK (role IN ('operator','senior','lead')),
  active        BOOLEAN DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  session_id    UUID PRIMARY KEY,
  operator_id   UUID NOT NULL REFERENCES operators(operator_id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL,
  last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- queue_claims voorkomt twee operators die simultaan zelfde decision pakken
-- (queue-safe vanaf dag 1, ook met één operator V0 — geen singleton assumption)
CREATE TABLE queue_claims (
  decision_id   UUID PRIMARY KEY REFERENCES decisions(decision_id),
  claimed_by    UUID NOT NULL REFERENCES operators(operator_id),
  claimed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL  -- claim verloopt automatisch (bijv. 10 min)
);
```

### 5.4 Niet-onderhandelbare state-preservation contracts

Drie technische contracts die het hele flow-gevoel maken:

| Contract | Wat het verzekert |
|---|---|
| **Queue position preservation** | Bij `Esc` uit audit-view, of bij return-from-Telegram-deep-link: operator komt terug op exact dezelfde queue-positie + scroll-positie binnen card |
| **Search non-destructive** | `/`-overlay opent boven de huidige view; cancel laat alle state intact |
| **State-preserving deep-links** | Telegram deep-links bevatten `return_to` parameter (queue, audit, triage). Esc weet altijd waar terug te gaan |

### 5.5 Geen singleton-assumpties

V0 draait solo, maar de architectuur is bij voorbaat **queue-safe / session-safe / state-safe / lock-safe**:

- Geen "current_operator" globale state in de codebase — altijd uit sessie afgeleid
- Geen "first-come" race conditions in queue-fetch — `queue_claims` tabel met TTL voorkomt dubbele claims
- Geen "single browser tab" assumptions — sessions zijn DB-persistent, niet localStorage-only
- Geen "always-on operator" assumptions — alle achtergrondprocessen weten dat de operator afwezig kan zijn

Implicatie: tweede operator hire vereist geen architectuur-wijziging, alleen een nieuwe rij in `operators`.

---

## 6 — Triage Overview (landing screen)

5-seconden situational awareness bij elke console-opening. Geen dashboard.

```
┌─────────────────────────────────────────────────────────────────┐
│  Lead Radar — Operator console               founder | sign out │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ROUTING            CLASSIFICATION       CONVERSIONS            │
│   5 leads            8 signals            2 pending              │
│   [1] enter →        [2] enter →          [3] enter →            │
│                                                                  │
│   • 1 HOT >24h       • 1 source-novelty   • 0 disputed          │
│   • 2 WARM           • 3 taxonomy-flag    • 2 awaiting reply    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│   ALERTS                                                         │
│   ⚠ Operational Headroom: 64% (geel) — see kill-states          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│   [/] search    [K] kill-states    [V]iew recent audits          │
└─────────────────────────────────────────────────────────────────┘
```

### Ergonomic regels

- Drie workflow-blokken zijn de enige primaire affordance
- `1/2/3` keys = jump direct in queue (bypasst muis)
- Mini-details onder elk blok (HOT, novelty, awaiting) geven scan-niveau context
- Alerts-zone toont *operationele* alerts (kill-state, headroom, anomaly) — niet AI-marketing
- Footer met universal `/` search + `K` kill-states + `V` recent audits

### Wat het NIET toont

- Geen leads-met-detail (operator klikt eerst in een queue)
- Geen metrics-charts of trend-grafieken
- Geen "today's stats" / "this week's progress"
- Geen agent-suggesties op het landing-niveau
- Geen filters/zoekopties direct (search is universal via `/`)

---

## 7 — Card-Stack Decision Pattern (universele queue-UX)

Wanneer operator vanuit triage in een queue klikt, opent de card-stack:

```
─ Routing  •  3 of 5  •  Next: Classification (HOT, 8min)  •  ⬤ on-pace ─
─ ⓘ Why: HOT lead (score 87), trust-load-bearing T1 — always-review ──

[ Workflow-specifieke card-body — sectie 8 ]

─────────────────────────────────────────────────────────────────────
[A]pprove & route  [P]ick alt  [O]verride  [H]old  [N]ext  [V]iew audit  [?]
─────────────────────────────────────────────────────────────────────
```

### 7.1 Shell-elementen (gedeeld door alle workflows)

| Element | Doel | Gedrag |
|---|---|---|
| **Top-strip (regel 1)** | Workflow + positie + next-up preview + urgency-dot | Altijd zichtbaar; tekstualiseer next-up als één regel; urgency-dot is groen/geel/rood |
| **Why-string (regel 2)** | Verklaring waarom deze decision in de queue staat | Operationele taal, ≤8 woorden ideaal, ≤12 max (zie 7.2) |
| **Card body** | Workflow-specifieke content (sectie 8) | Vult de meeste schermruimte |
| **Cluster banner** | Verschijnt conditioneel boven body wanneer ≥3 vergelijkbare items | "ⓘ 3 similar routes queued (Drenthe • heat pump)" — geeft batch-modus hint |
| **Action bar** | Single-letter keyboard shortcuts | Letters visueel zichtbaar op knoppen ("[A]pprove") |

### 7.2 De "Why-string" — strict copy-guide

De Why-string is **gegenereerd door de autonomy-architectuur regels**, niet door een LLM. Letterlijk gemapped vanuit het Workflow Profile en de tier-rule die deze decision in de queue zette.

| Regel | Goed | Fout |
|---|---|---|
| ≤ 8 woorden ideaal, ≤ 12 max | "Confidence below autonomy threshold" | "We detected an interesting opportunity here" |
| Verwijs naar regel/drempel, niet lead-eigenschap | "T1 always-review, trust-load-bearing" | "Premium lead from Tweakers" |
| Geen adjectieven (high-value, promising) | "Within ambigue band 40-75" | "High-value lead requiring attention" |
| Geen werkwoorden met AI-agency (detected, identified, suggests) | "Outcome confirmation pending" | "AI identified potential conversion" |
| Operationele taal, geen marketing | "Sample rate quota — Y-mark for audit" | "Spotlight on a hot prospect" |

**Implementation pattern**: een server-side `whyString(decision, workflow_profile)` functie die uit een vaste lookup-tabel kiest op basis van: tier, risk_class, sample-policy, en de specifieke trigger. Geen LLM-generatie. Geen marketing-creativiteit.

### 7.3 Action key conventies (uniform over alle cards)

| Key | Betekenis | Universeel? |
|---|---|---|
| **A** | Primary approve / accept agent recommendation | Routing card only |
| **R** | Reject / discard | Workflow-specifiek |
| **P** | Pick alternative | Routing card |
| **O** | Override (start inline override-flow) | All workflows |
| **H** | Hold (lead apart zetten, kom later terug) | All workflows |
| **N** | Next without action (skip naar volgende, decision blijft staan) | All workflows except classification (zie 8.2) |
| **V** | View audit chain (inline tree-view) | All workflows |
| **Esc** | Back / cancel — preserves state | All workflows |
| **?** | Show keyboard shortcuts overlay | All workflows |
| **1/2/3** | Pick top-3 categorie (classification) of installeur-alt | Workflow-specifiek |
| **S** | Save | Conversion card only |
| **E** | Edit fields | Conversion card only |
| **F** | Flag dispute | Conversion card only |
| **U** | Uncertain qualifier | Classification card only |
| **M** | Mixed intent qualifier | Classification card only |
| **T** | Taxonomy gap qualifier | Classification card only |

### 7.4 Cluster-banner regels

Banner verschijnt **alleen wanneer ≥3 items in de huidige queue** dezelfde clustering-criteria delen:

- Routing: zelfde geo + zelfde niche
- Classification: zelfde source + vergelijkbare confidence-band
- Conversion: zelfde installateur

Banner-tekst is feitelijk, geen marketing:

```
ⓘ 3 similar routes queued (Drenthe • heat pump) — same installer fits 2/3 → batch-mode tip
```

Banner verdwijnt zodra cluster onder 3 items zakt. Geen permanent UI-element.

### 7.5 Auto-save discipline

- Elke A/R/P/O/S/H actie commit direct naar `decisions` tabel
- Geen "save-button" UI
- Optimistic UI: card flipped naar volgende voordat DB ack komt (rollback bij fail)
- Failures tonen één-regel error onder card (geen modal), met retry

### 7.6 Queue-claim voor multi-operator safety (vanaf V0)

Bij openen van een card: console claimt de decision via `queue_claims` (TTL 10min). Andere operators zien claimed-items als "in review by X" en kunnen niet parallel claimen.

Solo V0 = geen zichtbare gedrag-verandering. Multi-V1 = geen race conditions.

---

## 8 — De drie workflow-specifieke card-bodies

### 8.1 Routing card (lead delivery)

```
[ Top-strip + Why + cluster-banner uit sectie 7 ]

┌─────────────────────────────────────────────────────────────────────┐
│  LEAD                                                                │
│  HOT (score 87) • Tweakers thread • 2u oud                          │
│  Niche: warmtepomp        Geo: Drenthe / Schoonebeek (zip 7741)     │
│                                                                       │
│  "We willen onze gasketel vervangen, hebben offerte van XYZ          │
│  gekregen maar willen tweede mening. Iemand recente ervaring met     │
│  hybride lucht-water systemen in deze regio?"                        │
│                                                                       │
│  [+ show full thread (3 replies)]    [+ show agent reasoning]        │
├─────────────────────────────────────────────────────────────────────┤
│  AGENT RECOMMENDS                                                    │
│  ▸ HVAC Schoonebeek BV          Strong regional fit • 8 km          │
│    • High conversion history • Open capacity                         │
│    • Hybrid-specialized • Responsive (recent: 2u 14min)              │
│                                                                       │
│  Alternatives:                                                       │
│  ◯ Klima-Tech Drenthe          Moderate regional fit • 12 km       │
│    • Limited capacity • Generalist                                   │
│  ◯ NoordWarmte BV              Distance limit • 18 km              │
│    • Slow response history • Generalist                              │
├─────────────────────────────────────────────────────────────────────┤
│  [A]pprove & route  [P]ick alt  [O]verride  [H]old  [N]ext  [V]  [?]│
└─────────────────────────────────────────────────────────────────────┘
```

#### Wat altijd zichtbaar is

- Lead-meta: score-band, source, age, niche, geo (postcode), post-text max 6 regels
- Top-installer met **decision-support language** (sectie 8.4): kwalitatieve labels, geen fake precision
- 2 alternatives, ook in decision-support-language
- Action bar

#### Wat één klik verder zit

- Full thread / reply tree
- Agent's LLM reasoning trace
- Per-installateur conversie-historie (klik op naam → mini-view)

#### Acties

- **A**: keurt agent's top-aanbeveling goed, route + save
- **P**: opent inline alt-select (radio op de twee alternatieven), pijl/1-2 + Enter
- **O**: opent inline override flow (sectie 9.1)
- **H**: hold met optionele single-line reden
- **N**: skip zonder beslissing, lead blijft in queue, komt aan einde terug
- **V**: opent audit chain inline (sectie 9.3)

### 8.2 Classification card (signal ambigue band, confidence 40-75)

```
[ Top-strip + Why uit sectie 7 ]

┌─────────────────────────────────────────────────────────────────────┐
│  SIGNAL                                                              │
│  Source: ouders.nl forum • 4u oud • user: tweemoeders-bart           │
│  Pre-score: 0.62 (ambigue band)                                      │
│                                                                       │
│  "Even geleden post ik over de subsidie maar nog niet veel reactie.  │
│  Iemand toch een idee wat zo'n hybride installatie nu echt gaat      │
│  kosten met de huidige aanvragen? Mijn aannemer wil offerte maar     │
│  ik wil eerst beeld."                                                │
│                                                                       │
│  [+ show 30s context window from forum]                              │
├─────────────────────────────────────────────────────────────────────┤
│  AGENT'S BEST GUESSES                                                │
│  [1]  research_intent           confidence 62%  ▓▓▓▓▓▓░░░░          │
│       reasoning: "kostenvergelijking, geen koopintentie nu"          │
│                                                                       │
│  [2]  purchase_intent_pre_quote conf 28%  ▓▓░░░░░░░░                 │
│       reasoning: "aannemer wil offerte uitbrengen → mogelijke buyer" │
│                                                                       │
│  [3]  no_intent                 conf 10%  ▓░░░░░░░░░                 │
├─────────────────────────────────────────────────────────────────────┤
│  [1][2][3] confident pick  [U]ncertain  [M]ixed  [T]axonomy gap     │
│  [N]o intent  [O]verride  [H]old  [V]  [?]                          │
└─────────────────────────────────────────────────────────────────────┘
```

#### Operator uncertainty signals

Geen geforceerde zekerheid in de dataset. Vier qualifier-acties:

- **1/2/3** = confident pick van getoonde top-3 → `qualifier: confident`
- **U** = uncertain pick → daarna 1/2/3 → `qualifier: uncertain`
- **M** = mixed intent → pick primary 1/2/3, dan secondary 1/2/3 → `qualifier: mixed, secondary_category: <X>`
- **T** = taxonomy gap (niets past) → save `category: <taxonomy_gap>, qualifier: taxonomy_gap` → queue voor taxonomy review (Learning Velocity Metric input)
- **N** = no intent (confident negative classification, NIET een skip) → `category: no_intent, qualifier: confident`
- **O** = override (free-form, opens override flow)
- **H** = hold

**Geen plain "skip" key**: ambigue classificatie *moet* een operator-keuze hebben. `H` (hold) is wel beschikbaar voor "ik weet het niet, kom later terug".

#### Dataset-implicatie

`decisions.reviewer_decision` JSONB krijgt:

```json
{
  "category": "research_intent",
  "qualifier": "uncertain",
  "secondary_category": null,
  "source": "operator_pick"
}
```

### 8.3 Conversion registration card

```
[ Top-strip + Why uit sectie 7 ]

┌─────────────────────────────────────────────────────────────────────┐
│  LEAD HISTORY                                                        │
│  lead-7423 • delivered 2026-05-01 to HVAC Schoonebeek BV            │
│  Follow-up email sent 2026-05-15 (auto-draft, you approved)          │
│  Installer responded 2026-05-16 14:32                                │
├─────────────────────────────────────────────────────────────────────┤
│  INSTALLER'S REPLY                                                   │
│                                                                       │
│  "Hi, klant heeft inderdaad bij ons getekend op 12 mei.              │
│  Hybride lucht-water systeem, installatie staat gepland voor         │
│  15 juni. Bedrag: 14.500 incl BTW. Bedankt voor de doorverwijzing!"  │
│                                                                       │
│  [+ show full email thread]                                          │
├─────────────────────────────────────────────────────────────────────┤
│  AGENT'S PARSED FIELDS  (review and confirm)                        │
│                                                                       │
│  Outcome:        ☑ Won    ☐ Lost    ☐ Unclear                       │
│  Value band:     ☐ <€5k   ☑ €5-15k  ☐ €15-30k  ☐ >€30k             │
│  Install:        ☐ Confirmed  ☑ Likely  ☐ Uncertain                 │
│  Attribution:    ☑ High (installer expliciet bevestigd)             │
│                  ☐ Medium  ☐ Low  ☐ Disputed                        │
│  Notes:          [korte tekst, optioneel______________________]      │
├─────────────────────────────────────────────────────────────────────┤
│  [S]ave conversion  [E]dit fields  [F]lag dispute  [V]  [?]         │
└─────────────────────────────────────────────────────────────────────┘
```

#### Lichter V0

Geen exacte bedragen, exacte datums, of CRM-veld-explosie V0. Vijf velden, allemaal kwalitatief-band of toggle:

- **Outcome** (Won / Lost / Unclear)
- **Value band** (4 banden in €5k stappen, geen exacte bedragen)
- **Install** (Confirmed / Likely / Uncertain)
- **Attribution** (High / Medium / Low / Disputed)
- **Notes** (optioneel single-line)

Detailliering komt zodra echte conversie-processen bestaan. V0 = robuuste dataset-basis, geen vroege rigiditeit.

#### Save-discipline (dataset-defining workflow)

- **S** save vraagt "are you sure?" als parse-confidence ≥80%; verplicht `E` edit eerst als <80%
- **E** edit zet velden in edit-mode, Tab tussen velden, Space toggle, pijlen voor band-selectie
- **F** flag dispute opent korte dispute-flow (reason + Telegram naar founder als dispute-resolutie workflow nog niet bestaat in V0)
- **Save is irreversibel-in-UI** maar reversibel via rollback (autonomy spec 8.5)

### 8.4 Decision-support language

In plaats van "91% fit" (fake mathematische precisie):

| Categorie | Kwalitatieve labels |
|---|---|
| **Regional fit** | Strong / Moderate / Distance limit / Out of region |
| **Conversion history** | High / Solid / Limited / No history yet |
| **Capacity** | Open / Tight / Limited / Closed |
| **Niche match** | Hybrid-specialized / Generalist / Off-niche |
| **Response history** | Very responsive / Responsive / Slow / Unresponsive |

Numerieke data blijft secundair (km, response-times) maar de **headline** is de eerlijke kwalitatieve label. Het scoring-systeem mag intern rekenen, maar de UI presenteert geen onverdiende decimalen.

### 8.5 Wat de drie cards delen

- Identieke shell + top-strip + Why-string pattern
- `[?]` help overlay toont workflow-specifieke shortcuts
- `[V]` audit chain inline view
- `[Esc]` terug naar exact queue-positie
- Cluster-banner verschijnt cross-workflow wanneer ≥3 similar items
- Auto-save op actie

### 8.6 Wat de drie cards expliciet NIET tonen V0

- **Aanverwante leads** ("you processed 3 similar last week") — visueel ruis
- **Operator-performance metrics** — anti-gamification
- **Confidence-scoring uitleg als infographic** — agent reasoning regel volstaat
- **Sneak peek van toekomstige queue-items** behalve next-up regel
- **Real-time updates tijdens card-flow** — queue freeze tot card-actie
- **Hover-cards / tooltips overal** — alleen waar operationeel zinvol

---

## 9 — Override flow + Audit + Search

### 9.1 Override inline mini-form (geen modal)

```
[O]verride pressed →

─ Override ───────────────────────────────────────────────────────
  Category:   [1] taxonomy miss   [2] too strict   [3] too lax
              [4] context missing [5] other
  →
  Reason:     [Agent miste lokale Drenthe HVAC specialist________]
  →
  [Enter] save & next  •  [Esc] cancel
─────────────────────────────────────────────────────────────────
```

- Twee-step inline form binnen dezelfde card-shell
- Category: één-toets selectie (1-5), tekst wordt rechtstreeks gerendered uit `override_categories` tabel
- Reason: single-line input, max 200 tekens, vrije tekst
- Enter slaat op + flipped naar volgende decision
- Esc breekt af, terug naar pre-override card-staat

#### Audit log fields gevuld

```
override_category: "too_strict"          
override_reason: "Agent miste lokale Drenthe HVAC specialist"
reviewer_decision: { ... operator's eigen pick ... }
agreement: N
```

### 9.2 Override taxonomy als evolvable DB-data

```sql
CREATE TABLE override_categories (
  category_key   TEXT PRIMARY KEY,         
  display_label  TEXT NOT NULL,
  active         BOOLEAN DEFAULT true,
  sort_order     INT,
  added_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

V0 seed-data:

| category_key | display_label |
|---|---|
| `taxonomy_miss` | taxonomy miss |
| `too_strict` | too strict |
| `too_lax` | too lax |
| `context_missing` | context missing |
| `other` | other |

UI rendert live uit deze tabel. Toevoegen/hernoemen/retireren = data-operatie, geen UI-deploy. Toevoeging is een T0-beslissing (lead operator). Per-categorie statistieken accumuleren automatisch in `decisions.override_category` → wordt input voor V1 pattern-analyse en Learning Velocity Metrics.

### 9.3 Audit chain view: inline tree, default compact

Vanuit elke card, `V`-toets opent inline ASCII-tree:

```
─ Audit chain  •  lead-7423  •  [Esc] back ──────────────────────

📨 Signal           2026-04-28 14:02   Tweakers thread #abc-123
└─ 🔍 Intake         04-28 14:03         pre-score 0.62 (ambigue)
   └─ 🤖 Classify    04-28 14:04         "research_intent" 
      │                                  agent: research 62% / purchase 28%
      │                                  operator: research (confident)
      └─ ⚖️  Score    04-28 14:05         87 (HOT band)
         └─ 📦 Lead   04-28 14:06         lead-7423 created
            └─ ⏳ Queued for routing 04-28 14:06
               └─ ✅ Routed  05-01 09:14  → HVAC Schoonebeek BV
                  └─ 📧 Follow-up         05-15 09:00  (op approved draft)
                     └─ 💬 Reply          05-16 14:32  installer responded
                        └─ ✓ Conversion   05-16 15:08  Won, €5-15k band

  Click any node for full decision details  •  [/] search elsewhere
─────────────────────────────────────────────────────────────────
```

#### Per-decision expand (default compact)

```
   └─ 🤖 Classify    04-28 14:04    "research_intent"
      ┌──────────────────────────────────────────────────────┐
      │ workflow:       signal_classification                 │
      │ agent_rec:      research_intent (62%) / purch (28%)   │
      │ operator:       founder                               │
      │ op_decision:    research_intent (qualifier: confident)│
      │ agreement:      Y                                     │
      │ time_to_decide: 18s                                   │
      │ outcome:        delivered, won                        │
      │                                                       │
      │ [A]dvanced inspect →  [L]LM reasoning →  [-]collapse │
      └──────────────────────────────────────────────────────┘
```

Default toont **operational truth**, niet infrastructure metadata.

`[A]dvanced inspect` toont alleen-dan: `decision_id`, `profile_version`, `tier_at_decision`, raw `agent_id`, `inputs_hash`, profile-numeric-thresholds. Voor engineering-debugging, niet voor dagelijkse ops.

`[L]LM reasoning` toont het volle agent reasoning trace (mogelijk lang).

#### Audit inspect-on-demand discipline (anti-rabbit-hole)

- **Time-in-audit indicator** verschijnt na 60s in audit-view: subtiele `⏱ 90s in audit` rechtsboven
- **Soft prompt na 3 min**: `Continue queue work? [C]ontinue • [stay]`
- **Esc herstelt EXACT** queue-positie + scroll-positie van pre-audit moment
- **Geen "open in new tab"** pattern — single-threaded focus
- **Current-lead-scoped V0**: geen klik-door naar "andere leads van dezelfde installateur" of "vergelijkbare conversies" — dat is V1 pattern-analyse

### 9.4 Universal search

```
[/] →

─ Search ─────────────────────────────────────────────────────────
  > heat pump drenthe                                              
                                                                   
  Matches:                                                         
  • lead-7423  Tweakers • "willen onze gasketel..."  • Won 05-16  
  • lead-7401  Reddit • "warmtepomp advies regio..."  • Routed   
  • lead-7389  ouders.nl • "subsidie hybride..."     • Hold      
                                                                   
  [Enter] open audit chain  •  [Esc] cancel                       
─────────────────────────────────────────────────────────────────
```

#### V0 search scope

- Match op: lead_id (exact), signal text (Postgres tsvector full-text), installer name (exact + prefix), niche, geo
- Max 10 matches, met 1-regel preview + status
- Enter → audit chain view voor die lead
- Geen advanced filters, geen faceting, geen sort-options

#### Retrieval architecture (extensible, niet doodontworpen V0)

```
retrieval/
├── interface:   retrieve(query, mode="text") → [match]
├── V0 modes:    "text" (Postgres tsvector full-text on signal + installer)
│                "exact" (lead_id, installer_id lookup)
├── V1+ modes:   "similar_lead" (vector-search op signal-embedding)
│                "similar_installer" (regional/historical pattern lookup)
│                "conversion_analog" (outcome-pattern matching)
│                "regional_pattern" (geo + niche aggregation)
└── UI:          rendert wat retrieve() teruggeeft, kent geen mode-specifics
```

V0 implementeert alleen "text" en "exact". Maar de **interface** is mode-aware vanaf dag 1. Latere modes pluggen in zonder UI-aanpassing.

**Anti-pattern dat we vermijden**: search direct tegen Postgres queryen in UI-code — dan moeten we het later her-architecten wanneer "vergelijkbare leads" of "installer memory" toegevoegd wordt.

### 9.5 Wat audit/search NIET in V0 bouwt

| Niet V0 | Reden |
|---|---|
| Aparte audit-pagina/dashboard | Inline-in-card = geen page-navigation |
| Filterbare/sortable audit-tabel | Audit is keten-traversal, geen tabular browse |
| Date-range pickers | YAGNI |
| Export naar CSV/PDF | Komt als compliance vraagt |
| Audit-diff view (decision N vs M) | Bouw als override-pattern-analyse echt nodig |
| Real-time audit-streaming | Pull-on-load past bij rest van console |
| Audit-alert notifications | Telegram + Operational Headroom dekt dit |
| Visualisaties (Sankey/timeline-graphs) | Cognitive overhead zonder operationele waarde |
| Cross-lead navigation in audit | Anti-rabbit-hole — V1 pattern-analyse |

---

## 10 — Auth, Multi-Operator Prep, Telegram

### 10.1 Single-user magic-link auth V0

- Email magic-link via NextAuth (of vergelijkbaar)
- Sessie in `sessions` tabel, 30-day default expiry
- `operators` tabel met `role` veld; founder = `lead`
- **Geen role-based UI gating V0** — alle rollen zien identieke UI

### 10.2 Multi-operator-ready architectuur (zonder singleton-assumpties)

- **Geen "current_operator"** globale state — altijd uit sessie afgeleid
- **Queue-claim mechanism** (`queue_claims` tabel) vanaf dag 1, ook met één operator
- **Sessions zijn DB-persistent**, niet localStorage-only
- **Geen "always-on" assumptions** — alle achtergrond-processen weten operator kan afwezig zijn
- **Tweede operator hire** = nieuwe rij in `operators`, geen code-wijziging

### 10.3 Telegram als enige notificatie-surface V0

Bestaand (uit autonomy/Plan B): launchd run-digests + heartbeat alerts → Telegram.

Console v0 toevoegingen:

- **High-urgency events** sturen Telegram + state-preserving deep-link:
  - Kill-switch fired
  - Anomaly-detector fired
  - CoF-exclusivity breach attempt
  - Operational Headroom rood
  - Conversion-registration overdue
- **GEEN in-console notifications V0** (toasts/badges/bell-icons)
- Operator's "console is dicht" staat is acceptabel — Telegram vangt wat ertoe doet

### 10.4 State-preserving deep-links

Deep-link format:

```
https://console.local/d/{decision_id}?return_to=triage
https://console.local/d/{decision_id}?return_to=routing&pos=3
https://console.local/l/{lead_id}?return_to=audit&parent_decision={uuid}
```

**Contract:**

- Telegram-link opent direct in target view (card of audit)
- Operator's Esc-handler leest `return_to` parameter
- Esc keert exact terug naar opgegeven context — niet naar generic landing
- Als `return_to` ontbreekt: Esc gaat naar triage (sane default)

Voorbeeld flow:

```
1. Operator zit niet in console
2. Telegram alert: "Kill-switch fired: signal_classification → 
   https://console.local/d/abc123?return_to=triage"
3. Operator klikt → console opent direct op decision-abc123 detail view
4. Operator inspecteert, beslist
5. Operator drukt Esc → triage opent (volgens return_to)
```

Tweede voorbeeld (operator was al aan het werk):

```
1. Operator zit in Routing queue, positie 3
2. Telegram alert (urgente kill-state)
3. Operator klikt link → opent dispute card direct
4. Operator handelt
5. Esc → terug naar Routing queue positie 3, scroll positie behouden
   (return_to van originele context blijft in sessie)
```

---

## 11 — One-look V0 + Typography/Density Discipline

V0 heeft **één visuele stijl**. Geen theming, geen customization, geen dark mode. Dit is een keuze, niet een gebrek.

**Maar:** binnen die ene look worden typography, spacing, scanability en reading rhythm **kritieke implementation-disciplines**. Niet feature-keuzes — executie-standaarden.

### Implementatie-discipline contracts

| Aspect | Contract |
|---|---|
| **Typography** | Monospace voor decision-data, sans-serif voor UI-chrome. Hiërarchie via gewicht en hoofdletter-pattern, niet via kleur-explosie. |
| **Density** | Cards optimaal voor 1280×800+ viewport. Geen wide-screen-only layouts. Geen mobile responsive scaling V0. |
| **Spacing** | Acht-pixel grid. Geen ad-hoc paddings. Card-zones (lead/agent/actions) duidelijk gescheiden door whitespace, niet door borders. |
| **Reading rhythm** | Post-text max 6 regels default met expand. Agent-reasoning max 1 regel default. Geen tekst-walls. |
| **Keyboard flow** | Tab-order matcht visuele flow. Tab nooit "skipt" naar onverwachte velden. Enter altijd commit primary action. |
| **Scanability** | Operator scant card in <3s. Belangrijkste info (score, geo, agent-rec) zichtbaar in top-2/3 van het scherm. |
| **Color** | Monochrome basis + groen (positive), geel (caution), rood (urgent). Geen secundaire kleurpaletten V0. |
| **Iconography** | Emoji-stijl symbols voor audit-tree (📨 🔍 🤖 ✅). Functioneel, niet decoratief. |

### Wat dit NIET betekent

- Geen design-systeem-document V0 (shadcn-defaults + bovenstaande disciplines volstaan)
- Geen styleguide-tool of Figma-library
- Geen aparte design-fase vóór implementatie
- Geen periodieke "visual polish" sprints V0

Implementation team werkt direct met deze contracts. Polish komt door dagelijks gebruik + iteratie (zie sectie 14).

---

## 12 — V0 Componenten-inventaris

Het concrete deliverable voor writing-plans. Twaalf componenten:

| # | Component | Type | Notes |
|---|---|---|---|
| 1 | Auth (magic-link login + session middleware) | Backend route + UI page | NextAuth of equivalent |
| 2 | Triage overview page | UI page | `/` route, leest counters uit DB |
| 3 | Card-shell component | UI component | Top-strip + body + actions + cluster-banner |
| 4 | Routing card-body | UI component | Workflow-specifieke layout |
| 5 | Classification card-body | UI component | Met U/M/T qualifier acties |
| 6 | Conversion card-body | UI component | Met won/lost/bands/attribution |
| 7 | Override inline-form component | UI component | Tweestap category + reason |
| 8 | Audit chain inline-view component | UI component | ASCII-tree renderer + node-expand |
| 9 | Universal search overlay (`/`) | UI overlay | Calls retrieval service |
| 10 | Operational Headroom widget | UI component | Top-right indicator |
| 11 | Why-string generator (server-side) | Backend service | Reads profile + tier-rule, no LLM |
| 12 | Retrieval service interface | Backend service | V0: text + exact modes |

**Backend ondersteuning** (niet apart genummerd, inherent aan deze componenten):
- DB schema migrations voor `operators`, `sessions`, `queue_claims`, `override_categories`
- `decisions` write-API (één endpoint dat alle workflow-acties handelt)
- Workflow Profile reader (cached, refetch op profile_version change)
- Kill-state checker (run per decision-fetch)
- Telegram-deep-link generator + handler

### Buildbaarheid

| Variabele | Waarde |
|---|---|
| Build-tijd (solo developer, V0) | 4-6 weken |
| Build-tijd (parallel agent-execution) | 2-3 weken |
| Lines-of-code schatting (excl. deps) | 3.000-5.000 LOC |
| Aantal DB-migrations | 4-5 |
| Test-coverage doel V0 | Critical paths (auth, decision-save, audit-fetch, queue-claim) |

---

## 13 — Wat V0 expliciet NIET levert (V1+ inventaris)

Dezelfde lijst als Out of Scope (sectie 3), nu met expliciete activatie-triggers:

| Component | V1+ trigger voor build |
|---|---|
| RBAC role-gating | Tweede operator hire + rol-specifieke restrictie nodig |
| Mobile-responsive UI | Aantoonbaar operator-mobile-use-case |
| Dark mode / theming | Operator-team aanvraag (vóór dat: not built) |
| Real-time updates / websockets | Multi-operator coordinatie wordt friction-point |
| In-console notifications | Real-time tier bereikt + multi-op coordinatie |
| Bulk acties / multi-select | Aantoonbaar workflow bottleneck |
| Export naar CSV/PDF | Compliance vraag of installateur-aanvraag |
| Operator analytics in UI | Permanent uitgesloten (anti-gamification) |
| Performance dashboards | Permanent uitgesloten (anti-dashboard) |
| Saved searches / favorites | Search-frequency rechtvaardigt het |
| Calendar / shift planning | Multi-op shift-coordinatie nodig |
| File upload / annotation | Workflow vraagt het |
| A/B testing UI varianten | Geen tooling V0 |
| Onboarding tour / tooltips | Tweede operator hire (founder kent eigen tool) |
| i18n / vertaling | Internationale ops |
| Cross-lead audit navigation | V1 pattern-analyse functionaliteit |
| Sandbox UI (Synthetic, Parallel A/B, Promotion Drill modes) | Eerste reële tier-promotie (uit autonomy spec) |
| Pattern-analyse UI voor overrides | >100 overrides/week wordt rauw lezen onmogelijk |
| Installer-facing portal | Separate product, separate spec |

---

## 14 — Build-time framing: V0 = first usable, niet production-mature

**Belangrijk:** "4-6 weken" levert een **werkbare** Console v0, geen **gepolijste** Console v0.

| Wat V0 levert | Wat V0 niet levert |
|---|---|
| Alle 12 componenten functioneel | Pixel-perfect typography |
| Keyboard-shortcuts werken | Optimale keyboard-flow per workflow (komt door iteratie) |
| Audit chain leesbaar | Ideale node-density in tree |
| Override flow snel | Optimale category-set (evolveert via override_categories tabel) |
| Search vindt leads | Ideale ranking van matches |
| Cluster-banner verschijnt correct | Optimale clustering-criteria (komt door observatie) |
| Operational Headroom widget zichtbaar | Optimale drempel-thresholds |

**Verwacht patroon na V0-launch:**

- Week 1-2 post-launch: ergonomic-frustraties surfacen (keyboard-shortcuts die niet voelen, audit-flow die haakt, search die irrelevante matches geeft)
- Week 3-4: per-workflow pacing wordt duidelijk (welke beslissingen voelen rush, welke voelen onnodig zwaar)
- Maand 2: Why-string copy wordt verfijnd op basis van patronen
- Maand 3: Override-categorieën uitgebreid op basis van geobserveerde gaps
- Maand 6: Eerste werkelijke promotion-evidence in audit log accumuleert

**Implication:** writing-plans output mag NIET ambiëren een "polished" Console v0 te bouwen. Het ambieert een **werkbare** Console v0 die snel in productie kan. Polish komt door operationele iteratie tegen echte data.

---

## 15 — Transitie naar writing-plans

Na founder-akkoord op deze spec, **volgende stap is wel** de writing-plans skill (in tegenstelling tot de autonomy spec die NIET direct geplanned werd). Reden: Console v0 is implementatie-bedoeld, geen north-star architectuur.

Writing-plans krijgt als input:

- Deze spec (Console v0 ontwerp)
- De autonomy spec (regelsysteem dat Console v0 implementeert)
- De V0 inventaris uit autonomy spec sectie 12 (DB-laag dependencies)

Writing-plans levert op:

- Concreet implementation-plan met taken, dependencies, gates
- Test-strategie per component
- Migration sequence voor DB-schema
- Deployment-aanpak (Vercel of self-hosted besluit)
- Eerste-week implementatie-prioriteiten

**Daarna**: implementatie + echte dagelijkse operator usage. Vanaf dat moment stopt het ontwerp-werk; iteratie begint.

---

## Appendix A — Action key reference

| Key | Triage | Routing card | Classification card | Conversion card | Audit view | Override flow | Search |
|---|---|---|---|---|---|---|---|
| `1` | Jump to Routing | (alt-select) | Pick top-1 | (band toggle) | (node-select) | Cat 1 | (match select) |
| `2` | Jump to Classification | (alt-select) | Pick top-2 | (band toggle) | (node-select) | Cat 2 | (match select) |
| `3` | Jump to Conversion | — | Pick top-3 | (band toggle) | (node-select) | Cat 3 | (match select) |
| `4` | — | — | — | — | — | Cat 4 | — |
| `5` | — | — | — | — | — | Cat 5 | — |
| `A` | — | Approve | — | — | Advanced inspect | — | — |
| `E` | — | — | — | Edit fields | — | — | — |
| `F` | — | — | — | Flag dispute | — | — | — |
| `H` | — | Hold | Hold | — | — | — | — |
| `K` | Kill-states | — | — | — | — | — | — |
| `L` | — | — | — | — | LLM reasoning | — | — |
| `M` | — | — | Mixed intent | — | — | — | — |
| `N` | — | Next w/o action | No intent | — | — | — | — |
| `O` | — | Override | Override | — | — | — | — |
| `P` | — | Pick alt | — | — | — | — | — |
| `R` | — | Reject | — | — | — | — | — |
| `S` | — | — | — | Save | — | — | — |
| `T` | — | — | Taxonomy gap | — | — | — | — |
| `U` | — | — | Uncertain pick | — | — | — | — |
| `V` | View recent audits | View audit | View audit | View audit | — | — | — |
| `/` | Search | Search | Search | Search | Search | — | (focus) |
| `?` | Help | Help | Help | Help | — | — | — |
| `Esc` | (no-op) | Back to triage | Back to triage | Back to triage | Back to card | Cancel | Cancel |
| `Enter` | — | — | — | — | (expand node) | Save & next | Open audit chain |
| `Tab` | (navigate) | (alt-select) | — | (edit fields) | — | (cat → reason) | — |

---

## Appendix B — Glossarium

| Term | Betekenis |
|---|---|
| **Card-stack** | UX-pattern: één beslissing per scherm-moment, geen list-with-rows |
| **Card-shell** | Gedeelde container: top-strip + Why + body + action-bar |
| **Card-body** | Workflow-specifieke content binnen de shell |
| **Top-strip** | Eén-regel context bovenin: workflow + positie + next-up + urgency-dot |
| **Why-string** | Eén-regel uitleg waarom deze decision in de queue staat (operationele taal, ≤8 woorden) |
| **Cluster-banner** | Conditionele banner wanneer ≥3 vergelijkbare items queued |
| **Hold state** | Expliciete "kom-later-terug" categorie, niet impliciete skip |
| **Override flow** | Tweestap inline form bij operator-divergentie van agent |
| **Audit chain** | ASCII-tree van lead-lifecycle, inline geopend met `V` |
| **Advanced inspect** | Optionele expand naar infrastructure-metadata van een decision |
| **Operational Headroom widget** | Top-right indicator van OCL-budget consumption (groen/geel/oranje/rood) |
| **Queue-claim** | DB-record dat decision-X door operator-Y geclaimd is (voorkomt race-conditions multi-op) |
| **Decision-support language** | Kwalitatieve labels ("strong fit") in plaats van pseudo-precieze cijfers ("91%") |
| **Qualifier** | Classification-modifier: confident / uncertain / mixed / taxonomy_gap |
| **State-preserving deep-link** | Telegram-link met `return_to` parameter zodat Esc juiste context herstelt |
| **Retrieval service** | Backend interface die search-modes afstract (V0: text, exact; V1+: similar_lead, etc.) |

---

## Appendix C — Workflow Profile contract

Hoe Console v0 een Workflow Profile (uit autonomy spec sectie 6.4) gebruikt:

```yaml
# Voorbeeld profile dat Console v0 leest bij elke decision:
workflow_id: lead_delivery_routing
current_tier: T1
terminal_tier: T2
risk_class: trust_load_bearing

# Velden die Console direct gebruikt:
ocl_budget:
  per_operator_minutes_per_day: 30
  complexity: medium
  expected_volume_per_day: 50
  # → Operational Headroom widget berekening

latency_class: L2
sla_budget_minutes: 240
  # → urgency-dot kleur in top-strip (groen/geel/rood op basis van age vs SLA)

fallback_policy: F-B
out_of_hours_policy: pause
  # → console toont "queue gepauzeerd buiten kantooruren" banner indien van toepassing

cof_circuit_breakers:
  - exclusivity_breach_risk_per_decision > 0.1%
  # → indien getripped: card toont expliciete "T1 forced" Why-string
```

Console kan geen profile-velden wijzigen. Wijzigingen aan profile gebeuren via:

1. Lead operator UI (sectie 9 van autonomy spec, V1+ activation) OF
2. Directe DB-edit met versioned audit-record OF
3. Migration-script bij architectural-shift

Console v0 is **read-only** voor workflow profiles. Schrijft alleen naar `decisions` (audit), `queue_claims` (locking), en `sessions` (auth).

---

**Einde spec.**

Versie 1.0 — 2026-05-18.
Volgende revisie wanneer operationele realiteit aantoont welke ergonomic-aannames bijgesteld moeten worden.
