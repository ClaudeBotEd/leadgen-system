# Apollo export-workflow — van saved search tot Instantly-campagne

Concrete stappen om een lijst op te bouwen, te schonen en te exporteren naar Instantly + HubSpot. Eind-tot-eind tijd: ~30 minuten per niche van 500 leads.

## Stap 1 — Saved search opbouwen (10 minuten)

1. Apollo -> Search -> People (NIET Companies)
2. Vul filter-set in volgens `apollo-filters-hvac.md` voor de gekozen niche
3. Klik **Search**
4. Bekijk eerste 20 resultaten — kloppen ze?
5. Indien nee: pas keywords aan, herhaal
6. Indien ja: klik **Save** rechtsboven, naam volgens conventie `<land>-<niche>-<size>-<datum>` bv `NL-warmtepomp-2-50-2026-04`

## Stap 2 — Lijst exporteren (5 minuten)

1. Bovenaan resultaten: **Select all** -> kies alle (max 100 op Free, 5.000 op Basic+)
2. Rechtsboven: **Save to list** -> nieuwe lijst aanmaken
3. Apollo navigeer naar **Lists** in linker zijbalk
4. Open de net-aangemaakte lijst
5. Klik **Export** -> CSV
6. Sla op als `apollo-export-<niche>-<datum>.csv`, bv `apollo-export-warmtepomp-2026-04-25.csv`

## Stap 3 — CSV schoonmaken (10 minuten)

Apollo's CSV-export bevat dit schema:

```
first_name, last_name, name, title, email, email_status, primary_email,
company, industry, num_employees, city, country, linkedin_url, website,
seniority, departments, secondary_email, headquarters, ...
```

### Schoonmaak-checklist

Open de CSV in Numbers/Excel/Google Sheets en doe deze 6 acties:

1. **Verwijder rijen zonder email**
   - Filter `email` is leeg -> verwijder

2. **Verwijder catch-all met persoonlijke voornamen**
   - Filter `email_status` = "catch-all" AND `first_name` != "" -> beoordeel handmatig

3. **Filter alleen generieke adressen** (compliance!)
   Houd alleen rows waar `email` matcht een van deze patterns:
   ```
   info@*
   sales@*
   contact@*
   administratie@*
   algemeen@*
   inkoop@*
   klantenservice@*
   service@*
   office@*
   hello@*
   ```
   In Sheets: voeg een kolom `is_generic` toe met formule:
   ```
   =OR(REGEXMATCH(LOWER(E2), "^(info|sales|contact|administratie|algemeen|inkoop|klantenservice|service|office|hello|bestellingen|klantcontact)@"))
   ```
   Filter `is_generic` = TRUE.

4. **Verwijder duplicates op email**
   Data -> Remove duplicates op kolom `email`.

5. **Verwijder bedrijven uit verkeerde categorieen** (handmatige scan):
   - Groothandel/distributeurs (zie negative keywords in `keywords-nl-be.md`)
   - Bedrijven zonder werkende website
   - Bedrijven met `linkedin_url` die laat zien dat ze geen installateur zijn

6. **Voeg Instantly-vereiste kolommen toe**
   - `country_code`: `NL` of `BE` (uit `country` kolom)
   - `specialty`: handmatig invullen op basis van company name/keywords
   - `lead_source`: `apollo-{datum}-{niche}` (bv `apollo-2026-04-warmtepomp`)
   - `consent_basis`: `legitimate_interest` (B2B generiek adres)

Eindresultaat: van bv. 500 raw rows -> 80-200 schone, mailwaardige adressen.

## Stap 4 — Upload in Instantly (5 minuten)

1. Instantly -> **Leads** -> **Add leads** -> **Upload from CSV**
2. Map kolommen:
   - `email` -> Email
   - `company` -> Company
   - `city` -> City
   - `specialty` -> Custom 1
   - `country_code` -> Custom 2
   - `lead_source` -> Custom 3
   - Andere kolommen: skip
3. Kies de bijbehorende sequence-campagne (warmtepomp / airco / etc.)
4. Klik **Upload**
5. Verifieer in Campaign overzicht dat de leads zijn toegevoegd

## Stap 5 — Sync naar HubSpot voor long-term storage (5 minuten)

Optie A — handmatige import (geen volume-limiet maar veel klikken):
1. HubSpot -> Contacts -> **Import** -> File from computer
2. Upload zelfde CSV
3. Map kolommen op HubSpot custom properties:
   - `email` -> Email (primaire ID)
   - `company` -> Company name
   - `city` -> City
   - `country_code` -> Country
   - `specialty` -> `specialty` (custom)
   - `lead_source` -> `original_source` (custom)
   - Set `hs_lead_status` -> alle "NEW"
   - Set `consent_processing_date` -> vandaag
   - Set `lawful_basis` -> `legitimate_interest`
4. Klik Next -> "Don't update existing contacts" -> Import

Optie B — automatisch via n8n cron job:
- Een eenvoudige n8n workflow die elke nacht een Google Sheet leest en in HubSpot zet
- Vraagt extra setup, niet aanbevolen voor de eerste 3 maanden

## Stap 6 — Suppressielijst checken (kritisch!)

Voor je de campagne start: check of een van de leads al op de suppressielijst staat.

1. Open je centrale suppressielijst (Google Sheet `Suppression list — DO NOT EMAIL`)
2. VLOOKUP: voor elke lead-email -> staat hij op suppressie?
3. Verwijder matches uit Instantly campagne
4. Resultaat-stand: `X opgeschoond, Y verzendklaar`

Geen suppressielijst nog? Maak nu een Google Sheet aan met header:
```
email,added_date,reason
opt-out@example.com,2026-04-25,Unsubscribe via campaign Q2-warmtepomp
```

Voeg aan toe: iedereen die ooit "stuur niet meer" of unsubscribe gebruikte.

## Stap 7 — Campagne start

1. In Instantly -> Campaign -> **Start**
2. Verzendvenster:
   - Dagen: dinsdag-donderdag
   - Uren: 09:00-11:30 en 13:30-16:00 (Europe/Amsterdam)
3. Aantal per dag: max 50 per mailbox (lager bij <14d warmup)
4. Cooldown tussen verzending: 90-180 seconden (random)

## Anti-patterns

- Niet alle 500 in 1 dag versturen — zal sender reputation verbranden
- Niet exporteren zonder eerst saved search te bewaren — anders kun je niet reproduceren
- Niet skippen op stap 3 (schoonmaak) — direct naar Instantly = lage deliverability + compliance-risico
- Niet uploaden zonder suppressielijst-check — een email naar opt-out kan ACM/GBA klacht triggeren

## Tijd-investering per maand

Bij 250 nieuwe prospects/week (1.000/mnd):

- Apollo refresh: 2x per maand x 30 min = 1u
- CSV-schoonmaak: 4x per maand x 15 min = 1u
- Upload Instantly: 4x per maand x 5 min = 20 min
- HubSpot sync: 4x per maand x 5 min = 20 min
- Suppressie-check: 4x per maand x 5 min = 20 min

**Totaal: ~3.5 uur per maand voor lead-pipeline.**
