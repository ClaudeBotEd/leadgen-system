# Email Sequences — HVAC/Installatie NL/BE

## Wat zit er in deze map

Vier 3-email sequences voor cold outreach naar installatiebedrijven:

| Bestand | Niche | Doelgroep |
|---------|-------|-----------|
| `sequence-warmtepompen.md` | Warmtepomp-installateurs | Bedrijven die warmtepompen plaatsen, gericht op ISDE-subsidie volume |
| `sequence-airco.md` | Airco-specialisten | Installateurs die residentiele/commerciele airco doen |
| `sequence-zonnepanelen.md` | Zonnepanelen | PV-installateurs |
| `sequence-generiek-hvac.md` | Multi-disciplinair | Bredere installatiebedrijven (lood/zink, CV, ventilatie + meer) |

Elke sequence bevat 3 emails: waardepropositie -> social proof -> break-up. Alle emails staan klaar voor copy-paste in Instantly/Smartlead.

## Juridische check (verplicht lezen voor verzending)

Op basis van het rapport (Tabel 4 — Juridisch kader):

### Nederland (Telecommunicatiewet Art. 11.7 lid 2)
Cold email naar **generieke/functionele adressen van rechtspersonen** is toegestaan zonder opt-in. Dat betekent:

- WEL: `info@installatiebedrijf.nl`, `sales@`, `administratie@`, `contact@`, `algemeen@`
- NIET: `jan.jansen@installatiebedrijf.nl`, `j.devries@`, persoonlijke voornaam-adressen

### Belgie (WER Art. XII.13)
Strenger — alleen onpersoonlijke adressen van rechtspersonen mogen, en die zijn geen persoonsgegevens.

- WEL: `info@installatiebedrijf.be`, `sales@`
- NIET: alles met voornaam.naam@ — ook al is het zakelijk

### Verplichte elementen per email (NL EN BE)
1. Bedrijfsnaam afzender
2. KvK-nummer (NL) of KBO-nummer (BE)
3. Postadres
4. Werkende opt-out link (`{unsubscribe_url}` in Instantly)
5. Maximaal 3 emails zonder reactie per prospect

Alle templates in deze map bevatten al een placeholder-footer met deze velden. Vul je eigen gegevens in voor je verstuurt.

### Bronnen
- https://maxius.nl/telecommunicatiewet/artikel11.7
- https://leadbarometer.be/kennis/cold-email-belgie-wetgeving
- GBA Aanbeveling 01/2025

## Personalisatie variabelen

Alle templates gebruiken Instantly/Smartlead syntax:

| Variabele | Bron | Voorbeeld |
|-----------|------|-----------|
| `{{first_name}}` | Apollo/Clay (vaak leeg bij info@) | "Beste team," (fallback indien leeg) |
| `{{company_name}}` | Apollo | "Jansen Installatietechniek" |
| `{{city}}` | Apollo | "Eindhoven" |
| `{{specialty}}` | Custom field via Clay | "warmtepompen" |
| `{{your_name}}` | Sender setting | Jouw eigen naam |
| `{{your_company}}` | Sender setting | Naam van jouw agency |
| `{{calendar_link}}` | Custom variable | https://cal.com/jouwnaam/intake |
| `{{kvk_number}}` | Custom variable | NL: KvK 12345678 |
| `{{address}}` | Custom variable | Straat 1, 1234 AB Stad |

Configureer deze in Instantly onder Settings -> Custom Variables voor je de campagne start.

## CSV-import structuur (voor Instantly upload)

| Kolom | Type | Voorbeeld | Verplicht |
|-------|------|-----------|-----------|
| email | string | info@voorbeeldinstallatie.nl | ja — alleen generiek (zie compliance) |
| company_name | string | Voorbeeld Installatie BV | ja |
| city | string | Eindhoven | aanbevolen |
| specialty | enum | warmtepomp / airco / zonnepanelen / cv / ventilatie | aanbevolen voor segmentatie |
| website | URL | https://voorbeeldinstallatie.nl | aanbevolen |
| employee_count | int | 12 | optioneel |
| country | enum | NL / BE | ja (voor compliance-routing) |

## Verzendcadans (per Instantly campagne)

Per Sectie 7 van het rapport (Week 3-4):
- Email 1 (waardepropositie): dag 0
- Email 2 (social proof): dag 3 (skip indien reactie)
- Email 3 (break-up): dag 7 (skip indien reactie)
- 50 prospects/dag verdeeld over 9 mailboxen = ~5-6 per mailbox per dag
- Verzendvenster: dinsdag-donderdag 09:00-11:30 en 13:30-16:00 (Europe/Amsterdam)

Alleen verzenden naar generieke adressen + 14 dagen warmup compleet voor verzending.

## Verwachte performance

Industrie-benchmark uit het rapport (Tabel 5):
- Reply rate cold email: 3-4% (industrie), 6.7% (AI-personalisatie via SaaStr case)
- Bij 250 emails/week en 3.5%: ~9 replies/week, waarvan ~3 positief

## A/B test backlog

Per email zijn er twee subject regels (A/B). Roteer ze in Instantly:
- A = directer, cijfer-gedreven
- B = vraag-gedreven, lichter

Na 200 sends per variant: meet open rate, kies winnaar.
