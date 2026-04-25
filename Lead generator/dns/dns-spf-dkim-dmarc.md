# SPF, DKIM en DMARC — complete records-templates

Voor elk outreach-domein moet je 3 records configureren: SPF, DKIM en DMARC. Zonder alle drie correct ingesteld zal cold email direct in spam belanden, ongeacht hoe goed je content is.

## Achtergrond — wat doen deze records?

| Record | Doel | Verplicht voor outreach? |
|--------|------|-----------------------------|
| **SPF** (Sender Policy Framework) | Specificeert welke mail-servers namens jouw domein mogen sturen | Ja |
| **DKIM** (DomainKeys Identified Mail) | Cryptografische handtekening op elke email — bewijs dat de mail authentiek is | Ja |
| **DMARC** (Domain-based Message Authentication) | Vertelt ontvangers wat te doen als SPF/DKIM falen | Ja |
| **MX** | Specificeert welke server inkomende mail accepteert | Verplicht (anders kun je geen replies ontvangen) |
| **BIMI** | Logo in inbox (Gmail/Yahoo) | Optioneel — pas later, vereist VMC certificaat (~$1.499/jr) |

## SPF record (per domein) — exact wat je toevoegt

### Format
- **Type:** `TXT`
- **Host/Naam:** `@` (apex, het hoofddomein zelf)
- **TTL:** 3600 (1 uur) of standaard

### Waarde per provider

**Google Workspace:**
```
v=spf1 include:_spf.google.com ~all
```

**Microsoft 365:**
```
v=spf1 include:spf.protection.outlook.com -all
```

**Maildoso:**
```
v=spf1 include:spf.maildoso.com ~all
```

**Combinatie Google + extra services (bv. Mailchimp):**
```
v=spf1 include:_spf.google.com include:servers.mcsv.net ~all
```

**Belangrijke regels:**
- Je mag MAXIMUM 1 SPF-record per domein hebben (anders falen alle)
- `~all` (softfail) tijdens setup, na 30 dagen overgaan naar `-all` (strict)
- Maximum 10 DNS-lookups in totaal — als je meer providers wilt, gebruik SPF-flattening

## DKIM record (per domein, per provider)

### Format
- **Type:** `TXT`
- **Host/Naam:** `<selector>._domainkey` (vervangen met provider's selector)
- **Waarde:** lange RSA public key string (verkrijg je van je provider)

### Per provider

**Google Workspace:**

1. In Admin Console: Apps -> Google Workspace -> Gmail -> Authenticate email
2. Klik **Generate new record** -> Selector: `google` (default), Key bit length: 2048
3. Google geeft je het record terug, type:
   - Host: `google._domainkey`
   - Value: `v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8...` (lange string)
4. Plaats in DNS, wacht 24-72u voor propagatie
5. Terug in Admin Console: klik **Start authentication**

**Microsoft 365:**

1. Microsoft 365 admin -> Security -> Email & collaboration -> Policies -> DKIM
2. Selecteer je domein -> Klik **Enable**
3. Microsoft genereert 2 CNAME records (ja, CNAME niet TXT):
   - Host: `selector1._domainkey` -> waarde: `selector1-<jouw-domein-with-dashes>._domainkey.<onmicrosoft-tenant>.onmicrosoft.com`
   - Host: `selector2._domainkey` -> waarde: `selector2-<jouw-domein-with-dashes>._domainkey.<onmicrosoft-tenant>.onmicrosoft.com`
4. Plaats beide CNAME records, wacht propagatie
5. Klik nogmaals **Enable** in MS portal

**Maildoso:**

1. Maildoso dashboard -> Domain settings -> DKIM
2. Kopieer beide records (Maildoso gebruikt `mlds1` en `mlds2` selectors)
3. Plaats als TXT records:
   - Host: `mlds1._domainkey` -> Value: `v=DKIM1; k=rsa; p=MIGfMA0...`
   - Host: `mlds2._domainkey` -> Value: `v=DKIM1; k=rsa; p=MIGfMA0...`

## DMARC record (per domein)

### Format
- **Type:** `TXT`
- **Host/Naam:** `_dmarc`
- **TTL:** 3600

### Waarde — gradueel strict maken

**Fase 1 — Monitoring (eerste 14 dagen):**
```
v=DMARC1; p=none; rua=mailto:dmarc-reports@jouwagency.nl; pct=100; aspf=r; adkim=r
```

Betekent: niets blokkeren, maar wel rapporten ontvangen over auth-fails.

**Fase 2 — Quarantine (na 14 dagen, indien geen issues):**
```
v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@jouwagency.nl; pct=10; aspf=r; adkim=r
```

10% van failende mail naar spam zetten. Als geen klachten: verhoog `pct=50`, dan `pct=100`.

**Fase 3 — Reject (na 60 dagen, full lockdown):**
```
v=DMARC1; p=reject; rua=mailto:dmarc-reports@jouwagency.nl; pct=100; aspf=s; adkim=s
```

Failende mail wordt afgewezen. Strict alignment voor SPF en DKIM.

### Belangrijke parameters

| Parameter | Betekenis | Aanbevolen |
|-----------|-----------|------------|
| `p=` | Wat te doen bij fail (none/quarantine/reject) | Begin none, eindig reject |
| `rua=` | Aggregate report ontvanger (kan apart adres zijn) | `dmarc@jouwagency.nl` of dmarc.postmarkapp.com |
| `ruf=` | Forensic reports (per fail) — meestal niet ondersteund door ontvangers | Weglaten |
| `pct=` | Percentage van fails om policy op toe te passen | 100 als production |
| `sp=` | Subdomain policy | Zelfde als p= |
| `aspf=` | SPF alignment (relaxed/strict) | r (relaxed) |
| `adkim=` | DKIM alignment | r (relaxed) tijdens setup |

### DMARC report-monitoring

DMARC stuurt dagelijks XML-reports naar het `rua=` adres. Te leesbare format zetten via:
- **Postmark DMARC** (gratis): https://dmarc.postmarkapp.com — vervang `rua=mailto:dmarc-reports@...` door hun adres
- **dmarcian.com** (gratis tier): meer detail
- **Valimail Monitor** (gratis): enterprise-feel

Aanbevolen tijdens setup: Postmark voor 1-pagina overzicht.

## MX records (voor inkomende mail)

### Per provider

**Google Workspace:**
| Priority | Host | Value |
|----------|------|-------|
| 1 | @ | smtp.google.com |

(Sinds 2023 gebruikt Google 1 MX record. Oude setups met 5 records werken nog, maar nieuwe accounts krijgen alleen `smtp.google.com`.)

**Microsoft 365:**
| Priority | Host | Value |
|----------|------|-------|
| 0 | @ | <jouw-tenant>-nl.mail.protection.outlook.com |

(Vervang `<jouw-tenant>` met jouw tenant naam, krijg je in MS admin onder Domains.)

**Maildoso:**
| Priority | Host | Value |
|----------|------|-------|
| 10 | @ | mx1.maildoso.com |
| 20 | @ | mx2.maildoso.com |

## Volledige DNS-config voorbeeld (Google Workspace, domein `voorbeeldleads.nl`)

| Type | Host | Value | TTL | Doel |
|------|------|-------|-----|------|
| MX | @ | smtp.google.com | 3600 | Inkomende mail naar Google |
| TXT | @ | v=spf1 include:_spf.google.com ~all | 3600 | SPF |
| TXT | google._domainkey | v=DKIM1; k=rsa; p=MIIBIjANBgkqhk... | 3600 | DKIM |
| TXT | _dmarc | v=DMARC1; p=none; rua=mailto:dmarc@jouwagency.nl; pct=100 | 3600 | DMARC monitoring fase |
| TXT | @ | google-site-verification=Xxx... | 3600 | Google domein-eigendom (krijg je tijdens setup) |
| CNAME | mail | ghs.googlehosted.com | 3600 | Webmail-redirect (optioneel) |

## Verificatie na setup

Wacht 24-72u na DNS-changes. Check dan:

1. **MXToolBox SuperTool** — https://mxtoolbox.com/SuperTool.aspx
   - Type domeinnaam, kies "MX Lookup" -> moet correcte MX tonen
   - Switch naar "SPF Record Lookup" -> check je SPF
   - Switch naar "DMARC Record Lookup" -> check DMARC
   - DKIM check vereist selector — type `google._domainkey.voorbeeldleads.nl` als hostnaam

2. **Mail-tester.com** — https://www.mail-tester.com/
   - Stuur een test-mail naar het toonde adres
   - Krijg je 9-10/10? Goed. <8/10? Iets klopt niet, check tabbladen.

3. **Google Postmaster Tools** — https://postmaster.google.com/
   - Voeg je domein toe, verifieer
   - Wacht 1-2 weken voor data verschijnt
   - Toont reputation (Bad/Low/Medium/High) per dag

## Veelgemaakte fouten

| Fout | Symptoom | Fix |
|------|----------|-----|
| 2 SPF records | Beide falen, alle mail in spam | Combineer naar 1 record |
| `_dmarc` op het verkeerde subdomain | DMARC werkt niet | Gebruik EXACT host `_dmarc` (niet `_dmarc.example.nl`) |
| DKIM key truncated bij DNS-aanbieder | Auth fails | Splits in 2 chunks van 255 chars (de meeste DNS-systemen vereisen quoting) |
| Te lage TTL tijdens setup | Lange propagatie | Zet TTL op 300 (5 min) tijdens setup, terug naar 3600 daarna |
| Vergeten apex-record | Mail werkt niet voor `@domein.nl` | MX record op host `@` (sommige UIs noemen het "root") |
| DMARC te snel naar `p=reject` | Legitieme mail (n8n notificaties) wordt geweigerd | Begin altijd 14 dagen `p=none` |
