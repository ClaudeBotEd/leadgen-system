# FB Scraper -- Operator Setup (1-page kickoff)

Wat al voor je is geregeld:
- Targets ingevuld (`config/facebook_targets.yaml`) -- 16 NL groepen + 1 page + 8 marketplace queries
- launchd plists klaar (08/12/17/21u scrapes + 00:00 quota-reset)
- Queue + state directories aangemaakt
- Drain in `run_consumer.py --daily` reeds gewired

Wat jij doet -- exact 3 stappen.

---

## STAP 1 -- Burner FB-account aanmaken & warmen (jouw werk, ~30 min over 3-5 dagen)

1. Maak los e-mail (Gmail/ProtonMail) -- niet je eigen naam.
2. Verkrijg een apart telefoonnummer voor SMS-verificatie:
   - Prepaid simkaart (~EUR 5 Lebara/Lyca) -- veiligst
   - Of online SMS-service (smspva.com / sms-activate) -- soms ban
   - **Niet** je eigen nummer
3. Registreer op facebook.com via een **gewone** browser (Safari/Chrome), realistische naam, leeftijd 25-45, NL profiel.
4. **Warm het account 3-5 dagen**, dagelijks 10-15 min:
   - Inloggen, feed scrollen, posts liken
   - Accepteer 2-3 friend requests
   - Join 2-3 willekeurige NL groepen (NIET onze target-niches uit `facebook_targets.yaml`)
   - Geen mass-activity -- FB flagged bursts

Wanneer klaar: je kunt zonder challenges inloggen op facebook.com vanaf een nieuwe browser-sessie.

---

## STAP 2 -- 1 commando draaien

```bash
cd "/Users/claudebot/Lead generator/lead-radar"
.venv/bin/python -m consumer.sources.facebook.runner login --account-id main
```

Wat gebeurt er:
- Een Chromium-venster opent op facebook.com/login
- Jij logt **handmatig** in met je burner (email + wachtwoord, 2FA als FB erom vraagt)
- Als FB een captcha/checkpoint toont: los het op in dat venster
- Sluit venster NIET -- ga terug naar terminal, druk ENTER
- Profiel + cookies worden opgeslagen in `data/fb_state/main/profile/`

Klaar als terminal zegt: "Login flow complete. Account state: warmed."

---

## STAP 3 -- Test 1 scrape, dan launchd activeren

```bash
# Test run -- 1 niche, kijken of het werkt
.venv/bin/python -m consumer.sources.facebook.runner scrape --niche warmtepomp

# Check resultaat
ls -la data/fb_queue/
cat data/fb_queue/*.jsonl | head -5
```

Als output >0 posts -> launchd activeren:

```bash
cp consumer/sources/facebook/com.leadradar.fbscrape.plist ~/Library/LaunchAgents/
cp consumer/sources/facebook/com.leadradar.fbquota.plist  ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.leadradar.fbscrape.plist
launchctl load ~/Library/LaunchAgents/com.leadradar.fbquota.plist
launchctl list | grep leadradar    # moet 2 regels tonen
```

Vanaf nu loopt de scraper automatisch om 08/12/17/21u en wordt elke `run_consumer.py --daily` de queue gedrained.

---

## Troubleshooting

| Probleem | Fix |
|---|---|
| `No active accounts in pool` | STAP 2 niet (af)gerund |
| Account flipt naar `challenged` | Re-run `login --account-id main`, los captcha op |
| 0 posts uit `groups.scrape` | FB DOM-redesign -> `consumer/sources/facebook/surfaces/_selectors.py` updaten |
| Mac slaapt -> geen runs | launchd vangt gemiste run op zodra wakker; check `data/fb_state/launchd.log` |
| Persoonlijk FB krijgt "verdachte activiteit" | Browserprofiel-isolatie werkt niet -- overweeg VPN of aparte machine |

---

## Status check

```bash
.venv/bin/python -m consumer.sources.facebook.runner health
```

Toont per account: state (fresh/warmed/active/challenged/dead), laatste run, quota.
