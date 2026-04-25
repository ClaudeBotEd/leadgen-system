# AI Lead Generation Agency — NL/BE — Implementatie Pakket

Werkbare bestanden + concrete instructies om een AI-powered lead gen agency op te zetten gericht op Nederlandse en Belgische installatiebedrijven (HVAC, warmtepompen, airco, zonnepanelen).

Gebaseerd op `rapport-ai-lead-gen-nl-be.md` (marktonderzoek) en de week 1 dagplanning. Alle bouw is gedaan zonder externe input — wat alleen jij kunt invullen staat onder ["Wat jij nog zelf moet doen"](#wat-jij-nog-zelf-moet-doen).

## Inhoudsopgave

| Map | Inhoud | Voor wie |
|-----|--------|----------|
| [`email-sequences/`](./email-sequences/README.md) | 4 cold email sequences (warmtepomp, airco, zonnepanelen, generiek) — copy-paste klaar voor Instantly/Smartlead | Outbound campagne-bouwer |
| [`landingspagina/`](./landingspagina/README.md) | Single-page HTML/CSS/JS landingspagina, deploybaar op Netlify/Cloudflare Pages | Web-eigenaar |
| [`n8n/`](./n8n/README.md) | 2 n8n workflows (lead intake + follow-up) + Docker self-host setup | Workflow-engineer |
| [`crm/`](./crm/README.md) | HubSpot Free + Close Solo configuratie, custom properties, pipeline stages, lead scoring | Sales-operator |
| [`apollo/`](./apollo/README.md) | Apollo filter-sets per niche, keywords NL/BE, export workflow, legal checklist | Lead-researcher |
| [`dns/`](./dns/README.md) | SPF/DKIM/DMARC templates, domein-strategie, provider setup, warmup procedure | Domein-admin |

Bestaande referentie-documenten:
- [`rapport-ai-lead-gen-nl-be.md`](./rapport-ai-lead-gen-nl-be.md) — Marktonderzoek (concurrenten, niches, juridisch kader, case studies, toolstack-prijzen)
- [`bronnen-ai-lead-generation.txt`](./bronnen-ai-lead-generation.txt) — ~140 bron-URL's gesorteerd op NL/BE-relevantie

## Quick start — wat je in de eerste 14 dagen doet

Volg deze volgorde. Hyperlinks gaan naar de relevante setup-instructie.

### Dag 1 — Domeinen + DNS
- Koop 3 outreach-domeinen ([dns/domain-strategy.md](./dns/domain-strategy.md)) — EUR 30/jr totaal
- Configureer SPF + DMARC bij registrar ([dns/dns-spf-dkim-dmarc.md](./dns/dns-spf-dkim-dmarc.md))

### Dag 2 — Email-provider
- Kies Google Workspace (default) of Maildoso ([dns/provider-setup.md](./dns/provider-setup.md))
- Maak 9 mailboxen aan (3 per domein)
- Voeg DKIM-records toe per provider-instructie

### Dag 3 — Verificatie + Instantly
- Check alle DNS-records via mxtoolbox ([dns/verification-tools.md](./dns/verification-tools.md))
- Maak Instantly Growth account ($37.60/mo) — voeg 9 mailboxen toe
- Start warmup ([dns/warmup-procedure.md](./dns/warmup-procedure.md))

### Dag 4 — CRM en Apollo
- Maak HubSpot Free account ([crm/hubspot-pipeline-config.md](./crm/hubspot-pipeline-config.md))
- Configureer 11 custom properties + pipeline stages
- Maak Apollo Free account
- Bouw eerste saved search per niche ([apollo/apollo-filters-hvac.md](./apollo/apollo-filters-hvac.md))

### Dag 5-6 — Landingspagina + n8n
- Vul placeholders in `landingspagina/index.html` ([landingspagina/README.md](./landingspagina/README.md))
- Deploy op Netlify of Cloudflare Pages
- Setup n8n (Cloud OF self-hosted) en importeer beide workflows ([n8n/README.md](./n8n/README.md))
- Configureer webhook URL in `form-handler.js`

### Dag 7-8 — Eerste content + email-templates
- Vul je echte gegevens in alle email-templates ([email-sequences/README.md](./email-sequences/README.md))
- Test sequences in Instantly (preview, niet live)
- Test webhook met curl uit n8n README

### Dag 9-13 — Warmup loopt door, Apollo refinement
- Refine Apollo filter-sets na bekijken eerste exports
- Schoon CSV-exports volgens [apollo/export-workflow.md](./apollo/export-workflow.md)
- Bouw lijsten per niche, ~200 prospects elk
- Doorloop legal checklist per lijst ([apollo/legal-checklist.md](./apollo/legal-checklist.md))

### Dag 14 — Pre-flight
- Mail-tester score 9-10/10 per mailbox?
- DMARC reports binnenkomend (geen surprises)?
- HubSpot custom properties allemaal getest met curl-test?
- Landingspagina form -> n8n -> HubSpot end-to-end werkt?
- Suppressielijst aangemaakt (leeg, klaar voor gebruik)?

### Dag 15 — Eerste echte campagne
- Start eerste 50 prospects/dag, 1 niche, 1 sequence
- Per [email-sequences/README.md](./email-sequences/README.md): di-do, 09:00-11:30 en 13:30-16:00

## Wat jij nog zelf moet doen

Onderdelen die ik niet voor je kon bouwen — vereisen jouw input:

### Juridisch / administratief
- [ ] **KvK-inschrijving** als eenmanszaak of VOF (~EUR 75)
- [ ] **Bankrekening** openen op bedrijfsnaam (Knab, bunq, ABN, ING — kies)
- [ ] **BTW-nummer** aanvragen via Belastingdienst (na KvK-inschrijving automatisch)
- [ ] **Bedrijfsnaam kiezen** (zie [dns/domain-strategy.md](./dns/domain-strategy.md) voor inspiratie)
- [ ] **Privacyverklaring** schrijven of laten genereren (bv. via privacyverklaring.nl, EUR 39)
- [ ] **Algemene voorwaarden** opstellen (bv. via DAS, EUR 79 of jurist-pakket)
- [ ] **Verwerkersovereenkomst-template** voor klanten (DPA — zie [apollo/legal-checklist.md](./apollo/legal-checklist.md))

### Tooling-accounts (kosten gespecificeerd)
- [ ] Apollo Free account — $0
- [ ] Instantly Growth account — $37.60/mo (annual)
- [ ] HubSpot Free account — $0
- [ ] n8n Cloud Starter (EUR 20/mo) OF self-host op Hetzner CX11 (EUR 4/mo)
- [ ] Google Workspace ($6/mailbox x 9 = $54/mo) OF Maildoso ($4/mailbox x 9 = $36/mo)
- [ ] Domain registrar account (TransIP voor .nl/.be — EUR 7.50/jr per domein)

### Inhoud die alleen jij kunt invullen
- [ ] Naam + persona voor de email-sender (jouw eigen naam? Persoonlijk aanbevolen)
- [ ] Calendar link (Cal.com gratis tier of Calendly EUR 8/mo)
- [ ] LinkedIn profiel afstemmen op agency (NIET noodzakelijk in week 1)
- [ ] Eerste 5 telefoongesprekken met installatiebedrijven om markt te valideren (per Sectie 7 actie 3 van het rapport)

### Beslissingen die jij moet maken
- [ ] **Pricing:** per-lead (EUR 25-50) of retainer (EUR 750-2.000/mo)? Beide kunnen, mijn advies: start per-lead voor lagere klantdrempel
- [ ] **Niche-volgorde:** start je met warmtepomp (groot maar concurrenter), airco (seizoensgevoelig), zonnepanelen (dalend volume) of generiek? Aanbeveling per rapport: warmtepomp (Sectie 6)
- [ ] **Geografie:** alleen NL, ook BE, of subset (bv. provincies binnen rijbereik)?
- [ ] **CRM-keuze:** HubSpot Free of Close Solo? Mijn aanbeveling: HubSpot voor maand 1-3

## Maandelijkse kosten (indicatief)

Per Tabel 3 van het rapport, gevalideerd in deze pakket-bestanden:

| Component | Kosten | Bron |
|-----------|--------|------|
| 3 .nl-domeinen | EUR 2.50/mo | TransIP via [dns/domain-strategy.md](./dns/domain-strategy.md) |
| Email mailboxen (Google Workspace, 9x) | ~EUR 50/mo | [dns/provider-setup.md](./dns/provider-setup.md) |
| Apollo Free | EUR 0 | [apollo/README.md](./apollo/README.md) |
| Instantly Growth | EUR 35/mo | [email-sequences/README.md](./email-sequences/README.md) |
| HubSpot Free | EUR 0 | [crm/hubspot-pipeline-config.md](./crm/hubspot-pipeline-config.md) |
| n8n Self-host (Hetzner) | EUR 4/mo | [n8n/README.md](./n8n/README.md) |
| Resend (email delivery, 3k free tier) | EUR 0 | [n8n/.env.example](./n8n/.env.example) |
| Cal.com (free tier) | EUR 0 | — |
| **Subtotaal** | **~EUR 92/mo** | |

Optionele kosten (later toe te voegen):
- Clay Launch ($179/mo) — wanneer je enrichment + personalisatie wilt automatiseren
- Dripify Basic ($39/mo) — wanneer je LinkedIn-kanaal toevoegt (let op risico-analyse Tabel 4)
- Landing-page domein (EUR 10/jr) — voor je hoofd-bedrijfssite
- Plausible analytics (EUR 9/mo) — wanneer je traffic-data wilt zonder GDPR-banner

## Tijdsinvestering schatting

| Fase | Tijdsinvestering eenmalig | Tijdsinvestering per maand (na setup) |
|------|---------------------------|------------------------------------------|
| Week 1-2 setup | ~16-20 uur (verspreid) | — |
| Apollo refresh + CSV schoonmaak | — | 3.5 uur ([apollo/export-workflow.md](./apollo/export-workflow.md)) |
| Reply handling + sales calls | — | 8-12 uur (afhankelijk van volume) |
| CRM bijhouden | — | 2 uur |
| Lead delivery aan klanten | — | varieert per klant — schatting 4 uur per klant per maand |
| **Totaal lopend werk** | | **~15-25 uur/mnd voor 5 klanten** |

## Architectuur in 1 diagram

```
                          [Apollo Free]
                                |
                        Saved searches per niche
                                |
                                v
                    Apollo CSV-export -> schoonmaak
                                |
                                v
                          [Instantly Growth]
                       9 mailboxen, 3 domeinen
                       Sequences uit /email-sequences/
                                |
                          (Outbound emails)
                                |
                                v
                       [Prospect ontvangt mail]
                                |
                          ┌─────┴─────┐
                          |           |
                   Reply rechtstreeks |   Klikt landingspagina-link
                          |           |
                          v           v
                   [Centrale inbox]   [Landingspagina form]
                          |                    |
                          | (handmatig)        | (POST JSON)
                          |                    |
                          v                    v
                      [HubSpot CRM] <—— [n8n workflow-lead-intake]
                                                |
                                          ┌─────┴─────┐
                                          |           |
                                   [Notify agency]  [Confirm to lead]
                                                |
                                          (24u zonder follow-up)
                                                |
                                                v
                                  [n8n workflow-followup] (cron)
                                                |
                                          [Reminder agency]
```

## Definitie van "klaar voor productie"

Je hebt week 1 succesvol afgerond als:
- [ ] Alle 9 mailboxen zijn warmgedraaid (dag 14+)
- [ ] mxtoolbox + mail-tester groen voor alle 3 domeinen
- [ ] Landingspagina is live op een custom subdomein
- [ ] HubSpot test-contact gemaakt via curl heeft alle 11 properties
- [ ] n8n webhook responseert <2s op test-payload
- [ ] Eerste Apollo-lijst van 200 prospects per niche is geschoond + in Instantly geladen
- [ ] Suppressielijst staat klaar (leeg)
- [ ] Eerste sequence is in Instantly aangemaakt en preview-klaar (NIET active)

## Volgorde van importance bij weinig tijd

Als je niet alle 14 dagen volgt, prioriteer in deze volgorde:

1. **Domeinen + warmup** (dag 1-3) — duurt 14 dagen real-time, dus eerste prioriteit
2. **Email sequences invullen + Apollo lijst** (dag 4-6)
3. **Landingspagina deploy** (dag 6-7)
4. **HubSpot setup** (dag 4-5)
5. **n8n workflows** (dag 5-6)

Zonder warmup geen email. Zonder lijst geen ontvangers. Zonder landingspagina werkt cold email nog (je calendar link kan ook direct), maar geen schaalbare instroom.

## Hoe te verifieren dat het pakket werkt

```bash
# 1. Static check — alle bestanden aanwezig?
find "/Users/claudebot/Lead generator" -type f | wc -l  # verwacht 30+

# 2. n8n workflow JSON valid?
cd "/Users/claudebot/Lead generator/n8n"
python3 -c "import json; json.load(open('workflow-lead-intake.json'))" && echo "lead-intake JSON OK"
python3 -c "import json; json.load(open('workflow-followup.json'))" && echo "followup JSON OK"

# 3. Landingspagina lokaal testen
cd "/Users/claudebot/Lead generator/landingspagina"
python3 -m http.server 8000
# Open http://localhost:8000 in browser

# 4. Markdown bestanden tellen
find "/Users/claudebot/Lead generator" -name "*.md" | wc -l   # verwacht 25+
```

## Bronnen + ondersteuning

- Volledig marktonderzoek: [`rapport-ai-lead-gen-nl-be.md`](./rapport-ai-lead-gen-nl-be.md)
- Bron-bibliografie: [`bronnen-ai-lead-generation.txt`](./bronnen-ai-lead-generation.txt)
- Per onderdeel: zie de README.md in de relevante submap

## Compliance disclaimer

Dit pakket bevat templates en instructies die opgesteld zijn op basis van het rapport van 2026-04-25, met verwijzingen naar GDPR, Telecommunicatiewet (NL) en WER (BE). Het is GEEN juridisch advies. Voor productie-gebruik:

- Laat je privacyverklaring en algemene voorwaarden door een jurist beoordelen
- Documenteer je GDPR-belangenafweging in een Register of Processing Activities (RoPA)
- Onderteken DPA's met alle sub-processors (Apollo, Instantly, HubSpot, n8n)
- Maak je eerste 30 dagen extra voorzichtig met volume — bouw geleidelijk op naar 500+/wk

## Toolstack op een rij (voor snelle referentie)

| Component | Tool | Prijs/mo |
|-----------|------|----------|
| Prospect data | Apollo Free | $0 |
| Cold email | Instantly Growth | $37.60 |
| Email warmup | Instantly (incl.) | inclusief |
| Email mailboxen | Google Workspace x 9 | $54 |
| Email mailbox alt. | Maildoso x 9 | $36 |
| Workflow engine | n8n self-host (Hetzner CX11) | EUR 4 |
| Workflow alt. | n8n Cloud Starter | EUR 20 |
| CRM | HubSpot Free | $0 |
| CRM alt. | Close Solo | $9 |
| Email delivery (transactioneel) | Resend free | $0 |
| Calendar booking | Cal.com free | $0 |
| Landing page hosting | Netlify free / Cloudflare Pages free | $0 |
| Domeinen | TransIP/Cloudflare x 3 | EUR 2.50 |

**Minimum levensvatbare stack:** ~EUR 92/mo
**Schaal-stack (Clay + LinkedIn):** ~EUR 310/mo
