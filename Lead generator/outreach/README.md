# Outreach — Personalisatie + Templates

> Combineer een leads CSV met een template -> klare berichten in `outbox/`. Geen automatische verzending. Je verstuurt zelf vanuit eigen Gmail/Outlook.

## Quickstart

```bash
cd "/Users/claudebot/Lead generator/outreach"

python personalize.py \
  --leads ../crm-light/data/leads.csv \
  --template templates/email/warmtepomp_v1.txt \
  --signature "Je naam" \
  --from-email "jij@jouwbedrijf.nl" \
  --from-company "JouwBedrijf B.V." \
  --filter-stage new \
  --min-score 50 \
  --max 25
```

Output: `outbox/batch_YYYYMMDD.txt`

Open dat bestand, kopieer elk bericht naar je eigen mail-tool, en verstuur.

## CLI opties

| Flag | Wat | Voorbeeld |
|---|---|---|
| `--leads` | Pad naar leads CSV | `../crm-light/data/leads.csv` |
| `--template` | Pad naar template | `templates/email/warmtepomp_v1.txt` |
| `--output` | Output bestand | `outbox/batch.txt` |
| `--signature` | Vervang `{{your_name}}` | `"Jan Jansen"` |
| `--from-email` | Vervang `{{your_email}}` | `jij@jouwbedrijf.nl` |
| `--from-company` | Vervang `{{your_company}}` | `JouwBedrijf B.V.` |
| `--filter-stage` | Alleen leads in deze stage | `new` |
| `--filter-niche` | Alleen niche | `warmtepomp` |
| `--filter-country` | NL of BE | `NL` |
| `--min-score` | Min intent_score | `60` |
| `--max` | Max berichten in batch | `25` |
| `--skip-already-contacted` | Skip leads met `last_contacted_at` | (flag) |
| `--eml` | Schrijf .eml files | (flag) |

## Template syntax

```
SUBJECT: <subject regel hier>

<body hier met placeholders>
```

### Placeholders

| Placeholder | Bron | Voorbeeld |
|---|---|---|
| `{{first_name}}` | Eerste woord uit `contact_name`, fallback "daar" | `Jan` |
| `{{company_name}}` | leads.csv `company_name` | `Voorbeeld BV` |
| `{{city}}` | leads.csv `city` | `Amsterdam` |
| `{{country}}` | leads.csv `country` | `NL` |
| `{{niche}}` | leads.csv `niche` | `warmtepomp` |
| `{{phone}}` | leads.csv `phone` | `+31 20 1234567` |
| `{{your_name}}` | --signature | `Jan Jansen` |
| `{{your_email}}` | --from-email | `jan@jouwbedrijf.nl` |
| `{{your_company}}` | --from-company | `JouwBedrijf B.V.` |
| `{{today}}` | vandaag | `25-04-2026` |
| `{{domain_short}}` | domein zonder TLD | `voorbeeld` |

### Special syntax

```
{{ifempty:company_name|jullie bedrijf}}    fallback als company_name leeg is
{{rand:dinsdag|woensdag|donderdag}}        random keuze (per lead anders)
```

## Beschikbare templates

```
templates/
├── email/
│   ├── warmtepomp_v1.txt          ← cold email v1 (uitleg + 0-risk)
│   ├── warmtepomp_v2.txt          ← variant 2 (volume-getallen, korter)
│   ├── warmtepomp_followup_v1.txt ← 3-day no-reply follow-up
│   ├── airco_v1.txt               ← airco specifiek (zomer-piek)
│   └── zonnepanelen_v1.txt        ← zonnepanelen (anti-massa pitch)
└── dm/
    ├── linkedin_connect_v1.txt    ← LinkedIn connection request (300 char)
    ├── linkedin_v1.txt            ← LinkedIn DM na accept
    └── facebook_v1.txt            ← Facebook Messenger naar business page
```

## Workflow

```
1. crm-light/data/leads.csv   <- bron (uit lead-radar of import)
        |
        v
2. python personalize.py --leads ... --template ...
        |
        v
3. outbox/batch_YYYYMMDD.txt  <- klare berichten
        |
        v
4. Kopieer naar Gmail/Outlook + verstuur (max 30/dag/mailbox)
        |
        v
5. python ../crm-light/crm.py log <id> --type email_sent --content "v1"
        |
        v
6. Reply ontvangen? python ../crm-light/crm.py move <id> replied
```

## Eigen template maken

1. Kopieer een bestaand template:
   ```bash
   cp templates/email/warmtepomp_v1.txt templates/email/mijn_eigen_v1.txt
   ```

2. Edit met je eigen tekst, gebruik placeholders waar je wil personaliseren.

3. Test met 1 lead:
   ```bash
   python personalize.py \
     --leads ../crm-light/data/leads.csv \
     --template templates/email/mijn_eigen_v1.txt \
     --max 1 \
     --output /tmp/test.txt
   cat /tmp/test.txt
   ```

## Volume regels (NL/BE wetgeving + deliverability)

- **Max 30 cold emails per mailbox per dag**
- **Max 3 follow-ups per lead** (NL Telecommunicatiewet, BE Wet Marktpraktijken)
- **Geen consumenten** (B2B opt-out only)
- **Unsubscribe optie** (de "stuur 'nee' en je hoort niets meer" regel in templates voldoet)
- **Bewaar bewijs van opt-out** in `crm-light/data/activities.csv` met `type=note`

## Goede praktijk

1. A/B test 2 templates per niche met 25 emails elk, vergelijk reply rate
2. Beste tijden NL/BE: dinsdag/woensdag/donderdag 9-11u of 14-16u
3. 1 zin specifiek over hun website (handmatig) verhoogt reply rate 3-5x
4. Stop bij 3 emails zonder reply
5. Goldmine: leads die op LinkedIn DM antwoorden, NIET op email

## Troubleshooting

| Probleem | Fix |
|---|---|
| Lege output | Check filters - verlaag `--min-score`, leeg `--filter-stage` |
| Placeholders niet vervangen | Check spelling - `{{first_name}}` niet `{{firstName}}` |
| Subject ontbreekt | Eerste regel moet `SUBJECT: ...` zijn |
| Emails ontbreken | Filter `has_email=False` zit erin |
| Excel breekt UTF-8 | Open `.txt` in editor, niet Excel |
