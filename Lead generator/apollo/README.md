# Apollo.io — filter-instructies en workflow

## Wat zit er in deze map

| Bestand | Doel |
|---------|------|
| `apollo-filters-hvac.md` | Concrete filter-sets per niche (warmtepomp, airco, zonnepanelen, generiek) |
| `sic-naics-codes.md` | Industry-codes om in Apollo te selecteren |
| `keywords-nl-be.md` | Nederlandstalige keywords + werkgeverskenmerken |
| `export-workflow.md` | Stap-voor-stap: lijst opbouwen, exporteren, importeren in Instantly + HubSpot |
| `legal-checklist.md` | Filter-criteria om alleen GDPR/Telecomwet-conforme adressen te krijgen |

## Setup eerst

1. Maak Apollo Free account: https://www.apollo.io/sign-up
2. Free tier geeft 10.000 export credits/maand. Voldoende voor maand 1-2.
3. Geen creditcard nodig voor Free.
4. Bevestig je email + skip de onboarding-vragen.

## Belangrijke randvoorwaarden voor compliance

Per Tabel 4 van het rapport:

### NL (Telecommunicatiewet Art. 11.7 lid 2)
Email naar **generieke/functionele adressen** van rechtspersonen mag zonder opt-in:
- WEL: `info@`, `sales@`, `administratie@`, `contact@`, `algemeen@`, `inkoop@`, `klantenservice@`
- NIET: voornaam.naam@, persoonlijke initialen

Apollo geeft standaard persoonlijke email-adressen (jan.devries@bedrijf.nl). Je MOET dus na export filteren op generieke adressen, OF de Apollo "Email status" en "Email type" filters gebruiken (zie `apollo-filters-hvac.md`).

### BE (WER Art. XII.13)
Strenger: alleen onpersoonlijke adressen. Zelfde regel als NL boven, maar geen wiggle-room.

## Pricing-context (per rapport Tabel 3)

| Tier | Maandprijs (annual) | Email credits/mnd | Wanneer upgraden |
|------|---------------------|---------------------|---------------------|
| Free | $0 | 10.000 | Start hier |
| Basic | $49/user | 12.000 | Als je sequences vanuit Apollo wilt sturen |
| Professional | $79/user | 24.000 | Bij 1.500+ exports/mnd |
| Organization | $99/user | 35.000 | Multi-user team |

Voor de eerste 6 maanden volstaat Free (10K/mnd is genoeg voor 250 prospects/week x 4 weken = 1.000/mnd).

## Workflow van leadlijst tot ingestoken sequence

```
Apollo search met filters
        |
        v
Save as List (Apollo)
        |
        v
Filter op generieke email-adressen
        |
        v
Export to CSV (Apollo)
        |
        v
Schoonmaak & dedup (apollo/export-workflow.md)
        |
        v
Upload in Instantly (sequence campagne) + HubSpot (long-term storage)
        |
        v
Sequence start volgens cadans uit /email-sequences/
```

Volledige uitwerking: zie `export-workflow.md`.
