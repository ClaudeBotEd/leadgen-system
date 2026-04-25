# Verification tools — DNS, deliverability, reputation

## Tools per use-case

### DNS records check

| Tool | URL | Wat check je |
|------|-----|---------------|
| **MXToolBox SuperTool** | https://mxtoolbox.com/SuperTool.aspx | MX, SPF, DKIM, DMARC, blacklists, reverse DNS |
| **DNSChecker** | https://dnschecker.org/ | Wereldwijde propagatie van DNS-records (per regio) |
| **dig** (CLI) | `dig TXT _dmarc.voorbeeldleads.nl +short` | Snelle CLI-check |
| **nslookup** (CLI) | `nslookup -type=TXT voorbeeldleads.nl` | Cross-platform check |

### Deliverability score

| Tool | URL | Frequentie |
|------|-----|------------|
| **Mail-Tester** | https://www.mail-tester.com/ | Wekelijks per mailbox |
| **GlockApps** | https://glockapps.com/ | Maandelijks |
| **MailReach Spam Test** | https://www.mailreach.co/spam-test | Per campagne-kickoff |

### Reputation monitoring

| Tool | URL | Frequentie |
|------|-----|------------|
| **Google Postmaster Tools** | https://postmaster.google.com/ | Dagelijks (data per week) |
| **Microsoft SNDS** | https://sendersupport.olc.protection.outlook.com/snds/ | Dagelijks |
| **Cisco Talos** | https://talosintelligence.com/reputation_center | Per maand |
| **Sender Score** | https://www.senderscore.org/ | Maandelijks |

### Blacklist check

| Tool | URL | Doel |
|------|-----|------|
| **MultiRBL** | https://multirbl.valli.org/ | Check 100+ blacklists tegelijk |
| **MXToolBox Blacklist** | https://mxtoolbox.com/blacklists.aspx | Check 30 grootste blacklists |
| **Barracuda Reputation** | https://www.barracudacentral.org/lookups | Specifiek Barracuda |

## Checklist: complete domein-audit (15 min)

Voer deze 5 stappen uit per outreach-domein, vooral als deliverability daalt.

### Stap 1 — DNS records
1. Ga naar https://mxtoolbox.com/SuperTool.aspx
2. Type je domein in zoekbalk
3. Linker dropdown -> kies sequentieel:
   - **MX Lookup** -> verwacht `smtp.google.com` (Google) of equivalent
   - **SPF Record Lookup** -> verwacht 1 record met juiste include
   - **DMARC Lookup** -> verwacht beleid (none/quarantine/reject)
4. Voor DKIM (handmatig in URL):
   - `https://mxtoolbox.com/SuperTool.aspx?action=dkim:google._domainkey.<jouw-domein>`

Alle 4 moeten groen zijn.

### Stap 2 — Mail-tester (per mailbox)
1. Open https://www.mail-tester.com/ in privemodus (niet ingelogd)
2. Kopieer het toonde adres `test-xyz@mail-tester.com`
3. Login op je outreach-mailbox (bv `info@voorbeeldleads.nl`)
4. Stuur een mail naar dat adres met subject "test" en body "test deliverability check"
5. Op mail-tester.com -> "Then check your score"
6. Doel: 9-10/10
7. Als <8/10: scroll naar de tabbladen, fix wat rood is

### Stap 3 — Blacklist check
1. https://multirbl.valli.org/
2. Type domein -> Run
3. Wacht ~30s
4. Check of er ENIGE blacklist op rood staat
5. Als ja: noteer welke -> ga naar de site van die blacklist -> request removal (vaak gratis 1x per blacklist)

### Stap 4 — Google Postmaster (alleen Google Workspace)
1. https://postmaster.google.com/
2. Open jouw domein
3. Check tabs:
   - **Spam rate**: <0.3% goed
   - **Domain reputation**: Medium of High (Bad/Low = problem)
   - **IP reputation**: zelfde
   - **Authentication**: 100% pass
   - **Encryption**: 100% TLS

Data is altijd 24-72u oud — check trends, niet snapshot.

### Stap 5 — Smartlead/Instantly inbox placement
In je sender tool:
1. **Email Accounts** -> klik mailbox
2. Tab **Health** of **Reputation**
3. Check Instantly's eigen inbox-placement-test (niet 100% accuraat maar goede leading indicator)

## CLI snippets voor snelle checks

```bash
# SPF
dig TXT voorbeeldleads.nl +short | grep "v=spf1"

# DMARC
dig TXT _dmarc.voorbeeldleads.nl +short

# DKIM (Google)
dig TXT google._domainkey.voorbeeldleads.nl +short

# MX
dig MX voorbeeldleads.nl +short

# Reverse DNS (PTR) — alleen relevant als je eigen mailserver runt
host -t PTR <jouw-server-IP>
```

Snelle bash-script om alles tegelijk te checken:

```bash
#!/usr/bin/env bash
# Sla op als check-domain.sh, chmod +x, gebruik: ./check-domain.sh voorbeeldleads.nl
DOMAIN="${1:?Domain required}"

echo "=== MX records ==="
dig MX "$DOMAIN" +short

echo -e "\n=== SPF record ==="
dig TXT "$DOMAIN" +short | grep "v=spf1"

echo -e "\n=== DMARC record ==="
dig TXT "_dmarc.$DOMAIN" +short

echo -e "\n=== DKIM (google selector) ==="
dig TXT "google._domainkey.$DOMAIN" +short

echo -e "\n=== DKIM (mlds1 selector — Maildoso) ==="
dig TXT "mlds1._domainkey.$DOMAIN" +short

echo -e "\n=== Open Mail-Tester to test deliverability ==="
echo "https://www.mail-tester.com/"

echo -e "\n=== Check blacklists ==="
echo "https://multirbl.valli.org/lookup/$DOMAIN.html"
```

## Cadans

| Wat | Frequentie |
|-----|------------|
| MXToolBox check | Bij elke DNS-wijziging |
| Mail-tester | Wekelijks tijdens warmup, daarna per campagne-start |
| Postmaster Tools dashboard | Dagelijks visueel scannen |
| Blacklist check | Wekelijks of bij deliverability-drop |
| Mailreach spam test | Voor elke nieuwe campagne (volume change of nieuwe content) |
| Reputation review | Maandelijks: kijk trend over 4 weken |

## Wat te doen bij rode vlaggen

| Symptoom | Eerste actie | Volgende stap als niet opgelost |
|----------|--------------|----------------------------------|
| Mail-tester score <7 | Check rood-gemarkeerde tabbladen | Pauseer campaign, fix DNS |
| Google Postmaster "Bad" reputation | Stop campaign 7 dagen | Re-warmup mailbox 14 dagen |
| Op blacklist | Request removal | Switch naar nieuw domein |
| Bounce rate >5% | Schoon lijst (verwijder slechte adressen) | Pauseer, test mailbox-by-mailbox |
| Reply rate <1% | Subject + body herzien | Mogelijk inbox-placement issue, check spam |
