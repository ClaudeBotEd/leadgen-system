# Facebook Scraper

Self-hosted Playwright-based scraper for FB Groups (MVP), Marketplace, and
Public Pages.  Feeds the lead-radar pipeline via a decoupled JSONL queue.

See full design spec: `docs/superpowers/specs/2026-05-15-facebook-self-hosted-scraper-design.md`

## ⚠ READ FIRST — Operator Isolation (mandatory)

FB does device-graph linking: it correlates burner accounts to your personal
account via shared IP + browser fingerprint + behavior.  Two real risks:

1. **Your personal FB starts seeing "Did you do this? Suspicious activity"
   prompts** within the first week, because FB associates burner activity with
   YOUR device-graph.
2. **The burner gets banned faster** because FB's risk scoring flags accounts
   that fingerprint-match an existing user acting as a different identity.

**Required isolation — at minimum ONE of:**
- A dedicated machine for this scraper (separate laptop, Mac Mini, RPi 5, or
  cheap VPS in NL — ~€5/mo)
- A browser profile that has NEVER touched personal FB (use a brand-new burner
  in `data/fb_state/main/profile/` and do not log in to your real FB there)
- A VPN with split-tunneling, bound only to the FB scraper process

**Recommended for production:** all three combined.

Also: **on macOS, `cron` does NOT wake a sleeping laptop.** Use a `launchd`
plist with `RunAtLoad=true` and `StartCalendarInterval`, or run on a Mac that
stays awake (caffeinate), or deploy to an always-on box.

## Quickstart

```bash
# 1. Install browser binary (once per machine)
playwright install chromium

# 2. Onboard a burner FB account (one-time, headed Chromium opens)
python -m consumer.sources.facebook.runner login --account-id main
# Log in manually, handle 2FA, then press ENTER in the terminal.

# 3. Edit target config — add group IDs / pages / marketplace queries per niche
$EDITOR config/facebook_targets.yaml

# 4. Run a scrape manually
python -m consumer.sources.facebook.runner scrape --niche warmtepomp

# 5. The next regular run_consumer.py --daily picks up data/fb_queue/*.jsonl
python run_consumer.py --daily
```

## Cron Setup

See `cron.example.txt` for the recommended crontab entries (08:00 / 12:00 /
17:00 / 21:00 with 4h gap, plus a midnight quota-reset).

## Account States

| State | Meaning |
|---|---|
| `fresh` | Just registered, never logged in |
| `warmed` | Logged in successfully, ready to scrape |
| `active` | Has completed at least one successful run |
| `challenged` | Hit a checkpoint/captcha — needs `login` again |
| `dead` | Permanently failed — replace the account |

## Troubleshooting

- **`NoActiveAccount`** — run `login` to onboard or recover the account
- **DOM extraction returned 0 posts** — FB likely redesigned; check
  `consumer/sources/facebook/surfaces/_selectors.py` and re-capture HTML
  fixtures from a live session
- **Account flipped to `challenged`** — open Chromium with the profile and
  resolve the captcha/identity challenge manually, then re-run `login`
