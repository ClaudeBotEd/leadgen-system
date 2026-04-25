# Close Solo CRM — alternatieve setup

**Wanneer kies je Close in plaats van HubSpot Free?**
- Je doet >100 outbound calls/week (Close heeft de beste built-in dialer)
- Je wilt sequences NATIEF in je CRM (HubSpot Free heeft geen sequences)
- Je hebt 1-2 sales mensen, niet meer (Solo tier = 1 user)

**Kosten:** $9/user/mo (annual). Een paar ronde tarieven verder upgraden:
- Solo: $9/mo, 1 user, 10.000 leads
- Startup: $59/mo, 3 users, 50.000 leads, automations
- Professional: $109/user/mo, sequences, sales automation, predictive dialer

## Stap 1 — Account aanmaken

1. https://www.close.com/pricing
2. Kies Solo plan, start met 14-day trial
3. Tijdens onboarding: skip de meeste assistant-vragen, je configureert handmatig

## Stap 2 — Pipeline aanpassen

Default Close heeft 1 pipeline met stages: Potential, Bad Fit, Qualified, Demo Set, Negotiation, Won.

Vervang door HVAC-pipeline:

Settings (rechtsboven) -> **Statuses** -> Lead statuses.

Verwijder defaults, voeg toe:

| Status naam | Type | Uitleg |
|-------------|------|--------|
| New (auto via API) | Active | Lead binnen, nog niet gecontacteerd |
| Contacted | Active | Eerste reply uit |
| Meeting Scheduled | Active | Call gepland |
| Pilot Discussion | Active | Criteria afgestemd |
| Pilot Running | Active | 3 gratis leads in levering |
| Proposal Out | Active | Aanbieding verstuurd |
| Customer | Won | Eerste betaling |
| Not Qualified | Lost | Past niet binnen criteria |
| Not Interested | Lost | Wilde uiteindelijk niet |
| Opted Out | Lost | Uitgeschreven |

## Stap 3 — Custom fields aanmaken

Settings -> **Custom Fields** -> tab **Lead** -> **Add custom field**.

| Veld | Type | Doel |
|------|------|------|
| `specialty` | Choices (dropdown) | warmtepomp/airco/zonnepanelen/cv/ventilatie/multi |
| `employee_count` | Text | "6-15", "16-50", etc. |
| `current_lead_source` | Text long | Vrij invul |
| `consent_processing_date` | Date | GDPR consent moment |
| `lawful_basis` | Choices | consent / legitimate_interest / contract |
| `original_source` | Text | landingspagina / cold-email-reply / linkedin |
| `utm_source` | Text | UTM tracking |
| `utm_campaign` | Text | UTM tracking |
| `lead_quality_score` | Number | 1-10 |
| `opted_out` | Boolean | Uitschrijfvlag |

## Stap 4 — Smart Views (zoals HubSpot Lists)

Linksboven het lead-overzicht: **Smart Views** -> Create new.

Maak deze 3 views:

**Nieuwe leads — laatste 7 dagen**
- Status = New
- Date created > 7 days ago
- Sort by Date created descending

**Pilot in uitvoering**
- Status = Pilot Running
- Sort by Date updated descending

**Stale leads (>24u zonder contact)**
- Status = New
- Date created < 24 hours ago

## Stap 5 — API key

Settings -> **Developer** -> **API Keys** -> Create new.

- Name: `n8n Lead Intake`
- Scope: `read+write`

Kopieer de key. Plak in `n8n/.env` als `CLOSE_API_KEY=`.

## Stap 6 — n8n workflow aanpassen voor Close

In `n8n/workflow-lead-intake.json`, vervang de HubSpot HTTP node "Create HubSpot contact" door:

```json
{
  "method": "POST",
  "url": "https://api.close.com/api/v1/lead/",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpBasicAuth",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      { "name": "Content-Type", "value": "application/json" }
    ]
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={\n  \"name\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.company_name }}\",\n  \"contacts\": [{\n    \"name\": \"\",\n    \"emails\": [{\"email\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.contact_email }}\", \"type\": \"office\"}],\n    \"phones\": [{\"phone\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.phone || '' }}\", \"type\": \"office\"}]\n  }],\n  \"status_id\": \"stat_NEW_ID_HIER\",\n  \"custom\": {\n    \"specialty\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.specialty }}\",\n    \"employee_count\": \"{{ $json.estimated_employees }}\",\n    \"current_lead_source\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.current_lead_source || '' }}\",\n    \"original_source\": \"landingspagina\",\n    \"consent_processing_date\": \"{{ $('Webhook (POST /lead-intake)').item.json.body.submitted_at }}\"\n  }\n}"
}
```

Voor `httpBasicAuth`: vul username = `${CLOSE_API_KEY}`, password = leeg.

Vind je `stat_NEW_ID_HIER` via: `GET https://api.close.com/api/v1/status/lead/` met auth header.

## Stap 7 — Sequences (Close ingebouwd)

Voor warm follow-up gebruik je Close's eigen sequences (in Pro tier). In Solo: alleen handmatige email-templates.

Templates aanmaken: Settings -> **Email Templates** -> Add template.

Importeer de 4 sequences uit `/email-sequences/sequence-*.md` als templates. Trigger handmatig vanuit lead-detailweergave.

## Verschillen met HubSpot

| | HubSpot Free | Close Solo |
|--|--------------|------------|
| Custom fields beperking | 100+ | Onbeperkt |
| Sequences | Nee (Pro) | Beperkt (Pro) |
| Built-in dialer | Nee | Ja (Pro+) |
| Email open/click tracking | Beperkt | Standaard |
| Snipplets/templates | Ja | Ja |
| API quality | Goed gedocumenteerd | Best in class |
| Mobile app | Goed | Goed |
| Reporting | Standaard | Standaard, beter aanpasbaar in Pro |

## Migratie van HubSpot naar Close (later)

Als je ooit migreert:

1. Export contacts uit HubSpot (Settings -> Import & Export -> Export contacts)
2. Bij export: kies CSV, alle properties
3. Import in Close: Lead -> Import -> Upload CSV -> map velden naar custom fields
4. Wijs status mappings toe (NEW -> New, etc.)
5. Verifieer een steekproef van 10 leads dat alles correct overkomt
6. Schakel n8n workflow over naar Close API
7. Houdt HubSpot 90 dagen actief als read-only backup
