# Rehearsal — installateur demo call

Doel: één installateur leren kennen + één lead samen doornemen.

## Voor de call

    cd lead-radar
    python3 run_seed_demo_inventory.py
    python3 run_render_demo.py
    open output/demo/inventory.html
    open output/demo/sample-receipt.html

## Volgorde op de call (<=20 min)

1. **Wie ben jij, wie zijn wij** (2 min)
   - Sem Vijn, 22, solo founder, Amersfoort
   - "We bouwen geen generiek lead-platform. We bouwen één scherpe lead-pijp voor jouw niche."

2. **Wat is een lead bij ons** (5 min)
   - Open `sample-receipt.html`
   - Loop de canonical velden langs: snippet, source, regio, niche, band
   - Benadruk: snippet is letterlijk, geen reformulering. Bron is altijd zichtbaar.

3. **Wat hebben we nu** (5 min)
   - Open `inventory.html`
   - Filter visueel op installateur's niche/regio
   - Wijs op decay-countdown ("over 13d") — vers, niet stale
   - Wijs op bron-badge (publiek vs. besloten + attestation)

4. **Wat verkopen we, wat niet** (5 min)
   - "Eén lead = één installateur. Exclusief. Geen broker-model."
   - "Wij filteren, jij belt of mailt. We doen het outbound niet voor je."
   - "Pricing: nog niet vandaag. Vandaag is alleen: wil je een pilot-week?"

5. **Vraag aan installateur** (3 min)
   - "Als ik je morgen één bruikbare lead in jouw niche/regio stuur, mag ik dan terug bellen?"

## Niet doen

- Niet over scalability, automation, of platform praten
- Geen kortingen aanbieden zonder pilot-resultaat
- Geen "AI" als verkooppunt — provenance is het verkooppunt

## Na de call

- Schrijf installateur in `data/installers.csv` als hij geïnteresseerd is
- Bevestig per email binnen 1 uur ("Bedankt voor het gesprek, ik stuur deze week één lead")
