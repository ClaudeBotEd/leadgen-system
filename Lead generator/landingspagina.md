# Landingspagina

Single-page HTML/CSS/JS landingspagina voor lead-capture. Deploybaar op Netlify of Cloudflare Pages (gratis tier). Form-submit POST → [[n8n]] webhook → [[crm]] contact-create + notificatie. Ontworpen voor NL/BE HVAC-niches met conversion-focused copy, mobile-first.

## 📂 Onderdelen

- [[landingspagina/README|README]] — placeholders, deployment-stappen, webhook config

## 🔗 Related

- [[n8n]] — verwerkt form-submissions via `workflow-lead-intake`
- [[crm]] — eindbestemming van form-leads
- [[dns]] — custom subdomein onder de outreach-root
- [[email-sequences]] — CTA-links in sequences wijzen naar deze pagina
- [[apollo]] — Apollo-lijsten linken naar deze pagina als landing-stap
