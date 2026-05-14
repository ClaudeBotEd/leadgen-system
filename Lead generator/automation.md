# Automation

End-to-end pipeline runner (`daily.sh`, `pipeline.py`). Eén commando draait: scrape → enrich → score → importeer in CRM → genereer email batch → toon dashboard. Wrapper rondom [[lead-radar]], [[crm-light]] en [[outreach]] — de "Snelstart MAX" van de MVP.

Voor 24/7 automation of multi-step workflows met externe systemen (CRM-sync, webhook triggers), zie [[n8n]] als opvolger.

## 📂 Onderdelen

- [[automation/README|README]] — pipeline-configuratie, cron-setup, environment

## 🔗 Related

- [[lead-radar]] — de scrape-stap van de pipeline
- [[crm-light]] — de import-stap
- [[outreach]] — de personalisatie-stap
- [[n8n]] — schaal-alternatief voor scheduled workflows
- [[MVP-START-HERE]] — beschrijft `./daily.sh warmtepomp amsterdam 50` als one-liner
