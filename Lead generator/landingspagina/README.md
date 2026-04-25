# Landingspagina — installatiebedrijven lead gen agency

## Wat zit er in deze map

| Bestand | Doel |
|---------|------|
| `index.html` | Single-page landingspagina, klaar voor deploy |
| `styles.css` | Pure CSS, geen frameworks, mobile-first |
| `form-handler.js` | Vanilla JS form handler, post JSON naar webhook |

Geen build-stap, geen dependencies. Upload deze 3 bestanden naar een statische host en je bent live.

## Voor je deployed

### 1. Vul je placeholders in

In `index.html` staan 7 plaatshouders die je moet vervangen voor je live gaat. Zoek-en-vervang:

| Placeholder | Vervang door |
|-------------|--------------|
| `{{your_company}}` | Naam van jouw agency (bv. "AILeads NL") |
| `{{your_email}}` | Jouw zakelijke email (bv. `info@jouwagency.nl`) |
| `{{your_phone}}` | Jouw telefoonnummer in clickable formaat (bv. `+31612345678`) |
| `{{your_address}}` | Postadres voor footer (verplicht — KvK eis) |
| `{{your_kvk}}` | KvK-nummer (bv. `12345678`) |
| `{{your_btw}}` | BTW-nummer (bv. `NL123456789B01`) |

Snel via sed (bewerk eerst de waarden, dan voer uit):

```bash
cd "/Users/claudebot/Lead generator/landingspagina"
sed -i '' \
  -e 's/{{your_company}}/AILeads NL/g' \
  -e 's/{{your_email}}/info@ailegen.nl/g' \
  -e 's/{{your_phone}}/+31612345678/g' \
  -e 's/{{your_address}}/Voorbeeldstraat 1, 1234 AB Amsterdam/g' \
  -e 's/{{your_kvk}}/12345678/g' \
  -e 's/{{your_btw}}/NL123456789B01/g' \
  index.html
```

### 2. Configureer de webhook URL

In `form-handler.js`, regel 22, vervang `WEBHOOK_URL`:

```js
var WEBHOOK_URL = 'https://n8n.jouwdomein.nl/webhook/lead-intake';
```

Endpoints die direct werken:
- **n8n** (zie `/n8n/workflow-lead-intake.json`): `https://<host>/webhook/lead-intake`
- **Make.com** (custom webhook trigger): `https://hook.eu1.make.com/xxx`
- **Zapier**: `https://hooks.zapier.com/hooks/catch/xxx/yyy/`
- **Eigen API**: elk endpoint dat JSON POST accepteert

### 3. Privacy- en cookie-pagina's

De footer linkt naar `#privacy`, `#voorwaarden`, etc. — die ankers gaan momenteel naar de footer-sectie. Voor productie maak je echte pagina's:
- `privacy.html` — Privacyverklaring (verplicht onder GDPR Art. 13)
- `voorwaarden.html` — Algemene voorwaarden
- `dpa.html` — Verwerkersovereenkomst-template

Zonder deze pagina's loop je AVG-risico.

## Deployment opties

### Optie 1: Netlify (gratis, aanbevolen)

```bash
# Installeer Netlify CLI eenmalig
npm install -g netlify-cli

# Deploy de map
cd "/Users/claudebot/Lead generator/landingspagina"
netlify deploy --prod --dir=.
```

Custom domein toevoegen via Netlify dashboard. SSL wordt automatisch geregeld via Let's Encrypt.

### Optie 2: Cloudflare Pages (gratis, snelste)

1. Ga naar https://dash.cloudflare.com/?to=/:account/pages
2. "Create a project" -> "Direct upload"
3. Sleep de map `landingspagina/` erin
4. Custom domein toevoegen

### Optie 3: Carrd (EUR 19/jaar — wat het rapport voorstelt)

Carrd accepteert geen complete HTML, alleen drag-and-drop blocks. Gebruik deze pagina alleen als referentie voor de tekst en bouw na in Carrd's editor. Carrd is sneller voor non-coders, dit HTML-pad is sneller voor coders.

### Optie 4: Eigen webserver (nginx/caddy)

Plaats de 3 bestanden in `/var/www/leadgen/` en serveer met:

```caddyfile
leadgen.jouwdomein.nl {
  root * /var/www/leadgen
  file_server
  encode gzip
  header /*.html Cache-Control "public, max-age=300"
  header /*.css Cache-Control "public, max-age=86400"
  header /*.js Cache-Control "public, max-age=86400"
}
```

## Form-data structuur

Wanneer een prospect het formulier indient, ontvangt je webhook deze JSON:

```json
{
  "company_name": "Voorbeeld Installatie BV",
  "contact_email": "info@voorbeeldinstallatie.nl",
  "phone": "+31612345678",
  "region": "Eindhoven",
  "specialty": "warmtepomp",
  "employee_count": "6-15",
  "current_lead_source": "Mond-tot-mond en Werkspot",
  "consent_processing": true,
  "submitted_at": "2026-04-25T13:45:00.000Z",
  "page_url": "https://leadgen.jouwdomein.nl/?utm_source=cold-email",
  "referrer": "",
  "user_agent": "Mozilla/5.0 ...",
  "utm": {
    "utm_source": "cold-email",
    "utm_campaign": "warmtepomp-q2"
  }
}
```

De `/n8n/workflow-lead-intake.json` workflow leest exact deze structuur.

## SEO en analytics

### SEO
- `<meta description>` is gevuld
- Open Graph tags voor LinkedIn/WhatsApp delen
- Schema.org markup ontbreekt — voeg toe als je organisch wilt scoren
- Sitemap: maak `sitemap.xml` met 1 entry voor productie

### Analytics
Geen analytics opgenomen om GDPR-prompt te vermijden. Voeg toe naar keuze:

- **Plausible** (cookieless, EU-hosted): voeg in `<head>` toe:
  ```html
  <script defer data-domain="jouwdomein.nl" src="https://plausible.io/js/script.js"></script>
  ```
- **Umami** (self-hosted, cookieless): zelfde idee
- **Google Analytics 4**: vereist cookie-consent banner (Cookiebot of zelfgebouwd)

## Honeypot anti-spam

Het formulier bevat een onzichtbaar veld `hp_field`. Echte gebruikers vullen dit niet in; bots wel. Gevulde submissions worden stilletjes geaccepteerd UI-zijdig maar nooit verzonden naar de webhook. Dit voorkomt 90%+ van bot-spam zonder reCAPTCHA (die GDPR-issues geeft).

## Toegankelijkheid (WCAG 2.2 AA)

Wat al goed is:
- Semantische HTML (header, section, footer, nav, form)
- `<label>` per form-veld, `for=id` koppeling
- `aria-live` op form-status
- Voldoende kleurcontrast
- Keyboard-navigatie werkt

Wat nog mist voor strikte AA:
- Skip-to-content link
- Focus-zichtbaarheid styling op links (alleen op inputs nu)
- Screenreader-tekst bij iconen (worden nu CSS-pseudo-elementen)

Voor MVP: huidig niveau is "AA-streefbaar". Voor publieke sector klanten: laat een audit doen.

## Lokale preview

```bash
cd "/Users/claudebot/Lead generator/landingspagina"
python3 -m http.server 8000
# Open http://localhost:8000 in je browser
```

Of met Node:
```bash
npx serve .
```

## Performance budget

- Totale grootte (3 bestanden): ~22 KB ongecomprimeerd, ~7 KB gzipped
- Geen externe HTTP calls bij page load (geen fonts, geen tracking, geen CDN)
- Lighthouse score doelmatig: 100/100/100/100 (Performance, Accessibility, Best Practices, SEO)
