# Custom contact properties — referentie

Volledig overzicht van alle custom properties die n8n schrijft en het sales-team handmatig bijwerkt. Maak ze EERST aan in HubSpot/Close voor je de eerste lead intake doet — anders weigert de API de write.

## Tabel

| Property naam (internal) | Label (display) | Type | Group | Geschreven door | Verplicht |
|--------------------------|------------------|------|-------|------------------|-----------|
| `specialty` | Specialiteit | Dropdown enum | Lead information | n8n (uit form) | Ja |
| `employee_count` | Aantal medewerkers | Single-line text | Lead information | n8n (uit form of Apollo) | Aanbevolen |
| `current_lead_source` | Huidige lead-bron | Multi-line text | Lead information | n8n (uit form) | Optioneel |
| `consent_processing_date` | GDPR consent gegeven op | Date | Compliance | n8n (uit form `submitted_at`) | Ja |
| `lawful_basis` | GDPR rechtsgrond | Dropdown enum | Compliance | Handmatig | Aanbevolen |
| `original_source` | Oorspronkelijke bron | Single-line text | Lead information | n8n (vaste waarde "landingspagina") | Ja |
| `utm_source` | UTM source | Single-line text | Marketing | n8n (uit form `utm.utm_source`) | Optioneel |
| `utm_campaign` | UTM campaign | Single-line text | Marketing | n8n (uit form `utm.utm_campaign`) | Optioneel |
| `followup_reminder_sent_at` | Follow-up reminder verstuurd | Date and time | Workflow | n8n followup workflow | Auto |
| `opted_out` | Uitgeschreven | Single checkbox | Compliance | Handmatig of unsubscribe-webhook | Auto/handmatig |
| `lead_quality_score` | Lead score (1-10) | Number | Lead information | Handmatig na intake-call (of optionele n8n function) | Aanbevolen |

## Enum waarden per dropdown property

### specialty
| Value | Label |
|-------|-------|
| `warmtepomp` | Warmtepompen |
| `airco` | Airco |
| `zonnepanelen` | Zonnepanelen |
| `cv` | CV / sanitair |
| `ventilatie` | Ventilatie / WTW |
| `multi` | Multi-disciplinair |

### lawful_basis
| Value | Label | Wanneer kiezen |
|-------|-------|----------------|
| `consent` | Toestemming (Art. 6(1)(a)) | Lead vulde formulier in met consent-checkbox |
| `legitimate_interest` | Gerechtvaardigd belang (Art. 6(1)(f)) | Cold email naar generieke adressen, B2B legitiem |
| `contract` | Contract (Art. 6(1)(b)) | Lead is al klant, contract loopt |

## Property-groepen (HubSpot)

Maak deze groepen aan VOOR de properties (Settings -> Properties -> Groups):

- `Lead information` — alle business-properties
- `Compliance` — GDPR-gerelateerde velden
- `Marketing` — UTM en bron-tracking
- `Workflow` — automation-state

In Close zijn groepen optioneel; gebruik consistente prefixes zoals `lead_*`, `compliance_*`.

## API import als bulk-script

Als je de properties NIET handmatig wilt aanmaken, gebruik dit cURL-script (vereist alleen jouw `HUBSPOT_API_KEY`):

```bash
#!/usr/bin/env bash
# Bulk-create custom contact properties in HubSpot
set -euo pipefail
TOKEN="${HUBSPOT_API_KEY:?HUBSPOT_API_KEY env var required}"

create_prop() {
  local payload="$1"
  curl -sS -X POST "https://api.hubapi.com/crm/v3/properties/contacts" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$payload" | jq -r '.name // .message'
}

create_prop '{"name":"specialty","label":"Specialiteit","type":"enumeration","fieldType":"select","groupName":"contactinformation","options":[{"label":"Warmtepompen","value":"warmtepomp"},{"label":"Airco","value":"airco"},{"label":"Zonnepanelen","value":"zonnepanelen"},{"label":"CV / sanitair","value":"cv"},{"label":"Ventilatie / WTW","value":"ventilatie"},{"label":"Multi-disciplinair","value":"multi"}]}'

create_prop '{"name":"employee_count","label":"Aantal medewerkers","type":"string","fieldType":"text","groupName":"contactinformation"}'

create_prop '{"name":"current_lead_source","label":"Huidige lead-bron","type":"string","fieldType":"textarea","groupName":"contactinformation"}'

create_prop '{"name":"consent_processing_date","label":"GDPR consent gegeven op","type":"date","fieldType":"date","groupName":"contactinformation"}'

create_prop '{"name":"lawful_basis","label":"GDPR rechtsgrond","type":"enumeration","fieldType":"select","groupName":"contactinformation","options":[{"label":"Toestemming","value":"consent"},{"label":"Gerechtvaardigd belang","value":"legitimate_interest"},{"label":"Contract","value":"contract"}]}'

create_prop '{"name":"original_source","label":"Oorspronkelijke bron","type":"string","fieldType":"text","groupName":"contactinformation"}'

create_prop '{"name":"utm_source","label":"UTM source","type":"string","fieldType":"text","groupName":"contactinformation"}'

create_prop '{"name":"utm_campaign","label":"UTM campaign","type":"string","fieldType":"text","groupName":"contactinformation"}'

create_prop '{"name":"followup_reminder_sent_at","label":"Follow-up reminder verstuurd","type":"datetime","fieldType":"date","groupName":"contactinformation"}'

create_prop '{"name":"opted_out","label":"Uitgeschreven","type":"bool","fieldType":"booleancheckbox","groupName":"contactinformation","options":[{"label":"True","value":"true"},{"label":"False","value":"false"}]}'

create_prop '{"name":"lead_quality_score","label":"Lead score (1-10)","type":"number","fieldType":"number","groupName":"contactinformation"}'

echo "Done. Verifieer in HubSpot Settings -> Properties -> Contact Properties."
```

Sla op als `scripts/create-hubspot-properties.sh`, `chmod +x`, draai met `HUBSPOT_API_KEY=xxx ./scripts/create-hubspot-properties.sh`.

## Validatie checklist na setup

- [ ] Alle 11 properties verschijnen in Settings -> Properties -> Contact Properties
- [ ] Dropdown waarden voor `specialty` en `lawful_basis` zijn aanwezig
- [ ] Test-contact via n8n curl-test heeft alle properties gevuld
- [ ] `consent_processing_date` is correct als datum geparsed (geen timestamp string)
- [ ] In Smart Views/Lists kun je filteren op `specialty=warmtepomp` etc.
