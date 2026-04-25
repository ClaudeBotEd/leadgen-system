# Email warmup — 14-dagen procedure

Per Sectie 7 van het rapport (Week 1-2): "Warmup starten — minimaal 14 dagen warmup voor je eerste campagne stuurt."

## Wat is warmup?

Een nieuwe email-mailbox heeft 0 reputation bij Gmail/Outlook. Als je direct 100 cold emails stuurt, ga je in spam. Warmup bouwt geleidelijk reputation op door:

1. Geleidelijk volume opbouwen (5/dag -> 50/dag in 14 dagen)
2. Hoge open-rate simuleren (warmup-tools beantwoorden je mails automatisch)
3. Reply-rate simuleren (5-15% replies binnen het warmup-netwerk)
4. Spam-folder rescue (warmup-tools markeren mails uit spam terug naar inbox)

## Tools

| Tool | Prijs | Pluspunten | Minpunten |
|------|-------|------------|-----------|
| **Instantly Warmup** | Gratis bij Instantly Growth ($37.60/mo) | Geintegreerd met sequences | Heeft eigen netwerk (kleiner) |
| **Smartlead Warmup** | Gratis bij Smartlead ($32.50/mo) | Groot netwerk | Vergelijkbaar |
| **Lemwarm** (Lemlist) | $29/mo standalone | Groot netwerk | Aparte tool |
| **Mailwarm** | $59/mo standalone | Groot netwerk | Apart van sender tool |
| **Warmup Inbox** | $14/mo | Goedkoopste standalone | Klein netwerk |

**Aanbeveling:** Instantly Warmup gebruiken — komt geintegreerd met Instantly Growth ($37.60/mnd) dat je toch al hebt.

## 14-dagen schema (Instantly default)

Instantly's default schema (per mailbox):

| Dag | Verzonden warmup-mails/dag | Cumulatief |
|-----|----------------------------|------------|
| 1 | 4 | 4 |
| 2 | 6 | 10 |
| 3 | 8 | 18 |
| 4 | 10 | 28 |
| 5 | 12 | 40 |
| 6 | 14 | 54 |
| 7 | 16 | 70 |
| 8 | 18 | 88 |
| 9 | 20 | 108 |
| 10 | 22 | 130 |
| 11 | 24 | 154 |
| 12 | 26 | 180 |
| 13 | 28 | 208 |
| 14 | 30 | 238 |

Na dag 14: stable warmup mode = 30/dag continu blijven sturen, ook als je echte campagnes draait.

## Instellingen in Instantly

1. Instantly -> **Email Accounts** -> klik mailbox
2. Tab **Warmup** -> Enable
3. Settings:
   - **Total emails to send per day:** Auto (volgt schema boven)
   - **Reply rate:** 30% (default — Instantly genereert auto-replies binnen warmup-netwerk)
   - **Increment per day:** 2 (default)
   - **Warmup tag:** laat default
4. Save

Doe dit voor alle 9 mailboxen.

## Wat je tijdens warmup NIET moet doen

- **Niet starten met je echte campagne voor dag 14**
- **Niet de mailbox handmatig gebruiken voor cold mails** (kan reputation crashen)
- **Niet veel test-emails verzenden naar jezelf** (Gmail ziet patroon)
- **Niet het wachtwoord wijzigen tijdens warmup** (breekt warmup-flow)
- **Niet 2FA uitschakelen** (Google ziet dit als security regression)
- **Niet de mailbox suspenderen of pausen** (warmup ratio verloren)

## Hoe weet je of warmup goed loopt?

Na 7 dagen, check in Instantly Email Accounts:

| Metric | Goed | Probleem |
|--------|------|----------|
| Sent emails | matcht schema (~70 voor dag 7) | <50 = warmup gepauzeerd ergens |
| Inbox placement | >95% | <90% = mailbox nog niet "vertrouwd" |
| Reply rate (warmup-mails) | 25-40% | <20% = warmup-netwerk werkt niet voor jou |
| Spam folder hits | <5% | >10% = mailbox al gemarkeerd, mogelijk reset nodig |

Bij problemen: pauseer warmup, check DNS records met mxtoolbox, herstart na fix.

## Externe verificatie tijdens warmup

Wekelijks tijdens warmup-fase:

1. Stuur een test-mail vanuit je warmup-mailbox naar `https://www.mail-tester.com/` (krijg je een uniek adres bij elk bezoek)
2. Klik "check your score" op die pagina
3. Doel: 9/10 of hoger. Onder 8/10 = iets klopt niet, fix voor je echte campagne start.

## Warmup tijdens productie

Ook na dag 14 blijft warmup ALTIJD aan, parallel met je echte campagnes. Reden: continu reputation onderhoud.

In Instantly: warmup blijft 30/dag, jouw echte sends komen daar bovenop tot dagmax (50-100/dag). Totaal per mailbox: 80-130/dag aan uitgaande mails.

## Wanneer warmup opnieuw doen?

- Na **30+ dagen pauze** met de mailbox: doe 7-dagen mini-warmup voor je weer cold emails stuurt
- Na een **bounce-spike** (>5% in 1 week): pauseer cold campaign, doe 14-dagen extra warmup
- Na **wachtwoord wijziging**: 3-dagen mini-warmup (provider ziet auth-pattern als security event)
- **Nieuw domein**: altijd 14-dagen volledige warmup
