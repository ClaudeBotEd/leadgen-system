# Landingspagina

Single-page HTML/CSS/JS landingspagina voor lead-capture. Deploybaar op Netlify of Cloudflare Pages (gratis tier). Form-submit POST → [[n8n/index]] webhook → [[crm/index]] contact-create + notificatie. Ontworpen voor NL/BE HVAC-niches met conversion-focused copy, mobile-first.

## 📂 Onderdelen

- [[landingspagina/README|README]] — placeholders, deployment-stappen, webhook config

## 🔗 Related

- [[n8n/index]] — verwerkt form-submissions via `workflow-lead-intake`
- [[crm/index]] — eindbestemming van form-leads
- [[dns/index]] — custom subdomein onder de outreach-root
- [[email-sequences/index]] — CTA-links in sequences wijzen naar deze pagina
- [[apollo/index]] — Apollo-lijsten linken naar deze pagina als landing-stap
