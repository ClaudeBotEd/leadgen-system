# CRM Pipeline — installatiebedrijven lead gen

## Wat zit er in deze map

| Bestand | Doel |
|---------|------|
| `hubspot-pipeline-config.md` | Stap-voor-stap setup HubSpot Free CRM (aanbevolen) |
| `close-pipeline-config.md` | Alternatief: Close Solo (`$9/user/mo`) |
| `pipeline-stages.md` | Shared pipeline definitie (5 stages, criteria per stage) |
| `lead-scoring.md` | Kwalificatie-rubric (binnen-werkgebied, koop-intentie, budget) |
| `custom-properties.md` | Lijst van alle custom contact properties |
| `import-template.csv` | CSV-template voor bulk-import (Apollo export -> HubSpot) |

## Welke CRM kiezen?

Per Tabel 3 in het rapport:

| | HubSpot Free | Close Solo |
|--|--------------|------------|
| Prijs | $0 | $9/mo |
| Limiet | 1M contacten | 10.000 leads |
| Email integratie | Beperkt zonder Marketing Hub | Sterk (sales-first ingebouwd) |
| Workflow automatisering | Beperkt zonder Sales Hub Pro | Goed |
| LinkedIn-integratie | Geen native | Geen native |
| EU-dataresidentie | Op aanvraag (Enterprise) | US-only |
| Beste voor | Lange-termijn schaal | Solo-sales-focus |

**Aanbeveling: start met HubSpot Free.** Argumenten:
1. Echt gratis, geen contactenlimiet die je snel raakt
2. Native API + Zapier/n8n integraties zijn bewezen
3. Marketing Hub upgrade-pad als je ooit content-marketing wilt
4. Account migratie naar betaalde tier later is naadloos

Stap over naar Close zodra: je >2 sales-mensen hebt EN HubSpot Free's email/automation-limieten knellen.

## Volgorde van setup (voor je live gaat)

1. Maak HubSpot Free account aan: https://www.hubspot.com/products/get-started-free
2. Volg `hubspot-pipeline-config.md` — settings, properties, pipeline stages
3. Maak HubSpot Private App aan voor API-key (zie `hubspot-pipeline-config.md` -> sectie API)
4. Vul `HUBSPOT_API_KEY` en `HUBSPOT_PORTAL_ID` in `n8n/.env`
5. Test n8n workflow met de curl-test uit `n8n/README.md`
6. Verifieer dat een test-contact verschijnt in HubSpot met alle custom properties
7. Importeer Apollo-export via `import-template.csv` template

## Hoe pipeline en sequence-templates samenwerken

Wanneer een lead binnenkomt via de landingspagina, plaatst n8n hem in HubSpot in stage **"NEW"**. Vanaf daar is de progressie:

```
NEW                  ──────►   CONTACTED            ──────►   MEETING SCHEDULED
(lead binnen)                  (eerste reply)                 (call gepland)

                                       │
                                       ▼

CUSTOMER             ◄──────   PILOT RUNNING        ◄──────   PROPOSAL SENT
(eerste betaling)              (3 gratis leads)                (offerte uit)
```

Dit is `pipeline-stages.md` in detail.

Email-sequences zijn alleen actief tot status = "CONTACTED". Daarna handmatige opvolging (handmatige antwoorden, niet meer automatisch).

## Compliance — GDPR-implicaties

Bij iedere contact die je creeert in HubSpot:
- `consent_processing_date` MOET gevuld zijn (uit form `submitted_at`)
- `original_source` MOET gevuld zijn (audittrail naar herkomst)
- `lawful_basis` aanbevolen veld: "consent" (form) of "legitimate_interest" (cold email naar generieke adressen)

Bij opt-out request:
- Markeer `opted_out` = true
- Verwijder uit alle actieve sequences
- Bewaar contact (voor suppressie) maar nooit meer benaderen

Bij verwijderverzoek (GDPR Art. 17 — recht op vergetelheid):
- Verwijder contact volledig binnen 30 dagen
- Bewaar wel een hash van het emailadres in suppressielijst (zodat je niet per ongeluk weer mailt)
