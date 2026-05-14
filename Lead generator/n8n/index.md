# n8n

Workflow-engine — self-hosted (Hetzner CX11, ~EUR 4/mo) of cloud (~EUR 20/mo). Bevat 2 voorgebouwde workflows:

1. **`workflow-lead-intake`** — [[landingspagina/index]] form → HubSpot contact + Slack/Resend notificatie
2. **`workflow-followup`** — cron-driven reminder als 24u geen actie op nieuwe lead

Docker setup + JSON workflow-exports klaar voor import. Schaal-alternatief voor [[automation/index]] zodra je >1 host nodig hebt of 24/7 cron-execution wil.

## 📂 Onderdelen

- [[n8n/README|README]] — Docker self-host, workflow-imports, webhook & env-config

## 🔗 Related

- [[landingspagina/index]] — webhook-bron (form-submit)
- [[crm/index]] — bestemming van workflow-data (HubSpot / Close)
- [[email-sequences/index]] — n8n kan follow-ups versturen buiten Instantly om
- [[automation/index]] — Python-alternatief tijdens de MVP-fase
- [[dns/index]] — outbound mail-laag voor n8n-notificaties (Resend / SMTP)
