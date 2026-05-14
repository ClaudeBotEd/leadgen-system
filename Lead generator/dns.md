# DNS / Email Infrastructuur

Cold-email infrastructuur-laag. Bevat: domein-strategie (3 outreach-domeinen, ~EUR 30/jr), SPF/DKIM/DMARC templates, provider setup (Google Workspace vs Maildoso), verificatie tools (mxtoolbox + mail-tester) en de 14-daagse warmup-procedure. Vereiste fundering voor [[email-sequences]] en [[apollo]]-outbound zonder direct in spam te belanden.

## 📂 Onderdelen

- [[dns/README|README]] — overzicht en volgorde van setup
- [[dns/domain-strategy|Domein-strategie]] — naam-keuze, TLD, 3-domein-regel
- [[dns/provider-setup|Provider setup]] — Google Workspace / Maildoso instructies
- [[dns/dns-spf-dkim-dmarc|SPF / DKIM / DMARC]] — record templates
- [[dns/verification-tools|Verificatie tools]] — mxtoolbox, mail-tester checks
- [[dns/warmup-procedure|Warmup procedure]] — 14-daagse opbouw

## 🔗 Related

- [[email-sequences]] — sequences vereisen warm-gedraaide domeinen
- [[apollo]] — Apollo-volumes → Instantly heeft volledige DNS-laag nodig
- [[n8n]] — kan deliverability + bounces monitoren
- [[landingspagina]] — gebruikt custom subdomein onder dezelfde root
- [[rapport-ai-lead-gen-nl-be]] — juridische context (Telecommunicatiewet, GDPR)
