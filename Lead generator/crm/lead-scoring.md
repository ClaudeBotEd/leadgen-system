# Lead scoring rubric

Eenvoudige 0-10 schaal voor `lead_quality_score` custom property. Hand in te vullen na intake-call (of automatisch via n8n als je dit later digitaliseert).

## Doel

Niet elke lead is gelijk. Een 9 verdient binnen 4 uur opvolging, een 3 mag 48u wachten. Score helpt je prioriteren als volume groeit.

## Scoring per dimensie

Vier dimensies, elk 0-2 punten + 2 bonuspunten = max 10.

### Dimensie 1 — Niche fit (0-2 pt)

| Score | Criterium |
|-------|-----------|
| 0 | Ander type bedrijf dan installatiebedrijf |
| 1 | Installatiebedrijf maar buiten kern-niches (bv. industrieel groot-installateur, zonneparken) |
| 2 | Kern-niche: warmtepomp, airco, zonnepanelen, of multi-installatie residentieel |

### Dimensie 2 — Bedrijfsgrootte (0-2 pt)

| Score | Criterium |
|-------|-----------|
| 0 | ZZP zonder ambitie te groeien — onvoldoende capaciteit voor leadflow |
| 1 | 2-5 medewerkers, kan ~10 leads/mnd verwerken |
| 2 | 6-50 medewerkers, kan ~25+ leads/mnd verwerken zonder overspannenheid |

Boven de 50: vaak te corporate, beslissingen via comite. Score 1.

### Dimensie 3 — Werkgebied match (0-2 pt)

| Score | Criterium |
|-------|-----------|
| 0 | Werkt in regio waar jij geen distributie/ads voor hebt |
| 1 | Werkt in regio waar jij wel kunt leveren maar zonder bewezen volume |
| 2 | Werkt in regio waar jij al lead-flow draait of weet dat te kunnen genereren |

### Dimensie 4 — Koop-intentie (0-2 pt)

| Score | Criterium |
|-------|-----------|
| 0 | "Eens kijken wat het kost" — geen actieve pijn |
| 1 | Kent het probleem maar verkent meerdere opties |
| 2 | Heeft expliciet doel ("ik wil X leads/mnd"), beslissingsmandaat, urgentie |

### Bonuspunten (max +2)

- +1 als lead via warm referral kwam
- +1 als bedrijf >5 jaar bestaat (lagere risico op stoppen tijdens contract)
- +1 als ze al budget hebben voor marketing (>EUR 500/mnd huidig spending)

Maximum cap blijft 10.

## Score interpretatie

| Score | Categorie | Aanbevolen actie |
|-------|-----------|-------------------|
| 9-10 | A-lead | Binnen 4 uur opvolgen, prioriteit in agenda |
| 7-8 | B-lead | Binnen 24 uur opvolgen |
| 5-6 | C-lead | Binnen 48 uur opvolgen |
| 3-4 | D-lead | Binnen 7 dagen opvolgen, alleen als capaciteit |
| 0-2 | Disqualify | Markeer NOT_QUALIFIED met notitie |

## Praktijkvoorbeelden

### Voorbeeld 1
- Warmtepomp-installateur, 12 medewerkers, regio Eindhoven, zegt "ik wil 20 leads/mnd"
- Niche fit: 2, Bedrijfsgrootte: 2, Werkgebied: 2, Koop-intentie: 2, Bonus: bestaat 8 jaar (+1) = **9**
- Actie: A-lead, binnen 4u callen

### Voorbeeld 2
- Multi-installateur, 4 medewerkers, regio Drenthe (geen ad-distributie), "we kijken nog wat opties"
- Niche fit: 2, Bedrijfsgrootte: 1, Werkgebied: 0, Koop-intentie: 1, Bonus: 0 = **4**
- Actie: D-lead, lage prioriteit

### Voorbeeld 3
- ZZP airco, 1 persoon, "wat kost het ongeveer"
- Niche fit: 2, Bedrijfsgrootte: 0, Werkgebied: 1, Koop-intentie: 0, Bonus: 0 = **3**
- Actie: D-lead of NOT_QUALIFIED

## Anti-patterns

- Niet inflateren — een 9 betekent echt 9. Anders is het systeem waardeloos
- Niet alleen op gevoel — vul de 4 dimensies in (in CRM-notitie of als losse properties)
- Score is een momentopname, niet permanent — herzie als nieuwe info beschikbaar komt

## Optionele uitbreiding — automatische scoring via n8n

Voeg na "Merge enrichment data" in `workflow-lead-intake.json` een Function node toe met:

```js
const body = $('Webhook (POST /lead-intake)').item.json.body;
const enrich = $json;

let score = 0;

// Niche fit
if (['warmtepomp','airco','zonnepanelen','multi'].includes(body.specialty)) score += 2;
else if (['cv','ventilatie'].includes(body.specialty)) score += 1;

// Bedrijfsgrootte
const empRanges = {'2-5': 1, '6-15': 2, '16-50': 2, '51+': 1};
score += empRanges[body.employee_count] || 0;

// Werkgebied — lijst van postcodes/plaatsen waar je actief bent
const activeRegions = ['eindhoven','utrecht','amsterdam','rotterdam','antwerpen','gent'];
const regionLower = (body.region || '').toLowerCase();
if (activeRegions.some(r => regionLower.includes(r))) score += 2;

// Koop-intentie kun je niet automatisch scoren — laat handmatig

return [{ json: { ...enrich, lead_quality_score: score } }];
```

Dit geeft een baseline-score 0-6. Handmatige update naar 0-10 na intake-call.
