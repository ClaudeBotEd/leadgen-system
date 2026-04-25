# Pipeline stages — definitief

Geldig voor zowel HubSpot (Lead Status enum) als Close (Lead Statuses).

## Visuele flow

```
                                 ┌──> NOT_QUALIFIED (lost)
                                 │
NEW ──> CONTACTED ──> MEETING ──┼──> PILOT_DISCUSSION ──> PILOT_RUNNING ──> PROPOSAL_OUT ──┬──> CUSTOMER (won)
                                 │                                                          │
                                 └──> NOT_INTERESTED (lost)                                 └──> NOT_INTERESTED (lost)

                                 OPTED_OUT (kan vanuit elke stage)
```

## Stages in detail

### NEW
- **Wanneer:** lead binnen via landingspagina-form OF cold-email reply
- **Set door:** n8n workflow (auto) of handmatig
- **Auto-actie:** notificatie naar agency, bevestigings-email naar lead
- **Volgende stap:** binnen 24u contact opnemen (anders triggert follow-up workflow)
- **Exit:** een van: CONTACTED / NOT_QUALIFIED / OPTED_OUT
- **SLA:** 24 uur tot eerste contact

### CONTACTED
- **Wanneer:** je hebt gereageerd (call, mail, LinkedIn — handmatig)
- **Set door:** handmatig na verzending van eerste antwoord
- **Auto-actie:** geen
- **Volgende stap:** kwalificatie of meeting plannen
- **Exit:** MEETING / NOT_INTERESTED / NOT_QUALIFIED / OPTED_OUT
- **SLA:** binnen 7 dagen vervolgactie of stage-wisseling, anders flag in CRM

### MEETING_SCHEDULED
- **Wanneer:** een intake-call is gepland (Cal.com / Calendly link aangevraagd of telefonisch afgesproken)
- **Set door:** handmatig
- **Auto-actie:** geen (Cal.com agendaboeking apart)
- **Volgende stap:** call uitvoeren, daarna stage update
- **Exit:** PILOT_DISCUSSION (call ging goed) / NOT_QUALIFIED (past niet) / NOT_INTERESTED (call wel, geen vervolg)
- **SLA:** call binnen 14 dagen, anders contact opnemen

### PILOT_DISCUSSION
- **Wanneer:** call gehad, criteria besproken, gaat naar pilot
- **Set door:** handmatig na meeting
- **Auto-actie:** geen
- **Volgende stap:** 3 gratis leads leveren in vervolg-stage
- **Exit:** PILOT_RUNNING (klant zegt ja) / NOT_INTERESTED (klant haakt af na bedenktijd)
- **SLA:** 3 dagen tot ja/nee

### PILOT_RUNNING
- **Wanneer:** eerste van 3 gratis leads is geleverd
- **Set door:** handmatig of via n8n trigger als je lead-levering automatiseert
- **Auto-actie:** evt. wekelijkse statusmail (handmatig of via n8n)
- **Volgende stap:** alle 3 leads geleverd, daarna evaluatie
- **Exit:** PROPOSAL_OUT (alle 3 geleverd) / NOT_INTERESTED (klant trekt zich terug) / NOT_QUALIFIED (criteria bleken onhaalbaar)
- **SLA:** alle 3 leads binnen 30 dagen

### PROPOSAL_OUT
- **Wanneer:** evaluatie call gedaan, voorstel voor maandcontract verstuurd
- **Set door:** handmatig
- **Auto-actie:** geen
- **Volgende stap:** wachten op acceptatie, opvolgen elke 5 werkdagen
- **Exit:** CUSTOMER (akkoord + betaling) / NOT_INTERESTED (afwijzing)
- **SLA:** maximum 21 dagen sales-cycle, daarna evt. naar NOT_INTERESTED

### CUSTOMER (won)
- **Wanneer:** eerste betaling ontvangen
- **Set door:** handmatig na zien van Stripe/bankafschrift
- **Auto-actie:** verwijder uit alle outbound sequences (NIET meer prospecten)
- **Volgende stap:** delivery, monthly review meeting plannen
- **SLA:** n.v.t.

### NOT_QUALIFIED (lost)
- **Wanneer:** lead past niet binnen je niche/werkgebied/budget
- **Set door:** handmatig na kwalificatie
- **Auto-actie:** verwijder uit sequences
- **Notitie verplicht:** waarom niet kwalificerend (gebruik dit later om Apollo-filters te verfijnen)
- **Re-engagement:** na 12 maanden mag je opnieuw contact zoeken

### NOT_INTERESTED (lost)
- **Wanneer:** lead heeft expliciet afgehaakt op enig moment
- **Set door:** handmatig
- **Auto-actie:** verwijder uit sequences
- **Re-engagement:** na 6 maanden mag je opnieuw contact zoeken — tenzij OPTED_OUT

### OPTED_OUT (lost, terminal)
- **Wanneer:** lead heeft "stuur niet meer" gezegd of unsubscribe gebruikt
- **Set door:** handmatig OF n8n als je een unsubscribe-webhook hebt
- **Auto-actie:** toevoegen aan suppressielijst, verwijderen uit alle sequences
- **Re-engagement:** NOOIT meer email zonder nieuwe expliciete opt-in

## Stage progressie regels

1. **Skip-back is toegestaan** behalve vanuit terminal stages (CUSTOMER, OPTED_OUT)
2. **Notitie verplicht** bij elke move naar een lost-stage (NOT_QUALIFIED, NOT_INTERESTED)
3. **Datum-stempel automatisch** via HubSpot/Close ingebouwde stage-history
4. **Multi-pipeline** niet nodig in maand 1-3 — alle leads in een pipeline

## Reporting

Bouw deze 5 reports in HubSpot/Close:

| Rapport | Definitie | Frequency |
|---------|-----------|-----------|
| Funnel conversie | Aantal leads per stage / aantal in NEW (afgelopen 30 dagen) | Weekly |
| Time-to-CONTACTED | Mediaan uren tussen NEW en CONTACTED | Weekly |
| Win rate | CUSTOMER / (CUSTOMER + NOT_INTERESTED + NOT_QUALIFIED) afgelopen 90 dagen | Monthly |
| Drop-off per stage | Welke stage heeft hoogste % naar lost | Monthly |
| Source effectiviteit | Win rate per `original_source` | Monthly |

## Anti-patterns (NIET doen)

- Niet alle replies automatisch op CONTACTED zetten — out-of-office mails zijn geen contact
- Niet OPTED_OUT herzien onder druk — terminal is terminal
- Niet stage skippen ("we doen direct PROPOSAL") — je verliest funnel-data
- Niet op CUSTOMER zetten voor de eerste betaling rond is — anders vertekenen forecasts
