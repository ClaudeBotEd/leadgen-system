# Lead Radar — Receipt Artifact v0 Design

**Status:** Awaiting founder review (na strategie-brief 2026-05-18)
**Auteur:** Claude Opus 4.7 (i.s.m. founder, sessie 2026-05-18)
**Datum:** 2026-05-18
**Branch:** `feat/facebook-scraper`
**Input contract:**
- `specs/doctrine/trust-provenance-moderation.md` v0.1 — in het bijzonder secties **00.2** (five-thing rule), **01.1** (canonical lead fields), **01.3** (archive obligation), **02.1** (citation surface), **02.2** (uncertainty rendering), **02.3** (vocabulary), **02.4** (anti-AI tells), **02.5** (credibility test), **02.6** (empty & error states), **03.6** (signature semantics), **04.1** (trust contract), **04.2** (five trust events), **04.3** (exclusivity guarantee), **04.4** (dispute right), **04.5** (the receipt) en Appendix A.
- `docs/superpowers/specs/2026-05-18-operator-intelligence-console-v0-design.md` — leverancier van het reviewer-signal (banding, reviewed_by, reviewed_at) en operationele afhandeling van disputes.

**Type:** Operationele UX-, product-semantiek- en trust-rendering spec voor het *afgeleverd-artifact*: het ding dat een installateur in handen krijgt op het moment dat een lead transitioneert naar `DELIVERED`. Geen frontend code, geen HTML, geen Tailwind. Element-ordering en taalregels zijn doctrine; layout-tekeningen zijn v0 sketches.

---

## 0 — Context

Per 2026-05-18 staan vast:

- Doctrine v0.1 — frozen, citeerbaar per ID (A1–A31, B.1 termen)
- Operator Intelligence Console v0 — accepteert reviewer-decisions die de `DELIVERED`-state triggeren
- PCS-v0 — append-only `lead_log.csv`, `installers.csv`, state-machine (NEW → APPROVED → DELIVERED → OUTCOME / REJECTED / EXPIRED)
- Bands HOT / WARM / OPP, reviewer-gebonden (nooit model-gebonden, A4 / A19)

Wat tot vandaag ontbreekt is de specificatie van **wat de installateur fysiek ontvangt** op het moment van delivery. Doctrine 04.5 noemt de vijf benodigde elementen (snippet, source, capture-time, band+reden, reviewer+reply), maar laat hierarchy, visual grammar, email-structuur, en anti-patterns open.

Deze spec sluit dat gat. Eén artifact, twee verschijningsvormen (email-as-receipt, optionele web-permalink), één set regels.

### Wat deze spec IS

Een receipt-grammar:

- Welke vijf elementen verschijnen in welke leesvolgorde
- Hoe provenance gerenderd wordt zodat verificatie binnen 1 klik kan
- Hoe band en onzekerheid eerlijk worden gecommuniceerd zonder pseudo-precisie
- Hoe exclusiviteit en dispute-recht worden gesignaleerd zonder marketing-toon
- De visuele grammatica die *operational intelligence* signaleert in plaats van *SaaS dashboard*
- De anti-patterns die geweigerd worden (citeerbaar per A-ID)
- De email-structuur regel-voor-regel, sender-identity, dispute-pad
- De "looks expensive" mechanica: waar restraint zelf de premium-signal is

### Wat deze spec NIET is

- Geen implementation-plan (volgt via `writing-plans` na founder-akkoord)
- Geen MJML / HTML / Tailwind classes / template-engine keuze
- Geen copy-deck (voorbeelden zijn v0 sketches, geen lockfile)
- Geen design-token systeem (komt in Receipt v0.2 wanneer er twee live touchpoints zijn)
- Geen vervanging of revisie van doctrine 04.5 — dit is implementatie-doctrine, niet trust-doctrine
- Geen `delivery_email.html` templates, geen MTA-keuze, geen DKIM/SPF spec (deployment-spec separaat)
- Geen reviewer-laag onboarding (Operator Console spec dekt dat)

### Lezer-contract

Wie deze spec leest, krijgt antwoord op één vraag:
**"Wat zou ik bouwen / coderen / verifiëren om een installateur in 8 seconden te laten voelen: dit is echt, dit is van mij, dit is reviewed?"**

Element-volgorde en taalregels zijn doctrine. Pixel-keuzes zijn open voor de implementer, mits ze de element-volgorde en regels niet breken.

---

## 1 — Strategische intentie

**De receipt is het product. Niet een notificatie.**

Doctrine 04.1 vat het trust-contract in zes regels. De receipt is het fysieke artifact waarin die zes regels gelijktijdig waarneembaar zijn. Een installateur die het artifact opent moet — *zonder te lezen* — al voelen welke vijf van de zes regels gehonoreerd worden. De zesde (dispute) wordt door het artifact uitnodigend, niet defensief, ondersteund.

| Wat we leveren | Wat we expliciet niet leveren |
|---|---|
| Eén intelligence receipt per delivered lead | Een lead-card in een dashboard |
| Verifiable artifact: snippet + URL + reviewer | "AI-detected interest in heat pumps" |
| Reviewer-by-name, reply-to-human | "no-reply@" / "support@" / generic alias |
| Band als categorie (HOT/WARM/OPP) met één-zin-reden | Score, percentage, gauge, "match rating" |
| One-time delivery; exclusivity is invariant | Lead-card in een queue waar je nog op moet klikken |
| Dispute = direct antwoorden op de reviewer | Ticketing systeem / support workflow |
| Quietly operational, intelligence-grade | Glossy SaaS / marketplace UX |

### Founder-principes voor het artifact

1. **Een receipt, geen notificatie.** "Notificatie" suggereert volume; "receipt" suggereert transactie en bewijs.
2. **Verifieerbaarheid binnen één klik.** Source resolveert, of het archief presenteert zichzelf met een DECAYED-stamp (01.3).
3. **Reviewer is een mens met een naam.** A24 / A26 zijn niet onderhandelbaar.
4. **De snippet is heilig.** Geen paraphrase, geen "cleanup", geen samenvatting (A9, B.1 `signal`).
5. **De band is een categorie, geen getal.** A8, 02.2.
6. **Exclusiviteit is structureel, niet decoratief.** De installateur ziet niet "Exclusief!"; de installateur ziet dat er één ontvanger is, één case-id, één lead-state.
7. **Restraint is het premium-signaal.** Geen "Powered by AI", geen gradient, geen mascotte (A10–A16).

### Strategische uitkomst

Een artifact dat:

- In **≤8 seconden** alle vijf de canonical fields toont (00.2, 02.1, 02.5)
- Binnen **1 klik** een tweede bewijslaag opent (source-url of archief)
- Een reviewer-naam toont die te beantwoorden is **zonder route door support**
- Voorkomt dat de installateur ooit moet vragen: *"is deze lead alleen voor mij?"* — die vraag is per definitie al beantwoord door het bestaan van het artifact
- Past op één scherm zonder scrollen op laptop en mobiel
- Door een reviewer in **≤30s** te lezen is voor self-audit (de reviewer ontvangt een blind copy)

---

## 2 — Information hierarchy

### 2.1 Leesvolgorde (canonical)

De vijf canonical fields uit 04.5 en 02.1, in deze volgorde:

```
1. Snippet (verbatim)                    ← above the fold, eerste element
2. Source affordance + captured_at        ← direct onder snippet
3. Band + één-zin-reden                   ← op gelijke hoogte als source affordance, rechts
4. Reviewer (naam + reviewed_at)          ← signature row, derde lees-moment
5. Exclusivity & dispute affordance       ← footer-strip
```

De volgorde is **niet** alfabetisch, niet visueel-balans-gedreven, niet operator-comfort-gedreven. Hij is **leesgedrag-gedreven**: een installateur die het artifact opent, leest in dit ritme:

| Lees-moment | Vraag in het hoofd van de installateur | Antwoord in het artifact |
|---|---|---|
| t = 0–2s | "Wat zegt deze persoon?" | Snippet, verbatim |
| t = 2–4s | "Waar komt dit vandaan, wanneer?" | Platform + relatief tijdstempel |
| t = 4–6s | "Hoe serieus is dit?" | Band + reden in één zin |
| t = 6–8s | "Wie heeft dit gezien voordat ik het kreeg?" | Reviewer naam + reply-to |
| t = post-read | "Wat als het mis is?" | Dispute-strip onderaan |

### 2.2 Boven-de-vouw / onder-de-vouw

| Zone | Inhoud | Reden |
|---|---|---|
| **Boven de vouw** (altijd zichtbaar zonder scroll, laptop én email-client preview-pane) | Snippet, source affordance, captured_at, band, reden-zin, reviewer-naam | 02.5 credibility-test: alle drie de verificatie-acties moeten zonder scroll te bereiken zijn |
| **Onder de vouw** (toegestaan om te scrollen) | Exclusivity-statement, dispute-strip, lead-case-id, footer | Operationeel maar niet credibility-bepalend |

### 2.3 Wat mag nooit verborgen zitten

Doctrine 02.1 / A17: een band tonen zonder provenance in dezelfde view is een violation. Daarom — en dit gaat verder dan doctrine — geldt voor het receipt-artifact:

```
NEVER HIDDEN          must be visible in the first paint:
  snippet                no truncation > 240 tekens
  source_url             label "open bron" + URL-host zichtbaar
  captured_at            relative form ("4u geleden", "2d geleden")
  band                   HOT / WARM / OPP, with one-sentence reason
  reviewer_name          first + last, never role
  reviewer_reply         direct email address, parseable

NEVER REQUIRED click before exposure:
  the snippet body
  the source host
  the band token
  the reviewer's first name
```

### 2.4 Wat mag wel achter een klik

Acceptabel om one-click weg te zetten (maar niet weg te stoppen):

- Full source URL (verwijst, maar host is wel zichtbaar in tooltip / link-text)
- Captured_at exact ISO-timestamp (relative form bovenaan, hover/tap geeft absolute)
- Lead case-id (zichtbaar in footer, klikbaar voor permalink/dispute pad)
- Archive snapshot (alleen relevant wanneer source 404'd of decayed, 01.3)
- Reviewer's previous-week throughput (V1+, expliciet niet V0)

### 2.5 Wat nooit in het artifact verschijnt

```
NEVER IN THE RECEIPT
  numerieke score                       (A8)
  paraphrase / samenvatting van snippet (A9)
  band-zonder-reden                     (eigen extensie van 04.5)
  reviewer als rol of alias             (A24, A26)
  "AI"/"GPT"/"model" in chrome of body  (A14, A15, A16)
  suggested-action-list zonder citatie  (A12)
  CTA-knoppen ("Accepteer deze lead!")  (eigen, zie §8)
  badges met urgency-trucs              (eigen, zie §8)
  meeloop-tekst à la "AI is thinking…"  (A16)
  "12 leads deze maand" zonder outcome  (A27)
  call-to-action voor andere leads      (zie §8)
```

---

## 3 — Provenance rendering

Provenance is het kerncomponent. Section 01 van doctrine zegt wat we opslaan; deze sectie zegt hoe het verschijnt op het artifact.

### 3.1 Snippet treatment

| Regel | Specificatie |
|---|---|
| Verbatim | Geen edits. Geen capitalisatie-fix. Geen grammar-cleanup. (A3) |
| Quote-grammar | Snippet staat in halve aanhalingstekens of typografische quote-frame; *typografisch*, niet visueel-decoratief. Geen quotebox met gradient, geen "AI-summary" badge. |
| Truncation | Hard cut bij 240 tekens, gevolgd door `…` met expand-affordance. Truncatie alleen waar de oorspronkelijke post langer was; vier-zinnen-post wordt niet ingekort om "schoner" te ogen. |
| Taal | Originele taal. Geen translation V0 (zelfs niet voor non-NL snippets — die hoeft NL-installateur in 99% niet te zien; A9 risk). |
| Emphasis | Geen highlighting van keywords ("warmtepomp" bolden = paraphrase-by-emphasis, A9). |
| Typography-rol | De snippet is *de* serif-of-quietly-prominent passage van het artifact. Body-tekst eromheen is metadata-rang. |

### 3.2 Source affordance

| Element | Regel |
|---|---|
| Link-label | `open bron ↗` (NL) — niet "Bekijk lead", niet "Origineel bekijken", niet "Source". |
| Host preview | Linktext toont host-domain ("tweakers.net", "reddit.com/r/...", "facebook.com/groups/...") als secondary text onder of naast `open bron`. |
| Target | New tab, `rel="noopener"`. Geen redirector. Geen tracking-wrapper. |
| Failure state | Wanneer source = `404` / `decayed` / `taken_down`: vervang link-label door `open snapshot (gearchiveerd)` met DECAYED-stamp. Doctrine 01.3 + B.1 `archive`. |
| Archive stamp visual | Inline pill `DECAYED · gearchiveerd op {datum}` — neutrale kleur (niet rood, niet alarmerend; het ís het systeem). |
| Never | Geen "preview-card" met thumbnail/og:image — dat is marketplace-aesthetic. We tonen de host, niets meer. |

### 3.3 Captured_at rendering

| Vorm | Wanneer | Voorbeeld |
|---|---|---|
| Relative | First paint, primary | `4 uur geleden`, `2 dagen geleden`, `vorige week` |
| Absolute | Hover/long-press, secondary | `2026-05-18 14:21 CEST` |
| Decay marker | Wanneer signal > decay-window (01.6) | `8 dagen geleden · gedimd` met OPP-band |

Geen "now", geen "just now". Receipts worden niet binnen seconden afgeleverd; alles begint bij minuten.

### 3.4 Band rendering

Strikt per 02.2:

```
HOT    solid mark        accent kleur, geen gradient
WARM   outlined mark     dezelfde accent, hollow
OPP    muted mark        grijs, geen accent
```

**Plus** doctrine 04.5: één-zin reden direct onder de band.

```
HOT  ●  Expliciete koopintentie binnen 4 weken;
        homeowner noemt budget en regio.

WARM  ○  Onderzoeksfase; vraagt om vergelijking,
         geen tijdshorizon genoemd.

OPP   ·  Indirecte interesse; geen tijdshorizon
         en geen platform-vraag.
```

| Regel | Specificatie |
|---|---|
| Mark is een glyph, niet een grote badge | Discrete, niet roeptoeterend |
| Reden-zin altijd verplicht | Anders is de band kaal (A17, eigen extensie naar de receipt) |
| Reden-zin is door reviewer geschreven | Geen template-vulling. Geen LLM-gegenereerde reden zonder reviewer-overschrijving. |
| Maximaal 20 woorden | Forceert reviewer-discipline. Lange redenen verraden onzekerheid. |
| Geen percentage, ooit | A8 |
| Geen progress bar / gauge | A8 + 02.2 |

### 3.5 Vocabulary discipline op het artifact

Zonder uitzondering. B.1:

| We zeggen | We zeggen nooit |
|---|---|
| `lead` (na review) | `match`, `kandidaat`, `opportunity` (B.2) |
| `signal` (pre-review) | `lead score`, `AI-prediction` |
| `bron` / `source` | `data point`, `record` |
| `gereviewd door` | `goedgekeurd door AI`, `verified by our system` |
| `vastgelegd vanuit {platform}` | `scraped from web` |
| `verifieerbare intent` | `qualified lead` |
| `de reviewer` | `ons systeem`, `onze AI` |
| `installateur` | `klant`, `gebruiker`, `partner` |
| `dispuut openen` | `support ticket`, `klacht indienen` |

De copy in het artifact wordt door Codex gelint tegen deze tabel (en Appendix B.2) als blok-violation: één treffer = build-fail.

---

## 4 — Exclusivity & lifecycle signaling

Doctrine 04.3 zegt: exclusiviteit is operationeel, niet retorisch. Het artifact moet dat reflecteren — exclusiviteit wordt niet verkondigd, het wordt **gedemonstreerd** door wat er wel en niet in het artifact staat.

### 4.1 De drie demonstraties van exclusiviteit

| Demonstratie | Hoe het werkt | Wat het vervangt |
|---|---|---|
| **Unieke case-id zichtbaar in footer** | `LR-2026-05-18-0042 · uw exclusieve case` | Geen banner "Exclusive!" |
| **`naar: {installateur naam}` in header** | Persoonlijk geadresseerd, niet `Beste partner` of `Dag installateur` | Geen "Geachte SaaS-klant" generic |
| **Geen sociale bewijsdruk** | Geen "5 installateurs hebben deze lead bekeken", geen "haast u" | Geen marketplace-FOMO patterns |

### 4.2 Een expliciete maar ingehouden exclusivity-zin

Eén regel, exact bovenaan footer-strip:

```
Deze lead is uitsluitend naar u verzonden. De casus blijft toegewezen
zolang u reageert; bij geen reactie binnen 5 werkdagen vervalt
het toegewezen-zijn (state: EXPIRED).
```

Geen uitroepteken. Geen markup. Geen icon. **De zin doet het werk.**

Wat de zin expliciet níét belooft:
- "Lifetime exclusive" — dat is onwaar; expired-state bestaat
- "Geen andere installateurs weten van deze lead" — irrelevant; we zeggen dat we hem niet sturen, niet dat hij geheim is

### 4.3 Lifecycle-signalen in het artifact zelf

Het artifact heeft één state op het moment van delivery: `DELIVERED`. Maar het artifact moet de installateur **wegwijzen** in wat erna gebeurt:

| State na delivery | Hoe het artifact dat signaleert |
|---|---|
| `OUTCOME` (deal) | Reply-instructie: "Reageer met 'gewonnen' of details. We registreren het uitkomst-veld." |
| `OUTCOME` (geen deal) | Reply-instructie: "Reageer met 'geen deal' + korte reden. Houdt het corpus eerlijk (04.6)." |
| `EXPIRED` | Footer-zin (zie 4.2) |
| `DISPUTE` | Eigen strip, zie 4.4 |

V0 implementeert deze signalen als **enkele zin per state**, niet als knoppen, niet als CTA-blokken. Reply-by-email is de enige interactie-modus.

### 4.4 Dispute-strip (04.4)

De installateur moet binnen 14 dagen kunnen disputen, en het artifact moet dat dispute-pad als **eerstegraadse aanwezigheid** tonen — niet weggestopt onder een "feedback" link.

```
┌──────────────────────────────────────────────────────────────┐
│ Onjuist iets aan deze lead? Antwoord op deze e-mail.         │
│ {reviewer voornaam} beoordeelt persoonlijk binnen één        │
│ werkdag. Geen ticketing-flow, geen support-queue.            │
│                                                              │
│ Bij gegrond dispuut: credit op uw account, lead-record       │
│ wordt geannoteerd in het archief (01.3).                     │
└──────────────────────────────────────────────────────────────┘
```

| Regel | Specificatie |
|---|---|
| Naam van reviewer in dispute-tekst | Dezelfde naam als in signature-row — anders is de claim leeg (A26, A28) |
| Reply-to-adres = reviewer's persoonlijke (of role-mailbox-die-uitsluitend-de-reviewer-leest) | A26, A28 |
| Geen "dispute form", geen ticket-portal | Email-reply is doctrine-conform |
| 14-dagen-window expliciet | "14 dagen vanaf {delivered_at}" — geen vage "binnen redelijke termijn" |
| Credit-belofte expliciet | Doctrine 04.4 |

---

## 5 — Visual grammar

Doel: het artifact voelt **operational** waar SaaS **showy** zou voelen. Geen frontend code in deze sectie — alleen grammar-regels die de implementer (Codex) als constraint accepteert.

### 5.1 Operational vs SaaS — de grond-keuze

| Operational (wat we doen) | SaaS / Marketplace (wat we vermijden) |
|---|---|
| Tinted neutral background, één accent voor band-mark | Brand-gradient, hero-stripe, color-system reveal |
| Mono- of grotesk-display-typeface alleen voor lead case-id en timestamps | Display-serif voor "personality" |
| Body in een rustige humanist sans (Inter, Söhne-achtig, IBM Plex Sans) | Custom "branded" font dat de huisstijl roeptoetert |
| Snippet in subtle blockquote, links-aligned, geen sierranden | Quote in colored box met aanhalingsteken-illustratie |
| Geen iconen behalve het band-glyph en `↗` op de bronlink | Icon-grid voor metadata, illustrated empty states |
| Spacing: dichtbij waar elementen samenhoren, royaal waar ze los staan | Uniforme padding (operator console spec §11 ondersteunt dit principe) |
| Borders eerlijk gebruikt: één regel-onderscheid tussen body en footer; verder niets | Side-stripes, cards-in-cards, drop-shadows (zie absolute bans in impeccable laws) |

### 5.2 Typography hierarchy

Vier ranks, ratio ≥1.25 tussen stappen:

| Rank | Rol | Voorbeeld | Gewicht |
|---|---|---|---|
| **R1** Display | Niet gebruikt in het artifact | (n.v.t.) | (n.v.t.) |
| **R2** Prominent | Snippet body | quotation, regular weight, marginally larger dan body | regular |
| **R3** Body | Reden-zin, dispute-strip, exclusivity-zin | reading body | regular |
| **R4** Metadata | Captured_at, host, case-id, reviewer-handle | smaller, tighter | regular of slightly bolder |
| **R5** Marks | Band-glyph (●/○/·), `↗` | inline, body-height | (geen weight, glyph) |

Geen rank gebruikt voor "branding" of "vibe". Hiërarchie is functioneel.

### 5.3 Spacing-filosofie

Drie regels:

1. **Snippet ademt.** Royale ruimte boven en onder. De snippet is het zwaarste element; behandel hem zo.
2. **Metadata clustert.** Source, captured_at, band, reden — vier elementen, klein, dichtbij elkaar in één visueel "blok".
3. **Signature breekt.** Reviewer-row krijgt een eigen visuele zone, met witruimte ervoor.

Geen uniforme `padding: 16px`. De receipt heeft **drie zones** met verschillende ritmes:
- Snippet-zone (royaal)
- Metadata-zone (dicht)
- Signature + footer-zone (gemiddeld, met breaks tussen sub-blokken)

### 5.4 Kleur-discipline

Per impeccable laws (OKLCH, neutrals lichtjes getint), en doctrine 02.2:

| Rol | Toepassing | Verbod |
|---|---|---|
| Tinted neutral (background, body) | 99% van oppervlak | Geen `#fff`, geen `#000` |
| Eén accent kleur | Alleen HOT band-mark | Geen accent op buttons, headings, of source-link |
| Muted gray | OPP band-mark | Geen "disabled state" suggestie — OPP is geldig |
| Outlined accent | WARM band-mark | Geen outline op andere elementen |
| Decayed-pill kleur | Neutraal (geen rood) | Niet alarm-coderen — DECAYED is systeem-normaal |

**Drie kleur-rollen totaal.** Niet vier. Niet vijf. De receipt is *restrained* per impeccable color strategy.

### 5.5 Metadata treatment

Metadata = de drie elementen die niet de snippet, niet de reviewer-handtekening zijn. Specifiek:

```
host                  small text, monospace-optional (operator-grammar)
captured_at relative  small text, lower-case "u" / "d" / "w"
band-mark             glyph + label, inline
reden-zin             body-rank, geen quote, geen italic
case-id               smaller, monospace, footer-rank
```

**Monospace gebruik** is selectief: alleen waar het systeem-rang signaleert (case-id, eventueel host). Niet voor de snippet, niet voor reviewer-naam. Mono = "operational identifier", niet "code-aesthetic-because-it's-trendy".

### 5.6 Inspectability als visuele waarde

Elke regel in het artifact moet **inspecteerbaar** voelen — alsof de installateur er over kan hoveren, klikken, vragen "waar komt dit vandaan". Dit is geen feature; dit is een **toon-aspect**.

| Operationele inspectie-cue | Hoe het wordt gerenderd |
|---|---|
| Hover op `captured_at relative` | Absolute timestamp + timezone |
| Hover op band-glyph | Definitie van de band (zelfde tekst als doctrine 01.5) |
| Hover op `reviewed_by` naam | Tooltip: reviewer rol, reply-adres, hoeveelheid leads beoordeeld deze week (V1+; V0: alleen naam + reply) |
| Hover op `bron-host` | Volledige URL |

In V0 implementeert email-client geen hovers, dus deze treats horen bij **web-permalink** als die er komt (zie §11 founder-beslissingen).

---

## 6 — Trust surfaces

Een trust-surface is een element dat actief geloofwaardigheid opbouwt. Een anti-trust-surface is een element dat het ondermijnt. Beide bestaan; de receipt mag alleen het eerste type bevatten.

### 6.1 Trust-additive elementen

Elementen die credibility verhogen — opgenomen, in deze volgorde:

| # | Element | Waarom het werkt |
|---|---|---|
| 1 | **Verbatim snippet** | Tegen-bewijs is publiekelijk verifieerbaar. Niets te paraphraseren = niets te verbergen. |
| 2 | **Source URL zichtbaar + klikbaar** | "Niet vertrouwen? Klik." Dit is de Perplexity-citation analoog. |
| 3 | **Reviewer first + last name** | Een mens met een naam is dispuutbaar; een alias is niet (A24, A26). |
| 4 | **Reviewer reply-adres** | Direct contact = geen support-firewall (A28). |
| 5 | **Captured_at en reviewed_at, beide zichtbaar** | Dual-timestamp toont dat er tijd zat tussen capture en review — geen real-time AI gimmick. |
| 6 | **Unieke case-id** | Lead krijgt een identifier zoals een ticketnummer, niet zoals een notification-id. |
| 7 | **DECAYED-stamp bij oude leads** | Eerlijkheid over staleness ≠ verstoppen ervan. |
| 8 | **Exclusivity-zin (4.2)** | Operationeel, niet retorisch. |
| 9 | **Dispute-strip (4.4)** | Mogelijkheid tot terugslaan = installateur heeft hefboom. |

### 6.2 Trust-erosive elementen — verboden in V0

Elementen die naar AI-spam of marketplace neigen. Niet in het artifact:

| Anti-element | Cite | Waarom het ondermijnt |
|---|---|---|
| Numerieke score / percentage | A8 | Pseudo-precisie suggereert false certainty (00.5) |
| "AI" / "machine learning" in chrome | A14, A15 | Black-box impressie; het tegenovergestelde van auditable |
| Paraphrased / samengevatte snippet | A9 | Eén woord verandering en de verifieerbaarheid verdwijnt |
| Reviewer als rol of alias | A24, A26 | "The review team" is geen persoon, geen dispuut-adres |
| Suggested action zonder citatie | A12 | "Bel deze persoon morgen om 10:00 uur" zonder cite = AI-gok |
| Hero animation / gradient art | A10 | Schreeuwt SaaS, fluistert geen intelligence |
| Mascot / illustration in empty states | A11 | "Take a break 🌱" is niet operational |
| Banner met social proof / urgency | (eigen) | "🔥 5 installateurs willen deze lead" — marketplace anti-pattern |
| Loading animation "AI is thinking" | A16 | Anthropomorfisme — de reviewer dacht, de scanner verzamelde |
| Generic alias as sender | A26 | `leads@`, `noreply@`, `team@` allen verboden |
| Auto-generated subject line | A13 | Reviewer schrijft de subject of er is een template door reviewer-handen gegaan |

### 6.3 De drie verificatie-acties (02.5 credibility test)

Het artifact slaagt als de installateur deze drie zonder verlaten-van-surface kan:

```
1. Read the homeowner's own sentence.
   → snippet, verbatim, boven de vouw

2. Click through to the original post.
   → source link, one click, opens nieuwe tab
      of, bij decay: archief opent met DECAYED-pill

3. See who reviewed it, and when.
   → reviewer name + reviewed_at, signature row
```

Als één van de drie ontbreekt of effort kost: het artifact heeft gefaald.

### 6.4 Reviewer-surface: de signature row

De signature is een eersteklas trust-element. Specificatie:

```
─────────────────────────────────────────────────
gereviewd door  M. de Vries · 4u geleden
                m.devries@lead-radar.nl
─────────────────────────────────────────────────
```

| Element | Regel |
|---|---|
| Naam | Voornaam-initiaal + achternaam, óf voornaam + achternaam. **Nooit** "Reviewer team", "Het Lead-radar team", "M.D.V." (initialen-only) |
| Reviewed_at | Relative tijd, consistent met captured_at vorm |
| Reply-adres | Direct adres van reviewer of unieke role-alias die uitsluitend door één reviewer wordt gelezen |
| Geen titel ("Senior Lead Reviewer") | Marketing-trick, niet doctrine-conform |
| Geen photo / avatar V0 | Beslissing — zie §11 founder-decisions |
| Geen "AI-assisted" tag | A14 |

---

## 7 — Email structure

Het artifact wordt in V0 gedraad als **email**. Andere kanalen (web permalink, Telegram) zijn opt-in extensies, niet vervangers (zie §11).

### 7.1 Sender identity

| Veld | Specificatie |
|---|---|
| `From` (display) | `{reviewer voornaam} {reviewer achternaam} — Lead Radar` |
| `From` (address) | `{reviewer-handle}@lead-radar.nl` of `{reviewer-firstname}@lead-radar.nl` |
| `Reply-To` | Identiek aan `From` address — niet naar een ticketing-systeem |
| `Sender` header | Mag het MTA-relay zijn; nooit `noreply` |
| `Return-Path` | Eigen domein, gemonitord voor bounces |
| Verboden | `noreply@`, `leads@`, `team@`, `support@`, `info@` |

Sender = de reviewer. Niet een merk.

### 7.2 Subject line

| Aspect | Regel |
|---|---|
| Schrijver | Reviewer schrijft of bevestigt; nooit auto-generated (A13) |
| Vorm V0 | Eén operational template: `{regio of postcode-prefix} · {warmtepomp/airco/laadpaal/zonnepanelen/...} · {HOT/WARM/OPP}` |
| Voorbeeld | `1015AA · warmtepomp · HOT` |
| Niet toegestaan | Subject met emoji (🔥 etc.), subject met urgency-trucs ("⚠️ Last chance!"), subject met merknaam ("Lead Radar:..."), subject met first-line preview |
| Geen `[Lead Radar]` prefix | Verstoort professional toon; merk hoort niet in de subject |
| Vraag-vorm? | Toegestaan wanneer het de snippet weerspiegelt: `Vraag uit Amsterdam over warmtepomp + zonnepanelen` |

De subject line is **één van de elementen die door een mens wordt aangeraakt**. Pre-fill is OK, doorschuiven naar inbox zonder reviewer-bevestiging is niet (A13).

### 7.3 Pre-header / preview text

De preview-text (eerste regel die mail-clients tonen onder de subject) is **niet** automatisch de eerste regel van de body. Specificatie:

```
{reviewer eerstename} reviewde een {platform}-post uit {regio}.
```

Bijvoorbeeld:

```
Marieke reviewde een Reddit-post uit regio Utrecht.
```

Geen "Open snel!". Geen "U heeft een nieuwe lead".

### 7.4 Opening regel

```
Hallo {voornaam installateur},

Onderstaande post kwam binnen vanuit {platform}. Ik heb hem
beoordeeld en band {HOT/WARM/OPP} toegekend. Reden staat
onder de bron.
```

| Regel | Specificatie |
|---|---|
| `Hallo {voornaam}` | Niet "Beste", niet "Geachte". Operational-warm, niet formal-cold of casual-fake. |
| Eerste persoon enkelvoud | "Ik heb hem beoordeeld" — niet "Ons team", niet "Het systeem". |
| Eén alinea | Drie zinnen maximaal. Geen "ik hoop dat u het goed maakt" / niet "ik wilde u even informeren". |
| Verbod | Geen smileys. Geen exclamatie. Geen "We've matched you with a great lead". |

### 7.5 Body — de citation block

Het hart van de email. De vijf canonical fields in 02.1-volgorde, in plain-text-bestand of HTML-tabel-met-restraint:

```
─────────────────────────────────────────────────────────

  "{snippet — verbatim, max 240 chars, tot 4 regels}"

  vastgelegd vanuit {platform}, {captured_at relative}
  open bron ↗  ({host-domain})

  band:  ●  HOT
  reden: {één-zin reden door reviewer, max 20 woorden}

─────────────────────────────────────────────────────────

gereviewd door  {voornaam} {achternaam}  ·  {reviewed_at relative}
                {reviewer-email}

─────────────────────────────────────────────────────────
```

V0 mag dit renderen in HTML email met een gefocuste set CSS, of in plain text. **Beide moeten lezen.** Plain-text fallback is geen afterthought — het is de canonical vorm (operational systems trust plain text).

### 7.6 Exclusivity-zin + dispute-strip (footer)

Direct na de signature-row:

```
─────────────────────────────────────────────────────────

Deze lead is uitsluitend naar u verzonden. De casus blijft
toegewezen zolang u reageert; bij geen reactie binnen 5
werkdagen vervalt het toegewezen-zijn.

Onjuist iets aan deze lead? Antwoord op deze e-mail.
{reviewer voornaam} beoordeelt persoonlijk binnen één werkdag.
Bij gegrond dispuut: credit op uw account.

─────────────────────────────────────────────────────────

Lead Radar  ·  case {LR-2026-05-18-0042}
{permalink-url, optioneel V0.1+}
```

Geen marketing-footer. Geen "Unsubscribe from all leads" (A31 — silence breaks contract; opt-out is een gesprek, niet een link). Wel een **wijzig-frequentie / pauzeer-leveringen** link wanneer V0.1+ uitkomt — als email-only, dan via reply.

### 7.7 Sign-off

Specificatie:

```
{voornaam reviewer}
```

**Eén woord.** Niet "Met vriendelijke groet, Marieke de Vries, Senior Lead Reviewer, Lead Radar B.V.". Eén woord. De rest staat in de signature row.

### 7.8 Threading & follow-ups

| Geval | Regel |
|---|---|
| Installateur antwoordt op de receipt | Reviewer ziet het direct (geen support-routing) |
| Installateur reageert na 5 werkdagen | Reviewer mag re-engagen — het is geen "automated bounce-back" |
| Installateur dispute-treedt | Threading blijft op dezelfde email-thread; geen ticket-id-prefix in nieuwe subject |
| Reviewer wil status-update sturen | Reply binnen dezelfde thread; geen "Wij hebben uw klacht ontvangen, ticketnummer: ..." |

### 7.9 Voorbeeld — een complete V0 receipt (plain text)

```
From:    Marieke de Vries — Lead Radar <marieke@lead-radar.nl>
To:      Jeroen Visser <jeroen@visserinstallaties.nl>
Subject: 1015AA · warmtepomp · HOT
Preview: Marieke reviewde een Tweakers-post uit regio Amsterdam.

Hallo Jeroen,

Onderstaande post kwam binnen vanuit Tweakers. Ik heb hem
beoordeeld en band HOT toegekend. Reden staat onder de bron.

─────────────────────────────────────────────────────────

  "Ik zoek een installateur in regio Amsterdam voor een
   lucht/water warmtepomp + buffervat. Budget rond 12-15k,
   wil deze zomer plaatsen. Wie heeft ervaring met Vaillant
   aroTHERM plus?"

  vastgelegd vanuit Tweakers, 4 uur geleden
  open bron ↗  (tweakers.net)

  band:  ●  HOT
  reden: Expliciet budget, expliciete tijdshorizon (deze zomer),
         model genoemd, regio genoemd.

─────────────────────────────────────────────────────────

gereviewd door  Marieke de Vries  ·  2 uur geleden
                marieke@lead-radar.nl

─────────────────────────────────────────────────────────

Deze lead is uitsluitend naar u verzonden. De casus blijft
toegewezen zolang u reageert; bij geen reactie binnen 5
werkdagen vervalt het toegewezen-zijn.

Onjuist iets aan deze lead? Antwoord op deze e-mail.
Marieke beoordeelt persoonlijk binnen één werkdag.
Bij gegrond dispuut: credit op uw account.

Marieke

─────────────────────────────────────────────────────────

Lead Radar  ·  case LR-2026-05-18-0042
```

Dit is de canonical vorm. HTML mag het netter renderen — element-volgorde en taal blijven gelijk.

---

## 8 — Anti-patterns

Categorieën met cite naar Appendix A waar van toepassing.

### 8.1 Content-level anti-patterns

```
Verboden                                          Cite
──────────────────────────────────────────────────────
Numerieke score ("87% match")                     A8
Paraphrased snippet ("Deze homeowner is geïnter-
  esseerd in warmtepompen")                       A9
Band zonder reden-zin                             eigen extensie 04.5
Reviewer as alias ("Lead Team", "M.D.V.")         A24, A26
"AI-assisted review" / "powered by GPT"           A14, A15
"Onze scanner heeft net…" / "AI is processing"    A16
Suggested action zonder cite ("Bel om 10u")       A12
Auto-generated subject line                       A13
Generic alias sender (noreply@, leads@)           A26
"Geverifieerde lead" zonder reviewer-naam         A17, A24
```

### 8.2 Visual / chrome anti-patterns

```
Verboden                                          Cite
──────────────────────────────────────────────────────
Hero-animation / gradient header                  A10
Color stripe op de zijkant van de citation        impeccable absolute ban
Gradient text op band-label                       impeccable absolute ban
Glassmorphism / blur op snippet-quote             impeccable absolute ban
Big-number "lead score" treatment                 A8 + impeccable
Identical-card grid (meerdere leads in 1 email)   impeccable + 04.2
Modal voor dispute-flow                           §4.4
Pop-up "Was deze lead nuttig?" / NPS-prompt       eigen
Loading spinner "AI denkt na…"                    A16
Mascot illustration in empty states               A11
Drop-shadow / 3D-card op snippet                  impeccable
Trust-badges ("✓ Verified by AI")                 A14
```

### 8.3 Email-mechanics anti-patterns

```
Verboden                                          Cite
──────────────────────────────────────────────────────
"Bulk-send batched leads in één email"            04.5, 02.1 (one lead, one receipt)
"Lead recommendation" in footer ("U mag ook deze
  leads zien")                                    marketplace anti, 04.3
"5 dagen om te reageren! ⏰" urgency               eigen (marketplace anti)
"Was this useful? 👍👎"                            eigen (NPS-pollution)
"Refer a friend" CTA                              eigen (corpus/04.6 anti)
Unsubscribe link voor "alle leads"                A31 (silence = contract breach)
Tracking pixel die de receipt-view registreert    trust-eroding; expliciet
Cross-promo voor andere Lead Radar diensten       eigen
```

### 8.4 Lifecycle anti-patterns

```
Verboden                                          Cite
──────────────────────────────────────────────────────
Routing dezelfde lead twice                       A25, 04.3
Reviewer-id verandert tussen receipt en dispute   A26
"Lead is verlopen" mail zonder reden              eigen
Auto-marking lead als OUTCOME als installateur
  niet reageert                                   eigen (00.5 honesty)
"Wij hebben 12 leads geleverd deze maand" report  A27
Charging voor disputed-and-won leads              A29
```

---

## 9 — "Looks expensive" analysis

*Niet flashy. Maar welke details laten dit premium, serieus, intelligence-grade voelen?*

Premium-signaling in deze categorie is **subtractief, niet additief**. Wat we weglaten is wat het premium maakt.

### 9.1 De vijf "expensive" mechanismen

| Mechanisme | Hoe het werkt | Waarom het werkt |
|---|---|---|
| **1. Eén kleur, royaal getint** | Eén accent voor HOT, anders tinted-neutral. Geen palette-show-off. | Restraint signaleert dat de maker meerdere keuzes had en *koos*. |
| **2. Typografische rust** | Eén familie body, één rank voor de snippet, monospace alleen voor case-id. | Mode-mensen herkennen dit. Het is niet "branded"; het is *gecomponeerd*. |
| **3. Asymmetrische spacing** | Snippet ademt; metadata clustert; signature breekt los. Geen uniform padding. | Uniforme spacing is een spreadsheet. Composed spacing is een document. |
| **4. Plain-text fallback identiek aan HTML** | Dezelfde elementvolgorde, dezelfde taal, dezelfde tussenstrepen. | Tools die plain-text serieus nemen, signaleren dat de maker email-mechanics begrijpt. |
| **5. Eén human-touch detail** | Sign-off met alleen voornaam. Subject met reviewer-hand. Reden-zin door mens geschreven. | Eén onmogelijk-te-AI-genereren detail per receipt = "een mens stond hier even bij stil". |

### 9.2 Wat we expliciet weglaten omdat het "cheap" maakt

| Element | Waarom het goedkoop voelt |
|---|---|
| Gradient header met logo-grootverdiener | Generic SaaS template-aesthetic |
| "Verified by AI" badges | Trust-trick — premium producten claimen niet, ze bewijzen |
| Big-number score | Pseudo-precisie — premium = comfortable met onzekerheid |
| Stock-photo van een huis met zonnepanelen | Stock photography = "we hadden geen tijd voor echt" |
| Roeptoeterende kleuren voor "Hoge prioriteit!" | Premium = quiet urgency, niet visuele urgency |
| Te veel typografische niveaus | "Designer onzeker over hiërarchie" |
| Round-trip-tracker ("U heeft deze mail geopend") | Surveillance ≠ professional respect |
| Auto-emoji in subject | Generic marketing-stack |

### 9.3 De "Mercury / Linear / Perplexity" comparison

| Inspiratie | Wat we ervan overnemen | Wat we niet overnemen |
|---|---|---|
| **Mercury** | Restraint in color, asymmetrisch spacing, "operational document" tonality | Hun B2B-finance specifieke iconografie |
| **Linear** | Keyboard-first elsewhere; in receipt: density-and-quietness | Hun deep-purple accent; hun product-velocity vibes |
| **Perplexity** | Citation-as-interface — source en captured_at zijn eerstegraadse elementen | Hun AI-prominent chrome (we doen het tegenovergestelde) |
| **Retool** | Inspectable surface — alles kan klikt-en-onthult | Hun developer-aesthetic; we mikken niet op devs |
| **Clay** | Density met rust | Hun playful copy (we zijn minder speels) |
| **Palantir-lite** | "Operational intelligence" toon, no-jargon-marketing | Hun militaire associations; hun visual aggression |

### 9.4 Wat de installateur voelt na 8 seconden

Niet expliciet gezegd, wel uitgestraald:

- "Iemand heeft hier echt naar gekeken."
- "Dit is alleen voor mij."
- "Als ik twijfel kan ik dit verifiëren."
- "Dit voelt anders dan Werkspot / Bouwofferte / ...".
- "Ik heb een persoon die ik kan terug-mailen."

Geen van deze gevoelens komt uit een copy-claim. Allemaal komen ze uit **vorm**.

---

## 10 — Out of scope

Expliciet uitgesloten van V0:

| Categorie | Wat NIET V0 | V1+ trigger |
|---|---|---|
| Web permalink | Hosted view per receipt | Tweede operator hire OF founder-keuze (§11) |
| Mobile-optimized HTML email | Responsive-layout tuning beyond plain breakpoint | Eerste klacht over leesbaarheid op telefoon |
| Multi-language | Engelse versie / andere talen | Eerste niet-NL installateur live |
| Reviewer photo / avatar | Visuele identifier naast naam | Founder-decisie + reviewer-consent |
| Per-installateur branding | Whitelabel / co-branding | Niet voorzien |
| Analytics / open-tracking | Pixel / utm tracking | Architecturaal verboden V0 (trust-erosion) |
| Bulk-send / digest variant | Meerdere leads in één mail | Architecturaal verboden (04.5: one lead = one receipt) |
| Reply-automation / auto-classifier | NLP op de reply | Eerste 30 replies door reviewer handmatig gecategoriseerd |
| Lead-card UI op de website | Receipt-equivalent op `lead-radar-site` | Aparte spec — `lead-radar-site/` |
| Reviewer onboarding flow | Documentatie / training | Operator Console spec dekt dit |
| Telegram-delivery variant | Receipt via Telegram bot | Specifiek opt-in, separate spec |

---

## 11 — Open questions & founder-decisions

Vier beslissingen vragen founder-input vóór implementatie kan starten:

### Q1 — Receipt-medium V0

| Optie | Voordeel | Nadeel |
|---|---|---|
| **A. Email-only** | Simpelste, één surface, doctrine-conform | Geen perma-link voor latere referentie |
| **B. Email + web-permalink (read-only)** | Installateur kan dispute-pad ook in browser zien; receipt is shareable intern | Bouwt extra surface, vraagt host + auth |
| **C. Email + Telegram-bot mirror** | Reviewer kan vanuit Telegram doorduwen, snel | Trust-erosion door extra surface; off-pad |

**Aanbeveling:** A voor V0; B voor V0.1 wanneer eerste klacht over "ik kan de mail niet terugvinden" binnenkomt.

### Q2 — Reviewer-surface diepte

| Optie | Voordeel | Nadeel |
|---|---|---|
| **A. Naam + reply-email only** | Sober, doctrine-strict, minimal-exposure | Iets minder warm |
| **B. Naam + reply-email + foto-thumbnail** | Maximaal human, "premium B2B" cue | Foto-keuze wordt selling, foto wordt PR-element |
| **C. Naam + reply-email + reviewer-handle / signature-link** | Mid-weg; handle voelt operational | Voegt complexiteit toe |

**Aanbeveling:** A — voorbeeld in §7.9 toont dat naam alleen volstaat. Foto risk: marketing-creep.

### Q3 — Case-id zichtbaarheid

| Optie | Voordeel | Nadeel |
|---|---|---|
| **A. Case-id zichtbaar in footer (`LR-2026-05-18-0042`)** | Operational signal; installateur kan ernaar verwijzen in reply | Voegt techniek-toon toe; risico op feel-like-ticket |
| **B. Case-id alleen in headers (`X-LeadRadar-Case-ID:`)** | Geen visuele ruis | Installateur kan er niet naar verwijzen |
| **C. Geen case-id V0** | Maximaal minimaal | Maakt dispute-tracking moeilijker voor reviewer |

**Aanbeveling:** A — operational signal weegt op tegen minimalisme. De ticket-feel wordt voorkomen door geen `#` en geen woord "ticket" te gebruiken.

### Q4 — Exclusivity-zin: expliciet of impliciet

| Optie | Voordeel | Nadeel |
|---|---|---|
| **A. Expliciete zin (§4.2)** | Doctrine 04.3 wordt gemaakt-voelbaar | Risico: voelt als marketing-claim |
| **B. Impliciet, geen zin** | Maximaal restrained | Installateur weet het pas na een lange relatie |
| **C. Expliciet, alleen in eerste 5 receipts** | Onboarding-modus | Logica wordt complex |

**Aanbeveling:** A — de zin in §4.2 is bewust *operationeel* geformuleerd (state-machine taal, geen uitroepteken). Doctrine 04.3 verdient een hoorbare uitspraak op het artifact zelf.

---

## 12 — Implementation contract (voor Codex)

Wanneer founder akkoord geeft op Q1–Q4, levert deze spec aan Codex de volgende harde constraints:

| Constraint | Bron |
|---|---|
| Element-volgorde van §2.1 is non-negotiable | doctrine 02.1 + 04.5 |
| Vocabulary in §3.5 is linter-input | doctrine 02.3, B.1, B.2 |
| Reviewer-name + reply-address verplicht in elke receipt | doctrine 04.5, A24, A26 |
| Geen auto-generated subject | A13 |
| Geen "AI" in chrome | A14, A15 |
| Plain-text fallback canonical | §5.1, §7.5 |
| Eén lead per email | §8.3, doctrine 04.5 |
| Eén accent kleur | §5.4 |
| Anti-pattern lijst §8 is build-fail | A1–A31 + eigen extensies |

Implementation-plan wordt apart geschreven via `superpowers:writing-plans` zodra Q1–Q4 beslist zijn.

---

## Revision policy

Dit document is een **implementatie-doctrine** voor het receipt-artifact. Het ligt onder doctrine v0.1 (`specs/doctrine/trust-provenance-moderation.md`) en bovenaan implementation-plans.

Wijzigingen aan §2.1 (information hierarchy), §3 (provenance rendering), §6.4 (reviewer-surface), of §7.5 (citation block) raken de doctrine. Andere wijzigingen zijn revisable zonder doctrine-aanpassing.

Versionering: deze spec is **v0**, gefreezet op moment van founder-akkoord. Wijzigingen in §11 Q1–Q4 vragen revisie naar v0.1.
