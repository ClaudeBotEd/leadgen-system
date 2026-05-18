# Lead Intelligence Pipeline Run — `20260518T133041Z`

Started: `2026-05-18T13:30:41+00:00`

## Totals

- Leads in: **27**
- Successfully scored: **27**
- Qualified (≥ threshold 6): **15**
- Qualification rate: **55.6%**
- Errors: **0**

## Latency & throughput

| Stage | p50 (ms) | p95 (ms) | max (ms) |
| --- | --- | --- | --- |
| score-lead | 4012 | 7963 | 11500 |
| generate-sequence | 6013 | 9376 | 9712 |

- Wall-clock: **44.01 s**
- Throughput: **36.81 leads/min** (max_concurrent=6)

## Token usage

- Prompt tokens: **30,639**
- Completion tokens: **15,154**
- Total tokens: **45,793**
- Per-lead avg: **1,696**
- Estimated cost (gpt-4.1 list prices): **$0.1825**

## Score distribution (lead_quality_score)

| Score | Count | Bar |
| --- | --- | --- |
| 0 | 0 |  |
| 1 | 0 |  |
| 2 | 2 | ██ |
| 3 | 2 | ██ |
| 4 | 2 | ██ |
| 5 | 6 | ██████ |
| 6 | 3 | ███ |
| 7 | 8 | ████████ |
| 8 | 3 | ███ |
| 9 | 1 | █ |
| 10 | 0 |  |

## Aggregate stats

- Lead quality score — mean 5.74 / median 6 / min 2 / max 9
- Automation fit — mean 6.33 / median 7
- Urgency — mean 5.33
- Confidence — mean 6.67 / median 7

## Channel mix (council recommendation)

- email: 27

---

## Best lead

### Warmtepomp Amsterdam: Verbeter Uw Energieprestaties

```
lead_id              : lr_00002
domain               : amsterdamwarmtepomp.com
intent_score (scrape): 60
lead_quality_score   : 9/10
automation_fit_score : 8/10
urgency_score        : 8/10
outbound_potential   : 9/10
confidence_score     : 9/10
estimated_budget     : 10-50k EUR
recommended_channel  : email
```

**Recommended offer:** Wij automatiseren uw offerte- en klantopvolgingsproces zodat u meer aanvragen sneller en efficiënter kunt verwerken.

**Best outreach angle:** Ontvang meer gekwalificeerde aanvragen zonder extra werk door slimme AI-automatisering.

**AI opportunities:**
- Automatische offertegeneratie
- Leadkwalificatie en opvolging
- Klantenservice chatbots
- Planning en afspraakautomatisering

**Pain points:**
- Handmatige verwerking van offerteaanvragen
- Tijdrovende klantcommunicatie
- Inefficiënte leadopvolging
- Beperkte schaalbaarheid van dienstverlening

**Council reasoning:** De lead heeft een moderne website, duidelijke contactinformatie en een hoge intentiescore. De niche is competitief en gevoelig voor automatisering, met duidelijke signalen van handmatige processen. De data is volledig en actueel, wat het vertrouwen in deze beoordeling versterkt.

**Cold email draft:**

> **Subject:** Meer aanvragen verwerken zonder extra werk? Slimme AI voor uw warmtepompbedrijf
>
> Veel bedrijven zoals Warmtepomp Amsterdam zien het aantal offerteaanvragen stijgen, maar lopen tegen handmatige verwerking en tijdrovende klantcommunicatie aan. Met slimme AI-automatisering kunt u uw offerte- en klantopvolgingsproces versnellen, zonder in te leveren op persoonlijk advies. Zo verwerkt u meer aanvragen, houdt u grip op de kwaliteit en blijft uw dienstverlening schaalbaar. Bent u benieuwd hoe automatische offertegeneratie en leadopvolging voor uw team kunnen werken? Laten we vrijblijvend verkennen of dit past bij uw aanpak.

**LinkedIn opener:** Ik zag dat u bij Warmtepomp Amsterdam inzet op persoonlijk advies, maar handmatige offerteverwerking kan veel tijd kosten. Zou AI-automatisering u kunnen helpen om sneller te schakelen met klanten? Wat vindt u van deze aanpak?

**Follow-up sequence:**
- Day 3 (email) — *Automatische opvolging voor meer gekwalificeerde leads*
  > Heeft u al overwogen om offerteaanvragen en klantopvolging te automatiseren? Veel warmtepompspecialisten besparen hiermee tijd en verhogen de klanttevredenheid. Interesse om dit kort te bespreken?
- Day 7 (linkedin)
  > Benieuwd of automatisering uw team kan ontlasten bij het verwerken van aanvragen? Ik hoor graag of u hier al mee bezig bent.
- Day 10 (email) — *Laatste check: automatisering voor Warmtepomp Amsterdam?*
  > Ik hoor niets terug, dus wellicht is dit nu niet relevant. Wilt u in de toekomst sparren over automatisering, laat gerust iets weten.

**CTA suggestions:**
- Zullen we een korte call plannen om de mogelijkheden te bespreken?
- Wilt u een demo van automatische offertegeneratie zien?
- Mag ik u vrijblijvend een voorstel sturen voor uw situatie?

---

## Median lead

### Flint

```
lead_id              : lr_00018
domain               : weheat.nl
intent_score (scrape): 58
lead_quality_score   : 6/10
automation_fit_score : 7/10
urgency_score        : 5/10
outbound_potential   : 6/10
confidence_score     : 7/10
estimated_budget     : 10-50k EUR
recommended_channel  : email
```

**Recommended offer:** Wij helpen u met AI-automatisering om meer leads sneller en efficiënter op te volgen en uw klantenservice te verbeteren.

**Best outreach angle:** Uw innovatieve warmtepomp verdient een even innovatieve aanpak voor leadopvolging en klantenservice.

**AI opportunities:**
- Automatische leadkwalificatie en opvolging
- AI-ondersteunde klantenservice (chatbots)
- Voorraad- en orderbeheer automatisering
- Predictief onderhoud voor warmtepompen

**Pain points:**
- Handmatige verwerking van klantaanvragen
- Traag opvolgen van leads
- Inefficiënte klantenservice
- Beperkte schaalbaarheid bij groeiende vraag

**Council reasoning:** De lead heeft een moderne website, duidelijke contactinformatie en een relevant product in een groeiende markt. Er zijn signalen van digitalisering, maar geen expliciete pijnpunten rond automatisering, waardoor de fit en urgentie gemiddeld scoren. De data is redelijk compleet, maar bedrijfsgrootte en exacte budgetten ontbreken.

**Cold email draft:**

> **Subject:** Meer leads sneller opvolgen voor Flint van Weheat
>
> Flint is een opvallende innovatie in betaalbare warmtepompen. Toch zie ik dat veel aanbieders zoals Weheat kansen laten liggen door handmatige leadopvolging en trage verwerking van klantaanvragen. Met AI-automatisering kunt u niet alleen leads sneller en efficiënter opvolgen, maar ook uw klantenservice schaalbaar maken bij groeiende vraag. Dit sluit naadloos aan bij het innovatieve karakter van Flint. Zullen we kort sparren over hoe AI uw leadopvolging en service kan versterken?

**LinkedIn opener:** Uw Flint-warmtepomp valt op door prijs en innovatie. Heeft u al overwogen om leadopvolging en klantenservice te automatiseren met AI, zodat u sneller kunt inspelen op klantvragen? Benieuwd hoe u dit aanpakt?

**Follow-up sequence:**
- Day 3 (email) — *Kansen voor AI bij leadopvolging Flint*
  > Ik vroeg me af of u al stappen zet richting automatisering van uw leadopvolging of klantenservice. AI kan helpen om sneller te reageren op aanvragen en de groeiende vraag op te vangen. Zullen we hierover van gedachten wisselen?
- Day 7 (linkedin)
  > Heeft u interesse in hoe AI-automatisering Flint kan helpen bij efficiëntere leadopvolging en klantenservice? Hoor graag of dit actueel is voor Weheat.
- Day 10 (email) — *Laatste check: AI voor Flint-warmtepompen?*
  > Geen interesse in AI-automatisering voor Flint? Laat het gerust weten, dan sluit ik het dossier.

**CTA suggestions:**
- Zullen we een korte call plannen om mogelijkheden te verkennen?
- Wilt u een demo zien van AI-automatisering voor leadopvolging?
- Heeft u interesse in een vrijblijvend adviesgesprek over AI voor Weheat?

---

## Worst lead

### Je bent bijna op de pagina die je zoekt [funda]

```
lead_id              : lr_00025
domain               : funda.nl
intent_score (scrape): 32
lead_quality_score   : 2/10
automation_fit_score : 2/10
urgency_score        : 1/10
outbound_potential   : 2/10
confidence_score     : 3/10
estimated_budget     : <5k EUR
recommended_channel  : email
```

**Recommended offer:** Wij automatiseren het kwalificeren en opvolgen van woningleads met AI, zodat u sneller en efficiënter kunt werken.

**Best outreach angle:** Ontdek hoe AI uw leadopvolging en energie-informatie automatisch kan optimaliseren.

**AI opportunities:**
- Automatische leadkwalificatie voor woningverkoop
- AI-gestuurde energieprestatie-analyse
- Automatisering van klantcommunicatie

**Pain points:**
- Handmatige verwerking van woninginformatie
- Beperkte opvolging van potentiële kopers
- Inefficiënte communicatieprocessen

**Council reasoning:** De lead betreft een verkochte woning op Funda, zonder duidelijke bedrijfsinformatie of schaal. Er zijn beperkte signalen van automatiseringsbehoefte en het budget lijkt laag. De relevantie voor AI-automatisering is minimaal, waardoor de scores laag blijven.
