# CRM-light

CSV-based mini-CRM met terminal dashboard. Importeert leads vanuit [[lead-radar/index]], houdt status bij (new → contacted → replied → qualified → won/lost) en exporteert per stage. Geen accounts of subscription nodig — alleen Python + één CSV-bestand.

Bedoeld voor de **Pad A** MVP-fase. Zodra je team groeit of je >500 actieve leads beheert, schaal op naar [[crm/index]] (HubSpot Free of Close Solo).

## 📂 Onderdelen

- [[crm-light/README|README]] — commando's (`import`, `update`, `export`) en data-flow

## 🔗 Related

- [[lead-radar/index]] — leverancier van de geïmporteerde leads
- [[outreach/index]] — leest `leads.csv` om gepersonaliseerde berichten te genereren
- [[automation/index]] — automatiseert import + opent het dashboard in één run
- [[crm/index]] — betaalde tier voor team-CRM (HubSpot / Close)
- [[MVP-START-HERE]] — quickstart waarin crm-light de tweede stap is
