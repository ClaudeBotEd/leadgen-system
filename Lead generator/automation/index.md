# Automation

End-to-end pipeline runner (`daily.sh`, `pipeline.py`). Eén commando draait: scrape → enrich → score → importeer in CRM → genereer email batch → toon dashboard. Wrapper rondom [[lead-radar/index]], [[crm-light/index]] en [[outreach/index]] — de "Snelstart MAX" van de MVP.

Voor 24/7 automation of multi-step workflows met externe systemen (CRM-sync, webhook triggers), zie [[n8n/index]] als opvolger.

## 📂 Onderdelen

- [[automation/README|README]] — pipeline-configuratie, cron-setup, environment

## 🔗 Related

- [[lead-radar/index]] — de scrape-stap van de pipeline
- [[crm-light/index]] — de import-stap
- [[outreach/index]] — de personalisatie-stap
- [[n8n/index]] — schaal-alternatief voor scheduled workflows
- [[MVP-START-HERE]] — beschrijft `./daily.sh warmtepomp amsterdam 50` als one-liner
