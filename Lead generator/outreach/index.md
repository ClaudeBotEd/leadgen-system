# Outreach

Template-personalisatie engine. Leest een leads-CSV en een template-bestand, vervangt placeholders (bedrijfsnaam, niche, stad, intent-score, eerste-naam) en schrijft klare emails/DMs naar `outbox/`. **Geen verzending** — kopieer de output naar Gmail/Outlook drafts of plak ze in [[email-sequences/index]] / Instantly.

Templates zitten in `templates/email/` en `templates/dm/`. Placeholders volgen de syntax `{{lead.column_name}}`.

## 📂 Onderdelen

- [[outreach/README|README]] — template-syntax, placeholder lijst, voorbeelden

## 🔗 Related

- [[lead-radar/index]] — bron van leads die gepersonaliseerd worden
- [[crm-light/index]] — leest dezelfde `leads.csv` die outreach gebruikt
- [[email-sequences/index]] — markdown sequences voor Instantly/Smartlead (paid alternatief)
- [[automation/index]] — roept outreach aan na CRM-import
- [[apollo/index]] — bij opschalen vervangt Apollo-export de lead-radar CSV
