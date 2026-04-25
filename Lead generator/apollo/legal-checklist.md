# Legal checklist — voor je een Apollo-export gaat mailen

Op basis van rapport Tabel 4 (Juridisch kader NL/BE/EU) — alle bronnen verifieerbaar via maxius.nl, leadbarometer.be en gba/aanbeveling 01/2025.

## Pre-flight per export — verplicht doorlopen

Voor elke campagne, vink AF:

### 1. Email-adres soort
- [ ] Alle adressen zijn generiek/functioneel (`info@`, `sales@`, `contact@`, `administratie@`, `algemeen@`, `inkoop@`, `service@`, `office@`, `klantenservice@`)
- [ ] Geen voornaam.naam@ adressen
- [ ] Geen voornaaminitiaal.naam@ adressen (bv `j.devries@`)
- [ ] Geen adres@gmail.com / @outlook.com / @hotmail.com (consumer adres = persoonlijk)

**Reden:** NL Telecommunicatiewet Art. 11.7 lid 2 staat alleen toe naar "publiekelijk aangewezen" adressen voor commercieel gebruik. Persoonlijke adressen vereisen opt-in. BE WER XII.13 is nog strenger.

### 2. Doelgroep
- [ ] Alleen rechtspersonen / B2B (geen ZZP's met privé-mailadres)
- [ ] Werkgebied is afgestemd op jouw distributie (NL en/of BE)
- [ ] Geen consumenten — Telecommunicatiewet vereist altijd opt-in voor B2C

### 3. Email-inhoud
- [ ] Bedrijfsnaam afzender vermeld in body
- [ ] KvK-nummer (NL) of KBO-nummer (BE) vermeld in footer
- [ ] Postadres in footer
- [ ] Werkende opt-out link (`{unsubscribe_url}` in Instantly genereert dit)
- [ ] Onderwerp is niet misleidend ("Re:" alleen als echte reply)
- [ ] Geen valse uitspraken zoals "ik heb gebeld" als dat niet waar is

### 4. Verzend-volume
- [ ] Maximum 3 emails zonder reactie per prospect
- [ ] Minimaal 14 dagen warmup voor mailbox in gebruik
- [ ] Deliverability >95% (check in Instantly analytics)
- [ ] Bounce rate <5% (lijst is schoon)

### 5. Data-administratie
- [ ] Bron van elk email-adres documenteerbaar (Apollo + datum + saved search)
- [ ] Verwerking gedocumenteerd in Register of Processing Activities (RoPA) onder GDPR Art. 30
- [ ] Verwerker-overeenkomst (DPA) met Instantly/Apollo getekend
- [ ] Suppressielijst actief en wordt voor elke send gecheckt

### 6. Specifiek voor BE-adressen
- [ ] EXTRA strikt: alleen `info@`-achtige adressen, geen ruimte voor "publiekelijk aangewezen" interpretatie
- [ ] NACE-Bel checken indien van toepassing
- [ ] Frans-talige contacten: ofwel vermijden, ofwel Frans-talige variant van de email gebruiken

## Wat te doen bij twijfel

| Situatie | Actie |
|----------|-------|
| Adres `info@bedrijf.nl` maar website is van een ZZP'er | Persoonlijke mail in bedrijfsjasje. Skip. |
| Adres `pieter@bedrijfsnaam.nl` met website van 50+ FTE bedrijf | Niet "publiekelijk aangewezen voor commercieel". Skip. |
| Adres `bestelling@webshop.nl` | Functioneel adres, mag — maar webshop is mogelijk geen ICP. Apart kwalificeren. |
| Adres `opmerkingen@gemeente.nl` | Overheid — andere context. Skip tenzij specifiek B2G aanbod. |

## Rechtsgrond per type send

| Send type | Lawful basis (GDPR Art. 6) | Te documenteren |
|-----------|----------------------------|------------------|
| Cold email naar `info@` | Art. 6(1)(f) — gerechtvaardigd belang (B2B contact via openbaar adres) | Belangenafweging in RoPA |
| Email naar lead die formulier invulde | Art. 6(1)(a) — toestemming | `consent_processing_date` in CRM |
| Email naar betalende klant | Art. 6(1)(b) — uitvoering overeenkomst | Contract bewaard |
| Reminder na opt-in (soft) | Art. 6(1)(f) + bestaande klantrelatie | Bewijs van vorige interactie |

## Acties bij opt-out

Wanneer een prospect "stuur niet meer", unsubscribe of GDPR-verwijderverzoek doet:

1. **Direct (binnen 24u):**
   - Verwijder uit alle actieve Instantly-campagnes (handmatig in UI)
   - Voeg toe aan suppressielijst (Google Sheet)
   - Update HubSpot: `opted_out` = TRUE, status = `OPTED_OUT`

2. **Binnen 30 dagen (bij verwijderverzoek Art. 17 GDPR):**
   - Verwijder volledig uit Apollo lijsten
   - Verwijder uit HubSpot (na hashen email voor suppressie-check)
   - Bevestig verwijdering aan verzoeker per email

3. **Permanent:**
   - Hash van email (SHA-256) blijft in suppressielijst — voorkomt per ongeluk re-import

## Documentatie die je MOET hebben

Op je hard schijf of in Notion/Google Drive:

- [ ] **Privacyverklaring** (gepubliceerd op landingspagina)
- [ ] **Algemene voorwaarden** voor klantcontracten
- [ ] **Verwerkersovereenkomst (DPA)** met klanten — jij bent verwerker als jij hun leads beheert
- [ ] **DPA's met Apollo, Instantly, HubSpot, n8n** — jij als verwerkingsverantwoordelijke moet deze met sub-processors hebben
- [ ] **Register of Processing Activities (RoPA)** — wettelijk verplicht onder GDPR Art. 30 voor bedrijven met >250 werknemers OF systematische verwerking, EN voor MKB sterk aanbevolen
- [ ] **Data Processing Impact Assessment (DPIA)** — alleen verplicht bij hoog risico verwerking, niet voor cold email

## Wat je NIET mag doen

| Praktijk | Waarom verboden |
|----------|------------------|
| Email scrapen van LinkedIn | LinkedIn ToS Sec 8.2 + GDPR scraping issues |
| Gekochte lijsten van databrokers zonder verifieerbare consent | Verantwoordelijkheid blijft bij jou (niet bij broker) |
| Email "voor wetenschappelijk onderzoek" sturen die eigenlijk verkoop is | Misleidende handelspraktijk |
| Tracking pixels zonder consent-mechanisme | Cookiewet/ePrivacy violation |
| Doorgaan met emails na opt-out | EUR 450K boete (NL) per overtreding mogelijk |
| Non-EU sub-processors zonder SCC's of adequacy decision | GDPR Hoofdstuk V violation |

## Recente handhaving (om als waarschuwing te gebruiken)

Per rapport Tabel 4 (handhavingscases 2024-2026):

- **Daisycon (NL):** EUR 770.000 boete voor 2+ miljard ongewenste emails
- **All4Call (NL):** EUR 350.000 totaal voor twee Art. 11.7 lid 1 overtredingen
- **Belgische data-broker:** EUR 20.000 GBA-boete voor onrechtmatig delen B2B-emails

## Bronnen

- https://maxius.nl/telecommunicatiewet/artikel11.7
- https://leadbarometer.be/kennis/cold-email-belgie-wetgeving
- https://www.gegevensbeschermingsautoriteit.be/publications/aanbeveling-01-2025-over-de-verwerking-van-persoonsgegevens-bij-direct-marketing.pdf
- https://www.acm.nl/nl/telecom/zakelijk-abonnement-voor-bellen-en-internet/spam
