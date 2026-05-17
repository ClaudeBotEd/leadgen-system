# ORCHESTRATION.md — lead-radar-site

> Build playbook for Codex/Cursor. Nine phases (F1–F9). Each phase is one branch, one PR, one squash-merge to `main`. No phase begins until the previous phase's DoD passes.
>
> **Authority order:** `DESIGN-BRIEF.md` > `AGENTS.md` > this file. If anything here contradicts `AGENTS.md`, this file is wrong — fix this file, not the implementation.
>
> Working principles:
> - One narrow prompt per phase.
> - Every prompt loads `@AGENTS.md` as context.
> - Definition of Done is verifiable, not subjective.
> - Reject-loop the diff with specific feedback, never "do better."
> - Design tokens are the single source of truth for color, spacing, type.

---

## Table of contents

1. [Build roadmap](#1-build-roadmap)
2. [Codex execution protocol](#2-codex-execution-protocol)
3. [Exact prompts per phase (F1–F9)](#3-exact-prompts-per-phase-f1f9)
4. [Cursor/Codex workflow rules](#4-cursorcodex-workflow-rules)
5. [Definition of Done per phase](#5-definition-of-done-per-phase)
6. [QA checklist per phase](#6-qa-checklist-per-phase)
7. [Git workflow + commit conventions](#7-git-workflow--commit-conventions)
8. [Build order (dependency tree)](#8-build-order-dependency-tree)
9. [Component test order](#9-component-test-order)
10. [Codex anti-instructions](#10-codex-anti-instructions)
11. [AI design-mistakes](#11-ai-design-mistakes)
12. [Performance-mistakes](#12-performance-mistakes)
13. [UI/UX anti-patterns](#13-uiux-anti-patterns)
14. [Anti-AI-tells enforcement](#14-anti-ai-tells-enforcement)
15. [Pre-F1 requirements](#15-what-i-need-from-the-founder-before-f1-starts)

---

## 1. Build roadmap

Nine phases. One PR per phase. Sequential, no overlap. Estimated 6–8 working days end-to-end.

| #  | Phase                              | Deliverable                                                                 | Branch                  | Est.    |
|----|------------------------------------|-----------------------------------------------------------------------------|-------------------------|---------|
| F1 | Foundation                         | Scaffold + light tokens + fonts + 8 placeholder routes + Header + Footer    | `feat/01-foundation`    | 0.5 d   |
| F2 | Hero + LiveSignalStrip + FinalCta  | Homepage top + bottom anchors (Hero, signal strip, conversion close)        | `feat/02-hero-finalcta` | 0.5 d   |
| F3 | HowItWorks + ExampleLeadCard       | Mechanism teaser (no icons) + single redacted lead card (cols 3–10)         | `feat/03-howitworks`    | 0.5 d   |
| F4 | Why + Pricing + FAQ + Founder      | Homepage complete (9 sections live)                                         | `feat/04-home-complete` | 1 d     |
| F5 | `/leads`                           | 9-card gallery + niche filter + empty state + page CTA                      | `feat/05-leads`         | 0.5 d   |
| F6 | `/zo-werkt-het`                    | 7-section methodology page + embedded lead card + timeline                  | `feat/06-zo-werkt-het`  | 0.5 d   |
| F7 | `/prijzen`                         | 2 pricing cards + money-back block + 4-item pricing FAQ                     | `feat/07-prijzen`       | 0.5 d   |
| F8 | `/pilot` + intake API + `/bedankt` | Form (7 fields) + Resend + rate-limit + honeypot + post-submit confirmation | `feat/08-pilot-intake`  | 1 d     |
| F9 | SEO + analytics + utility + deploy | Metadata + sitemap + JSON-LD + Plausible + privacy + voorwaarden + prod     | `feat/09-seo-deploy`    | 0.5 d   |

Each phase ends with a working commit on its feature branch, a Vercel preview URL, and a visual review pass on three viewports (375 / 768 / 1440 px). Only then does it squash-merge to `main`.

---

## 2. Codex execution protocol

### Session structure

Each phase is one Cursor session. Don't stuff multiple phases into one context.

```
1.  Open Cursor in lead-radar-site/
2.  Load @AGENTS.md, @DESIGN-BRIEF.md
3.  Load relevant files from prior phases (see "Context loading" below)
4.  Paste the phase prompt from §3 verbatim
5.  Codex produces diff
6.  Review diff manually (DoD checklist §5)
7.  Accept / reject loop until DoD passes
8.  Commit (§7)
9.  Push, open PR, get Vercel preview URL
10. Self-review on real mobile device
11. Squash-merge to main
12. Delete feature branch
13. Start next phase
```

### Context loading per phase

| Phase | Files to open in Cursor context (`@filename`)                                                                  |
| ----- | -------------------------------------------------------------------------------------------------------------- |
| F1    | `@AGENTS.md`, `@DESIGN-BRIEF.md`                                                                               |
| F2    | `@AGENTS.md`, `@src/styles/globals.css`, `@src/app/layout.tsx`, `@src/components/layout/SiteHeader.tsx`        |
| F3    | `@AGENTS.md`, `@src/components/home/Hero.tsx`, `@src/components/home/LiveSignalStrip.tsx`                      |
| F4    | `@AGENTS.md`, `@src/components/home/ExampleLeadCard.tsx`, `@src/content/leads.ts`                              |
| F5    | `@AGENTS.md`, `@src/components/home/ExampleLeadCard.tsx`, `@src/content/leads.ts`                              |
| F6    | `@AGENTS.md`, `@src/components/home/HowItWorks.tsx`, `@src/components/home/ExampleLeadCard.tsx`                |
| F7    | `@AGENTS.md`, `@src/components/home/PricingTeaser.tsx`, `@src/content/pricing.ts`                              |
| F8    | `@AGENTS.md`, `@src/components/ui/Input.tsx`, `@src/components/ui/Button.tsx`, `@src/components/ui/Select.tsx` |
| F9    | `@AGENTS.md`, all `@src/app/**/page.tsx` files                                                                 |

### Review checkpoint protocol (three filters)

Every diff must pass three independent filters before it's accepted:

1. **Compile** — `pnpm dev` starts clean. `pnpm tsc --noEmit` and `pnpm lint` report 0 errors, 0 warnings.
2. **DoD** — every checkbox in the phase's DoD (§5) is met.
3. **Visual** — the Vercel preview matches the spec on 1440 / 768 / 375 px and survives the §14 anti-AI checklist.

Failing any filter triggers a reject. Re-prompt with a specific instruction — never "do better." See §4 for the reject-loop patterns.

### Roll-back protocol

If a phase output fails two reject rounds:

1. `git restore .` (or `git reset --hard HEAD` if files were committed)
2. Split the prompt into smaller sub-tasks
3. Re-run with narrower scope

Never push through with half-broken code.

---

## 3. Exact prompts per phase (F1–F9)

Paste these verbatim into Cursor Composer (Cmd+I). Do not paraphrase. Open `@AGENTS.md` first.

---

### Prompt F1 — Foundation

```
@AGENTS.md
@DESIGN-BRIEF.md

Phase F1: Project scaffold + light-theme design tokens + layout shell.

Goals, in order:

1. Initialize Next.js 15 + TypeScript strict + App Router + Tailwind v4 + pnpm + ESLint.
   Run:
     pnpm create next-app@latest . --typescript --tailwind --app --src-dir --eslint --import-alias "@/*"

2. Install extra dependencies:
   - react-hook-form
   - zod
   - lucide-react
   - resend
   - clsx
   Do NOT install: framer-motion, motion, gsap, @shadcn/ui CLI, sonner, react-toastify,
   carousel libs, lodash, dayjs. See AGENTS.md §3.

3. Configure next/font in src/app/layout.tsx:
   - Inter (variable, weights 400/500/600 subset latin)
   - Geist Mono (variable, weight 400 subset latin)
   - Both display:'swap'
   - Export as CSS variables --font-inter and --font-mono on <html>.
   - DO NOT use Google CDN. Self-hosted via next/font/google with subsets.

4. Write src/styles/globals.css with EXACTLY the tokens from AGENTS.md §6:
   - All surface tokens (--paper, --paper-elevated, --paper-inset)
   - All ink tokens (--ink, --ink-soft, --ink-mute)
   - --rule
   - All signal tokens (--signal, --signal-hover, --signal-active, --signal-bright)
   - All radius tokens
   Then add a Tailwind v4 `@theme inline { }` block that exposes each variable as a
   utility name (bg-paper, text-ink, border-rule, bg-signal, etc.).
   Set body { background: var(--paper); color: var(--ink); font-family: var(--font-inter); }

5. Create 8 placeholder routes. Each renders a valid <main> wrapper with the page's H1
   in display-lg style (or display-xl on /). Routes:
   - src/app/page.tsx
   - src/app/zo-werkt-het/page.tsx
   - src/app/leads/page.tsx
   - src/app/prijzen/page.tsx
   - src/app/pilot/page.tsx
   - src/app/bedankt/page.tsx
   - src/app/privacy/page.tsx
   - src/app/voorwaarden/page.tsx

6. Build src/components/layout/SiteHeader.tsx:
   - Sticky top, height 72px desktop, 56px mobile
   - Wordmark "lead-radar" left, no logomark, Inter weight 500
   - Three text links center: "Hoe het werkt" → /zo-werkt-het, "Voorbeeldleads" → /leads,
     "Prijzen" → /prijzen
   - One primary button right: "Start pilot" → /pilot (uses --signal fill, --ink text,
     per AGENTS.md §9)
   - Background: var(--paper)
   - Bottom border: 1px var(--rule), but ONLY when scrollY > 40px. Above the fold,
     header is borderless. Use a `'use client'` scroll listener for this.
   - Mobile (< 768px): replace center nav with a lucide Menu hamburger, slide-in drawer

7. Build src/components/layout/SiteFooter.tsx:
   - 3 columns desktop, stacked mobile
   - Col 1: wordmark + tagline "Exclusieve intent-leads voor installateurs in NL en BE."
   - Col 2: nav (mirrors header) + utility links (Privacy, Voorwaarden)
   - Col 3: contact (founder email, LinkedIn placeholder)
   - 1px var(--rule) top border
   - Bottom line: "© 2026 lead-radar · Eindhoven" in body-sm var(--ink-mute)
   - Padding 48px top/bottom desktop, 32px mobile

8. Wire SiteHeader + SiteFooter in src/app/layout.tsx. Add a skip-to-content link
   at the very top of <body>.

DON'T:
- Use --bg-base, --bg-elevated, --text-primary, or any dark-theme token name.
- Add Roboto/Open Sans/Poppins/Lato.
- Add boilerplate "Welcome to Next.js" content.
- Add gradients, drop shadows, dot-grid, glassmorphism.
- Add a logo image; use the text wordmark only.
- Add a "Built with Next.js" badge.
- Add a cookie-consent banner.
- Add #pilot-form anchor — the form lives at /pilot.

DoD (self-verify before committing):
- pnpm dev starts with 0 warnings.
- All 8 routes return 200 with a visible H1.
- Header is sticky and gains its bottom border only after scrolling 40px.
- Footer is at the bottom of every page.
- Page background is #FAFAF7 (not white). Body text is #0A0A0A (not pure black).
- The "Start pilot" button in the header is GREEN (#1FB371) with NEAR-BLACK TEXT.
- Inter and Geist Mono load without FOUT.
- pnpm tsc --noEmit passes.
- pnpm lint passes (0 errors, 0 warnings).
```

---

### Prompt F2 — Hero + LiveSignalStrip + FinalCta

```
@AGENTS.md
@src/styles/globals.css
@src/app/layout.tsx
@src/components/layout/SiteHeader.tsx

Phase F2: Homepage Hero + LiveSignalStrip + FinalCta.

Build src/app/page.tsx and three components:
- src/components/home/Hero.tsx
- src/components/home/LiveSignalStrip.tsx
- src/components/home/FinalCta.tsx

Also build:
- src/content/copy.ts (founder name, email, LinkedIn)
- src/lib/signal.ts (returns { postsScanned, hot, scope } for the strip)
- src/components/ui/Button.tsx (Button primitive with variant: 'primary' | 'secondary' | 'quiet')

----------------------------------------------------------
Hero.tsx — exact specs (matches AGENTS.md §16.1)

- Server Component.
- Layout: content occupies cols 1–8 desktop (grid grid-cols-12), cols 1–12 mobile.
- Padding: pt-24 (96px) desktop, pt-16 (64px) mobile. pb-0.
- Min-height: 100vh - 72px header on desktop. On < 768px, size to content.
- The right column on desktop (cols 9–12) is EMPTY. No mockup, no illustration,
  no graphic, no abstract shape.
- LEFT-ALIGNED on every viewport. text-left, not text-center. This is the locked rule.

Content:
- H1 (display-xl):
    Eén lead. Eén installateur. Geen concurrentie.
  Inter 500, clamp(64px, 7vw, 88px), line-height 1.02, letter-spacing -0.025em,
  color var(--ink), max-width none (let it flow within cols 1–8).

- Sub-line (body-lg, mt-8 = 32px below H1):
    Exclusieve warmtepomp-leads voor installateurs in NL en BE. Gevonden waar
    klanten écht praten. Forums, communities, open social.
  Inter 400, 19px desktop / 17px mobile, line-height 1.55, color var(--ink-soft),
  max-width 540px.
  EXACT COPY. No em-dash. No rewording.

- Buttons (mt-12 = 48px below sub, gap-3 = 12px between):
    Primary:  "Start pilot — 5 gratis leads"  →  /pilot
    Secondary: "Bekijk voorbeeldleads"          →  /leads
  Stacked full-width on mobile.

The em-dash inside the primary CTA label is the ONE allowed em-dash in any CTA, per
the locked spec in AGENTS.md §16.1. Em-dashes are forbidden everywhere else.

----------------------------------------------------------
LiveSignalStrip.tsx — exact specs (matches AGENTS.md §16.2)

- 'use client' (handles the import of signal data via a server-passed prop is fine;
  use 'use client' only because the keyframe animation lives on this component).
- Position: mt-16 (64px below Hero), mb-16 (64px above next section).
- Single horizontal line, left-aligned within container.
- A 6px diameter circle in bg-[var(--signal-bright)] with class `animate-pulse-signal`
  defined in globals.css:
    @keyframes pulse-signal {
      0%, 100% { opacity: 0.4; }
      50%      { opacity: 1; }
    }
    .animate-pulse-signal {
      animation: pulse-signal 1.6s ease-in-out infinite;
    }
- Dot sits 12px to the left of the text.
- Line text (mono-sm var(--ink-mute), UPPERCASE +0.04em tracking):
    LIVE · vandaag 312 posts gescand · 17 HOT · NL + BE
- Numbers come from lib/signal.ts. Hard-code the fallback values above for V1.

This pulse dot is the ONLY animation on the entire site. Do not add anything else.

----------------------------------------------------------
FinalCta.tsx — exact specs (matches AGENTS.md §16.9)

- Full-width container.
- py-40 (160px) top/bottom desktop, py-24 (96px) mobile.
- Content centered (the ONE centered section on the homepage).

- H2 (display-md, centered, color var(--ink)):
    Klaar om 5 leads te bekijken?
- Sub (body-lg, mt-6 = 24px, max-width 480px centered, var(--ink-soft)):
    Geen creditcard. Geen contract. Ik mail je binnen 24 uur de eerste batch in je regio.
- Primary button (mt-10 = 40px below sub, centered):
    "Start pilot — gratis" → /pilot
- Below button (mt-6 = 24px, mono-sm var(--ink-mute) centered):
    Of mail direct: {founderEmail}
  Where {founderEmail} comes from content/copy.ts.

----------------------------------------------------------
Button.tsx — primitive (per AGENTS.md §9)

Accept variant: 'primary' | 'secondary' | 'quiet', size: 'md' (only md in V1),
asChild prop for use as <Link>. Implement per AGENTS.md §9.

- primary: bg-[var(--signal)] text-[var(--ink)] font-medium hover:bg-[var(--signal-hover)]
  active:bg-[var(--signal-active)] focus-visible:outline-2 focus-visible:outline-[var(--ink)]
  focus-visible:outline-offset-2 rounded-lg h-12 px-[22px] transition-colors duration-[150ms]
- secondary: bg-[var(--paper)] text-[var(--ink)] border border-[var(--ink)] font-medium
  hover:bg-[var(--paper-elevated)] focus-visible:outline-2 focus-visible:outline-[var(--ink)]
  focus-visible:outline-offset-2 rounded-lg h-12 px-[22px] transition-colors duration-[150ms]
- quiet: text-[var(--ink)] font-medium underline underline-offset-4
  hover:[text-decoration-color:var(--signal)] focus-visible:outline-2
  focus-visible:outline-[var(--ink)] focus-visible:outline-offset-2 focus-visible:rounded
  transition-colors duration-[150ms]

NO drop shadow. NO scale on hover. NO loading spinner inside. NO icon glued to label.
NO pill shape. NO outline-button-with-green-text variant. NO black-filled primary.

----------------------------------------------------------
page.tsx wiring:

<>
  <Hero />
  <LiveSignalStrip />
  {/* mid sections in F3-F4 */}
  <FinalCta />
</>

----------------------------------------------------------
DON'T:
- Center the Hero on any viewport.
- Add a hero image, illustration, mockup, blob, or aurora glow.
- Use bg-black or bg-[#000000] anywhere — primary buttons are bg-[var(--signal)].
- Add Tailwind's default `animate-pulse` — write the keyframes in globals.css.
- Add a third button variant.
- Add an em-dash anywhere other than the locked primary CTA label "Start pilot — 5 gratis leads".

DoD:
- Hero is left-aligned on 1440, 768, 375 px viewports.
- The H1 is fully readable in ≤ 3 seconds without scrolling.
- Primary CTA is GREEN. Secondary is OUTLINE INK. No black-filled buttons.
- LiveSignalStrip pulse dot animates at 1.6s loop.
- FinalCta is centered. The mono-sm email line below the button is visible.
- All routes still return 200.
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile Performance ≥ 95 on the preview URL.
```

---

### Prompt F3 — HowItWorks + ExampleLeadCard

```
@AGENTS.md
@src/app/page.tsx
@src/components/home/Hero.tsx
@src/components/home/LiveSignalStrip.tsx

Phase F3: HowItWorks teaser (3 steps, no icons) + ExampleLeadCard.

Build:
- src/content/leads.ts          (Lead type + 1 seed entry)
- src/components/home/HowItWorks.tsx
- src/components/home/ExampleLeadCard.tsx
- src/components/ui/Badge.tsx   (HOT badge primitive, reusable on /leads)

Then update src/app/page.tsx to insert <HowItWorks /> and <ExampleLeadCard />
between <LiveSignalStrip /> and <FinalCta />.

----------------------------------------------------------
src/content/leads.ts

- Define and export the Lead type EXACTLY as in AGENTS.md §20.
- Export const leads: Lead[] with 1 entry now (the remaining 8 land in F5):

  {
    id: 'wp-nl-001',
    status: 'HOT',
    country: 'NL',
    niche: 'warmtepomp',
    city: 'Eindhoven',
    sourceType: 'tweakers',
    sourceLabel: 'Tweakers — forum: 11k offerte',
    snippet: '"Heb offerte gehad, vind 11k te duur, iemand idee waar ik moet zoeken?"',
    context: 'gas-cv ±12 jaar, eigen woning, ISDE relevant',
    route: 'publieke reactie, evt DM',
    score: 87,
    date: '2026-05-09',
  }

The em-dash in `sourceLabel` is allowed because it's inside a mono label (rendered
in `mono-sm` per AGENTS.md §13). Em-dashes are forbidden in body text only.

----------------------------------------------------------
HowItWorks.tsx — exact specs (AGENTS.md §16.3)

- Server Component.
- Section padding: mt-[160px] above (chapter gap), mb-[120px] below.
- Container: max-width 1140px, px-8 desktop / px-5 mobile.
- H2 (display-md, left-aligned col 1, var(--ink)): "Hoe het werkt"
- Sub-line (body, mt-4 = 16px below H2, max-width 480px, var(--ink-soft)):
    Drie stappen. Geen platform, geen biedoorlog.
- Step blocks: mt-10 (40px below sub), grid grid-cols-12 desktop, flex-col mobile.
  Desktop: each step spans 4 cols. Mobile: stacked with 40px gap.

Per step block:
- Step prefix: mono-sm text-[var(--signal)] UPPERCASE — "01 ·" / "02 ·" / "03 ·"
- Step title: display-sm, mt-2 (8px below prefix)
- Step body: body, mt-4 (16px below title), var(--ink-soft), max-width 320px
- NO icons. NO border around the block. NO background tint. NO card-like surface.

Step content (EXACT, no rewording):

01 · Wij scrapen publieke intent.
We monitoren forums, communities en open social platforms waar mensen vragen stellen
over warmtepompen en airco. Alleen publiek, niets achter login.

02 · Wij classificeren op HOT of WARM.
Elke post wordt door een taalmodel beoordeeld op intent, urgentie en regio. Alleen
leads boven de drempel gaan eruit.

03 · Jij ontvangt de lead exclusief.
Eén lead is één installateur. Met bron-URL, samenvatting, regio, en een voorgestelde
route naar contact.

Below the step row (mt-10 = 40px, right-aligned within container):
A quiet button → /zo-werkt-het, label: "Lees de volledige methodologie →"

----------------------------------------------------------
Badge.tsx primitive

- Single component with variant: 'hot' | 'warm'
- 'hot': bg-[var(--signal-bright)] text-[var(--ink)] px-2 py-[3px] rounded-sm
  font-mono text-[12px] uppercase tracking-[0.04em] leading-none
- 'warm': bg-[var(--paper-inset)] text-[var(--ink-soft)] same size
- Used as <Badge variant="hot">HOT</Badge>

----------------------------------------------------------
ExampleLeadCard.tsx — exact specs (AGENTS.md §13 + §16.4)

- Server Component.
- Section padding: mt-[120px] above, mb-[120px] below.
- Container: max-width 1140px, grid grid-cols-12.
- H2 inside section, col 1–8 left-aligned: "Zo ziet een lead eruit"
- Sub (mt-4, body var(--ink-soft)):
    Een echte lead uit mei 2026. De bron-URL gaat alleen naar de koper.

- The LEAD CARD itself: max-width 720px, placed in cols 3–10 of the container grid
  (col-start-3 col-span-8 on desktop, col-span-12 on mobile), mt-10 below the sub.

Lead card anatomy (matches AGENTS.md §13 exactly):
- bg-[var(--paper-elevated)]
- border border-[var(--rule)]
- rounded-[12px] (--radius-xl)
- p-7 desktop (28px), p-5 mobile (20px)

Header row (flex justify-between items-center):
- Left: <Badge variant="hot">HOT</Badge>
- Right: mono-sm var(--ink-mute) — "Warmtepomp · NL · vandaag 09:14"

Body (mt-4, grid grid-cols-[max-content_1fr] gap-x-6 gap-y-4):
- For each row: label is mono-sm var(--ink-mute) UPPERCASE; value is body var(--ink).
- Rows in order: REGIO, BRON, SIGNAAL, CONTEXT, SCORE, ROUTE.

Divider: hr 1px var(--rule), my-4.

Snippet block: body var(--ink-soft), clamped to 3 lines (line-clamp-3).
Use <blockquote> for semantic correctness. Render leads[0].snippet directly
(no extra surrounding decorative quote marks — the data already includes "...").

Footer row (mt-4, mono-sm var(--ink-mute)):
    Geleverd aan: ███████ · 09 mei 2026
Render the seven block characters literally.

Below the card (mt-6, centered or quiet-link-style):
A quiet button → /leads, label: "→ Bekijk 8 andere voorbeelden"

----------------------------------------------------------
Update src/app/page.tsx:

<>
  <Hero />
  <LiveSignalStrip />
  <HowItWorks />
  <ExampleLeadCard />
  <FinalCta />
</>

----------------------------------------------------------
DON'T:
- Add icons to step blocks.
- Add a card-like border or background to step blocks.
- Use a different color for step prefixes — must be var(--signal) #1FB371.
- Center-align the section H2 or step blocks.
- Use --signal-bright anywhere except the HOT badge fill.
- Add drop shadows on the lead card.
- Linkify the lead card (it's an artifact, not navigation).
- Replace ███████ with anything else.

DoD:
- 5 sections visible in order: Hero · LiveSignalStrip · HowItWorks · ExampleLeadCard · FinalCta
- Vertical rhythm: 64 between hero and strip, 160 above HowItWorks, 120 between
  HowItWorks and Lead, 160 around FinalCta.
- HowItWorks step row has NO icons.
- Step prefix "01 ·" is colored var(--signal) #1FB371.
- Lead card sits in cols 3–10 (off-center), not centered, not full-width.
- HOT badge is the only --signal-bright element on the page.
- Redacted footer renders literally as "Geleverd aan: ███████ · 09 mei 2026".
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F4 — WhyDifferent + PricingTeaser + FaqSection + Founder

```
@AGENTS.md
@src/app/page.tsx
@src/components/home/ExampleLeadCard.tsx
@src/components/ui/Button.tsx

Phase F4: WhyDifferent + PricingTeaser + FaqSection + Founder.

Build:
- src/content/pricing.ts
- src/content/faq.ts
- src/components/home/WhyDifferent.tsx
- src/components/home/PricingTeaser.tsx
- src/components/home/FaqSection.tsx
- src/components/home/Founder.tsx
- src/components/ui/Accordion.tsx  (custom, single-open, no shadcn)

Then update src/app/page.tsx to insert the 4 new sections between
<ExampleLeadCard /> and <FinalCta />.

----------------------------------------------------------
src/content/pricing.ts

Export type PricingTier per AGENTS.md §20. Export const tiers: PricingTier[]:

[
  {
    id: 'pilot',
    name: 'Pilot',
    price: { amount: 0, currency: 'EUR', unit: 'eenmalig' },
    tagline: '5 gratis leads, geen creditcard.',
    features: [
      '5 HOT-leads',
      'Geen creditcard',
      'Eenmalig per installateur',
      'Exclusief',
      'Bron-URL erbij',
    ],
    cta: { label: 'Start pilot →', href: '/pilot' },
    highlight: false,
  },
  {
    id: 'ppl',
    name: 'Pay-per-lead',
    price: { amount: 75, currency: 'EUR', unit: 'per lead' },
    tagline: 'Exclusief, geen contract.',
    features: [
      'HOT-leads on demand',
      'Maandopzegbaar',
      'Geen minimum',
      'Exclusief',
      'Bron-URL erbij',
      'Money-back garantie',
    ],
    cta: { label: 'Start pilot →', href: '/pilot' },
    highlight: false,
  },
]

----------------------------------------------------------
src/content/faq.ts

Export type FaqItem per AGENTS.md §20. Export const homeFaq: FaqItem[] with the
7 entries from AGENTS.md §18 EXACTLY. Use ids 'q1' through 'q7'.

----------------------------------------------------------
WhyDifferent.tsx — exact specs (AGENTS.md §16.5)

- Server Component.
- Section padding: mt-[120px] above, mb-[120px] below.
- Container: max-width 1140px, grid grid-cols-12.
- Column: col-start-1 col-span-6 desktop, col-span-12 mobile. max-width 680px.
- LEFT-aligned.

H2 (display-md, var(--ink)): "Waarom exclusief het verschil maakt"

Directly below the H2 (no extra gap): a 64px-wide, 1px-tall horizontal rule in
bg-[var(--signal)]. Wrap as <span> with display block, w-16 h-px bg-[var(--signal)],
my-6 (24px above and below).

Three paragraphs, body-lg var(--ink), space-y-6 (24px between):

Paragraph 1:
Veel leadplatforms werken vanuit een formulier. De klant vult iets in, en de aanvraag
gaat naar drie of vier installateurs tegelijk. Je betaalt voor één lead, maar je deelt
hem met je concurrenten.

Paragraph 2:
Wij draaien het om. We vinden klanten op het moment dat ze nog vragen stellen, niet
als ze al offertes verzamelen. Daardoor kunnen we elke lead aan exact één installateur
leveren. Geen biedoorlog. Geen race om als eerste te bellen.

Paragraph 3:
Het verschil zit niet in de prijs. Het zit in het mechaniek.

EXACT copy. Werkspot is NOT named.

----------------------------------------------------------
PricingTeaser.tsx — exact specs (AGENTS.md §16.6 + §14)

- Section padding: mt-[120px] mb-[120px].
- Container max-width 1140px.
- H2 (display-md, left-aligned, var(--ink)): "Eerlijke prijzen, zonder vooraf-risico"
- Sub (body-lg, mt-4, max-width 540px, var(--ink-soft)):
    Eén lead gaat naar één installateur. Geen contract, geen minimum, money-back
    als de lead niet klopt.

Cards container (mt-10, grid grid-cols-12, gap-4 = 16px between cards):
- Each card: col-span-5 desktop, col-span-12 mobile.
- Wrap the grid so cards occupy cols 1–11 with col 12 as whitespace.

PricingCard structure (matches AGENTS.md §14):
- bg-[var(--paper-elevated)] border border-[var(--rule)] rounded-lg p-8 desktop / p-6 mobile.
- Card name display-sm.
- Price line: Inter 44px font-medium leading-[1.1] var(--ink). Mount as <span> "€{amount}".
- Unit: mono-sm var(--ink-mute) directly below, no top margin (mt-0 or mt-1).
- Tagline: body var(--ink-soft) mt-4.
- Divider: hr 1px var(--rule) my-4.
- Feature list (ul, space-y-3 = 12px): each <li> prefixed by '✓ ' as the first
  character of the rendered string. NOT a separate span with a color — just the
  text. The ✓ inherits var(--ink) text color.
- Button (mt-6, w-full inside card):
  - 'pilot' card → Button variant="secondary"  label="Start pilot →"  href="/pilot"
  - 'ppl' card   → Button variant="primary"    label="Start pilot →"  href="/pilot"

Below the cards (mt-8, centered): quiet link → /prijzen, label "→ Volledige prijzen-pagina"

DO NOT add a "Most Popular" highlight to either card. Both visually identical weight.

----------------------------------------------------------
Accordion.tsx — primitive

'use client'. Single-open behavior. No shadcn install.

Props: items: { id, question, answer }[].

Per item:
- <button aria-expanded={isOpen} className="w-full flex items-center justify-between
  py-6 border-t border-[var(--rule)] text-left">
    <span className="text-[19px] font-medium leading-[1.55] text-[var(--ink)]">
      {question}
    </span>
    <ChevronDown
      className="w-5 h-5 text-[var(--ink-mute)] transition-transform duration-200
                 ease-out shrink-0"
      style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)' }}
    />
  </button>
- <div className="grid transition-[grid-template-rows] duration-200 ease-out"
       style={{ gridTemplateRows: isOpen ? '1fr' : '0fr' }}>
    <div className="overflow-hidden">
      <p className="pt-3 pb-6 body text-[var(--ink-soft)] max-w-[64ch]">
        {answer}
      </p>
    </div>
  </div>

Last item gets a bottom border in --rule to close the stack.

Default state: all closed. Opening one item closes the others (single-open).

----------------------------------------------------------
FaqSection.tsx

- Section padding: mt-[120px] mb-[120px].
- Container max-width 1140px, grid grid-cols-12.
- Column: col-start-1 col-span-8, max-width 720px.
- H2 (display-md, left-aligned): "Veelgestelde vragen"
- mt-10: <Accordion items={homeFaq} />

----------------------------------------------------------
Founder.tsx — exact specs (AGENTS.md §16.8)

- Section padding: mt-[120px] mb-[120px].
- Container max-width 1140px, grid grid-cols-12.
- Photo: col-start-1 col-span-3 desktop, col-span-12 mobile. 160×160 circle.
  Use next/image with src="/founder.jpg" (placeholder if not yet uploaded).
  Wrap in a div with bg-[var(--paper-elevated)] so the image edge blends.
- Text column: col-start-5 col-span-6 desktop, col-span-12 mobile, mt-0 desktop / mt-6 mobile.
- Founder name: display-sm — "Ik ben {firstName}." (firstName from content/copy.ts)
- Paragraph (mt-4, body-lg var(--ink-soft)):
    Ik bouw lead-radar omdat installateurs nu nog geld betalen voor leads die ze met
    drie concurrenten delen. Ik laat dat anders werken. Vragen, klacht, of nieuwsgierig?
    Mail me direct.
- Two quiet links (mt-3, flex gap-6):
    "→ {email}"          (mailto:{email})
    "→ LinkedIn"          ({linkedinUrl})

----------------------------------------------------------
Update src/app/page.tsx:

<>
  <Hero />
  <LiveSignalStrip />
  <HowItWorks />
  <ExampleLeadCard />
  <WhyDifferent />
  <PricingTeaser />
  <FaqSection />
  <Founder />
  <FinalCta />
</>

----------------------------------------------------------
DON'T:
- Add a "Most Popular" / "Recommended" highlight on either pricing card.
- Use shadcn Accordion.
- Default-open any FAQ item.
- Add a drop shadow on the pricing card.
- Add a 3rd pricing tier.
- Add a monthly/annual pricing toggle.
- Add stock photo or placeholder smiling-person image for Founder.
- Add icons in pricing feature list (✓ is a text glyph, not an icon).
- Center the WhyDifferent column.

DoD:
- 9 homepage sections render in correct order.
- Vertical rhythm: 120 between mid sections, 160 around hero + FinalCta.
- Both pricing cards have identical visual weight.
- Pilot card has OUTLINE button. PPL card has GREEN FILLED button. Neither is black.
- Accordion toggles smoothly, no layout shift on open.
- aria-expanded toggles on each accordion trigger.
- Founder block has photo cols 1–3 and text cols 5–10 (visible asymmetric gap col 4).
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F5 — `/leads`

```
@AGENTS.md
@src/components/home/ExampleLeadCard.tsx
@src/content/leads.ts

Phase F5: /leads page — gallery, niche filter, empty state.

Build:
- Fill src/content/leads.ts to 9 entries total (1 already exists from F3).
- src/components/leads/LeadCard.tsx (extract reusable card from ExampleLeadCard)
- src/components/leads/NicheFilter.tsx ('use client')
- src/components/leads/LeadGallery.tsx ('use client', handles filter state)
- src/app/leads/page.tsx

----------------------------------------------------------
leads.ts — 8 additional entries

Add 8 more Lead entries beyond the existing leads[0]. Distribute across niches
and countries roughly:
- 4 warmtepomp (2 NL, 2 BE)
- 2 airco (1 NL, 1 BE)
- 2 zonnepanelen (1 NL, 1 BE)

Status mix: 6 HOT, 3 WARM (warm entries should be the less-urgent looking snippets).

Each entry must have all 11 fields populated. Snippets should sound real — quote
actual-sounding questions about price, brand, installation timing, regulations.
Use real Dutch/Belgian cities (Utrecht, Antwerpen, Groningen, Gent, Rotterdam,
Brugge, etc.). Use 'tweakers' | 'reddit' | 'facebook' | 'ouders' | 'bouwinfo' |
'klusidee' as sourceTypes. Dates: spread across April–May 2026, all in YYYY-MM-DD.

This is content work — produce 8 realistic-sounding entries inline. Founder will
review and replace with real bekomen leads before going to production.

----------------------------------------------------------
LeadCard.tsx

Extract the lead-card markup from ExampleLeadCard.tsx into a reusable component
that accepts `lead: Lead` as prop. Same styling (AGENTS.md §13). Used by
LeadGallery on /leads.

Difference from homepage version:
- On the homepage example, snippet is clamped to 3 lines.
- On /leads, snippet is NOT clamped (line-clamp-none).
- WARM badge uses <Badge variant="warm">WARM</Badge> when lead.status === 'WARM'.

Card is NOT clickable in V1. (Future: link to a static detail view. V1 ships as static.)

After extracting, update ExampleLeadCard.tsx to render <LeadCard lead={leads[0]} />
with a wrapper that adds the 3-line clamp.

----------------------------------------------------------
NicheFilter.tsx — 'use client'

Props: activeNiche: 'alle' | 'warmtepomp' | 'airco' | 'zonnepanelen', onChange.

Render 4 pills in a horizontal row (flex gap-2 mobile / gap-3 desktop):
- Each pill: <button> with text mono-sm UPPERCASE
- Inactive: bg-[var(--paper)] border border-[var(--rule)] text-[var(--ink-soft)]
  hover:border-[var(--ink)] rounded-md px-4 py-2 transition-colors duration-150
- Active: bg-[var(--ink)] text-[var(--paper)] border border-[var(--ink)]
- Labels: "Alle" "Warmtepomp" "Airco" "Zonnepanelen"

Behavior: click sets active. No URL state in V1.

----------------------------------------------------------
LeadGallery.tsx — 'use client'

Props: leads: Lead[].

State: const [activeNiche, setActiveNiche] = useState<NicheKey>('alle')

Filter: when activeNiche === 'alle', show all. Else filter lead.niche === activeNiche.

Render <NicheFilter> at top, then a grid:
- grid grid-cols-3 gap-6 desktop (24px gap)
- grid-cols-1 mobile
- mt-10 below the filter

Each cell renders <LeadCard lead={lead} />.

Empty state (if filteredLeads.length === 0):
- Centered narrow column max-width 480px.
- mono-sm var(--ink-mute):
    Geen voorbeelden in deze niche nog. Mail me of je toch wilt starten, dan kijken
    we naar volume.

----------------------------------------------------------
src/app/leads/page.tsx

Server Component. Imports leads from content/leads.ts and passes to <LeadGallery>.

Sections in order:

1. Page header
   - Container max-width 1140px, grid grid-cols-12
   - col-start-1 col-span-8
   - H1 (display-lg): "Voorbeeldleads"
   - Sub (body-lg mt-4 var(--ink-soft), max-width 640px):
       Negen recente leads, geredigeerd. De volledige lead met directe bron-URL
       ontvangt alleen de koper.

2. <LeadGallery leads={leads} />   (mt-16 below the header)

3. Methodology footnote (mt-[120px]):
   - Narrow column max-width 680px, var(--ink-soft) body:
       Wat je hier ziet is geredigeerd. De volledige lead, met directe bron-URL en
       route naar contact, gaat alleen naar de installateur die de lead koopt.

4. CTA block (mt-[160px] mb-[160px]):
   - Centered. H2 display-md: "Lijkt er één bij jouw regio?"
   - Sub body-lg var(--ink-soft) max-width 480px:
       Vraag de pilot aan, ik kijk welke open leads er nu voor jou liggen.
   - Primary button: "Start pilot →" → /pilot

Add Metadata export:
- title: "Voorbeeldleads — lead-radar"
- description: "Negen recente intent-leads, geredigeerd. Exclusief geleverd aan
  één installateur per regio."

----------------------------------------------------------
DON'T:
- Add URL state for the filter in V1 (no query params).
- Linkify the lead cards.
- Add a search box.
- Add pagination (only 9 entries).
- Add a "load more" button.
- Center the gallery on mobile (it's left-aligned in its container, naturally
  full-width as 1-col).

DoD:
- /leads renders 9 cards in 3×3 grid desktop, 1-col mobile.
- Niche filter pills work: click 'Warmtepomp' shows only warmtepomp leads.
- Click 'Airco' shows airco entries (should be 2 visible).
- Empty state appears if any niche has 0 entries.
- HOT and WARM badges render correctly.
- No overflow on 375px viewport.
- LeadCard component is reused on homepage ExampleLeadCard without regression.
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F6 — `/zo-werkt-het`

```
@AGENTS.md
@src/components/home/HowItWorks.tsx
@src/components/home/ExampleLeadCard.tsx
@src/components/leads/LeadCard.tsx

Phase F6: /zo-werkt-het — the deep methodology page.

Build:
- src/content/methode.ts            (deep step copy, "wat we niet doen" copy, tijdlijn data)
- src/components/methode/MechanismDeep.tsx
- src/components/methode/WhatLeadLooksLike.tsx
- src/components/methode/WatWeNietDoen.tsx
- src/components/methode/Tijdlijn.tsx
- src/components/methode/GdprBlock.tsx
- src/app/zo-werkt-het/page.tsx

----------------------------------------------------------
methode.ts content

Export const mechanism: { id, title, body }[] — 3 entries, deeper text than the
homepage teaser. The homepage uses 3-sentence summaries; this page uses ~80-word
paragraphs per step.

Step 01 — "Wij scrapen publieke intent"
Body should mention specific sources by name: Tweakers, Reddit r/zonnepanelen,
ouders.nl, bouwinfo.be, klusidee.nl, publieke Facebook-groepen. Explain that
the scraper runs every 4 hours.

Step 02 — "Wij classificeren op HOT of WARM"
Body should explain the LLM classification: intent, urgency, region. HOT = urgent
+ specific. WARM = exploring. Mention the score 0–100.

Step 03 — "Jij ontvangt de lead exclusief"
Body should describe what's IN a lead (bron-URL, samenvatting, regio, profiel,
score, route) and emphasize "één installateur per lead."

Export const watWeNietDoen: { id, line }[] — 5 entries, each ≤ 2 sentences:
- Geen scraping achter login. We crawlen alleen publieke pagina's. Geen account-
  scraping, geen private groups.
- Geen privébericht. We sturen niemand een DM in jouw naam. Wat je met de lead doet
  is aan jou.
- Geen marketplace-formulier. Klanten vullen niets in bij ons. Wij vinden hen
  waar ze al praten.
- Geen contract. Pay-per-lead is geen abonnement. Je stopt wanneer je wilt.
- Geen rebrand van Werkspot. We laten gedeelde leads aan anderen.

Export const tijdlijn: { time, label }[]:
[
  { time: '09:11', label: 'Gevonden' },
  { time: '09:13', label: 'Geclassificeerd' },
  { time: '09:14', label: 'Geleverd' },
  { time: '11:42', label: 'Gebeld door installateur' },
]

----------------------------------------------------------
src/app/zo-werkt-het/page.tsx — 7 sections

Container max-width 1140px throughout. Vertical rhythm 120px between sections,
160px around hero header and CTA.

Section 1 — Page header
- col-start-1 col-span-8 grid
- H1 (display-lg): "Hoe het werkt"
- Sub (body-lg mt-4 var(--ink-soft), max-width 640px):
    De volledige werking, zonder marketingvocabulaire.

Section 2 — MechanismDeep
- H2 (display-md): "Wat we doen"
- Three step blocks below, similar layout to HowItWorks but each step body is the
  longer paragraph from methode.ts.
- Step prefix "01 ·" / "02 ·" / "03 ·" in mono-sm var(--signal).
- Step title display-sm.
- Step body body var(--ink-soft), max-width 480px per step.
- Stack vertically (not 3-col row) because the bodies are too long for columns.
- 64px vertical gap between step blocks.

Section 3 — WhatLeadLooksLike
- H2: "Wat de installateur écht ontvangt"
- Sub (body var(--ink-soft) mt-4 max-width 540px):
    Hetzelfde voorbeeld als op de homepage, hier zonder ingekorte tekst. De bron-URL
    is het enige veld dat we voor de koper bewaren.
- mt-10: render <LeadCard lead={leads[0]} /> with line-clamp-none.

Section 4 — WatWeNietDoen
- H2: "Wat we niet doen"
- 5 paragraph blocks below in a single column, max-width 680px, space-y-8 (32px).
- Each item: bold or weight-500 first sentence ("Geen scraping achter login."),
  followed by an explanatory sentence in var(--ink-soft).
  Use Inter 500 for the first sentence, Inter 400 var(--ink-soft) for the rest.
  Do NOT use bullets or icons.

Section 5 — Tijdlijn
- H2: "Tijdlijn van een lead"
- Sub (body var(--ink-soft) mt-4):
    Concrete tijden uit een echte lead. Geen versnelde demo.
- mt-10: render the 4-step horizontal flow.
  Desktop: grid grid-cols-4 gap-6, each cell shows:
    - mono-sm var(--ink-mute) "09:11" (time)
    - display-sm mt-2 "Gevonden" (label)
    - Between cells: a 1px var(--rule) horizontal line at vertical-center, with a
      small "→" glyph in var(--ink-mute) overlaid.
  Mobile: flex-col, each cell stacks. Connect cells with a vertical 1px var(--rule).

Section 6 — GdprBlock
- H2: "GDPR en AVG"
- Paragraph block, max-width 680px:
    Alle leads komen uit publieke bronnen. Geen scraping van besloten of betaalde
    groepen. Geen privé-berichten. Je krijgt de bron-URL zodat je elke lead zelf
    kunt verifiëren. Wil je een lead laten verwijderen omdat een persoon daarom
    vraagt? Mail me, ik regel het binnen 24 uur.
- 1 quiet link below: "→ Mail me direct" → mailto:{email}

Section 7 — CTA block (mt-[160px] mb-[160px])
- Centered, same pattern as the /leads CTA.
- H2: "Klaar om de eerste batch te krijgen?"
- Sub body-lg max-width 480px:
    Start de pilot. 5 leads, geen creditcard, geen contract.
- Primary button: "Start pilot →" → /pilot

Add Metadata export:
- title: "Hoe het werkt — lead-radar"
- description: "Hoe lead-radar publieke intent vindt, classificeert en exclusief
  levert aan één installateur."

----------------------------------------------------------
DON'T:
- Add a comparison table with competitors.
- Name Werkspot, Slimster, or Solvari outside the existing locked "Geen rebrand van
  Werkspot" line in WatWeNietDoen.
- Add icons to the tijdlijn cells.
- Add scroll-triggered animations.
- Re-use the homepage HowItWorks component — this page has its OWN deeper version
  (MechanismDeep).

DoD:
- 7 sections render in correct order.
- Section 5 tijdlijn is horizontal on desktop, vertical on mobile.
- Section 3 lead card has no 3-line clamp (full snippet visible).
- Section 4 "Wat we niet doen" has 5 paragraph blocks, no bullets, no icons.
- The /zo-werkt-het link in the homepage HowItWorks teaser navigates here.
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F7 — `/prijzen`

```
@AGENTS.md
@src/components/home/PricingTeaser.tsx
@src/content/pricing.ts
@src/components/ui/Accordion.tsx

Phase F7: /prijzen — full pricing page.

Build:
- src/components/prijzen/PricingCard.tsx (extract from PricingTeaser)
- src/components/prijzen/MoneyBackBlock.tsx
- src/components/prijzen/LeadContents.tsx
- src/components/prijzen/PricingFaq.tsx (reuses Accordion)
- src/content/pricing-faq.ts
- src/app/prijzen/page.tsx

After extracting PricingCard, refactor PricingTeaser.tsx to use it.

----------------------------------------------------------
PricingCard.tsx — exact specs (AGENTS.md §14)

Same component used in PricingTeaser. Accepts `tier: PricingTier`. Renders the
full pricing card per the spec:

- bg-[var(--paper-elevated)] border border-[var(--rule)] rounded-lg
- p-8 desktop / p-6 mobile
- Name: display-sm var(--ink)
- Price: Inter 44px font-medium leading-[1.1] var(--ink) — render as "€{amount}"
- Unit: mono-sm var(--ink-mute) directly below
- Tagline: body var(--ink-soft) mt-4
- hr 1px var(--rule) my-4
- Feature ul with "✓ " text prefix
- Button: primary for 'ppl', secondary for 'pilot'

NO "Most Popular" highlight, ever, on either card.

----------------------------------------------------------
MoneyBackBlock.tsx

- bg-[var(--paper-inset)] rounded-lg p-8 desktop / p-6 mobile
- max-width 720px, centered or left-aligned in section depending on parent
- H3 (display-sm): "Money-back garantie"
- Body (body-lg var(--ink-soft) mt-4):
    Als een geleverde lead onbereikbaar blijkt of nep is, mail me binnen 7 dagen.
    Refund binnen 24 uur. Geen formulier, geen toelichting nodig.
- Signature (mt-6 right-aligned, mono-sm var(--ink-mute)):
    — {firstName}
  (the em-dash IS allowed here because it's inside a mono label)

----------------------------------------------------------
LeadContents.tsx

A single sentence + a 6-line list of what a lead contains.

- H3 (display-sm): "Wat zit er in een lead"
- Sub body var(--ink-soft) mt-4:
    Zes velden, één bron, één installateur.
- ul mt-6, space-y-3, body var(--ink). Each <li> prefix "· " (middot + space):
    bron-URL
    samenvatting van de intent
    regio en niche
    profielcontext (woningtype, leeftijd CV, indien bekend)
    score 0–100
    voorgestelde route naar contact

(The middot prefix here is a stylistic choice — NOT ✓, because this is a "fields"
list, not a "features" list.)

----------------------------------------------------------
pricing-faq.ts

Export const pricingFaq: FaqItem[] with the 4 items from AGENTS.md §19 EXACTLY.

----------------------------------------------------------
PricingFaq.tsx

Wraps <Accordion items={pricingFaq} /> with an H2 ("Veelgestelde vragen — prijzen")
above it. Max-width 720px col-start-1 col-span-8 grid.

----------------------------------------------------------
src/app/prijzen/page.tsx — 6 sections

Section 1 — Page header
- H1 display-lg: "Prijzen"
- Sub body-lg var(--ink-soft) mt-4 max-width 640px:
    Twee opties. Beide zonder contract. Beide met money-back.

Section 2 — Two pricing cards
- mt-16 below the header
- Container max-width 1140px, grid grid-cols-12, gap-4
- Cards span 5 cols each, centered in the grid (col-start-2 / col-start-7 on desktop),
  full-width stacked mobile
- Render both <PricingCard tier={pilot} /> and <PricingCard tier={ppl} />

Section 3 — MoneyBackBlock (mt-[120px])
- Container max-width 1140px, grid grid-cols-12
- col-start-3 col-span-8 (off-center)
- Render <MoneyBackBlock />

Section 4 — LeadContents (mt-[120px])
- Container max-width 1140px, grid grid-cols-12
- col-start-1 col-span-8 left-aligned
- Render <LeadContents />

Section 5 — PricingFaq (mt-[120px])
- Render <PricingFaq />

Section 6 — CTA block (mt-[160px] mb-[160px])
- Centered, same pattern as /leads CTA.
- H2: "Start met de pilot."
- Sub body-lg var(--ink-soft) max-width 480px:
    €0, 5 leads, geen creditcard.
- Primary button: "Start pilot →" → /pilot

Metadata:
- title: "Prijzen — lead-radar"
- description: "Twee transparante opties: een gratis pilot van 5 leads, en
  pay-per-lead à €75 zonder contract."

----------------------------------------------------------
DON'T:
- Add a monthly/annual toggle.
- Add a 3rd pricing tier.
- Add comparison vs competitors.
- Add testimonials.
- Add "Most Popular" highlights or color shifts on either card.
- Use red text for the money-back guarantee.
- Use a banner background for MoneyBackBlock.

DoD:
- 6 sections render in order.
- Both pricing cards are visually identical weight (no highlight, no border-color
  shift, no scale).
- Pilot card has OUTLINE button, PPL card has GREEN FILLED button.
- MoneyBackBlock has var(--paper-inset) background.
- PricingFaq accordion behaves identically to homepage FAQ.
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F8 — `/pilot` + intake API + `/bedankt`

```
@AGENTS.md
@src/components/ui/Button.tsx

Phase F8: Pilot intake — dedicated form page, API route, Resend wiring, post-submit page.

Build:
- src/lib/intake-schema.ts            (zod schema for form validation)
- src/lib/email.ts                    (Resend wrapper, 2 templates: intake-notification, applicant-confirmation)
- src/components/ui/Input.tsx
- src/components/ui/Select.tsx
- src/components/ui/Textarea.tsx
- src/components/ui/Label.tsx
- src/components/pilot/PilotForm.tsx  ('use client', react-hook-form + zod)
- src/components/pilot/PilotSideTrust.tsx
- src/app/pilot/page.tsx
- src/app/api/pilot/route.ts
- src/app/bedankt/page.tsx

----------------------------------------------------------
src/lib/intake-schema.ts

Export a zod schema `intakeSchema` and inferred type `IntakeInput`:

const intakeSchema = z.object({
  bedrijf:     z.string().min(2, 'Bedrijfsnaam ontbreekt').max(120),
  naam:        z.string().min(2, 'Naam ontbreekt').max(120),
  email:       z.string().email('Geen geldig e-mailadres'),
  telefoon:    z.string().regex(/^[\d\s+()-]{6,20}$/, 'Telefoonnummer klopt niet').optional().or(z.literal('')),
  niche:       z.enum(['warmtepomp', 'airco', 'zonnepanelen', 'anders']),
  regio:       z.string().min(1, 'Kies een regio'),
  opmerking:   z.string().max(500).optional().or(z.literal('')),
  // honeypot
  website:     z.string().max(0, 'spam').optional().or(z.literal('')),
});

----------------------------------------------------------
src/lib/email.ts

Export two functions:
- sendIntakeNotification(input: IntakeInput): notify founder email
- sendApplicantConfirmation(input: IntakeInput): confirm receipt to applicant

Both use Resend (process.env.RESEND_API_KEY). Plain-text templates (no HTML
templating in V1).

Founder email comes from process.env.FOUNDER_EMAIL.

----------------------------------------------------------
UI primitives

Input.tsx:
- <label> + <input>
- Input: w-full bg-[var(--paper)] border border-[var(--rule)] rounded-md
  px-[14px] py-[12px] text-[var(--ink)] body
- Focus: border-[var(--ink)] outline-2 outline-[var(--ink)] outline-offset-2
- Error: border-[var(--ink)] (NOT red), and helper text becomes weight-500 ink
  with a "✕ " prefix.

Select.tsx and Textarea.tsx: same surface + focus pattern.

Label.tsx: mono-sm UPPERCASE var(--ink-soft), mb-2.

----------------------------------------------------------
PilotForm.tsx — 'use client'

Uses react-hook-form with zodResolver(intakeSchema).

Form layout: vertical stack, max-width 480px within its column. space-y-6.

Fields in order (all rendered with <Label> + <Input>/<Select>/<Textarea>):
1. Bedrijfsnaam (text, required)
2. Naam (text, required)
3. E-mail (email, required)
4. Telefoon (tel, optional) — helper text: "Optioneel, voor snelle terugbel"
5. Niche (select, required) — options: Warmtepomp / Airco / Zonnepanelen / Anders
6. Regio (select, required) — optgroup "Nederland" with 12 provincies,
   optgroup "België" with 11 provincies (incl. Brussel), + final "Anders / nog onbekend"
7. Opmerking (textarea, optional, max 500) — helper: "Optioneel, vrije ruimte"

Honeypot (hidden input name="website") with aria-hidden, tabIndex=-1,
position absolute -left-[9999px].

Submit button at the bottom: Primary variant, label "Vraag de pilot aan",
w-full on mobile, content-width on desktop.

Submit handler:
- POST to /api/pilot with JSON body.
- On 200, redirect via router.push('/bedankt').
- On 4xx/5xx, show an inline error line above the submit button in mono-sm
  weight-500 var(--ink) prefixed with "✕ ":
    "✕ Iets ging mis bij verzenden. Mail me direct: {email} en ik los het op."
- During submission, disable the button (use the disabled style from Button.tsx)
  and show a `Verzenden...` line in mono-sm var(--ink-mute) below the button.
  NO spinner inside the button.

----------------------------------------------------------
PilotSideTrust.tsx — desktop-only side panel

- Hidden on mobile (md:block hidden).
- Renders inside the cols 7–12 column of /pilot's grid.
- Content:
   - A small lead-card-ish block. Use <LeadCard /> at scale ~75% (max-width 360px)
     OR a simplified preview component with the same visual language.
   - Below it (mt-6): mono-sm var(--ink-mute):
       Zo ziet je eerste lead eruit. De echte heeft een werkende bron-URL.

----------------------------------------------------------
src/app/pilot/page.tsx

Server Component for the layout, client form mounted inside.

Sections:

1. Page header (single full-width row above the form grid)
   - Container max-width 1140px, col-start-1 col-span-8 grid (header is asymmetric)
   - H1 display-lg: "Start je pilot"
   - Sub body-lg var(--ink-soft) mt-4 max-width 540px:
       5 leads in je niche en regio, binnen 24 uur. Geen creditcard, geen contract.

2. Body section (mt-16) — 12-col grid
   - Form column: col-start-1 col-span-6 desktop, col-span-12 mobile
     Wraps PilotForm. Form sits on var(--paper-elevated) bg, p-8 rounded-lg.
   - Trust column: col-start-7 col-span-6 desktop, hidden mobile
     Renders <PilotSideTrust />

3. Founder sub-block (mt-[120px]) — narrow column, same pattern as homepage Founder
   but scaled smaller. Photo 120×120, name display-sm, 2 quiet links.

Metadata:
- title: "Start pilot — lead-radar"
- description: "Vraag 5 gratis intent-leads aan. Geen creditcard, geen contract,
  binnen 24 uur in je inbox."

----------------------------------------------------------
src/app/api/pilot/route.ts

import { NextRequest, NextResponse } from 'next/server';
import { intakeSchema } from '@/lib/intake-schema';
import { sendIntakeNotification, sendApplicantConfirmation } from '@/lib/email';

// V1: in-memory rate limit per IP. Map<ip, timestamps[]>
const rate = new Map<string, number[]>();
const WINDOW_MS = 10 * 60 * 1000; // 10 min
const MAX_REQ = 3;

export async function POST(req: NextRequest) {
  const ip = req.headers.get('x-forwarded-for')?.split(',')[0].trim() ?? 'unknown';
  const now = Date.now();
  const recent = (rate.get(ip) ?? []).filter(t => now - t < WINDOW_MS);
  if (recent.length >= MAX_REQ) {
    return NextResponse.json({ error: 'rate-limited' }, { status: 429 });
  }
  rate.set(ip, [...recent, now]);

  const body = await req.json();
  const parsed = intakeSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid' }, { status: 400 });
  }
  // honeypot check
  if (parsed.data.website && parsed.data.website.length > 0) {
    return NextResponse.json({ ok: true }, { status: 200 }); // pretend success
  }

  await Promise.all([
    sendIntakeNotification(parsed.data),
    sendApplicantConfirmation(parsed.data),
  ]);
  return NextResponse.json({ ok: true }, { status: 200 });
}

----------------------------------------------------------
src/app/bedankt/page.tsx

Server Component. Centered narrow column max-width 560px, py-40.

- H1 display-lg centered: "Je pilot staat in de lijst."
- Body-lg mt-6 var(--ink-soft) centered:
    Ik mail je binnen 24 uur met je eerste batch leads. Vragen tussendoor? Mail direct.
- mt-8 quiet link centered: "→ {email}" (mailto)
- mt-16 body-sm var(--ink-mute) quiet link: "← terug naar home" (href="/")

Metadata:
- title: "Bedankt — lead-radar"
- description: "Je pilot-aanvraag is binnen. Binnen 24 uur ontvang je je eerste leads."
- robots: noindex

----------------------------------------------------------
DON'T:
- Use red color for error messages.
- Show a loading spinner inside the submit button.
- Add a multi-step form.
- Add a CAPTCHA (honeypot + rate-limit is enough for V1).
- Add a newsletter checkbox.
- Add a "I agree to terms" checkbox (link to /voorwaarden in helper text instead).
- Block the submit button while a field is empty — let zod do inline validation
  on submit attempt.
- Use #pilot-form anchor anywhere — /pilot is a dedicated route.

DoD:
- Submitting valid form → /bedankt + 2 emails sent (founder + applicant).
- Invalid form: zod errors inline, NO red color, NO red border.
- Honeypot: filled honeypot returns 200 to client but does NOT send emails.
- Rate-limit: 4th submit within 10 min from same IP returns 429.
- /bedankt is noindex.
- Side trust block hidden on mobile, visible on desktop.
- pnpm tsc + pnpm lint pass.
- Lighthouse mobile ≥ 95.
```

---

### Prompt F9 — SEO + analytics + utility pages + deploy

```
@AGENTS.md
@src/app/page.tsx
@src/app/zo-werkt-het/page.tsx
@src/app/leads/page.tsx
@src/app/prijzen/page.tsx
@src/app/pilot/page.tsx
@src/app/bedankt/page.tsx

Phase F9: SEO meta + Plausible + sitemap + robots + JSON-LD + /privacy + /voorwaarden + deploy doc.

Build:
- Per-route Metadata exports (finalize for / and any missed)
- src/app/sitemap.ts
- src/app/robots.ts
- src/app/opengraph-image.tsx
- src/components/seo/JsonLd.tsx
- src/content/legal.ts (privacy + voorwaarden prose)
- src/app/privacy/page.tsx
- src/app/voorwaarden/page.tsx
- Plausible script in src/app/layout.tsx (next/script, strategy="afterInteractive")
- DEPLOY.md (DNS + Vercel env setup steps)

----------------------------------------------------------
Per-route Metadata

Each page exports its own metadata. Pattern:

export const metadata = {
  title: '<page-specific> — lead-radar',
  description: '<page-specific, max 155 chars>',
  openGraph: { title, description, type: 'website', locale: 'nl_NL' },
  twitter: { card: 'summary_large_image' },
};

Homepage title: "lead-radar — exclusieve intent-leads voor installateurs"
Homepage description: "Vind klanten op het moment dat ze nog vragen stellen, niet
als ze al offertes verzamelen. Eén lead, één installateur."

----------------------------------------------------------
src/app/sitemap.ts

Default-exported function returning MetadataRoute.Sitemap with all 5 primary
routes + /bedankt (priority 0.3) + /privacy + /voorwaarden. Use a fixed lastModified
date (today's ISO date).

----------------------------------------------------------
src/app/robots.ts

Default-exported function returning:
- userAgent '*'
- allow '/'
- disallow ['/bedankt']
- sitemap '<absolute-domain>/sitemap.xml'

Domain comes from process.env.NEXT_PUBLIC_SITE_URL.

----------------------------------------------------------
src/app/opengraph-image.tsx

Edge runtime. Renders a 1200×630 image with:
- Background var(--paper) (#FAFAF7)
- Wordmark "lead-radar" top-left, Inter 500 32px var(--ink)
- Headline center-left: "Eén lead. Eén installateur. Geen concurrentie."
  Inter 500 ~72px clamp, line-height 1.05, var(--ink)
- Sub-line: "Exclusieve warmtepomp-leads voor installateurs in NL en BE."
  Inter 400 24px var(--ink-soft)
- A small horizontal var(--signal) accent rule bottom-left

No images, no gradients. Generate via the `next/og` ImageResponse helper.

----------------------------------------------------------
src/components/seo/JsonLd.tsx

A server component that emits a <script type="application/ld+json"> tag.
Accepts `data` prop (any). Used to inject schema.org JSON-LD on specific routes:

- Layout: Organization schema with name, url, email, logo (placeholder).
- Homepage: FAQPage schema generated from src/content/faq.ts.
- /prijzen: Product schema with offers (the two pricing tiers).

----------------------------------------------------------
Plausible

In src/app/layout.tsx <head>:
- <Script defer data-domain="<production-domain>" src="https://plausible.io/js/script.js"
  strategy="afterInteractive" />
- No GA, no GTM, no Hotjar.
- Site sends pageviews automatically; no custom events in V1.

----------------------------------------------------------
src/content/legal.ts + privacy/voorwaarden pages

Plain prose, max-width 680px, single column. Body-lg var(--ink) for paragraphs,
display-sm var(--ink) for headings, mono-sm var(--ink-mute) for the
"Laatst bijgewerkt: 2026-05-17" line beneath the H1.

/privacy must mention by name:
- The bronnen we scrape (Tweakers, Reddit, ouders.nl, bouwinfo.be, klusidee.nl,
  publieke Facebook-groepen)
- That only publieke data is processed
- That AVG-rights (inzage, verwijdering, bezwaar) can be exercised via the
  founder email
- Retention period (30 dagen na laatste contact / 90 dagen voor leads die
  zijn doorverkocht)
- Plausible cookieless analytics
- No third-party trackers

/voorwaarden must cover:
- Lead-levering en exclusiviteit
- Pay-per-lead facturatie
- Money-back garantie binnen 7 dagen
- Geen contract, opzegging op elk moment
- Aansprakelijkheid (uitgesloten behalve grove nalatigheid)
- Geschillen (NL recht, Rechtbank Oost-Brabant)

Treat these as legitimate legal prose, NOT templated boilerplate. Refer to
"lead-radar" by name throughout. Use first-person founder voice where applicable.

Both pages export robots: { index: true, follow: true } in metadata.

----------------------------------------------------------
DEPLOY.md (documentation file at repo root)

Single Markdown document covering:

1. Vercel project creation
2. Required env vars: RESEND_API_KEY, FOUNDER_EMAIL, NEXT_PUBLIC_SITE_URL
3. DNS records (A + AAAA + CNAME for www) for production domain
4. Plausible setup (add domain to Plausible dashboard)
5. Smoke-test protocol post-deploy:
   - GET /, /zo-werkt-het, /leads, /prijzen, /pilot, /privacy, /voorwaarden → all 200
   - POST /api/pilot with a valid payload (founder mailbox check)
   - Plausible "Realtime" shows current visit
   - Lighthouse mobile ≥ 95 on / and /prijzen
   - OG-image renders correctly (use a debug tool to preview)

No code in DEPLOY.md — operational documentation only.

----------------------------------------------------------
DON'T:
- Add Google Analytics or Google Tag Manager.
- Add Hotjar, Mixpanel, Segment, Posthog.
- Add Cookiebot or any cookie-consent banner (Plausible cookieless, no banner needed).
- Add a sitemap entry for /bedankt at priority > 0.3 (it's a confirmation page).
- Add a generated favicon with the AI brand colors of the dark-theme draft.
- Use Roboto or Open Sans in the OG image.

DoD:
- Every route has unique title + description in <head>.
- /sitemap.xml lists all primary + utility routes.
- /robots.txt disallows /bedankt.
- /opengraph-image.png renders for / with the locked H1.
- JSON-LD (Organization, FAQPage, Product) validates via the Schema.org Markup Validator.
- Plausible dashboard receives pageviews from production domain.
- /privacy mentions all bronnen by name.
- /voorwaarden references "lead-radar" by name throughout.
- DEPLOY.md exists at repo root.
- pnpm build green.
- Lighthouse mobile Performance ≥ 95, Accessibility ≥ 95, Best Practices ≥ 95,
  SEO ≥ 95 on /, /leads, /prijzen.
```

---

## 4. Cursor/Codex workflow rules

### Tool-to-task mapping

| Situation                              | Cursor tool       | Why                                    |
| -------------------------------------- | ----------------- | -------------------------------------- |
| New phase (multi-file diff)            | Composer (Cmd+I)  | Multi-file edits, single diff view     |
| One-component tweak                    | Inline edit (Cmd+K) | Faster, less context pollution       |
| Understanding / question               | Chat (Cmd+L)      | Read-only, no mutations                |
| Inject file context                    | `@filename.tsx`   | Native context mechanism               |
| Inject folder context                  | `@/components/home` | Multi-file reviews                   |
| Library API question                   | `@web`            | Library-specific lookups               |

### Reject-loop patterns

Reject a diff with a specific, narrow instruction. Never "do better."

| Output failure                                          | Reject prompt                                                                                                                                                |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Hero is centered                                        | "Hero is centered. Switch to left-aligned, content in cols 1–8 desktop, cols 1–12 mobile. text-left on every viewport."                                      |
| Button has a drop shadow                                | "Remove the drop shadow from the button. Hover effect is fill-color shift only — bg-[var(--signal-hover)]. No shadow, no scale."                              |
| Button uses bg-black or var(--ink) fill                 | "Black-filled buttons are forbidden site-wide (AGENTS.md §9). Switch the primary button fill to bg-[var(--signal)] with text-[var(--ink)]."                  |
| Section heading is centered                             | "Move the section H2 to the left of the container at col 1. Section headings are never centered (AGENTS.md §8). Only the FinalCta H2 is centered."             |
| Icons appear in step blocks                             | "Remove all icons from HowItWorks step blocks. The '01 ·' '02 ·' '03 ·' mono prefix is the only visual cue (AGENTS.md §16.3)."                                |
| Wrong color used as accent                              | "Two accent colors are not allowed (AGENTS.md §6 rule 4). Remove the blue. The only accents are var(--signal) #1FB371 and var(--signal-bright) #3EFFA1 (HOT badge only)." |
| Tailwind default color used                             | "Replace bg-blue-500 / bg-violet-500 / any Tailwind default. Use design tokens: bg-[var(--paper-elevated)], text-[var(--ink-soft)], etc."                    |
| Em-dash in body copy                                    | "Em-dash in body is forbidden (AGENTS.md §15). Replace with a period or comma. Em-dash is only allowed in mono labels and the locked button label 'Start pilot — 5 gratis leads'." |
| Italic text appears                                     | "Italic forbidden anywhere on the site (AGENTS.md §7). Replace with weight 500 or remove the emphasis."                                                       |
| font-bold (700) used                                    | "Weight 700+ forbidden (AGENTS.md §7). Inter 500 is the maximum weight. Replace font-bold with font-medium."                                                   |
| Pure white background                                   | "bg-white forbidden (AGENTS.md §26). Use bg-[var(--paper)] = #FAFAF7."                                                                                          |
| #pilot-form anchor                                      | "The pilot form lives at /pilot, not an anchor. Replace href='#pilot-form' with href='/pilot'."                                                              |
| Animation library installed                             | "Animation libraries are forbidden (AGENTS.md §3). Uninstall framer-motion / motion / gsap. Hover transitions use Tailwind transition-colors duration-150."  |
| 3-icon feature card grid                                | "3-icon feature card grid is the #1 AI tell (AGENTS.md §26). Remove the cards and icons. Use the HowItWorks no-icon layout instead."                          |

### When NOT to use Codex

Do these yourself:
- Typographic micro-tweak (1 padding, 1 color).
- Copy-edit of < 10 words.
- Import-order fix.
- Codex has failed twice on the same instruction.

---

## 5. Definition of Done per phase

Each phase's DoD must be fully ticked before its PR merges.

### F1 — Foundation
- [ ] `pnpm dev` starts with 0 warnings.
- [ ] All 8 placeholder routes return 200.
- [ ] `pnpm tsc --noEmit` passes.
- [ ] `pnpm lint` passes (0 errors, 0 warnings).
- [ ] Page background is `#FAFAF7`. Body text is `#0A0A0A`.
- [ ] SiteHeader is sticky and shows its bottom border only after scrolling 40px.
- [ ] SiteFooter renders on every page with 3 cols desktop / stacked mobile.
- [ ] Header "Start pilot" button is GREEN (`var(--signal)` `#1FB371`) with NEAR-BLACK text.
- [ ] Inter and Geist Mono load without FOUT.
- [ ] No dark-theme tokens (`--bg-base`, `--text-primary`, etc.) appear anywhere in the repo.

### F2 — Hero + LiveSignalStrip + FinalCta
- [ ] Hero is left-aligned on 1440 / 768 / 375 px.
- [ ] H1 reads in ≤ 3 seconds without scrolling.
- [ ] Primary CTA is GREEN. Secondary is OUTLINE INK. No black-filled buttons anywhere.
- [ ] LiveSignalStrip pulse dot animates at 1.6s loop with `var(--signal-bright)` color.
- [ ] FinalCta is centered. Mono-sm email line visible below the button.
- [ ] No mockup, illustration, blob, or gradient on the page.
- [ ] Lighthouse mobile Performance ≥ 95.

### F3 — HowItWorks + ExampleLeadCard
- [ ] 5 sections render: Hero · LiveSignalStrip · HowItWorks · ExampleLeadCard · FinalCta.
- [ ] Vertical rhythm: 64 between hero+strip, 160 above HowItWorks, 120 between HowItWorks+Lead, 160 around FinalCta.
- [ ] HowItWorks step row has NO icons, NO card borders.
- [ ] Step prefix `01 ·` is colored `var(--signal)`.
- [ ] Lead card sits in cols 3–10 (off-center), not centered, not full-width.
- [ ] HOT badge is the only `var(--signal-bright)` element on the page.
- [ ] Redacted footer renders literally as `Geleverd aan: ███████ · 09 mei 2026`.

### F4 — Why + Pricing + FAQ + Founder
- [ ] 9 homepage sections render in correct order.
- [ ] Both pricing cards visually identical weight (no highlight, no shift).
- [ ] Pilot card has OUTLINE button. PPL card has GREEN FILLED button.
- [ ] Accordion toggles smoothly, no layout shift on open.
- [ ] `aria-expanded` toggles per accordion trigger.
- [ ] Single-open accordion behavior verified (opening item 2 closes item 1).
- [ ] WhyDifferent column is narrow (max-width 680px) and left-aligned cols 1–6.
- [ ] Founder block: photo cols 1–3, text cols 5–10. Visible col-4 whitespace.

### F5 — `/leads`
- [ ] `/leads` renders 9 cards in 3×3 grid desktop, 1-col mobile.
- [ ] Niche filter pills work: clicking 'Warmtepomp' filters correctly.
- [ ] Empty state appears when a niche has 0 entries.
- [ ] HOT and WARM badges render correctly.
- [ ] No overflow at 375px.
- [ ] LeadCard component reused on homepage without regression.

### F6 — `/zo-werkt-het`
- [ ] 7 sections render in correct order.
- [ ] Section 5 tijdlijn is horizontal on desktop, vertical on mobile.
- [ ] Section 3 lead card shows full snippet (no line-clamp).
- [ ] Section 4 "Wat we niet doen" has 5 paragraph blocks, no bullets, no icons.
- [ ] The `Lees de volledige methodologie →` link in homepage HowItWorks navigates here.

### F7 — `/prijzen`
- [ ] 6 sections render in order.
- [ ] Both pricing cards visually identical weight.
- [ ] Pilot card has OUTLINE button. PPL card has GREEN FILLED button.
- [ ] MoneyBackBlock background is `var(--paper-inset)`.
- [ ] PricingFaq accordion behaves identically to homepage FAQ.

### F8 — `/pilot` + intake API + `/bedankt`
- [ ] Valid submit → `/bedankt` + 2 emails delivered (founder + applicant).
- [ ] Invalid form: zod errors inline, NO red color anywhere.
- [ ] Honeypot: filled honeypot returns 200 to client but does NOT send emails.
- [ ] Rate-limit: 4th submit within 10 min from same IP returns 429.
- [ ] `/bedankt` is `noindex`.
- [ ] PilotSideTrust is hidden on mobile, visible on desktop.
- [ ] Form sits on `var(--paper-elevated)` surface.

### F9 — SEO + analytics + utility + deploy
- [ ] Every route has unique title + description in `<head>`.
- [ ] `/sitemap.xml` lists all primary + utility routes.
- [ ] `/robots.txt` disallows `/bedankt`.
- [ ] `/opengraph-image.png` renders for `/` with the locked H1.
- [ ] JSON-LD (Organization, FAQPage, Product) validates via Schema.org Markup Validator.
- [ ] Plausible dashboard receives pageviews from production domain.
- [ ] `/privacy` mentions all bronnen by name.
- [ ] `/voorwaarden` references "lead-radar" throughout.
- [ ] `DEPLOY.md` exists at repo root with DNS + env-var steps.
- [ ] `pnpm build` green.
- [ ] Lighthouse mobile Performance ≥ 95, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 95 on `/`, `/leads`, `/prijzen`.

---

## 6. QA checklist per phase

Run before every merge. Save as `CHECKLIST.md` at repo root.

```
□ pnpm tsc --noEmit              → 0 errors
□ pnpm lint                      → 0 errors, 0 warnings
□ pnpm build                     → green
□ pnpm dev → every route returns 200

□ Vercel preview on:
  □ Chrome desktop 1440×900
  □ iPhone SE 375×667 (DevTools 4G throttle)
  □ iPad 768×1024

□ Lighthouse mobile (preview URL):
  □ Performance ≥ 95
  □ Accessibility ≥ 95
  □ Best Practices ≥ 95
  □ SEO ≥ 95

□ Keyboard-only navigation: tab through every interactive element, Enter/Space
  activate correctly, Escape closes mobile nav.

□ Visual check vs DESIGN-BRIEF.md and AGENTS.md.

□ Copy check vs AGENTS.md §15:
  □ No forbidden words (EN or NL)
  □ No em-dashes in body
  □ No italics, no serif
  □ No exclamation marks, no ellipses

□ Anti-AI tells grep (AGENTS.md §27):
  □ No `bg-gradient`
  □ No `shadow-lg` / `shadow-xl` / `drop-shadow`
  □ No `animate-pulse` (Tailwind default) — our pulse is custom
  □ No `italic` / `font-serif` / `font-bold`
  □ No `bg-blue-` / `bg-violet-` / `bg-purple-` / `bg-cyan-`
  □ No `#ffffff` / `#fff`
  □ No `#000000` / `#000`
  □ No "Most Popular", no "Trusted by"

□ Commit message follows the convention in §7.
```

---

## 7. Git workflow + commit conventions

### Branch strategy

- `main` is always deployable. Protected on GitHub.
- Feature branches: `feat/<NN>-<short-name>`. Example: `feat/04-home-complete`.
- One PR per phase. Squash-merge to `main`.
- Local micro-commits (`wip: ...`) allowed during development. Squash on merge.

### Commit message format

```
<type>(<scope>): <imperative subject ≤ 70 chars>

<optional body — what & why, not how>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Types: `feat` `fix` `refactor` `style` `docs` `chore` `perf` `test`
Scopes: `home` `methode` `leads` `prijzen` `pilot` `layout` `seo` `deploy` `agents` `tokens`

### Per-phase merge protocol

1. `pnpm verify` (npm script that chains tsc + lint + build) → green
2. Push branch
3. Open PR. Title = commit subject. Body = §5 DoD checklist + screenshots (1440, 768, 375).
4. Vercel preview URL pasted in the PR comments.
5. Self-review on a real mobile device.
6. Squash + merge to `main`.
7. Delete the remote branch.

### Forbidden in commits

- `.env.local`, `node_modules/`, `.next/` (gitignored)
- Half-working code (revert first)
- AI-generated commit messages without human review
- Commits authored by anything other than the developer (the Co-Authored-By line for Claude is fine)

---

## 8. Build order (dependency tree)

```
Layer 0 — Documentation (pre-F1)
  AGENTS.md, DESIGN-BRIEF.md, ORCHESTRATION.md, README.md,
  .env.example, .gitignore

Layer 1 — Configuration (F1)
  package.json, tsconfig.json, next.config.ts,
  tailwind.config.ts (Tailwind v4 still uses postcss config),
  postcss.config.mjs

Layer 2 — Foundation (F1)
  src/styles/globals.css         ← LIGHT-THEME design tokens (the load-bearing file)
  src/app/layout.tsx             ← fonts, theme, skip-link, Plausible (F9)
  src/lib/utils.ts               ← cn() helper

Layer 3 — Layout shell (F1)
  src/components/layout/SiteHeader.tsx
  src/components/layout/SiteFooter.tsx
  src/components/layout/MobileNav.tsx

Layer 4 — UI primitives (built as needed)
  Button (F2), Badge (F3), Accordion (F4),
  Input + Select + Textarea + Label (F8)

Layer 5 — Content (per phase)
  content/leads.ts              ← F3 (1 entry), F5 (8 more)
  content/pricing.ts            ← F4
  content/faq.ts                ← F4
  content/pricing-faq.ts        ← F7
  content/methode.ts            ← F6
  content/legal.ts              ← F9
  content/copy.ts               ← F2 (founder name/email/LinkedIn)

Layer 6 — Section components
  Home (F2-F4):  Hero, LiveSignalStrip, HowItWorks, ExampleLeadCard,
                 WhyDifferent, PricingTeaser, FaqSection, Founder, FinalCta
  Leads (F5):    LeadCard, NicheFilter, LeadGallery
  Methode (F6):  MechanismDeep, WhatLeadLooksLike, WatWeNietDoen, Tijdlijn, GdprBlock
  Prijzen (F7):  PricingCard, MoneyBackBlock, LeadContents, PricingFaq
  Pilot (F8):    PilotForm, PilotSideTrust

Layer 7 — Pages
  src/app/page.tsx                  ← grows F2 → F4
  src/app/leads/page.tsx            ← F5
  src/app/zo-werkt-het/page.tsx     ← F6
  src/app/prijzen/page.tsx          ← F7
  src/app/pilot/page.tsx            ← F8
  src/app/bedankt/page.tsx          ← F8
  src/app/privacy/page.tsx          ← F9
  src/app/voorwaarden/page.tsx      ← F9

Layer 8 — Backend
  src/lib/intake-schema.ts          ← F8
  src/lib/email.ts                  ← F8
  src/lib/signal.ts                 ← F2
  src/app/api/pilot/route.ts        ← F8

Layer 9 — SEO + analytics
  src/app/sitemap.ts                ← F9
  src/app/robots.ts                 ← F9
  src/app/opengraph-image.tsx       ← F9
  src/components/seo/JsonLd.tsx     ← F9
  Per-page metadata exports         ← F9 (and incrementally in F5-F8)
  Plausible script in layout.tsx    ← F9

Layer 10 — Deploy
  DEPLOY.md, Vercel env vars, DNS  ← F9
```

---

## 9. Component test order

Test the most-visible / most-risky components first.

| Priority | Component         | Why                                             | Test                                              |
| -------- | ----------------- | ----------------------------------------------- | ------------------------------------------------- |
| 1        | Hero              | First impression. 80 % of conversion.           | 1440 / 768 / 375 vs DESIGN-BRIEF §6.1. H1 in 3s.  |
| 2        | SiteHeader        | Every page. Sticky-bug = site-wide breakage.    | Scroll, mobile menu toggle, "Start pilot" CTA.    |
| 3        | LeadCard          | Central proof. Reused on /leads.                | 9 leads render. HOT/WARM badges. No overflow.     |
| 4        | PricingCard       | Conversion-critical.                            | Side-by-side equal weight. Pilot/PPL buttons.     |
| 5        | PilotForm         | The one form that must work.                    | Valid submit, invalid inline, honeypot, 429.      |
| 6        | LiveSignalStrip   | Only animation on the site.                     | Pulse dot loops smoothly, numbers are real.       |
| 7        | Accordion         | Keyboard accessibility critical.                | Tab + Enter/Space toggle, single-open behavior.   |
| 8        | NicheFilter       | First interactive client-state on /leads.       | Each pill filters correctly.                      |
| 9        | HowItWorks        | Static, low-risk.                               | Visual check, step prefix is green.               |
| 10       | WhyDifferent      | Pure copy.                                      | Read aloud vs AGENTS.md §16.5.                    |
| 11       | Founder           | Photo + asymmetric layout.                      | Photo loading, link correctness, col-4 whitespace.|
| 12       | MoneyBackBlock    | Inset surface.                                  | bg = paper-inset, founder signature right.        |
| 13       | Tijdlijn          | Horizontal-vs-vertical responsive switch.       | Desktop: 4 cells. Mobile: stacked.                |

---

## 10. Codex anti-instructions (DO NOT DO)

### Libraries
- ❌ `framer-motion`, `gsap`, `react-spring`, `motion`, `auto-animate`
- ❌ `@radix-ui/*` directly (only via hand-copied shadcn extracts)
- ❌ `styled-components`, `emotion`, `stitches`, `vanilla-extract`
- ❌ `@mui/*`, `@chakra-ui/*`, `@mantine/*`, `@nextui-org/*`, `antd`
- ❌ `swiper`, `embla-carousel`, `keen-slider`
- ❌ `react-toastify`, `sonner`
- ❌ `aos`, `wow.js`, `scrollreveal`
- ❌ `lodash`, `moment.js`, `dayjs`
- ❌ `react-icons` (Lucide only)

### Code patterns
- ❌ `any` (use `unknown` + narrowing)
- ❌ `@ts-ignore` / `@ts-expect-error`
- ❌ `console.log` in commits (lint rule)
- ❌ `dangerouslySetInnerHTML`
- ❌ Inline `style={{...}}` unless Tailwind cannot express it
- ❌ `useEffect` for data fetching
- ❌ `'use client'` at page level

### Product choices
- ❌ Extra pages outside the 8 specified
- ❌ Extra features outside the spec
- ❌ Placeholder content that reads as real ("John Smith, CEO at Acme")
- ❌ Persisting intake form to a database (V1 = Resend only)
- ❌ External services beyond Resend + Plausible

### Routing / anchors
- ❌ `#pilot-form` or any homepage anchor pointing at the intake form. The form lives at `/pilot`.

---

## 11. AI design-mistakes

| #  | Mistake                                                    | What instead                                                                    |
| -- | ---------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 1  | Linear-gradient hero `from-violet-500 to-cyan-500`         | Flat `var(--paper)` background                                                  |
| 2  | Aurora / glow behind H1                                    | The H1 stands on its own                                                        |
| 3  | Dot-grid pattern background                                | Plain background                                                                 |
| 4  | 3-column feature grid with emoji-icons                     | HowItWorks 3-step row, no icons, mono prefix                                    |
| 5  | "Trusted by" logo strip                                    | Nothing, or the founder statement                                                |
| 6  | Default-blue accent `#3b82f6`                              | `var(--signal)` `#1FB371` only                                                  |
| 7  | Black-filled primary button                                | `bg-[var(--signal)]` with `text-[var(--ink)]`                                   |
| 8  | Roboto / Open Sans / Poppins                                | Inter + Geist Mono (self-hosted)                                                |
| 9  | Italic serif text in hero                                  | No italic, no serif, ever                                                       |
| 10 | "Built with Next.js" badge                                  | Remove after scaffold                                                            |
| 11 | Carousel of testimonials                                    | Don't have testimonials yet, don't fake them                                    |
| 12 | "Most Popular" highlight middle pricing card                | Both cards identical weight                                                      |
| 13 | Stock photo of smiling employees                            | One real founder photo                                                           |
| 14 | Animated count-up "10,000+ users"                           | Real scraper numbers via `lib/signal.ts`, or omit                                |
| 15 | Scroll-triggered fade-in on every element                   | Static CSS                                                                       |
| 16 | "Get Started Free" generic CTA                              | "Start pilot — 5 gratis leads"                                                   |
| 17 | Hero headline > 88px                                        | Max 88px clamp                                                                   |
| 18 | Spatial metaphors ("navigeer het landschap")                | Concrete verbs (vinden, leveren, scrapen, mailen)                               |
| 19 | Em-dashes throughout body                                   | Periods and commas                                                               |
| 20 | Drop-shadows + neumorphism                                  | 1px hairline borders                                                             |
| 21 | Icons before every list-item                                | Unicode `✓` or no markers                                                        |
| 22 | "Powered by AI" badge                                       | AI is `how`, not `what`                                                          |
| 23 | "🌗 Dark/Light" theme toggle                                 | V1 light-only                                                                    |
| 24 | Hero with video background                                  | Static composition                                                               |
| 25 | Floating CTA button bottom-right                            | Inline CTAs only                                                                 |
| 26 | Page-load animation                                         | Direct content                                                                   |
| 27 | Light-theme with pure-white `#FFFFFF`                       | `var(--paper)` `#FAFAF7`                                                         |
| 28 | Pure-black `#000000` body text                              | `var(--ink)` `#0A0A0A`                                                           |
| 29 | Neon green `#3EFFA1` as button color                        | Deep green `var(--signal)` `#1FB371` for buttons; neon is for HOT badge only    |
| 30 | Hero illustration / 3D blob / floating shape                | The H1 alone in cols 1–8                                                         |

---

## 12. Performance-mistakes

| #  | Mistake                                       | How to avoid                                                              |
| -- | --------------------------------------------- | ------------------------------------------------------------------------- |
| 1  | Importing all of `lucide-react`               | Per-icon import: `import { Menu, ChevronDown } from 'lucide-react'`       |
| 2  | Fonts via Google CDN                          | `next/font/google` self-hosted                                            |
| 3  | `<img>` instead of `next/image`               | `next/image` everywhere, `priority` on hero photo only                    |
| 4  | `'use client'` too broadly                    | RSC by default. Opt-in only on interactive subtrees                        |
| 5  | No `width` / `height` on images               | Always props                                                              |
| 6  | Inline SVG for large illustrations            | We have none                                                              |
| 7  | `useState` for data RSC can serve             | Server-state default                                                      |
| 8  | External scripts without `next/script`        | `next/script` with `strategy="afterInteractive"`                          |
| 9  | Animation lib for one fade                    | Pure CSS `transition-colors`                                              |
| 10 | `console.log` in production                   | Strip via Next config                                                     |
| 11 | No `loading="lazy"` on offscreen images       | `next/image` does this by default                                         |
| 12 | OG image as a 4 MB JPG                        | Auto-generated via `opengraph-image.tsx` (Edge runtime)                   |
| 13 | `dynamic import` without need                 | Only for genuine lazy boundaries                                          |
| 14 | No route-level revalidate                     | Static = ISR default                                                      |
| 15 | Not analyzing bundle                          | F9: `@next/bundle-analyzer`, first-load < 100 kb gzipped                  |

---

## 13. UI/UX anti-patterns

| #  | Anti-pattern                              | What to do                                                                |
| -- | ----------------------------------------- | ------------------------------------------------------------------------- |
| 1  | Modal on page load                        | No modals in V1                                                           |
| 2  | Cookie banner over content                | Plausible cookieless, no banner needed                                    |
| 3  | Newsletter popup after 5s                 | Never                                                                     |
| 4  | Sticky chat widget                        | Founder email instead                                                     |
| 5  | "Read more" expanding text only           | Full text or a real link to a real page                                   |
| 6  | Scroll-jacking                            | Native scroll only                                                        |
| 7  | Hover-only navigation                     | Click is always available                                                 |
| 8  | Hamburger on desktop                      | Full nav on ≥ 768px                                                       |
| 9  | Carousels                                 | Grid                                                                      |
| 10 | Auto-playing video hero                   | No video                                                                  |
| 11 | Fake countdown timers                     | Real deadlines or nothing                                                 |
| 12 | "X people viewing this now"               | Never                                                                     |
| 13 | Registration required to see pricing      | Pricing visible immediately                                               |
| 14 | Multi-step form when one step suffices    | `/pilot` is one step, 7 fields                                            |
| 15 | Disabled CTA until email entered          | CTA active, inline validation                                             |
| 16 | "Subscribe to newsletter" footer           | No V1 newsletter                                                          |
| 17 | 100-link footer sitemap                   | Minimal footer (3 cols)                                                   |
| 18 | CAPTCHA on intake                          | Honeypot + rate-limit (V1)                                                |
| 19 | Pricing table with 30 features            | 5–6 features per card                                                     |
| 20 | "Choose your plan" header without context | Tagline + sub before pricing cards                                        |

---

## 14. Anti-AI-tells enforcement

Run grep against every diff before commit. Empty results = clean.

### 14.1 Word-level

Forbidden words (per AGENTS.md §15):

EN: `leverage`, `supercharge`, `robust`, `comprehensive`, `seamless`, `seamlessly`, `delve`, `navigate the landscape`, `ecosystem`, `journey`, `unlock`, `empower`, `transform`, `revolutionary`, `game-changing`, `cutting-edge`, `paradigm`, `AI-powered`, `powered by AI`, `intelligent`, `smart-platform`

NL: `naadloos`, `krachtig`, `ongeëvenaard`, `ontketenen`, `transformeren`, `revolutie`, `baanbrekend`, `intelligent`, `slimme oplossing`, `bij uitstek`, `het ecosysteem`, `de reis`

Use concrete verbs (vinden, leveren, scrapen, mailen). Use concrete nouns (Tweakers-forum, Eindhoven, warmtepomp). Use real numbers.

### 14.2 Layout-level

- **Symmetry test:** if every section is centered, the page reads as AI. Left-align as the default.
- **Size discipline:** no H1 > 88px, no body < 14px.
- **Whitespace test:** if elements can be made less compact, do so.
- **Asymmetry:** one off-axis section per page (Founder 2-col, ExampleLeadCard cols 3–10, WhyDifferent cols 1–6).
- **Sticky header:** the bottom border appears only after 40px scroll. This subtlety is a craft signal.

### 14.3 Typography-level

- No Roboto, Open Sans, Poppins, Lato, Montserrat.
- Inter weight 500 for display. Never 700.
- Mono only for data.
- `-0.02em` to `-0.025em` letter-spacing on display tokens.

### 14.4 Color-level

- One working accent (`var(--signal)`), one reserved flash (`var(--signal-bright)`).
- `#FAFAF7` paper has warmth (not pure `#FFFFFF`).
- `#0A0A0A` ink has warmth (not pure `#000000`).
- Strict palette of 9 tokens, no more.

### 14.5 Micro-interaction

- Hover states are color-only.
- No wow-animations. Border-color shift > glow pulse.
- Focus rings always 2px `var(--ink)` outline at 2px offset, never `outline: none`.

### 14.6 Copy test (the killer)

Read every paragraph aloud. If you wouldn't say it in a Slack message to an installer, rewrite.

> ❌ AI style: "We leverage cutting-edge intent data to seamlessly deliver high-quality, exclusive leads."
>
> ✅ Mens style: "We vinden klanten waar ze écht praten. Forums, communities, open social. Eén lead, één installateur."

### 14.7 Proof-level

- Real numbers > vague claims.
- Real faces > stock photos.
- Real sources > generic "data points".

### 14.8 Per-commit verification

Three questions before every commit:

1. Would I write this in a mail to an installer? No → rewrite.
2. Have I seen this layout 100× on landing pages? Yes → reduce ornamentation.
3. Does this feel from a person, or from a prompt? Must feel from a person.

Grep checklist (matches AGENTS.md §27):

```
✗ from-violet  ✗ to-cyan  ✗ from-blue  ✗ via-purple
✗ bg-gradient
✗ shadow-lg  ✗ shadow-xl  ✗ drop-shadow
✗ animate-bounce  ✗ motion.div
✗ italic  ✗ font-serif
✗ font-bold  ✗ font-extrabold  ✗ font-black
✗ bg-blue-  ✗ bg-violet-  ✗ bg-purple-  ✗ bg-cyan-
✗ #ffffff  ✗ #fff  ✗ rgb(255,255,255)
✗ #000000  ✗ #000  ✗ rgb(0,0,0)
✗ "AI-powered"  ✗ "leverage"  ✗ "supercharge"
✗ —  (em-dash in body — the only allowed em-dashes are inside mono labels and the locked Hero primary CTA label)
✗ "Most Popular"  ✗ "Recommended"
✗ "Trusted by"
✗ #pilot-form
```

Empty results across every line above = commit is clean.

---

## 15. What I need from the founder before F1 starts

1. **Domain confirmed** — proposal: `leadradar.nl` (fallback: `lead-radar.nl`).
2. **GitHub repo created** — proposed name: `lead-radar-site` (private).
3. **Pricing tiers V1** — confirmed: 2 (Pilot + Pay-per-lead). PPL price €75. Pilot €0.
4. **Founder name + email + LinkedIn URL** for `content/copy.ts`.
5. **Founder photo** — square JPG, 640×640 minimum, uploaded to `/public/founder.jpg` by F4.
6. **Voorbeeldleads content** — 9 real-but-anonymized HOT/WARM leads for `content/leads.ts` by F5. Template in F3 covers entry 1; the other 8 can be generated by Codex with realistic placeholder text, then validated by founder before merge.
7. **Resend account + API key** — required by F8.
8. **Plausible account + domain registered** — required by F9.
9. **Confirmation that AGENTS.md + DESIGN-BRIEF.md + this file are approved** — required before F1.

**No code starts until items 1, 4, and 9 are confirmed.**
