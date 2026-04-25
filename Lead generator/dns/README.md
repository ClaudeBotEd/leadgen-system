# DNS records & email-domein setup

## Wat zit er in deze map

| Bestand | Doel |
|---------|------|
| `dns-spf-dkim-dmarc.md` | Complete SPF/DKIM/DMARC records-templates per email-provider |
| `domain-strategy.md` | Welke domeinen kopen, welke patronen, hoeveel mailboxen |
| `provider-setup.md` | Stap-voor-stap voor Google Workspace, Microsoft 365 en Maildoso |
| `warmup-procedure.md` | 14-dagen warmup proces voor nieuwe mailboxen |
| `verification-tools.md` | Tools om DNS-config te checken (mxtoolbox, mail-tester) |

## Architectuur overzicht

Per Sectie 7 van het rapport (Week 1-2):

```
              [hoofddomein.nl] (NIET voor outreach gebruiken)
                        |
                        |  (apart, voor reputation isolation)
                        v
[outreach-domein-1.nl]   [outreach-domein-2.nl]   [outreach-domein-3.nl]
       |                        |                          |
   3 mailboxen              3 mailboxen                3 mailboxen
   = 9 mailboxen totaal voor 50 prospects/dag
```

Reden voor 3 domeinen, 3 mailboxen elk:
- Schade-isolatie: als 1 domein in spam komt, blijven 2 over
- Volume: 9 mailboxen x 50/dag = 450/dag rotation = ~250 echte sends/dag (na cooldowns)
- Reputatie-spreiding: niet alle eieren in 1 mand

## Volgorde van setup (chronologisch)

| Dag | Actie | Tijd |
|-----|-------|------|
| 1 | Koop 3 outreach-domeinen (TransIP, Hostnet, Cloudflare Registrar) | 15 min |
| 1 | Configureer DNS bij registrar: SPF + (placeholder) DKIM + DMARC | 30 min |
| 2 | Kies email-provider (Google Workspace EUR 6/mailbox of Maildoso $4) | 5 min |
| 2 | Maak 9 mailboxen aan (3 per domein) | 60 min |
| 2 | Voeg DKIM-records toe per provider-instructie | 30 min |
| 3 | Verifieer alle records via mxtoolbox.com | 15 min |
| 3 | Connect alle 9 mailboxen in Instantly | 30 min |
| 3-16 | Warmup-fase (14 dagen, automatisch via Instantly) | 0 min/dag |
| 17 | Eerste echte campagne start | — |

## Domein-naam conventies

Goede patronen voor outreach-domeinen:

- `<brand>leads.nl`, `<brand>leads.be`
- `<brand>installatie.nl`
- `<brand>hvac.nl`
- `<brand>aanvragen.nl`
- `<brand>data.nl`

Vermijd:
- Trefwoorden die als spam triggeren ("free", "winnen", "discount")
- Cijfers in het hoofddeel ("leads4u", "1leads")
- Te lange domeinen (>15 karakters voor het brand-deel)
- .top, .xyz, .info — bekende lage-vertrouwen TLDs

Per Sectie 7 van het rapport (kosten): EUR 30/jaar voor 3 .nl-domeinen.

## Belangrijke noot — hoofddomein NOOIT voor outreach

Je primaire bedrijfs-domein (`jouwagency.nl`) wordt gebruikt voor:
- De landingspagina
- Inkomende klant-emails (`info@jouwagency.nl`)
- Facturen + contracten

Het wordt NOOIT gebruikt voor cold outreach. Reden: cold email kan tijdelijk in spam terechtkomen. Als dat met je hoofddomein gebeurt, krijg je ook geen klant-emails meer. Daarom strikt apart houden.

## Estimated kosten

Per Tabel 3 van het rapport en deze setup:

| Component | Kosten |
|-----------|--------|
| 3 .nl-domeinen | EUR 30/jaar = EUR 2.50/mnd |
| 9 Google Workspace mailboxen ($6/each) | $54/mnd = ~EUR 50/mnd |
| Of: 9 Maildoso mailboxen ($4/each) | $36/mnd = ~EUR 33/mnd |
| Instantly Growth (warmup ingebouwd) | $37.60/mnd |
| **Totaal Google route** | **~EUR 88/mnd** |
| **Totaal Maildoso route** | **~EUR 71/mnd** |

Maildoso is goedkoper, Google Workspace heeft betere deliverability-reputation maar hogere kosten.

Per rapport (Sectie 7): "Google Workspace ~$6/account/mo of Woodpecker Maildoso $4/mailbox/mo".
