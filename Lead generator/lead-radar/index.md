# Lead Radar

Gratis Python-scraper die installatiebedrijven (HVAC / warmtepomp / airco / zonnepanelen) vindt via DuckDuckGo HTML, Reddit JSON, het KVK publiek register en directe website-crawls. Output: CSV met intent-gescoorde leads per niche en locatie. Geen API keys, geen accounts, alleen publieke bronnen met rate limiting.

Dit is het hart van **Pad A — de gratis MVP**. De CSV die hier uitkomt voedt [[crm-light/index]], die op zijn beurt [[outreach/index]] aanstuurt voor personalisatie.

## 📂 Onderdelen

- [[lead-radar/README|README]] — installatie, commando's, troubleshooting
- [[lead-radar/SETUP|SETUP]] — uitgebreide setup-gids met env-variabelen
- [[lead-radar/consumer/README|Consumer pipeline]] — Reddit consumer architectuur (LLM verify, dedup, hardblock)

## 🔗 Related

- [[crm-light/index]] — importeert de leads-CSV en beheert pipeline status
- [[outreach/index]] — leest leads + template, schrijft klare berichten
- [[automation/index]] — orchestreert lead-radar in de dagelijkse pipeline (`daily.sh`)
- [[apollo/index]] — betaalde tegenhanger zodra je opschaalt naar 10k+ contacten
- [[MVP-START-HERE]] — snelstart-pad waar lead-radar de eerste stap is
