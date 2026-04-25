# SIC, NAICS en NL SBI codes voor installatiebedrijven

Apollo gebruikt onder de motorkap NAICS-codes (US-standaard) gekoppeld aan industry-namen. KvK gebruikt NL SBI-codes. Dit overzicht koppelt ze.

## Belangrijkste codes

| Sector | NAICS (US) | SIC (US, ouder) | NL SBI 2008 | Apollo Industry naam |
|--------|------------|-----------------|-------------|----------------------|
| HVAC contractors | 238220 | 1711 | 43.22.2 | "HVAC and refrigeration" |
| Plumbing/loodgieters | 238220 | 1711 | 43.22.1 | "Construction" + keyword filter |
| Elektrotechnische installatie | 238210 | 1731 | 43.21 | "Electrical/Electronic Manufacturing" of "Construction" |
| PV / Solar installation | 238220 | 1731 | 43.21.2 | "Renewables and Environment" |
| Algemene bouw | 236220 | 1542 | 41.20 | "Construction" |
| Onderhoud installaties | 811310 | 7699 | 33.20 | "Mechanical or Industrial Engineering" |

## NL SBI-codes (KvK) in detail

Als je later een KvK-export wilt doen (of via een data-vendor zoals Company.info een NL-specifieke lijst), hier de relevante SBI-codes:

| SBI | Omschrijving |
|-----|--------------|
| 43.21 | Elektrotechnische installatie |
| 43.21.1 | Elektrotechnische bouwinstallatie |
| 43.21.2 | Telecommunicatie installatie |
| 43.22 | Loodgieters- en fitterswerk; installatie van sanitair en van verwarmings- en luchtbehandelingsapparatuur |
| 43.22.1 | Loodgieterswerk en sanitair |
| 43.22.2 | Installatie van verwarmings- en luchtbehandelingsapparatuur |
| 43.22.3 | Installatie van overige bouw-installaties (n.e.g.) |
| 43.29 | Overige bouw-installatie |
| 33.12 | Reparatie van machines en apparaten |
| 71.12 | Ingenieurs en overig technisch ontwerp en advies |

**Bron:** CBS SBI 2008 — https://www.cbs.nl/nl-nl/onze-diensten/methoden/classificaties/activiteiten/sbi-2008-standaard-bedrijfsindeling-2008

## BE NACE-Bel codes

Belgische tegenhanger van NL SBI. Apollo herkent NACE-Bel niet direct, maar je kunt KBO-data hierop filteren.

| NACE-Bel | Omschrijving |
|----------|--------------|
| 43.221 | Loodgieterswerk en sanitair |
| 43.222 | Installatie van verwarming en airconditioning |
| 43.211 | Elektrotechnische bouwinstallatie |
| 35.140 | Verkoop van elektriciteit (relevant voor PV) |

**Bron:** Statbel NACE-Bel 2008.

## Gebruik in Apollo

Apollo's UI laat je niet rechtstreeks NAICS-codes invoeren. Selecteer in plaats daarvan de overeenkomstige Apollo Industry naam (kolom rechts in tabel). Voorbeelden:

- Voor warmtepomp/airco/CV: kies **HVAC and refrigeration** + **Construction**
- Voor zonnepanelen: kies **Renewables and Environment** + **Construction**
- Voor multi-disciplinair: alle drie + keyword filter

## Alternatieve data-bronnen (niet Apollo) voor NL/BE

Als Apollo's NL/BE coverage te dun is voor jouw gebied, overweeg:

| Bron | Wat | Kosten |
|------|-----|--------|
| KVK Open Data | Officiele NL bedrijfsregistratie, alleen basisgegevens (naam, adres, SBI) zonder email | Gratis API |
| Company.info | KvK + verrijking met emails, telefoon, omzet | Vanaf ~EUR 200/mnd |
| Graydon | Premium NL/BE bedrijfsdata | Custom pricing |
| Bisnode (Dun & Bradstreet) | Internationaal, alle EU | Custom |
| Europages.nl | Europese B2B-directory, gratis lijsten downloaden | Gratis (laag volume) |
| Drimble | NL-specifiek, scraping van openbare bronnen | Free + paid tiers |

Voor maand 1-3 is Apollo Free voldoende. Daarna evalueren of een NL-native bron beter is voor jouw niche.

## Hoe een SBI-code achterhalen voor een specifiek bedrijf

Als je tijdens kwalificatie wilt checken welke SBI-code een bedrijf heeft:

1. KvK Handelsregister: https://www.kvk.nl/zoeken/
2. Zoek op bedrijfsnaam
3. Open detailpagina -> "Activiteiten" sectie -> daar staat de SBI-code

Voor BE: KBO Public Search https://kbopub.economie.fgov.be/kbopub/zoekwoordenform.html
