# n8n — workflow orchestration

## Wat zit er in deze map

| Bestand | Doel |
|---------|------|
| `workflow-lead-intake.json` | Webhook -> Apollo enrichment -> HubSpot CRM -> notificatie agency + bevestiging lead |
| `workflow-followup.json` | Cron (elke 6 uur) -> zoek stale leads -> notificeer agency |
| `docker-compose.yml` | Self-host setup (n8n + Caddy reverse proxy + SSL) |
| `Caddyfile` | Reverse proxy + HTTPS + CORS-headers voor webhook |
| `.env.example` | Template voor environment variables (kopieer naar `.env`) |

## Twee deploy-paden

### Path A: n8n Cloud (eenvoudigst, EUR 20/mnd Starter, EU-gehost)

1. Maak account op https://n8n.io/cloud (Starter tier = EUR 20/mnd, 2.500 executies/mnd, EU-server)
2. In de n8n UI: Workflows -> Import from File -> upload `workflow-lead-intake.json`
3. Doe hetzelfde voor `workflow-followup.json`
4. Voor elke workflow: open de instellingen, vul de Credentials in voor:
   - Apollo HTTP node — Header `X-Api-Key`
   - HubSpot HTTP node — Header `Authorization: Bearer <token>`
   - Resend HTTP nodes — Header `Authorization: Bearer <token>`
5. Activate beide workflows (toggle rechtsboven)
6. Kopieer de webhook URL uit de "Webhook (POST /lead-intake)" node — die zet je in `landingspagina/form-handler.js`

### Path B: Self-hosted (gratis tot je eigen schaal)

Vereisten:
- Server met Docker + docker-compose (DigitalOcean droplet EUR 6/mnd, Hetzner CX11 EUR 4/mnd)
- Een (sub)domein dat je naar de server-IP kunt wijzen (bv. `n8n.jouwdomein.nl`)
- Apollo, HubSpot en Resend accounts met API-keys

```bash
# 1. SSH naar de server, kloon de bestanden hierheen
mkdir -p /opt/n8n-leadgen && cd /opt/n8n-leadgen
# Kopieer alle 5 bestanden uit deze map naar de server (via scp of rsync)

# 2. Configureer
cp .env.example .env
nano .env   # vul alle waarden in

# 3. Genereer encryption key
openssl rand -hex 32
# Plak deze in N8N_ENCRYPTION_KEY in .env

# 4. DNS A-record: n8n.jouwdomein.nl -> server-IP
# (Dit duurt 5-30 min om te propageren)

# 5. Start
docker compose up -d

# 6. Wacht ~30s, check logs
docker compose logs -f n8n
docker compose logs -f caddy

# 7. Open https://n8n.jouwdomein.nl in browser
# Login met N8N_BASIC_AUTH_USER + PASSWORD uit .env

# 8. Importeer beide workflows via UI:
#    Workflows -> Import from URL -> file:///workflows/lead-intake.json
#    (de docker-compose mount maakt ze beschikbaar onder /workflows/)

# 9. Activate beide workflows
```

## Webhook URL bepalen

Na activate van `workflow-lead-intake.json` is de URL:

- **n8n Cloud**: `https://<jouw-instance>.app.n8n.cloud/webhook/lead-intake`
- **Self-hosted**: `https://n8n.jouwdomein.nl/webhook/lead-intake`

Tijdens testen (workflow niet active) krijg je `/webhook-test/lead-intake` — dat triggert maar 1x per ophaal-actie in de UI.

## Workflow-architectuur

### `workflow-lead-intake.json` — flow

```
[Webhook POST]
    |
[Validate payload] ── (faalt) ──> [Respond 400]
    |
    | (consent_processing=true, email+company aanwezig)
    v
[Add lead metadata]   (lead_id, country, received_at)
    |
[Enrich via Apollo]   (org info, employee count, industry)
    |
[Merge enrichment data]
    |
[Qualification check] ── (specialty niet in lijst) ──> [Respond OK]
    |
    | (specialty match)
    v
[Create HubSpot contact]      [Notify agency]      [Confirm to lead]
                                       |
                                  [Respond OK]
```

### `workflow-followup.json` — flow

```
[Cron elke 6h]
    |
[Find stale new leads]      (HubSpot search: status=NEW, createdate 24-48h geleden)
    |
[Split per lead]
    |
[Send reminder email]       (mail naar AGENCY_INTERNAL_EMAIL)
    |
[Mark reminder sent]        (HubSpot patch: followup_reminder_sent_at)
```

## Custom HubSpot properties die je vooraf moet aanmaken

Ga in HubSpot naar Settings -> Properties -> Contact -> Create property.

| Property naam | Type | Doel |
|---------------|------|------|
| `specialty` | Single-line text (of dropdown enum) | warmtepomp/airco/zonnepanelen/cv/ventilatie/multi |
| `employee_count` | Single-line text | "6-15", "16-50" — uit form of Apollo |
| `current_lead_source` | Multi-line text | Vrij invulveld over huidige lead-bron |
| `consent_processing_date` | Date | Tijdstip GDPR-consent gegeven |
| `original_source` | Single-line text | "landingspagina" / "cold-email-reply" / etc. |
| `utm_source` | Single-line text | UTM tracking |
| `utm_campaign` | Single-line text | UTM tracking |
| `followup_reminder_sent_at` | Date | Tijdstip reminder verstuurd door follow-up workflow |

Zie `crm/hubspot-pipeline-config.md` voor de complete CRM setup.

## Aanpassingen die je waarschijnlijk wilt doen

### Vervang HubSpot door Close
Edit `workflow-lead-intake.json`:
- Vervang HTTP node `Create HubSpot contact` met:
  - URL: `https://api.close.com/api/v1/lead/`
  - Auth: `Authorization: Basic <base64(api_key:)>`
  - Body: zie Close docs voor lead-create payload

### Vervang Resend door Gmail
Vervang HTTP nodes `Notify agency` en `Confirm to lead` met n8n's native `Gmail` node (vereist Gmail OAuth2 credentials in n8n).

### Voeg Slack-notificatie toe
Na "Notify agency" een extra HTTP node naar `https://hooks.slack.com/services/T.../B.../...` met body `{"text": "Nieuwe lead: ..."}`.

### Voeg WhatsApp-notificatie toe (Twilio)
HTTP POST naar `https://api.twilio.com/2010-04-01/Accounts/<SID>/Messages.json` met body `From=whatsapp:+14155238886&To=whatsapp:+31...&Body=Nieuwe lead`.

## Testen

### 1. Lokale test van webhook (vereist n8n draaiend)

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
    "utm": null
  }'
```

Verwachte response:
```json
{
  "status": "received",
  "lead_id": "lead_1745581500000_info",
  "message": "Bedankt — wij nemen binnen 1 werkdag contact op."
}
```

### 2. Validate consent rejection

```bash
curl -X POST https://n8n.jouwdomein.nl/webhook/lead-intake \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Test", "contact_email": "info@test.nl", "consent_processing": false}'
```

Verwachte response: HTTP 400 met `{"status": "rejected", "error": "missing_required_fields_or_consent"}`.

## Backup en disaster recovery

n8n slaat alle workflows + executies op in `./n8n_data/` (SQLite). Backup:

```bash
# Dagelijks via cron
0 3 * * * cd /opt/n8n-leadgen && tar czf /backup/n8n-$(date +\%Y\%m\%d).tar.gz n8n_data/
```

Voor productie met Postgres: gebruik `pg_dump`.

## Monitoring

n8n exposed `/healthz` endpoint. Voeg toe aan UptimeRobot of Better Stack:
- URL: `https://n8n.jouwdomein.nl/healthz`
- Verwachte response: `{"status":"ok"}`
- Check: elke 5 minuten

## Kosten-overzicht

| Component | Kosten/mnd |
|-----------|-----------|
| n8n Cloud Starter | EUR 20 |
| n8n Self-host (Hetzner CX11 + domein) | EUR 5 |
| Apollo Free | EUR 0 (10k credits/mnd) |
| HubSpot Free CRM | EUR 0 (max 1M contacten) |
| Resend (3.000 emails/mnd) | EUR 0 (free tier) |
| **Totaal self-host** | **~EUR 5/mnd** |
| **Totaal cloud** | **~EUR 20/mnd** |
