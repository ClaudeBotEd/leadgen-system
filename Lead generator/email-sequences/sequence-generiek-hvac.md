# Sequence — Generiek installatiebedrijf (multi-disciplinair)

**Doelgroep:** Installatiebedrijven met breed pakket: CV, ventilatie, sanitair, eventueel warmtepomp/zonnepanelen als bijspecialiteit. Vaak 5-50 medewerkers, generations-old familiebedrijf of overgenomen door PE.
**Pijn:** Te weinig differentiatie online, geen sterke marketing, leadflow afhankelijk van mond-tot-mond + Google. Veel concurrentie van platform-spelers.
**Verzendcadans:** dag 0, dag 3, dag 7.

---

## Email 1 — Waardepropositie (dag 0)

**Subject A:** `Vraag aan {{company_name}}: aanvragen via internet`
**Subject B:** `Voor installatiebedrijven in {{city}}: groei zonder personeel`

**Pre-header:** `Hoe komen jullie aan nieuwe klussen — en kan dat met minder werk?`

**Body:**

```
Beste team,

Korte vraag aan {{company_name}}: waar komen de meeste
nieuwe klussen vandaan — bestaande klanten, mond-tot-mond,
of online?

De installatiebedrijven die ik spreek zeggen meestal "70%
mond-tot-mond, 30% Google-toeval". Voorspelbaar is anders.

Wij bouwen voor installateurs een vaste maandelijkse stroom
gekwalificeerde aanvragen op basis van:

- Type klus (CV, ventilatie, warmtepomp, sanitair)
- Postcode/werkgebied
- Indicatie projectgrootte (geen kleine reparaties)
- Geverifieerde contactgegevens

U betaalt per aanvraag die past binnen criteria. Geen vast
maandbedrag, geen jaarcontract.

15 min koffie of via Meet? {{calendar_link}}

Met vriendelijke groet,
{{your_name}}
{{your_company}}

—
{{your_company}} | {{kvk_number}} | {{address}}
Uitschrijven: {{unsubscribe_url}}
```

---

## Email 2 — Argument / pilot (dag 3, skip bij reactie)

**Subject A:** `Re: aanvragen via internet`
**Subject B:** `Wat installateurs vaak missen aan online`

**Body:**

```
Beste team,

Vervolg op vorig bericht.

Wat ik regelmatig zie: installatiebedrijven adverteren op
Google met termen als "installateur Eindhoven", krijgen
prijsvechter-aanvragen, en concluderen "online werkt niet
voor ons".

Probleem zit niet in online — het zit in de filter. Wij
filteren aanvragen vooraf op:

- Werkelijke koopkracht (geen hobby-tuinier-projecten)
- Type klus dat jullie willen doen (geen kleine reparaties
  als jullie nieuwbouw doen)
- Realistische timing (binnen 3 maanden, niet "ooit")

Resultaat: minder aanvragen, hogere conversie naar opdracht.
Geen tijd verlies aan offertes die nooit getekend worden.

Aanbod: eerste 3 aanvragen gratis als pilot. Geen verplichting.

Open voor een gesprek? {{calendar_link}}

Met vriendelijke groet,
{{your_name}}
{{your_company}}

—
{{your_company}} | {{kvk_number}} | {{address}}
Uitschrijven: {{unsubscribe_url}}
```

---

## Email 3 — Break-up (dag 7, skip bij reactie)

**Subject A:** `Sluit ik dit voor {{company_name}}?`
**Subject B:** `Drie pogingen, dan stop ik`

**Body:**

```
Beste team,

Drie keer mailen, geen reactie. Daarmee weet ik genoeg.
Geen probleem, ik sluit het af.

Mocht het in 2026 alsnog relevant worden, of als jullie
willen testen met 5 gratis aanvragen om de kwaliteit te
beoordelen: stuur antwoord en ik kom terug.

Veel succes verder.

Met vriendelijke groet,
{{your_name}}
{{your_company}}

—
{{your_company}} | {{kvk_number}} | {{address}}
Uitschrijven: {{unsubscribe_url}}
```

---

## Niche-specifieke aanpassingen

Generieke installateurs reageren beter op concrete voorbeelden uit hun mix. Voeg in email 2 een variabele in op basis van wat Apollo/Clay als hoofdactiviteit detecteert:

| Custom field `{{specialty_focus}}` | Te vervangen tekst in email 2 |
|------------------------------------|-------------------------------|
| `cv` | "vervang CV-installaties" |
| `ventilatie` | "WTW-systemen of mechanische ventilatie" |
| `sanitair` | "complete badkamer-renovaties" |
| `warmtepomp` | "warmtepomp-installaties" |
| `nieuwbouw` | "nieuwbouw-projecten" |

Dit verhoogt relevantie en personalisatie zonder extra schrijfwerk.

---

## Reply handling

| Reactie | Antwoord-blueprint |
|---------|---------------------|
| "Wij hebben werk genoeg" | "Goed nieuws. Dan misschien interessant voor over 6 maanden — mag ik in september terugkomen?" |
| "Wat is jullie ervaring met installateurs?" | Wees eerlijk over fase: "Ik bouw nu mijn eerste case-studies op. Daarom de pilot met 5 gratis aanvragen." |
| "Hoe weet ik of het kwalitatief is?" | "Daarom de pilot — geen geld vooraf, je beoordeelt zelf op kwaliteit voor we afspreken over volume" |
| "Wij werken met [bestaand bureau]" | "Handig, ik vul aan in plaats van te vervangen. Wat is jullie grootste pijn met je huidige bron?" |
