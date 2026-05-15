# Facebook Self-Hosted Scraper — Design Spec

**Status:** v2 — post-review (Python + scraping reviewers)
**Author:** Claude Opus 4.7 + operator
**Date:** 2026-05-15
**Scope:** Replace the manual-paste-only `consumer/sources/facebook.py` with a self-hosted, multi-surface FB scraper that feeds the existing lead-radar pipeline.

**v2 changelog:** Added `listing_type` to MarketplaceTarget (§6.10); separated `BackoffRaised` from `ChallengeRaised` (§9); added CDP-fingerprint patches + warmup enforcement (§7-§8); added crash-safety requirements (§6.2, §12); revised success criteria to reflect realistic week-2 expectations (§15); added operator-isolation requirements (§16).

---

## 1. Goal

Lead-radar currently misses Facebook entirely because the legacy `facebook.py` only supports manual paste of text into a file. FB is the highest-volume NL source for consumer-intent posts ("Wie kent een goede warmtepomp-installateur in Tilburg?"), but its anti-scraping makes it the hardest. We will build a self-hosted scraper that covers Groups, Marketplace, and Public Pages on a 2-4x daily cron cadence, integrating cleanly into the existing pipeline via a JSONL queue.

## 2. Non-Goals

- **No third-party scraper APIs** (Apify, Phantombuster). Self-hosted only.
- **No real-time/continuous polling**. Cron-driven only.
- **No automated account creation/warmup** (Phase 2+).
- **No PII enrichment** (we extract intent signal, not user profiles).
- **No replacement of existing sources** — FB is additive.

## 3. High-Level Decisions (already approved)

| Decision | Choice |
|---|---|
| FB surfaces to cover | Groups + Marketplace + Public Pages (all three) |
| Resilience tier | Phased: Hobbyist now, Resilient architecture-ready |
| Cadence | 2-4× daily spread (cron 08:00 / 12:00 / 17:00 / 21:00) |
| Architecture | Modular package + decoupled JSONL queue (Approach B) |

## 4. Module Layout

```
consumer/sources/facebook/
  __init__.py              # re-export analyze_manual_posts (backward-compat with run_consumer.py)
  core/
    __init__.py
    session.py             # PlaywrightSession context manager (persistent profile + stealth)
    accounts.py            # AccountPool + Account dataclass (state machine)
    throttle.py            # HumanPace timing helpers (jitter, scroll, dwell, rest)
    proxy.py               # HTTPProxy interface (NoProxy default; ResidentialProxy in Phase 2)
    detector.py            # detect challenge/captcha/login-wall states
  surfaces/
    __init__.py
    base.py                # Surface ABC: scrape(account, targets) -> Iterable[RawPost]
    groups.py              # FB Groups DOM scraper + GraphQL fallback
    marketplace.py         # Marketplace "Wanted" search scraper
    pages.py               # Public Pages scraper (reuses Groups parser)
  targets.py               # Pydantic-validated YAML loader
  queue.py                 # JSONL write/read helpers
  runner.py                # CLI: login | scrape | health

config/facebook_targets.yaml      # operator-edited target config
data/fb_queue/<timestamp>.jsonl   # runner-output queue files
data/fb_state/<account_id>/       # Playwright user_data_dir + status.json per account

tests/test_fb_targets.py          # YAML schema + Pydantic validation
tests/test_fb_throttle.py         # timing helpers
tests/test_fb_detector.py         # challenge detection on HTML fixtures
tests/test_fb_groups_parser.py    # DOM parsing on HTML fixtures
tests/test_fb_marketplace_parser.py
tests/test_fb_pages_parser.py
tests/test_fb_queue.py            # JSONL roundtrip
tests/test_fb_runner_smoke.py     # opt-in via FB_E2E=1, runs real Playwright
tests/fixtures/fb/                # saved HTML snapshots of each surface
```

## 5. Data Flow

```
[cron 08:00 / 12:00 / 17:00 / 21:00]
       │
       ▼
  runner.py scrape --niche all
       │
       ▼
  Load config/facebook_targets.yaml (Pydantic-validated)
       │
       ▼
  AccountPool.acquire() → Account(id="main", state="active")
       │
       ▼
  PlaywrightSession(account) ─ launches Chromium headed with stealth, persistent user_data_dir
       │
       ▼
  for surface in [GroupsSurface, MarketplaceSurface, PagesSurface]:
      for target in targets[niche][surface.name]:
          raw_posts = surface.scrape(account, target)
          throttle.between_targets()  # 10-20s
      throttle.between_surfaces()    # 30-90s
       │
       ▼
  queue.write_jsonl(data/fb_queue/2026-05-15T08-04.jsonl, all_raw_posts)
       │
       ▼
[main pipeline run_consumer.py --daily on its own cadence]
       │
       ▼
  queue.drain(data/fb_queue/) → merge into RawPost stream alongside other sources
       │
       ▼
  Existing pipeline unchanged:
    clean_post → check_hardblock → classify_post_kind → score_post
    → llm_verify (if borderline) → CSV export
       │
       ▼
  data/leads/consumer/<niche>.csv with rows where source ∈ {facebook_groups, facebook_marketplace, facebook_pages}
```

## 6. Components

### 6.1 `core/session.py` — PlaywrightSession

```python
class PlaywrightSession:
    """Context manager that launches Chromium with persistent profile + stealth."""
    def __init__(self, account: Account, proxy: HTTPProxy | None = None) -> None: ...
    async def __aenter__(self) -> BrowserContext: ...
    async def __aexit__(self, *exc) -> None: ...
```

- Uses `playwright.async_api` with `user_data_dir=data/fb_state/<account_id>/profile/`
- Applies `playwright-stealth` plugin to mask `navigator.webdriver`, plugins array, etc.
- Viewport: 1920×1080 with random ±50px jitter per session start
- User-agent: left as Playwright default (stealth plugin handles consistency)
- Headed mode by default (`headless=False`); Phase 2 can switch to `headless=True` once anti-detection proven
- Resource blocking: optional — block images/fonts for speed, configurable per surface

### 6.2 `core/accounts.py` — AccountPool

```python
@dataclass
class Account:
    id: str
    state: Literal["fresh", "warmed", "active", "challenged", "dead"]
    last_used_at: datetime | None
    warmed_at: datetime | None       # when login transitioned to WARMED — used by min_warmup_hours
    last_run_stats: dict | None      # {posts_captured, errors, surfaces_visited, backoff_count}
    quota_remaining: dict[str, int]  # {"group_views": 100, "mp_queries": 50, "page_views": 30}

class AccountPool:
    def __init__(self, state_dir: Path) -> None: ...
    def acquire(self, *, min_warmup_hours: int = 0) -> Account: ...  # gates on warmup age
    def release(self, account: Account, stats: dict) -> None: ...    # also promotes WARMED -> ACTIVE on success
    def mark_challenged(self, account_id: str, reason: str) -> None: ...
    def mark_backoff(self, account_id: str, surface: str) -> None: ...  # non-fatal soft-block
    def reset_quota(self) -> None: ...   # called by cron at midnight
```

- Phase 1: AccountPool contains exactly 1 account ("main"); `acquire()` returns it or raises if challenged
- Phase 2: pool of 3-5, round-robin selection skipping non-active states
- Persists state to `data/fb_state/<account_id>/status.json` (state + timestamps + last_run_stats + quota_remaining)
- **State persistence MUST be crash-safe** — atomic writes via `core/state_io.py` (write-tmp + os.replace); pool acquires a flock at `data/fb_state/.lock` to prevent overlapping runs corrupting status
- **SingletonLock cleanup** — on session start, sweep stale Chromium `SingletonLock`/`SingletonCookie`/`SingletonSocket` files in `profile/` (left behind after non-clean shutdowns)
- **Warmup gating** — `acquire(min_warmup_hours=72)` refuses to return an account whose `warmed_at` is less than 72h ago. Phase 1 default is `0` (warmup-disabled), but the runner should default to `72` for production cron entries. Document clearly in README that warmup matters.
- **State machine** — both `WARMED` and `ACTIVE` are eligible for `acquire()`. `release()` promotes `WARMED → ACTIVE` after the first run that captures ≥1 post without `ChallengeRaised`. `challenged → warmed` happens via operator running `login` again.

### 6.3 `core/throttle.py` — HumanPace

```python
class HumanPace:
    @staticmethod
    async def between_clicks() -> None:           # 3-8s random
    @staticmethod
    async def between_targets() -> None:           # 10-20s random
    @staticmethod
    async def between_surfaces() -> None:          # 30-90s random
    @staticmethod
    async def read_dwell() -> None:                # 2-5s per post (mimics reading)
    @staticmethod
    async def scroll_burst(page: Page) -> None:    # 2-4 burst-scrolls (200-600px each, with 0.5-2s gaps)
```

All timings use `random.uniform` over the ranges above. No hardcoded constants — bounds live in `THROTTLE_CONFIG` dict for easy tuning.

### 6.4 `core/proxy.py` — HTTPProxy Interface

```python
class HTTPProxy(Protocol):
    def playwright_proxy_config(self) -> dict | None: ...  # for browser.launch(proxy=...)

class NoProxy(HTTPProxy):
    def playwright_proxy_config(self) -> None: return None

class ResidentialProxy(HTTPProxy):  # Phase 2 stub
    def __init__(self, endpoint: str, username: str, password: str) -> None: ...
    def playwright_proxy_config(self) -> dict: ...
```

Phase 1 uses `NoProxy`. Phase 2 plugs `ResidentialProxy` without changing session.py.

### 6.5 `core/detector.py` — ChallengeDetector

```python
class ChallengeState(Enum):
    OK = "ok"
    CHALLENGED = "challenged"   # /checkpoint/, "verify identity" dialogs
    LOGIN_WALL = "login_wall"   # redirect to /login
    RATE_LIMITED = "rate_limited"  # "Slow down" banners — RECOVERABLE
    EMPTY_FEED = "empty_feed"   # surface returned 0 articles but no challenge — possible shadow-block

async def detect_state(page: Page) -> ChallengeState: ...
```

Detection rules:
- URL contains `/checkpoint/` or `/security/` → CHALLENGED
- DOM selector `[role=dialog]:has-text("verify identity"), :has-text("we beschermen je account")` → CHALLENGED
- URL is `/login.php` or `/login/` after intended navigation → LOGIN_WALL
- Visible text "you're temporarily blocked" / "vertraag het tempo" / "slow down" → RATE_LIMITED
- Feed container exists but contains 0 articles after scroll burst → EMPTY_FEED (caller decides whether to escalate)

**Recovery distinction** — RATE_LIMITED and EMPTY_FEED are *recoverable*: surface raises `BackoffRaised`, runner skips remaining work in that surface but does NOT flip account state (just increments `last_run_stats.backoff_count`). After 3 consecutive runs with backoff on the same surface, escalate to CHALLENGED. CHALLENGED and LOGIN_WALL are *fatal for the run*: surface raises `ChallengeRaised`, runner flips account state immediately.

### 6.6 `surfaces/base.py` — Surface ABC

```python
class Surface(ABC):
    name: str  # e.g., "facebook_groups"

    @abstractmethod
    async def scrape(self, account: Account, target: Target, page: Page) -> list[RawPost]:
        ...
```

Each concrete surface implements `scrape()` and returns a list of `RawPost` objects ready for the queue.

### 6.7 `surfaces/groups.py`

```python
class GroupsSurface(Surface):
    name = "facebook_groups"
    async def scrape(self, account, target, page) -> list[RawPost]:
        await page.goto(f"https://www.facebook.com/groups/{target.id}/", wait_until="domcontentloaded")
        await HumanPace.read_dwell()
        state = await detect_state(page)
        if state != ChallengeState.OK:
            raise ChallengeRaised(state)
        await page.wait_for_selector('[role=feed]', timeout=15000)
        await HumanPace.scroll_burst(page)
        posts = await self._extract_posts(page, max_posts=target.max_posts)
        if len(posts) < target.max_posts * 0.5:
            # DOM extraction underperformed — try GraphQL fallback
            posts = await self._extract_from_graphql(page)
        return [self._to_raw_post(p, target) for p in posts]
```

DOM extraction selectors (subject to FB redesigns — kept centralized in `surfaces/_selectors.py`):
- Feed container: `[role=feed]`
- Post: `[role=article]`
- Post text: `[data-ad-preview="message"], [data-ad-comet-preview="message"]` (FB uses both)
- Author name: `[role=article] strong a[role=link]` first match
- Post URL: `[role=article] a[href*="/posts/"], a[href*="/permalink/"]`
- Timestamp: `[role=article] a[href*="/posts/"] span` (relative — needs parsing)

GraphQL fallback: registers `page.on("response")` handler before scroll, captures responses where `req.url.includes("/api/graphql/")` and request post-data contains `"GroupsFeedPaginationQuery"` operation name, parses `data.node.group_feed.edges[].node.story` payloads.

### 6.8 `surfaces/marketplace.py`

```python
class MarketplaceSurface(Surface):
    name = "facebook_marketplace"
    async def scrape(self, account, target, page) -> list[RawPost]:
        url = f"https://www.facebook.com/marketplace/{target.location_slug}/search?query={urlencode(target.query)}"
        if target.radius_km:
            url += f"&radius={target.radius_km}"
        await page.goto(url, wait_until="domcontentloaded")
        # ... similar extraction pattern
```

Listing-card selectors (centralized in `surfaces/_selectors.py`):
- Card: `[aria-label*="Marketplace"] a[role=link]`
- Title: card-internal `span` first text node
- Location/price: trailing `span` siblings
- URL: card-link `href`

### 6.9 `surfaces/pages.py`

Reuses `GroupsSurface._extract_posts()` parser (Pages and Groups share the FB Feed UI). Navigation differs: `https://www.facebook.com/<page_slug>/` then same selectors.

### 6.10 `targets.py` — Config Loader

```python
class GroupTarget(BaseModel):
    id: str
    name: str
    max_posts: int = 20

class PageTarget(BaseModel):
    slug: str
    name: str = ""
    max_posts: int = 20

class MarketplaceTarget(BaseModel):
    query: str
    from_city: str = "Tilburg"           # default to a real NL city — "nederland" returns landing page, 0 results
    location_slug: str = "tilburg"
    radius_km: int = 50
    max_results: int = 30
    listing_type: Literal["wanted", "sale", "all"] = "wanted"  # WANTED is what we want for lead-radar intent
    # NOTE: FB Marketplace URL params for filtering listing_type change frequently.  Operator MUST
    # verify the generated URL returns "Wanted" / "Gezocht" posts (people seeking) and not "For Sale"
    # listings (vendors offering) before relying on output.  Sale-mode is the FB default and will
    # surface vendor-equipment posts — exactly the opposite of consumer-intent we want.

class NicheTargets(BaseModel):
    groups: list[GroupTarget] = []
    pages: list[PageTarget] = []
    marketplace: list[MarketplaceTarget] = []

class FacebookTargetsConfig(BaseModel):
    defaults: dict
    niches: dict[str, NicheTargets]

def load_targets(path: Path) -> FacebookTargetsConfig: ...
```

YAML schema example:
```yaml
# config/facebook_targets.yaml
defaults:
  max_posts_per_target: 20
  max_age_days: 7

niches:
  warmtepomp:
    groups:
      - id: "123456789"
        name: "Warmtepomp NL Ervaringen"
        max_posts: 30
      - id: "987654321"
        name: "Duurzaam Wonen Brabant"
    pages:
      - slug: "warmtepompvergelijken"
        name: "Warmtepomp Vergelijken NL"
    marketplace:
      - query: "warmtepomp installateur gezocht"
        from_city: "Tilburg"
        location_slug: "tilburg"
        radius_km: 50

  airco: { ... }
  zonnepanelen: { ... }
  cv: { ... }
  renovatie: { ... }
```

### 6.11 `queue.py` — JSONL Queue

```python
def write_jsonl(path: Path, posts: list[RawPost]) -> None: ...
def drain(queue_dir: Path) -> Iterator[RawPost]:
    """Yields all RawPosts from all .jsonl files in queue_dir, then moves files to queue_dir/processed/."""
```

Format (one RawPost per line):
```json
{"id":"facebook_groups:abc123-0","source":"facebook_groups","url":"https://www.facebook.com/groups/123/posts/456/","title":"Wie kent een goede warmtepomp-installateur in Tilburg?","text":"...","author":"Jan de Vries","created_at":"2026-05-15T08:04:12Z","metadata":{"niche":"warmtepomp","group_id":"123456789","group_name":"Warmtepomp NL Ervaringen","run_id":"2026-05-15T08-04","surface":"groups"}}
```

The main pipeline's `run_consumer.py` is extended with a new step: before its existing source-fetch loop, it calls `queue.drain(DATA_DIR / "fb_queue")` and merges the resulting `RawPost`s into the same stream that goes into dedup/hardblock/scorer.

### 6.12 `runner.py` — CLI

```bash
# Onboard a new account (headed Chromium, operator logs in manually)
python -m consumer.sources.facebook.runner login --account-id main

# Scrape all surfaces for all niches (cron entry point)
python -m consumer.sources.facebook.runner scrape --niche all

# Scrape specific niche
python -m consumer.sources.facebook.runner scrape --niche warmtepomp

# Show account health
python -m consumer.sources.facebook.runner health
```

## 7. Anti-Detection Strategy (Hobbyist Tier)

| Layer | Implementation |
|---|---|
| Browser | Playwright Chromium, **headed mode**, `tf-playwright-stealth` (maintained fork) applied |
| CDP-leak patches | **Custom JS injected into every page** — nukes `window.__playwright__`, overrides `navigator.permissions.query` for `notifications` (Playwright returns `denied`, real Chrome returns `default`), neutralizes `chrome.runtime.connect` probe. Critical because stealth plugin alone does NOT cover CDP-presence vectors FB has used since late 2023. |
| Fingerprint | Stealth plugin handles `navigator.webdriver`, `chrome` object, plugins array, languages, WebGL vendor |
| Viewport | 1920×1080 base, ±50px random jitter per session |
| User-agent | Playwright default (not spoofed — stealth keeps everything consistent) |
| IP | Operator's residential IP (no proxy in Phase 1) — see §16 for isolation requirements |
| Profile | Persistent `user_data_dir` per account; cookies/localStorage survive; SingletonLock files swept on session start |
| **Warmup** | New burner accounts must sit in `WARMED` state for ≥72h before first scrape run (operator manually browses FB on the profile during warmup — likes 1-2 things, joins 2-3 groups, scrolls). `acquire(min_warmup_hours=72)` enforces this for production. |
| Clicks | 3-8s random gap between any two clicks |
| Scrolls | 2-4 burst-scrolls per page (200-600px) with 0.5-2s gaps |
| Dwell | 2-5s read-time per post before scrolling past |
| Targets | 10-20s gap between consecutive targets within a surface |
| Surfaces | 30-90s gap between surfaces in a run |
| Cron | 4h gap between runs (08:00 / 12:00 / 17:00 / 21:00) |
| Navigation | `wait_until="networkidle"` with 15s timeout, then `wait_for_selector` for the surface-specific feed/card selector — `domcontentloaded` alone is too early for FB's SPA architecture and produces empty captures intermittently |
| Quota | ≤100 group-views + ≤50 MP-queries + ≤30 page-views per account per day; `acquire()` gates on remaining quota |
| Off-hours | **Code-level guard** — runner exits early if `datetime.now().hour in {2,3,4,5}`, regardless of how it was invoked. Belt-and-suspenders alongside cron schedule. |

## 8. Account Onboarding Flow

```bash
$ python -m consumer.sources.facebook.runner login --account-id main
[INFO] Opening Chromium with persistent profile data/fb_state/main/profile/
[INFO] Navigate to https://www.facebook.com/login/ — please log in manually.
[INFO] Handle 2FA if prompted. Press ENTER here when fully logged in to FB home page.
> [ENTER]
[INFO] Verifying session...
[INFO] Detected logged-in state. Account "main" → state=warmed.
[INFO] Profile saved. Run `runner scrape` to start scraping.
```

State machine transitions:
- `fresh → warmed`: operator completes login (login subcommand verifies state and sets `warmed_at` timestamp)
- `warmed → active`: first successful scrape run produced ≥1 RawPost without ChallengeRaised — `pool.release()` does this promotion
- `active → challenged` OR `warmed → challenged`: ChallengeDetector returns CHALLENGED/LOGIN_WALL during a run (after the one-retry recovery attempt failed)
- `challenged → warmed`: operator runs `login` again and detector confirms OK — account re-enters the eligible pool but its `warmed_at` is reset, so production cron with `min_warmup_hours=72` will wait before scraping again
- `* → dead`: 3+ consecutive challenged runs without successful recovery

Both `WARMED` and `ACTIVE` are eligible for `acquire()` — the distinction is informational (has the account ever successfully run?). Production `acquire()` calls additionally enforce `min_warmup_hours=72` so genuinely fresh accounts aren't thrown into the deep end.

## 9. Error Handling

### Exception hierarchy

- **`BackoffRaised`** — recoverable: surface hit RATE_LIMITED, EMPTY_FEED, or transient network. Runner skips remaining targets in this surface but **does NOT flip account state**. Increments `last_run_stats.backoff_count[surface]`. After 3 consecutive runs with backoff on the same surface, escalates to `ChallengeRaised`.
- **`ChallengeRaised`** — fatal-for-run: surface hit CHALLENGED or LOGIN_WALL. Runner flips account state to `challenged`, skips remaining surfaces, writes partial queue file with what was captured before, alerts operator.

### Mid-run challenge recovery (one retry)

When `ChallengeRaised` is hit, before flipping account state, the runner navigates to `https://www.facebook.com/` (root), waits 30-60s, and re-checks state. If recovered (state == OK), resume next target. If still challenged, then flip. This catches transient interstitials that don't actually require operator login.

### Cookie-jar snapshot before risky surfaces

Before navigating to Marketplace (the most ban-prone surface), `core/session.py` copies `profile/Cookies` → `profile/Cookies.snapshot-pre-mp`. If the Marketplace run flips the account to `challenged`, the operator can run a `runner recover --account-id main` command that restores the pre-Marketplace cookie snapshot — often (~50%) this restores the account to OK without re-login.

### Per-run logging

Structured summary at run end: `{"run_id": "...", "account": "main", "captured": 23, "challenge_state": "ok"|"challenged"|..., "backoff_count": {"groups": 0, "marketplace": 1, "pages": 0}, "surfaces_completed": ["groups", "marketplace"]}`.

### Operator alerts

Fires `send_lead_alert()` (already in pipeline) when:
- Account flips to `challenged` or `dead`
- 3 consecutive backoffs on any surface
- Quota exhausted before run completion

### Process-level safety

- **SIGTERM/SIGINT handler** in runner: closes Playwright context cleanly, releases pool flock, removes `SingletonLock` from profile. Ctrl-C must not leave zombie Chromium processes or locked profiles.
- **Atomic status writes** — `core/state_io.py` writes to `status.json.tmp` then `os.replace`. Crash mid-write cannot brick an account record.
- **Pool flock** — runner acquires `data/fb_state/.lock` at start. Overlapping cron entries (12:00 still running when 17:00 fires — easy if Playwright hangs) exit cleanly with "another run in progress" instead of corrupting state.

### Per-target failures

Network/selector misses on a single target are logged and the surface continues with the next target. Only surface-level signals (challenge, login wall, repeated rate-limit) abort.

### Pipeline-side

`drain()` reads JSONL files; malformed records are logged and skipped. **`drain()` must collect a file's records into a list before moving the file to `processed/`** — otherwise early-exit iteration loses records permanently.

## 10. Testing Strategy

| Test file | Coverage |
|---|---|
| `test_fb_targets.py` | Pydantic schema validation, malformed YAML rejection, defaults inheritance |
| `test_fb_throttle.py` | Timing bounds (mocked `asyncio.sleep`), jitter distribution |
| `test_fb_detector.py` | All 4 ChallengeState outcomes on saved HTML fixtures in `tests/fixtures/fb/states/` |
| `test_fb_groups_parser.py` | DOM extraction on saved fixtures (3+ snapshots over time to catch drift) |
| `test_fb_marketplace_parser.py` | Same pattern, listing-card extraction |
| `test_fb_pages_parser.py` | Same |
| `test_fb_queue.py` | JSONL write/read roundtrip, drain moves files to processed/, malformed-line handling |
| `test_fb_runner_smoke.py` | Real Playwright E2E against test account — `pytest.skip` unless `FB_E2E=1` env set (operator opt-in only) |
| `test_fb_account_state.py` | AccountPool state machine transitions, quota tracking, status.json persistence |

**Fixtures**: `tests/fixtures/fb/` contains saved HTML snapshots of FB Groups feed, Marketplace search results, and Pages feed (sanitized of real user data). Refreshed when selectors break in production.

**Existing pipeline tests intact**: the queue files contain standard `RawPost` dicts → existing dedup/hardblock/scorer/verifier tests already cover the downstream path.

## 11. GDPR & Data Hygiene

**What we store:**
- Post URL (public-ish, depending on group privacy)
- Post text (intent signal)
- Public author display-name (visible to anyone with group access)
- Timestamp
- Surface tag (groups/marketplace/pages) + group/page identifier

**What we do NOT store:**
- FB user-id (numeric)
- Profile picture
- Friend graph / mutual friends
- Comment threads (only top-level post)
- Reactions or "who liked this"

**Retention:** Same as existing pipeline — `seen_hashes.json` TTL logic covers dedup-window; CSV exports follow operator's own retention policy.

**Legal basis (NL/EU):** Operating under "legitimate interest" (Art. 6.1.f GDPR) for B2B lead-generation. Processing is intent-detection-only — we do not enrich with PII or build profiles. FB's TOS prohibits scraping; practical enforcement is account suspension, not legal action. Operator accepts this risk as a normal cost of using burner accounts.

**Footnote:** This spec is technical. If operator wants formal legal review before production, that's a separate workstream.

## 12. Phased Rollout

### Phase 1 — MVP (weeks 1-4)
- AccountPool with single account, persisted to disk via atomic `state_io` writes
- Pool flock + SingletonLock cleanup on every session start
- NoProxy implementation
- All 3 surfaces with DOM-only extraction (GraphQL fallback wired but secondary), permissive parsers (recursive dict walk) tolerant to FB payload-shape drift
- ChallengeDetector with backoff vs challenge distinction + mid-run challenge retry
- CDP-fingerprint patches injected on every page (beyond stealth plugin)
- 72h warmup enforcement on production cron entries
- Cookie-jar snapshot before Marketplace + `recover` subcommand for rollback
- SIGTERM/SIGINT handler + zombie-process cleanup
- Off-hours code-level guard (02:00-06:00 skip)
- **Real HTML fixtures captured from operator's logged-in session BEFORE parser implementation**
- Cron 2-4x daily on operator's dedicated machine/VM (see §16 for isolation requirements)
- Manual operator recovery on challenge (login OR cookie-snapshot rollback)

**Done when:** account survives ≥14 days without permanent ban (transient checkpoints OK if operator-recoverable), with ≥5 facebook-source rows per active niche in the **second-week** CSV (week-1 is warmup + ramp-up).

### Phase 2 — Resilient (post-MVP, when leads prove valuable)
- AccountPool of 3-5 burner accounts with round-robin
- `ResidentialProxy` plugged in (€30-100/m), sticky per-account IP
- GraphQL fallback wired as primary for Groups (more durable than DOM)
- Auto-account-rotation on challenge (no manual recovery during business hours)
- Health-monitoring extension to existing alerting (Slack/email)
- Optional: switch from headed to headless mode after stealth proven

### Phase 3 — Industrial (only if business justifies)
- 10+ accounts, automated warmup procedure
- Per-account fingerprint randomization (canvas/WebGL/audio spoofing beyond stealth plugin)
- Multi-geo proxy pool
- Docker-isolated per-account browser containers

## 13. Open Questions

- **Group IDs**: operator needs to manually curate the initial list of NL groups per niche. Suggested process: browse FB groups, copy ID from URL, paste into `facebook_targets.yaml`. Maintenance: review monthly, prune dead groups.
- **Account creation**: operator creates burner FB accounts manually (FB requires phone number for new accounts these days). Phase 1 = 1 account is sufficient.
- **Cron mechanism**: macOS `launchd` plist OR `cron` OR `at` — operator preference. Default in spec: standard `cron` entries documented in README.

## 14. Out of Scope (Explicitly Not Building)

- Automated FB account creation
- Profile-data enrichment (friends, likes, page-membership lookup)
- Comment-thread scraping below top-level posts
- Cross-account behavior correlation
- Real-time/event-driven scraping
- Web UI for managing targets (YAML edit is sufficient)
- Multi-language support (NL/BE focus matches existing pipeline scope)

## 15. Success Criteria

Realistic week-by-week:

- **Week 1 (warmup + ramp):** Account in `warmed` state, operator manually browses on the profile to age it. Limited or no automated scrapes. 0-5 rows/day expected. Goal: account survives without checkpoint.
- **Week 2 (ramp + first real scrape weeks):** Production cron active. Expected: 5-15 FB rows/day total across niches in CSV. **Target: ≥5 FB rows per active niche by end of week 2.**
- **Week 3-4:** Steady state. ≥5 rows per niche per day, ≤1 operator intervention per week, account in `active` state.

Pass criteria for declaring Phase 1 successful (measured end of week 2):

1. **Account survival** — account is in `active` or `warmed` state (not `challenged` for >24h or `dead`)
2. **Volume** — ≥5 FB-source rows per active niche in the week-2 CSV (averaging over 7 days)
3. **Quality** — false-positive rate (vendor/promo reaching CSV) ≤10% — existing hardblock + vendor patterns should catch most
4. **Operator load** — ≤1× per week manual intervention (login refresh or cookie rollback)
5. **Pipeline integrity** — all non-FB tests still pass; non-FB lead counts in CSVs unchanged vs pre-deployment baseline

If criteria fail: do not escalate to Phase 2. Diagnose what specifically broke — DOM drift (capture new fixtures), CDP detection (escalate to `playwright-extra` or `camoufox`), warmup insufficient (extend warmup window), or operator-isolation breach (move to dedicated machine).

## 16. Operator Isolation Requirements

FB does device-graph linking — it correlates burner accounts to the operator's personal account through shared IP + browser fingerprint + behavior patterns. Without operator isolation, two real risks materialize:

1. **The operator's personal FB account starts seeing "suspicious activity from your account" prompts within the first week**, because FB associates burner-activity-spikes with the operator's device-graph.
2. **The burner gets banned faster** because FB's risk scoring flags accounts that fingerprint-match an existing user (the operator) acting from a different identity.

### Required isolation (Phase 1)

At minimum, **one** of the following:

- **Dedicated machine** for the FB scraper (separate laptop, Mac Mini, or RPi 5 — costs ~€100-200 one-time or €5/m for a cloud VPS)
- **Dedicated browser profile** that has NEVER been used to access personal FB (`data/fb_state/main/profile/` is fresh; operator must not log in to personal FB from this profile)
- **VPN bound only to the FB scraper process** (e.g., `ProtonVPN-CLI` or `mullvad-cli` with split-tunneling — Dutch endpoint to avoid geo-flag) — but this only helps if the IP truly differs from personal-FB activity

### Recommended isolation (production)

All three combined:
- Always-on dedicated box (Mac Mini at home, RPi 5, or cheap VPS)
- Fresh browser profile per burner
- VPN with Dutch residential endpoint

### What the spec does NOT do for you

- Provision the dedicated machine or VPS
- Create burner FB accounts (FB requires phone-verification — operator does this manually, can use a pay-as-you-go SIM)
- Resolve the legal/TOS grey-area (scraping public-ish posts under "legitimate interest" — see §11)

This must be in the README as a hard warning, not a footnote.
