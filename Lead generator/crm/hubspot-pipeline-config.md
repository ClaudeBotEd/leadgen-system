# HubSpot Free CRM — complete setup

**Tijd:** 45-60 minuten eerste keer.
**Vereist:** een HubSpot Free account (https://www.hubspot.com/products/get-started-free).

## Stap 1 — Maak een Private App aan voor API toegang

n8n praat met HubSpot via een Private App access token, niet via OAuth.

1. In HubSpot: rechtsboven **Settings (tandwiel-icoon)**.
2. Linksonder **Integrations -> Private Apps**.
3. Klik **Create a private app**.
4. **Basic Info** tab:
   - Name: `n8n Lead Intake`
   - Description: `Lead intake en follow-up automation via n8n`
5. **Scopes** tab — vink aan:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.deals.read` (optioneel, voor latere deal-flow)
   - `crm.objects.deals.write` (optioneel)
   - `crm.lists.read`
   - `crm.lists.write`
   - `crm.schemas.contacts.read`
6. **Create app** -> bevestig dialoog.
7. Kopieer de **Access token** (verschijnt eenmalig).
8. Plak in `/n8n/.env` als `HUBSPOT_API_KEY=`

## Stap 2 — Vind je Portal ID

Bovenin de HubSpot UI staat in de URL: `https://app.hubspot.com/contacts/12345678/...`
Het cijfer (12345678) is je Portal ID. Plak in `/n8n/.env` als `HUBSPOT_PORTAL_ID=12345678`.

## Stap 3 — Maak custom contact properties aan

Settings (tandwiel) -> **Properties** (links) -> tab **Contact properties** -> rechtsboven **Create property**.

Maak deze 11 properties aan:

### 1. specialty
- Group: `Lead information`
- Field type: `Dropdown select`
- Label: `Specialiteit`
- Internal name: `specialty` (HubSpot vult automatisch op basis van label, controleer)
- Options:
  - `warmtepomp` -> Warmtepompen
  - `airco` -> Airco
  - `zonnepanelen` -> Zonnepanelen
  - `cv` -> CV / sanitair
  - `ventilatie` -> Ventilatie / WTW
  - `multi` -> Multi-disciplinair

### 2. employee_count
- Group: `Lead information`
- Field type: `Single-line text`
- Label: `Aantal medewerkers`
- Internal name: `employee_count`

### 3. current_lead_source
- Group: `Lead information`
- Field type: `Multi-line text`
- Label: `Huidige lead-bron (zelf-gerapporteerd)`
- Internal name: `current_lead_source`

### 4. consent_processing_date
- Group: `Compliance`
- Field type: `Date picker`
- Label: `GDPR consent gegeven op`
- Internal name: `consent_processing_date`

### 5. lawful_basis
- Group: `Compliance`
- Field type: `Dropdown select`
- Label: `GDPR rechtsgrond`
- Options: `consent`, `legitimate_interest`, `contract`

### 6. original_source
- Group: `Lead information`
- Field type: `Single-line text`
- Label: `Oorspronkelijke bron`
- Internal name: `original_source`
- Standaardwaarden die n8n schrijft: `landingspagina`, `cold-email-reply`, `linkedin`, `referral`

### 7. utm_source
- Group: `Marketing`
- Field type: `Single-line text`

### 8. utm_campaign
- Group: `Marketing`
- Field type: `Single-line text`

### 9. followup_reminder_sent_at
- Group: `Workflow`
- Field type: `Date and time picker`
- Label: `Follow-up reminder verstuurd`

### 10. opted_out
- Group: `Compliance`
- Field type: `Single checkbox`
- Label: `Uitgeschreven`

### 11. lead_quality_score
- Group: `Lead information`
- Field type: `Number`
- Label: `Lead score (1-10)`

## Stap 4 — Configureer Lead Status enum (standaard property)

`hs_lead_status` is een ingebouwde property maar de waardes kun je aanpassen.

Settings -> Properties -> zoek `Lead Status` -> Edit.

Vervang de defaults door:
- `NEW` -> Nieuw (lead binnengekomen, nog niet gecontacteerd)
- `CONTACTED` -> Eerste contact gemaakt
- `OPEN_DEAL` -> Open conversatie / meeting gepland
- `IN_PILOT` -> 3 gratis leads in levering
- `CUSTOMER` -> Betalend
- `LOST` -> Niet kwalificerend / niet geinteresseerd / opgezegd

## Stap 5 — Maak een Sales Pipeline aan

Settings -> **Objects** -> **Deals** -> tab **Pipelines** -> **Create pipeline**.

Naam: `Installatie pilot pipeline`

Stages (in volgorde, met kans-percentages):

| Stage | Probability | Toelichting |
|-------|-------------|-------------|
| Intake gesprek gepland | 10% | Eerste call ingepland |
| Criteria afgestemd | 25% | Pilot-criteria besproken en geaccepteerd |
| Pilot leads geleverd | 50% | 3 gratis leads zijn verstuurd |
| Pilot evaluatie | 70% | Klant heeft leads beoordeeld, in gesprek over voortzetting |
| Aanbieding uit | 80% | Voorstel voor maandelijks contract verstuurd |
| Closed Won | 100% | Eerste betaling ontvangen |
| Closed Lost | 0% | Pilot afgewezen / niet doorgegaan |

## Stap 6 — Maak een gefilterde Contact List voor het dashboard

Contacts -> Lists -> **Create list** -> Active list.

Naam: `Nieuwe leads — laatste 7 dagen`
Filters:
- `Lead Status` is any of `NEW`
- `Create date` is in the last `7 days`
- `Original Source` is any of `landingspagina`

Save -> pin op je dashboard.

Maak ook:
- **Pilot in uitvoering** — `Lead Status = IN_PILOT`
- **Stale leads (>24u zonder contact)** — `Lead Status = NEW` AND `Create date > 24 hours ago`

## Stap 7 — Verifieer met een test-contact

Vanuit `/n8n/README.md`:

```bash
curl -X POST https://n8n.jouwdomein.nl/webhook/lead-intake \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Installatie BV",
    "contact_email": "info@test.nl",
    "phone": "+31612345678",
    "region": "Eindhoven",
    "specialty": "warmtepomp",
    "employee_count": "6-15",
    "current_lead_source": "Test",
    "consent_processing": true,
    "submitted_at": "2026-04-25T13:45:00Z",
    "page_url": "https://test.local/",
    "referrer": "",
    "user_agent": "curl/test",
    "utm": {"utm_source": "test", "utm_campaign": "verificatie"}
  }'
```

In HubSpot -> Contacts -> zoek `info@test.nl` -> alle 11 custom properties moeten gevuld zijn.

Verwijder het test-contact daarna.

## Stap 8 — Email integratie (optioneel maar aanbevolen)

HubSpot Free heeft beperkte email functies. Voor outreach gebruik je Instantly/Smartlead. Maar je wilt wel inkomende replies in HubSpot zien.

**Connect Inbox:**
- Settings -> General -> Email -> Connect inbox -> Google of Outlook
- Vink `Log emails` aan voor automatic inbound logging

Vanaf nu komt elke email aan jouw verbonden adres ook in HubSpot terecht aan het bijbehorende contact.

## Stap 9 — Notificaties

Settings -> Notifications -> Email notifications -> aanpassen wat je per email of in-app wilt zien:
- ✅ A new contact is created
- ✅ A contact replies to my email
- ✅ A deal moves to stage "Aanbieding uit" or higher

## Limieten van HubSpot Free die je moet kennen

| Feature | Limiet | Wanneer raakt je dit? |
|---------|--------|----------------------|
| Contacts | 1.000.000 | Vrijwel nooit |
| Email sends per maand (Marketing) | 2.000 | Snel — gebruik Instantly voor cold email |
| Workflows | 0 (alleen in Pro+) | Direct — daarom n8n |
| Custom properties per object | 100+ | Vrijwel nooit |
| API calls/dag | 250.000 (Free tier) | Vrijwel nooit voor 1 agency |
| Sequences | 0 (alleen in Pro+) | Direct — gebruik Instantly |

Wat HubSpot Free WEL heeft (en gebruik je):
- Contact + company + deal records
- Pipeline management
- Email tracking (incoming logging)
- Custom properties
- Lists
- Reporting
- Mobile app
- API toegang voor n8n

## Backup

HubSpot biedt geen native export-on-schedule. Optioneel script voor wekelijkse backup (via API):

```bash
# /etc/cron.weekly/hubspot-backup.sh
curl -s "https://api.hubapi.com/crm/v3/objects/contacts?limit=100" \
  -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  > /backup/hubspot-contacts-$(date +%Y%m%d).json
```

Voor productie: gebruik HubSpot's Data Backup API of een tool als Backupify.
