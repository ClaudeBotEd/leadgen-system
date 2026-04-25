# Apollo filter-sets per niche

Vier filter-sets, een per niche. Elke set is letterlijk in te vullen in de Apollo "People Search" UI. Bewaar elke set als "Saved Search" voor later hergebruik.

## Algemene aanpak

1. Apollo UI -> linksboven **Search** -> tab **People** (NIET Companies)
2. Vul alle filters hieronder in
3. Klik **Save Search** (rechtsboven), geef naam
4. Bekijk resultaten -> klik **Export** -> CSV (max 100 per export op Free, 5.000 op Basic+)

## Filter-set 1 — WARMTEPOMPEN

**Saved search naam:** `NL-warmtepomp-installateurs-2-50`

| Filter | Waarde |
|--------|--------|
| **Location** | Country = Netherlands |
| **Company location** | Country = Netherlands |
| **Industry** | "HVAC and refrigeration", "Construction", "Renewables and Environment" |
| **Keywords (Company)** | warmtepomp OR "heat pump" OR "lucht-water" OR "lucht-lucht" |
| **Number of employees** | 2 - 50 |
| **Job titles** | (laat leeg — wij willen op bedrijfsniveau, niet op rol) |
| **Email status** | "Verified" only |
| **Has email** | Yes |
| **Seniority** | Owner, Founder, C-Suite, VP, Director (om kleinere bedrijven met info@ vaak gekoppeld aan owner te krijgen) |

**Verwacht resultaat:** ~500-1.500 bedrijven NL.

## Filter-set 2 — AIRCO

**Saved search naam:** `NL-airco-installateurs-2-50`

| Filter | Waarde |
|--------|--------|
| **Location** | Country = Netherlands |
| **Industry** | "HVAC and refrigeration", "Construction" |
| **Keywords (Company)** | airco OR "air conditioning" OR "klimaatbeheersing" OR "split-unit" OR "airconditioning" |
| **Number of employees** | 1 - 50 (ZZP'ers tellen mee) |
| **Email status** | Verified |
| **Has email** | Yes |

**Verwacht resultaat:** ~300-800 bedrijven NL.

## Filter-set 3 — ZONNEPANELEN / PV

**Saved search naam:** `NL-PV-installateurs-5-100`

| Filter | Waarde |
|--------|--------|
| **Location** | Country = Netherlands |
| **Industry** | "Renewables and Environment", "Construction", "Electrical/Electronic Manufacturing" |
| **Keywords (Company)** | zonnepanelen OR "solar panels" OR PV OR fotovoltaisch OR "thuisbatterij" OR "energieopslag" |
| **Number of employees** | 5 - 100 (PV-bedrijven zijn doorgaans groter) |
| **Email status** | Verified |
| **Has email** | Yes |

**Verwacht resultaat:** ~400-900 bedrijven NL.

## Filter-set 4 — GENERIEK INSTALLATIEBEDRIJF

**Saved search naam:** `NL-installatiebedrijf-multi-3-50`

| Filter | Waarde |
|--------|--------|
| **Location** | Country = Netherlands |
| **Industry** | "Construction", "HVAC and refrigeration", "Mechanical or Industrial Engineering" |
| **Keywords (Company)** | installatiebedrijf OR "installation company" OR "loodgieter" OR "CV" OR "centrale verwarming" OR "ventilatie" OR "WTW" |
| **Number of employees** | 3 - 50 |
| **Email status** | Verified |
| **Has email** | Yes |

**Verwacht resultaat:** ~1.500-3.500 bedrijven NL.

## Filter-set 5 — BELGIE (alle niches gecombineerd)

**Saved search naam:** `BE-installatie-warmte-airco-PV-2-50`

Apollo's BE-data is dunner dan NL. Beter een breder net + handmatige curatie achteraf.

| Filter | Waarde |
|--------|--------|
| **Location** | Country = Belgium |
| **Industry** | "HVAC and refrigeration", "Construction", "Renewables and Environment" |
| **Keywords (Company)** | warmtepomp OR airco OR zonnepanelen OR installatie OR HVAC |
| **Number of employees** | 2 - 50 |
| **Email status** | Verified |
| **Has email** | Yes |

**Verwacht resultaat:** ~400-800 bedrijven BE.

## Apollo "Email Type" filter — kritisch voor compliance

Apollo segmenteert email-adressen in:
- **Verified** — Apollo heeft de email gevalideerd via SMTP-handshake. Veel hiervan zijn persoonlijke emails (jan@bedrijf.nl).
- **Likely to engage** — gegokt op basis van patroon, niet gevalideerd.
- **Unverified** — onbekende status.
- **Catch-all** — de mailserver accepteert alle adressen, dus ook foute. Apollo geeft GENERIEKE adressen vaak deze status.

**Voor jouw use-case:** je wilt vooral catch-all OF verified met `info@` patroon. Apollo zelf heeft GEEN filter "alleen generieke adressen". Daarom moet je na export schonen — zie `legal-checklist.md`.

## Aanvullende filters die je later kunt overwegen

| Filter | Wanneer gebruiken |
|--------|--------------------|
| **Technologies** | Als bedrijven tools als "Solar Edge", "Daikin Cloud", etc. gebruiken — wijst op specialisatie |
| **Funding stage** | Niet relevant voor installateurs (private/family-owned) |
| **Founded year** | Toevoegen als je alleen bedrijven >5 jaar oud wilt (lagere churn-risico) |
| **Annual revenue** | Toevoegen als je alleen >EUR 1M revenue wilt (afgevallen ZZP'ers) |
| **News/Buying signals** | Als je premium hebt: "Hiring decision makers" of "New funding" als extra qualifier |

## Frequency

Maak elke maand een fresh export per saved search. Apollo's data verandert: bedrijven sluiten, nieuwe ontstaan, employees wisselen.

Zet een herinnering elke 1e van de maand: "Apollo refresh exports".
