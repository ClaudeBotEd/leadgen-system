# Domein-strategie

## Hoeveel domeinen + mailboxen

Per Sectie 7 van het rapport en industrie best-practices voor cold outreach:

| Configuratie | Wanneer | Send capaciteit/dag |
|--------------|---------|---------------------|
| 1 domein, 1 mailbox | Alleen test | 20-30/dag |
| 1 domein, 3 mailboxen | Solo, klein volume | 100-150/dag |
| **3 domeinen, 9 mailboxen** | **Aanbevolen voor maand 1-3** | **250-450/dag** |
| 6 domeinen, 18 mailboxen | Schaalfase (>500 prospects/wk) | 500-900/dag |
| 10+ domeinen, 30+ mailboxen | Productie agency-scale | 1.000+/dag |

## Waarom meerdere domeinen?

1. **Schade-isolatie:** als 1 domein in spam komt (bv. door verkeerde campagne), blijven 2 over om mee te werken.
2. **A/B testen:** 1 domein voor variant A, 1 voor variant B — meet welke patroon beter werkt.
3. **Niche-gebaseerde branding:** `<brand>warmtepompleads.nl` voor warmtepomp-campagnes, `<brand>airco.nl` voor airco — sommige ontvangers letten op domein-relevantie.
4. **Wettelijke spreiding:** als 1 domein klacht oploopt bij ACM, valt niet alles uit.

## Hoeveel mailboxen per domein?

3 mailboxen per domein is de sweet spot:
- **Te weinig (1-2):** beperkt volume, snel als spam gemarkeerd
- **Te veel (5+):** ontvangers zien volume-patroon, sender reputation lijdt
- **3:** meest gebruikte ratio in commerciële cold outreach setups

Mailbox-namen voorbeeld:
- `info@`, `sales@`, `contact@` (generiek, look-alike voor professionele agency)

## Welke registrar?

Per rapport (Sectie 7): EUR 30/jaar voor 3 .nl-domeinen totaal.

| Registrar | Prijs .nl | Pluspunten | Minpunten |
|-----------|-----------|------------|-----------|
| **Cloudflare Registrar** | EUR 9.50/jr (at-cost) | Beste DNS UI, gratis DDoS bescherming, snelste propagatie | Geen .nl ondersteuning (nog) |
| **TransIP** | EUR 7.50/jr | NL-bedrijf, goede support in NL, ondersteunt .nl en .be | DNS UI minder modern |
| **Hostnet** | EUR 7.50/jr | NL, integreert met hosting | DNS UI verouderd |
| **Namecheap** | $10-15/jr | Goede UI, Whois privacy gratis | US-based, Whois privacy soms problematisch voor .nl |
| **Google Domains** | n.v.t. | Discontinued (overgegaan naar Squarespace) | — |

**Aanbeveling:** TransIP voor .nl/.be (NL-native, goede support). Cloudflare voor .com/.io/.app als je internationaal wilt.

## Domein-naam keuze — patroon-templates

Vermijd je hoofd-bedrijfsnaam. Pak een variant.

### Patroon 1 — service-gericht
- `<brand>leads.nl`
- `<brand>aanvragen.nl`
- `<brand>klanten.nl`

Voorbeelden: `vooruitleads.nl`, `directeaanvragen.nl`, `groeisignalen.nl`

### Patroon 2 — niche-gericht
- `<brand>installatie.nl`
- `<brand>hvac.nl`
- `<brand>energie.nl`

Voorbeelden: `slimminstallatie.nl`, `mijnenergiepartner.nl`

### Patroon 3 — generiek-zakelijk
- `<brand>nl.nl` (dubbel-NL klinkt vreemd, vermijden)
- `<brand>direct.nl`
- `<brand>partner.nl`

Voorbeelden: `groeipartner.nl`, `ontwikkelingdirect.nl`

### Patroon 4 — voorletters/afkorting
- `aiL.nl`, `agL.nl` — kort, makkelijk te onthouden
- Maar te kort kan goedkoop ogen

## Welke TLDs gebruiken?

| TLD | Verzendbaarheid | Kost | Wanneer |
|-----|-----------------|------|---------|
| .nl | Hoog (NL-context) | EUR 7-10/jr | NL-prospects |
| .be | Hoog (BE-context) | EUR 8-12/jr | BE-prospects |
| .com | Hoog (universeel) | EUR 10-15/jr | Internationale uitstraling |
| .io | Medium-hoog | EUR 30-40/jr | Tech-sector |
| .nl.com / .eu | Medium | EUR 5-15/jr | Niet aanbevolen |
| .top, .xyz, .info | LAAG | EUR 1-5/jr | NIET gebruiken — bekende spam-TLDs |

**Aanbeveling voor NL/BE focus:** 2x .nl + 1x .be (of 3x .nl).

## Mailbox-naming conventies

Per mailbox, 3 stijlen om te kiezen:

### Stijl 1 — generiek (BEST voor compliance)
```
info@<domein>.nl
sales@<domein>.nl
contact@<domein>.nl
```

### Stijl 2 — persona-gebonden (geeft "echte mens" gevoel)
```
jan@<domein>.nl
sandra@<domein>.nl
peter@<domein>.nl
```

LET OP: persona-gebonden adressen zijn juridisch GEEN generieke adressen voor de ontvanger. Voor cold email naar info@-prospects mag dit; maar het persona-adres moet wel matchen met een echte verantwoordelijke (jouw eigen naam of een echt teamlid).

### Stijl 3 — afdelings-gebonden
```
support@<domein>.nl
team@<domein>.nl
office@<domein>.nl
```

**Aanbeveling maand 1-3:** stijl 1 (generiek) of stijl 2 met je echte voornaam. Stijl 2 met fake namen is misleidend en niet conform GDPR Art. 13 (informatieplicht over de identiteit van de verantwoordelijke).

## Forwarding inbox

Alle 9 mailboxen zouden moeten doorsturen naar 1 centrale inbox waar JIJ de antwoorden leest.

In Google Workspace: per mailbox -> Settings -> Forwarding -> add `info@jouwagency.nl` -> klik "Forward a copy" + "Keep Gmail's copy".

In Microsoft 365: Outlook -> Rules -> Forward all to `info@jouwagency.nl`.

In Maildoso: dashboard -> per mailbox -> Forwarding -> centraal adres.

Reden: je wil snel reply detecteren zonder 9 inboxen te hoeven openen.

## Inkomende-mail filter

Stel in jouw centrale inbox (`info@jouwagency.nl`) een filter in:

- Van: `info@<domein>.nl OR sales@<domein>.nl OR contact@<domein>.nl OR ...`
- Label: `cold-email-replies`
- Skip inbox: NEE — je wilt dit zien

Reply-time matters: per `crm/pipeline-stages.md` SLA, NEW->CONTACTED moet binnen 24u.
