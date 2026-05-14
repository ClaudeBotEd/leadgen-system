# CRM (HubSpot / Close)

Configuratie voor de betaalde CRMs in **Pad B**: HubSpot Free (default) en Close Solo (alt.). Bevat 11 custom properties, pipeline stages, lead-scoring matrix en provider-specifieke setup-gidsen. Vervangt [[crm-light]] zodra je team groeit of je geautomatiseerde sync via [[n8n]] wil.

## 📂 Onderdelen

- [[crm/README|README]] — overzicht en provider-keuze
- [[crm/hubspot-pipeline-config|HubSpot pipeline config]]
- [[crm/close-pipeline-config|Close pipeline config]]
- [[crm/custom-properties|Custom properties]] — alle 11 velden + types
- [[crm/pipeline-stages|Pipeline stages]] — stage-definities + transitions
- [[crm/lead-scoring|Lead scoring]] — scoring matrix

## 🔗 Related

- [[crm-light]] — gratis tegenhanger voor de MVP-fase
- [[apollo]] — bron van CRM-contacten (CSV-import)
- [[n8n]] — synchroniseert form-submissions en follow-ups naar CRM
- [[landingspagina]] — vult CRM via webhook → n8n → contact-create
- [[email-sequences]] — replies en bounce-events landen in CRM
