# Email-provider setup — Google Workspace, Microsoft 365, Maildoso

Drie volledige walkthroughs. Kies er 1 — niet alle drie tegelijk.

## Beslissingsmatrix

| Criterium | Google Workspace | Microsoft 365 | Maildoso |
|-----------|------------------|---------------|----------|
| Prijs/mailbox/maand | $6 (~EUR 5.50) | $6 (Business Basic) of $12.50 (Business Standard) | $4 |
| Setup-complexiteit | Medium | Hoog (admin center vol opties) | Laag |
| Reputation voor cold email | Hoog | Medium-hoog | Medium |
| EU-dataresidentie | Op aanvraag (tier-up nodig) | Ja (EU-only datacenter optie) | Ja (EU-server) |
| Webmail UI | Gmail (bekend) | Outlook (corporate) | Basic |
| Inkomende mail forwarding | Native | Native | Native |
| Aansluiting Instantly | Native (OAuth) | Native (OAuth) | IMAP/SMTP |
| Aansluiting Smartlead | Native | Native | Native |
| Wanneer kiezen | Default | Bestaand MS-stack | Pure cold-email focus |

**Aanbeveling:** Google Workspace voor maand 1-3 (default). Switch naar Maildoso als je >18 mailboxen wilt en kostenbesparing prioriteit krijgt.

---

## Google Workspace — volledig setup

### Stap 1 — Account aanmaken

1. Ga naar https://workspace.google.com/
2. Klik **Get started**
3. Bedrijfsnaam: jouw agency-naam
4. Aantal medewerkers: kies "1" als het alleen jou is
5. Land: Netherlands
6. Domeinnaam: kies "Use a domain I already own" -> vul bv `voorbeeldleads.nl` in
7. Volg de wizard tot je in de Admin Console bent

### Stap 2 — Verifieer domein-eigendom

1. Admin Console -> linker menu -> **Account** -> **Domains**
2. Klik je domein -> **Verify**
3. Google geeft een TXT-record. Voorbeeld:
   - Host: `@`
   - Value: `google-site-verification=xxxxxxxxxxx`
4. Plaats in DNS bij je registrar (TransIP/Cloudflare)
5. Wacht 5-30 min, klik **Verify** in Admin Console

### Stap 3 — Voeg MX records toe

Volg `dns-spf-dkim-dmarc.md` -> sectie "Google Workspace MX records":
- Priority 1, Host @, Value `smtp.google.com`

### Stap 4 — Maak 3 mailboxen aan

1. Admin Console -> **Directory** -> **Users** -> **Add new user**
2. Maak `info`, `sales`, `contact`:
   - First name: bv `Info`
   - Last name: `Team`
   - Primary email: `info@voorbeeldleads.nl`
   - Tijdelijk wachtwoord: Generate
3. Herhaal voor `sales` en `contact`
4. Bewaar wachtwoorden in 1Password / Bitwarden

### Stap 5 — Activeer DKIM

1. Admin Console -> **Apps** -> **Google Workspace** -> **Gmail**
2. Scroll naar **Authenticate email**
3. Selecteer je domein
4. Klik **Generate new record**
5. Selector: laat default `google`, Key bit length: `2048`
6. Kopieer het TXT-record dat verschijnt
7. Plaats in DNS:
   - Host: `google._domainkey`
   - Value: heel lange string die begint met `v=DKIM1; k=rsa; p=MIIBIjAN...`
8. Wacht 24-72u
9. Terug in stap 2 boven: klik **Start authentication**

### Stap 6 — Voeg SPF en DMARC toe

Volg `dns-spf-dkim-dmarc.md`:
- SPF: `v=spf1 include:_spf.google.com ~all` (host @)
- DMARC: `v=DMARC1; p=none; rua=mailto:dmarc@jouwagency.nl; pct=100` (host _dmarc)

### Stap 7 — Per mailbox: enable IMAP voor Instantly

1. Login als de gebruiker (bv `info@voorbeeldleads.nl`) op gmail.com
2. Settings (tandwiel) -> See all settings -> **Forwarding and POP/IMAP**
3. Enable IMAP
4. Save

### Stap 8 — App Password voor Instantly

Met 2FA enabled (verplicht voor Google Workspace cold-email accounts):

1. Login als gebruiker -> https://myaccount.google.com/security
2. **2-Step Verification** -> turn on
3. **App passwords** -> create new
4. App: Mail, Device: Other (custom name = "Instantly")
5. Kopieer het 16-character wachtwoord
6. In Instantly: Add account -> Custom IMAP/SMTP -> gebruik App password (NIET je gewone wachtwoord)

Herhaal stap 7-8 voor alle 3 mailboxen op dit domein. Daarna voor de andere 2 domeinen.

### Stap 9 — Forwarding naar centrale inbox

Per mailbox in Gmail:
1. Settings -> Forwarding and POP/IMAP -> Add forwarding address: `info@jouwagency.nl`
2. Verifieer via mail
3. Choose: "Forward a copy of incoming mail to..." -> `info@jouwagency.nl` -> "Keep Gmail's copy"

---

## Microsoft 365 — volledig setup

### Stap 1 — Account aanmaken

1. https://www.microsoft.com/nl-nl/microsoft-365/business/microsoft-365-business-basic
2. Kies **Buy now** -> Business Basic ($6/user/mnd) of Business Standard ($12.50)
3. Volg wizard
4. Bij domeinkeuze: "Use a domain you already own" -> `voorbeeldleads.nl`

### Stap 2 — Verifieer domein

1. Admin center: https://admin.microsoft.com/
2. **Settings** -> **Domains** -> **Add domain**
3. MS toont een TXT-record voor verificatie:
   - Host: `@`
   - Value: `MS=ms12345678`
4. Plaats in DNS, wacht propagatie, klik **Verify**

### Stap 3 — MX, SPF, DKIM, DMARC

Per `dns-spf-dkim-dmarc.md`:
- MX: `<jouw-tenant>-nl.mail.protection.outlook.com` (host @, priority 0)
- SPF: `v=spf1 include:spf.protection.outlook.com -all`
- DKIM: 2 CNAME records (selector1, selector2). Microsoft genereert deze in Security center -> Email & collaboration -> Policies -> DKIM
- DMARC: zelfde als Google Workspace template

### Stap 4 — Maak 3 mailboxen aan

1. Admin center -> **Users** -> **Active users** -> **Add a user**
2. Maak info, sales, contact aan
3. Wijs de Business Basic license toe (3x = $18/mnd voor 3 mailboxen op 1 domein)

### Stap 5 — App passwords / OAuth voor Instantly

Microsoft 365 stopt geleidelijk met App Passwords. Voor Instantly:
- **Optie A (aanbevolen):** Gebruik OAuth — Instantly heeft native MS365 integratie
- **Optie B:** Disable Modern Auth en gebruik App Password (deprecated, niet doen)

In Instantly: Add account -> Microsoft 365 -> OAuth flow -> grant permissions.

### Stap 6 — Forwarding

Outlook (web) -> Settings -> Mail -> Forwarding -> Enable -> centrale adres.

---

## Maildoso — volledig setup

Maildoso is door Woodpecker gemaakt, specifiek voor cold email. $4/mailbox/mo.

### Stap 1 — Account aanmaken

1. https://maildoso.com/
2. Sign up -> kies aantal mailboxen (start met 9 voor 3 domeinen)
3. $4 x 9 = $36/mnd, $432/jr met annual billing

### Stap 2 — Voeg domeinen toe

1. Maildoso dashboard -> **Domains** -> **Add domain**
2. Type domeinnaam, bv `voorbeeldleads.nl`
3. Maildoso toont alle DNS-records die je moet zetten:
   - MX: `mx1.maildoso.com` (priority 10), `mx2.maildoso.com` (priority 20)
   - SPF: `v=spf1 include:spf.maildoso.com ~all`
   - DKIM: 2 TXT records met selectors `mlds1` en `mlds2`
   - DMARC: standaard template

### Stap 3 — Wacht op verificatie

Maildoso checkt automatisch elke 15 min. Status in dashboard: "Verifying" -> "Active".

### Stap 4 — Maak 3 mailboxen per domein

In dashboard: domein klikken -> **Add mailbox** -> info, sales, contact.

### Stap 5 — Connect met Instantly

Maildoso geeft per mailbox IMAP/SMTP credentials:
- IMAP host: `imap.maildoso.com`, port 993, SSL
- SMTP host: `smtp.maildoso.com`, port 465, SSL
- Username: full email address
- Password: gegenereerd (laat Maildoso genereren)

In Instantly: Add account -> Custom IMAP/SMTP -> vul bovenstaande in.

### Stap 6 — Forwarding

Maildoso dashboard -> per mailbox -> **Forwarding** -> centrale adres.

---

## Na setup — checklist

- [ ] 9 mailboxen werkend (kun je inloggen op alle 9?)
- [ ] Inkomende test-mail naar elk adres komt aan in centrale inbox
- [ ] Uitgaande test-mail vanaf elk adres bereikt jouw persoonlijke gmail (geen spam)
- [ ] mxtoolbox.com bevestigt MX, SPF, DKIM, DMARC voor alle 3 domeinen
- [ ] mail-tester.com geeft 9-10/10 score voor elk domein
- [ ] Alle 9 mailboxen toegevoegd in Instantly
- [ ] Warmup gestart in Instantly (zie `warmup-procedure.md`)
