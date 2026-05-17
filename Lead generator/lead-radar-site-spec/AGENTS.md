# AGENTS.md — lead-radar-site

> Single source of truth for Codex/Cursor. Loaded as `@AGENTS.md` on every prompt. Everything you only want to say once, you say here.
>
> If anything in this file conflicts with `DESIGN-BRIEF.md`, the brief wins — this file is the engineering encoding of the brief. Mismatches are bugs in this file.

---

## 1. Project Context

This is the marketing website for **lead-radar**, an intent-based lead-generation service for installation companies in NL and BE (warmtepompen, airco, zonnepanelen, isolatie).

- **Status:** pre-launch, 0 paying customers, V1 = conversion-first.
- **Audience:** small and medium installation companies (3–15 FTE), 35–55 years old, skeptical of shared-lead platforms (Werkspot, Slimster, Solvari).
- **Core differentiator:** exclusive intent-leads from public sources — one lead per installer.
- **V1 conversion goal:** pilot-signups (5 free leads, no creditcard) via `/pilot`.

---

## 2. Stack

- Next.js 15 (App Router) + TypeScript strict
- Tailwind CSS v4 (CSS-first config via `@theme inline { }`)
- pnpm
- react-hook-form + zod (forms)
- resend (email)
- lucide-react (icons, used sparingly)
- Plausible (analytics, no GA, no GTM)
- Vercel (hosting)
- next/font with Inter + Geist Mono (self-hosted, no Google fetch)

---

## 3. Forbidden Dependencies

PRs that add any of the below are rejected.

- `framer-motion`, `motion`, `gsap`, `react-spring`, `auto-animate` — no animation libraries
- `@shadcn/ui` as a CLI install (we copy only what we need by hand)
- `styled-components`, `emotion`, `stitches`, `vanilla-extract`
- `@mui/*`, `@chakra-ui/*`, `@mantine/*`, `@nextui-org/*`, `antd`
- `swiper`, `embla-carousel`, `keen-slider` — no carousels in V1
- `react-toastify`, `sonner` — no toasts in V1
- `aos`, `wow.js`, `scrollreveal` — no scroll-triggered animations
- `lodash`, `moment.js`, `dayjs` — use native ES + `Intl`
- `react-icons` — Lucide only

---

## 4. Information Architecture

Five primary routes plus three utility routes. The pilot form is a dedicated page, not a homepage anchor.

| Route              | Page name (NL)    | Purpose                                | Nav         |
| ------------------ | ----------------- | -------------------------------------- | ----------- |
| `/`                | Homepage          | Convert cold visitors                  | (logo)      |
| `/zo-werkt-het`    | Hoe het werkt     | Deep methodology, trust-build          | 1           |
| `/leads`           | Voorbeeldleads    | Live proof gallery                     | 2           |
| `/prijzen`         | Prijzen           | Pricing detail + money-back + FAQ      | 3           |
| `/pilot`           | Start pilot       | Intake form + side trust artifact      | CTA button  |

Utility routes (no nav placement):
- `/bedankt` — post-intake confirmation
- `/privacy` — privacy policy, plain prose
- `/voorwaarden` — terms, plain prose

---

## 5. Directory Structure

```
src/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                       (homepage)
│   ├── zo-werkt-het/page.tsx
│   ├── leads/page.tsx
│   ├── prijzen/page.tsx
│   ├── pilot/page.tsx
│   ├── bedankt/page.tsx
│   ├── privacy/page.tsx
│   ├── voorwaarden/page.tsx
│   ├── api/pilot/route.ts
│   ├── sitemap.ts
│   ├── robots.ts
│   └── opengraph-image.tsx
├── components/
│   ├── layout/         (SiteHeader, SiteFooter, MobileNav)
│   ├── home/           (Hero, LiveSignalStrip, HowItWorks, ExampleLeadCard,
│                        WhyDifferent, PricingTeaser, FaqSection, Founder,
│                        FinalCta)
│   ├── methode/        (page sections for /zo-werkt-het)
│   ├── leads/          (LeadGallery, LeadCard, NicheFilter)
│   ├── prijzen/        (PricingCard, MoneyBackBlock, PricingFaq, LeadContents)
│   ├── pilot/          (PilotForm, PilotSideTrust)
│   └── ui/             (Button, Input, Select, Textarea, Accordion, Badge)
├── content/            (leads.ts, faq.ts, pricing.ts, pricing-faq.ts,
│                        methode.ts, copy.ts)
├── lib/                (utils.ts, email.ts, intake-schema.ts, signal.ts)
└── styles/             (globals.css)
```

One responsibility per file. If a file approaches 200 lines, split.

---

## 6. Design Tokens

All colors, radii, and spacing live as CSS custom properties in `globals.css`. Tailwind v4 picks them up via `@theme inline { }`. **Never use raw hex codes in components.** Always reference the token.

```css
:root {
  /* Surfaces — paper, never pure white */
  --paper:           #FAFAF7;   /* page background, default */
  --paper-elevated:  #F4F4EF;   /* card surface, one per page max */
  --paper-inset:     #EFEFEA;   /* inset block (money-back, founder quote) */

  /* Ink — near-black, never pure black */
  --ink:             #0A0A0A;   /* primary text, button text, link text */
  --ink-soft:        #4A4A48;   /* secondary text, subheads */
  --ink-mute:        #8A8A86;   /* tertiary text, timestamps, captions */

  /* Hairlines */
  --rule:            #E4E4DF;   /* all borders, 1px only */

  /* Signal — the one accent, two roles */
  --signal:          #1FB371;   /* working green — primary CTA fill, step prefixes, hover underlines */
  --signal-hover:    #2BC57F;   /* primary CTA hover */
  --signal-active:   #19A063;   /* primary CTA active */
  --signal-bright:   #3EFFA1;   /* reserved neon — HOT badge fill, live-ticker pulse dot ONLY */

  /* Radii */
  --radius-sm:       4px;       /* HOT badge */
  --radius-md:       6px;       /* inputs */
  --radius-lg:       8px;       /* buttons, pricing cards, generic cards */
  --radius-xl:       12px;      /* lead card only */
}
```

### Color usage rules

1. The page is 90% `--paper` + `--ink`. Everything else is rare.
2. `--signal-bright` neon (#3EFFA1) appears in exactly two places on the entire site: the HOT badge fill on lead cards, and the pulse dot on the live signal strip. Nowhere else.
3. `--signal` deep (#1FB371) is the primary CTA fill, the step-number prefix in HowItWorks, the focus-state underline shift on quiet links, and the 64px accent rule under the WhyDifferent H2. Nowhere else.
4. `--signal` and `--signal-bright` never touch — they are not adjacent within one composition.
5. No second accent. No blue links. No red errors (form errors use `--ink` weight 500 + `✕` glyph). No yellow warnings.
6. Charts or data viz, if any, use only `--ink` at 100 / 60 / 30 / 10 % opacity.

---

## 7. Typography

### Families

- `Inter` (variable), weights 400 / 500 / 600 only. **Never 700+.**
- `Geist Mono`, weight 400 only.
- Self-hosted via `next/font`. No Google CDN fetch. `display: swap`. Variables `--font-inter` and `--font-mono`.

### Scale

These are the only sizes that exist. No improvisation.

| Token         | Desktop          | Mobile | Weight | Line height | Tracking      | Use                                                       |
| ------------- | ---------------- | ------ | ------ | ----------- | ------------- | --------------------------------------------------------- |
| `display-xl`  | clamp(64,7vw,88) | 48     | 500    | 1.02        | -0.025em      | Homepage H1 only. One per site.                           |
| `display-lg`  | 56               | 38     | 500    | 1.05        | -0.022em      | Page H1 on `/zo-werkt-het`, `/leads`, `/prijzen`, `/pilot` |
| `display-md`  | 40               | 30     | 500    | 1.10        | -0.018em      | Section H2                                                |
| `display-sm`  | 28               | 24     | 500    | 1.20        | -0.012em      | Subsection H3, pricing card name, founder name            |
| `body-lg`     | 19               | 17     | 400    | 1.55        | 0             | Hero sub, long-form, FAQ question                         |
| `body`        | 16               | 16     | 400    | 1.62        | 0             | Default body                                              |
| `body-sm`     | 14               | 14     | 400    | 1.55        | 0             | Captions, footer body                                     |
| `mono-md`     | 14               | 14     | 400    | 1.50        | 0             | Lead data values                                          |
| `mono-sm`     | 12               | 12     | 400    | 1.45        | +0.04em UPPER | Labels (REGIO, BRON, SCORE), ticker text, timestamps      |

### Type rules

- **Italics: never.**
- **Serif: never.**
- All-caps: only on `mono-sm` labels.
- Hierarchy comes from **size + tracking**, not from weight. Inter 500 is the heaviest weight on the site.
- Body paragraphs cap at **64ch per line**. Use max-width to enforce this.
- `-0.02em` to `-0.025em` letter-spacing on display tokens. Default `0` elsewhere.

---

## 8. Layout & Vertical Rhythm

### Container widths

- Default content container: **max-width 1140px**, padding-x 32px desktop, 20px mobile.
- Narrow prose column (Why, How-it-works long-form, utility pages): max-width 680px.
- Form column on `/pilot`: max-width 560px.

### Grid

- 12 columns, 24px gutter desktop, 16px mobile.
- Default sections occupy cols 1–12 (full) or cols 1–8 (narrow content with right-side whitespace).
- **Asymmetric rule:** at least one section per page uses an off-center placement (cols 3–10 for the lead example, cols 1–6 for the Why column, cols 1–3 + 5–10 for the Founder block). Pages with all sections cols 1–12 read as templates.

### Horizontal alignment

- **Hero: left-aligned** on every viewport. Centered hero is the #1 cheap-template tell. Forbidden.
- Section H2s: left-aligned in the container's left gutter. Never centered.
- Long-form body: left-aligned within its narrow column.
- Pricing cards, FAQ items, ticker, founder block: left-aligned within their container.
- Centered alignment exists in exactly two places: the FinalCta block (centered signals "conclusion"), and inline status badges within a card.

### Vertical rhythm scale

Use only these gaps. Never improvise.

| Token         | Value | Use                                                                   |
| ------------- | ----- | --------------------------------------------------------------------- |
| `gap-micro`   | 4px   | icon-to-text                                                          |
| `gap-tight`   | 8px   | label-to-value                                                        |
| `gap-block`   | 16px  | within a block                                                        |
| `gap-para`    | 24px  | between paragraphs                                                    |
| `gap-loose`   | 40px  | between blocks within a section                                       |
| `gap-major`   | 64px  | mobile section-to-section, or under a section heading before content  |
| `gap-section` | 120px | default desktop section-to-section                                    |
| `gap-chapter` | 160px | around the hero, around the FinalCta. Twice per page maximum.         |

The asymmetry between 120 and 160 creates audible page tempo. Same gap everywhere = monotone.

### Surfaces

- **No drop shadows on any element.** Not on cards, not on buttons, not on the header. Ever.
- Elevation is shown by **either** a 1px hairline (`--rule`) **or** a background shift (`--paper` → `--paper-elevated`), **never both** at once.
- Cards radius: `--radius-lg` (8px). Lead card radius: `--radius-xl` (12px). Full-width sections and the hero have no radius.
- All borders are 1px `--rule`. There is no 2px border anywhere except the focus ring.

---

## 9. Buttons

Three variants. No others exist.

### Primary

Used for the conversion CTA across the site (`Start pilot`, `Vraag pilot aan`, `Start pilot — gratis`).

- Fill: `--signal` (#1FB371)
- Text: `--ink` (#0A0A0A), weight 500
- Padding: 14×22px desktop, 14×20px mobile
- Height: 48px
- Radius: `--radius-lg` (8px)
- Border: none
- Hover: fill shifts to `--signal-hover` (#2BC57F). 50ms ease-out. No scale, no shadow, no glow.
- Active: fill shifts to `--signal-active` (#19A063).
- Focus: 2px `--ink` outline at 2px offset (visible against paper).
- Disabled: fill `--rule`, text `--ink-mute`, cursor `not-allowed`.

### Secondary

Used as the alternate CTA (`Bekijk voorbeeldleads`, `Lees hoe het werkt`).

- Fill: `--paper` (matches page surface)
- Border: 1px `--ink`
- Text: `--ink`, weight 500
- Same padding, height, radius, focus as primary.
- Hover: fill shifts to `--paper-elevated`. Border stays `--ink`.
- Active: fill `--paper-inset`.

### Quiet

Inline text-style links (`→ alle voorbeelden bekijken`, `→ Volledige prijzen-pagina`, `→ Lees de volledige methodologie`).

- No border, no fill.
- Text: `--ink`, weight 500.
- Underline: 1px, offset 4px.
- Hover: underline color shifts to `--signal`. Text color stays `--ink`.
- Focus: 2px `--ink` outline at 2px offset, with a 4px rounded outline radius for legibility.

### Button rules

- **`--ink` is NEVER a filled button color.** Black-filled buttons are forbidden across the entire site.
- Pill shape (radius > 12px) on buttons is forbidden — reads as consumer app.
- An "outline button with green text" is forbidden — reads as a discount coupon.
- Arrow icons glued to button labels are forbidden — context implies action.
- Loading spinners inside buttons are forbidden. Use a separate inline state line (`Verzenden...` in `mono-sm` `--ink-mute` below the form).
- The only state shift on a button is fill-color. No scale, no shadow, no glow, no border-width change.

---

## 10. Forms

Inputs are quiet by default and become structural under focus.

- Background: `--paper`. Form sits on `--paper-elevated` for contrast.
- Border: 1px `--rule`.
- Radius: `--radius-md` (6px).
- Padding: 12×14px.
- Label: above input. `mono-sm` style (UPPERCASE). 8px gap before input.
- Helper text: below input. `body-sm` `--ink-mute`. 6px gap.
- Focus: border becomes `--ink`. Plus 2px `--ink` outline at 2px offset.
- Error: 1px `--ink` border (no red). Helper text becomes `--ink` weight 500, prefixed with a small `✕` glyph in `--ink`.
- Submit button: end of form. Full-width on mobile. Content-width (auto) on desktop.

---

## 11. Iconography

- **Lucide icons only.** Stroke-width 1.5px. Never filled. Never colored — always `--ink`.
- Sizes: 16×16 in body, 20×20 in headers, 24×24 in hero affordances.
- **Permitted:** chevrons on accordion, hamburger on mobile nav, external-link arrow on outbound links, LinkedIn glyph in footer.
- **Forbidden:** icons inside feature/step cards, icons before every list item (use `✓` glyph instead), icons as section decoration, Lottie animations, custom SVG illustrations of process flows.

---

## 12. Motion

The site barely moves. That is the point.

- **Allowed:** 150ms color or border-color transitions on hover/focus, `ease-out-quart`.
- **Allowed:** 200ms `height` transition on accordion expand, `ease-out-quart`.
- **Allowed:** one 1.6s opacity loop on the live-ticker pulse dot (`--signal-bright`, 0.4 → 1 → 0.4). This is the only "alive" animation on the entire site.
- **Forbidden:** scroll-triggered fade-ins, parallax, hover scale on cards/images, count-up number animations, page-load animations, marquee strips, layout-property transitions (top/left/width/height except the accordion height).

If a transition needs more than 200ms, it's not a transition, it's a state change. Render the new state discretely.

---

## 13. Lead Card spec

The most important component on the site. Treated as a redacted intelligence dossier, not a marketing card.

```
┌────────────────────────────────────────────────────┐
│ [HOT]   Warmtepomp · NL · vandaag 09:14            │  ← header row
│                                                    │
│ REGIO    Eindhoven                                 │
│ BRON     Tweakers — forum: 11k offerte             │
│ SIGNAAL  vraagt advies, wil 2e mening              │
│ CONTEXT  gas-cv ±12 jaar, eigen woning, ISDE       │
│ SCORE    87 / 100                                  │
│ ROUTE    publieke reactie, evt DM                  │
│ ─────────────────────────────────────────          │  ← divider
│   "Heb offerte gehad, vind 11k te duur, iemand     │
│    idee waar ik moet zoeken?"                      │  ← snippet
│                                                    │
│ Geleverd aan: ███████ · 09 mei 2026                │  ← redacted footer
└────────────────────────────────────────────────────┘
```

### Anatomy

- Background: `--paper-elevated`
- Border: 1px `--rule`
- Radius: `--radius-xl` (12px)
- Padding: 28px desktop, 20px mobile
- Header row: HOT badge (left) + source label (right). 16px below before body.
- Body: 2-column label/value grid. Labels `mono-sm` `--ink-mute`. Values `body` `--ink`. Vertical gap 16px between rows. Rows in order: Regio, Bron, Signaal, Context, Score, Route.
- Divider: 1px `--rule` above the snippet. 16px gap above and below.
- Snippet: `body`, `--ink-soft`. 3-line clamp on the homepage example. Full on `/leads`. No italics, no surrounding decorative quote marks (real quotes inside the snippet text are fine).
- Footer row: `mono-sm` `--ink-mute` — `Geleverd aan: ███████ · 09 mei 2026`. The redacted recipient block is rendered as a literal `███████` string (7 block characters).

### HOT badge

- Fill: `--signal-bright`
- Text: `--ink`
- Padding: 3×8px
- Radius: `--radius-sm` (4px)
- Style: `mono-sm` UPPERCASE — `HOT`
- This is the ONLY place `--signal-bright` is used on a static element.

### Source label (top right)

- Style: `mono-sm` `--ink-mute`
- Format: `Warmtepomp · NL · vandaag 09:14`

### Behavior

- Homepage example: not clickable. This is an artifact, not a navigation.
- `/leads`: each card opens a read-only static detail view that expands the snippet to full and shows the source URL un-clickable as `bron-URL: ████████████████` (also redacted — the URL is the paid product).

---

## 14. Pricing Card spec

Two cards on `/prijzen` and in the homepage `PricingTeaser`. **Identical visual weight.** No "Most Popular" highlight, ever.

- Background: `--paper-elevated`
- Border: 1px `--rule`
- Radius: `--radius-lg` (8px)
- Padding: 32px desktop, 24px mobile

Internal structure (top to bottom):

1. Card name: `display-sm` (`Pilot` or `Pay-per-lead`)
2. Price: Inter 44px weight 500, line-height 1.1, color `--ink` (`€0` or `€75`)
3. Unit: `mono-sm` `--ink-mute`, directly below the price, no extra gap (`eenmalig` or `per lead`)
4. Tagline: `body` `--ink-soft`, 16px below the unit
5. Divider: 1px `--rule`, 16px above and below
6. Feature list (5 items): each line prefixed `✓ ` (single Unicode `✓` glyph in `--ink`, not green), `body`, vertical gap 12px between items
7. Button: bottom of card, full-width within card
   - Pilot card → Secondary (outline `--ink`): `Start pilot →`
   - PPL card → Primary (filled `--signal`): `Start pilot →`

Both card CTAs go to `/pilot`. Conversion always flows through the pilot first.

---

## 15. Voice & Copy Rules

- **Dutch primary language.** Headlines, body, CTAs, errors. English only in code identifiers.
- Direct. Sober. Never breathless.
- Founder voice: first-person, mens-van-vlees-en-bloed. Not corporate.

### Forbidden words (any language)

EN: leverage, supercharge, robust, comprehensive, seamless, seamlessly, delve, navigate the landscape, ecosystem, journey, unlock, empower, transform, revolutionary, game-changing, cutting-edge, paradigm, powered by AI, AI-powered, intelligent, smart-platform.

NL: naadloos, krachtig, ongeëvenaard, ontketenen, transformeren, revolutie, baanbrekend, intelligent, slimme-oplossing, op maat (in marketing context), bij uitstek, het ecosysteem, de reis.

### Punctuation rules

- **No em-dashes (`—`) in body copy.** Use periods or commas. Em-dashes only appear inside mono labels (e.g. `Tweakers — forum: 11k offerte` inside a lead-card mono value).
- No exclamation marks. Ever.
- No ellipsis (`...`).
- No double-quotes around emphasis — use weight 500 or a `<blockquote>`.

### Number rules

- Numbers earn trust. If a claim has a number, the number is **real** (from the scraper or a known source) or **absent**.
- Forbidden: `10,000+ users`, `97% satisfaction`, `over 1M leads found`, `trusted by Fortune 500`.
- Permitted: today's actual scraper output (`vandaag 312 posts gescand · 17 HOT`), real founder-stated prices (`€75 per lead`), accurate FAQ figures (`3 tot 8 HOT-leads per week`).

### Concreteness rules

Speak in concrete things, not abstractions.

- `forum post`, `Tweakers draadje`, `Eindhoven`, `gas-cv 12 jaar oud`. Yes.
- `data points`, `signals`, `intent surface`, `lead pipeline`, `growth engine`. No.

---

## 16. Homepage canonical content

The homepage uses 9 sections. Locked copy below — Codex does not reword.

### 16.1 Hero (locked)

**H1** (`display-xl`):
```
Eén lead. Eén installateur. Geen concurrentie.
```

**Sub-line** (`body-lg`, `--ink-soft`, max-width 540px):
```
Exclusieve warmtepomp-leads voor installateurs in NL en BE. Gevonden waar klanten écht praten. Forums, communities, open social.
```

(Period replaces the em-dash from earlier drafts, per §15.)

**Buttons** (48px below sub-line, 12px gap between):
- Primary: `Start pilot — 5 gratis leads` → `/pilot`
- Secondary: `Bekijk voorbeeldleads` → `/leads`

Layout: cols 1–8 desktop, cols 1–12 mobile. Top padding 96px, bottom padding 0. Right column (9–12) desktop is empty. No mockup, no illustration, no abstract shape.

### 16.2 Live signal strip

Position: 64px below hero, 64px above HowItWorks teaser.

Content: a single `mono-sm` `--ink-mute` line with a 6px `--signal-bright` pulse dot 12px to the left.

```
●  LIVE · vandaag 312 posts gescand · 17 HOT · NL + BE
```

Numbers come from `lib/signal.ts` which reads the latest scraper output JSON (or a build-time fallback). Numbers must be real — if volume is low the line still tells the truth (`vandaag 84 posts gescand · 3 HOT · NL`).

The pulse dot is the only animated element on the site.

### 16.3 HowItWorks teaser (3 steps, no icons)

Section H2: `Hoe het werkt`
Sub-line: `Drie stappen. Geen platform, geen biedoorlog.`

Three step blocks in a row on desktop (each ~4 cols wide, 64px horizontal gap), stacked on mobile.

Each block:
- Step prefix `mono-sm` `--signal` — `01 ·`, `02 ·`, `03 ·`
- Step title `display-sm`, 8px below the prefix
- Step body `body` `--ink-soft`, 16px below the title, max-width 320px
- **No icons. No borders around the block. No background tint.**

**01 · Wij scrapen publieke intent.**
We monitoren forums, communities en open social platforms waar mensen vragen stellen over warmtepompen en airco. Alleen publiek, niets achter login.

**02 · Wij classificeren op HOT of WARM.**
Elke post wordt door een taalmodel beoordeeld op intent, urgentie en regio. Alleen leads boven de drempel gaan eruit.

**03 · Jij ontvangt de lead exclusief.**
Eén lead is één installateur. Met bron-URL, samenvatting, regio, en een voorgestelde route naar contact.

Bottom-right of section: quiet text-link `→ Lees de volledige methodologie` to `/zo-werkt-het`.

### 16.4 ExampleLeadCard

Section H2: `Zo ziet een lead eruit`
Sub-line: `Een echte lead uit mei 2026. De bron-URL gaat alleen naar de koper.`

40px below: single lead card from §13, max-width 720px, **placed in cols 3–10** (off-center, extra whitespace right). Uses `leads[0]` from `content/leads.ts`.

Below the card, centered: quiet link `→ Bekijk 8 andere voorbeelden` to `/leads`.

### 16.5 WhyDifferent

Narrow column, max-width 680px, cols 1–6 desktop, cols 1–12 mobile.

H2: `Waarom exclusief het verschil maakt`

Directly below the H2: a 64px × 1px `--signal` rule. 24px gap above and below the rule.

Three paragraphs, `body-lg`:

> Veel leadplatforms werken vanuit een formulier. De klant vult iets in, en de aanvraag gaat naar drie of vier installateurs tegelijk. Je betaalt voor één lead, maar je deelt hem met je concurrenten.
>
> Wij draaien het om. We vinden klanten op het moment dat ze nog vragen stellen, niet als ze al offertes verzamelen. Daardoor kunnen we elke lead aan exact één installateur leveren. Geen biedoorlog. Geen race om als eerste te bellen.
>
> Het verschil zit niet in de prijs. Het zit in het mechaniek.

Werkspot is not named.

### 16.6 PricingTeaser

H2: `Eerlijke prijzen, zonder vooraf-risico`
Sub-line `body-lg` `--ink-soft`, max-width 540px:
```
Eén lead gaat naar één installateur. Geen contract, geen minimum, money-back als de lead niet klopt.
```

40px below: two pricing cards from §14, side by side on desktop (cols 1–11 with cols 12 as whitespace), stacked on mobile, gap 16px.

Below the cards, centered: quiet link `→ Volledige prijzen-pagina` to `/prijzen`.

### 16.7 FaqSection

H2: `Veelgestelde vragen`

Accordion (custom, see §17.6 component spec). Content from §18 (7 items). Default all closed. Single-open behavior (opening one closes the others).

Max-width 720px, cols 1–8 (off-center).

### 16.8 Founder block

Off-axis layout — photo cols 1–3, text cols 5–10. On mobile: photo above text, both left-aligned, 24px gap.

- Photo: 160×160 circle, real founder photo, `next/image` priority, background tint blends to `--paper-elevated`.
- Founder name: `display-sm` — `Ik ben [Voornaam].`
- Body paragraph `body-lg` `--ink-soft`:
  ```
  Ik bouw lead-radar omdat installateurs nu nog geld betalen voor leads die ze met drie concurrenten delen. Ik laat dat anders werken. Vragen, klacht, of nieuwsgierig? Mail me direct.
  ```
- 12px below the paragraph: two quiet links in a row — `→ [voornaam]@leadradar.nl` and `→ LinkedIn`.

Founder name + email + LinkedIn URL come from `content/copy.ts` so they're swap-once.

### 16.9 FinalCta

Full-width container. Top padding 160px desktop, 96px mobile. Bottom padding 160px desktop, 96px mobile. **The one centered moment per page.**

H2 `display-md` centered:
```
Klaar om 5 leads te bekijken?
```

Sub-line `body-lg` `--ink-soft` max-width 480px centered:
```
Geen creditcard. Geen contract. Ik mail je binnen 24 uur de eerste batch in je regio.
```

Single primary button centered: `Start pilot — gratis` → `/pilot`.

24px below the button: `mono-sm` `--ink-mute` centered:
```
Of mail direct: [voornaam]@leadradar.nl
```

---

## 17. Other-page canonical content

### 17.1 `/zo-werkt-het` (Hoe het werkt)

Seven sections per `DESIGN-BRIEF.md` §5.3. Bronnen named explicitly in section 2:

```
Tweakers · Reddit r/zonnepanelen · ouders.nl · bouwinfo.be · klusidee.nl · publieke Facebook-groepen
```

Section 4 (Wat we niet doen) contains five short paragraphs as separate blocks, each ≤ 2 sentences, each starting with "Geen":
- Geen scraping achter login.
- Geen privébericht.
- Geen marketplace-formulier.
- Geen contract.
- Geen rebrand van Werkspot.

Section 5 (Tijdlijn van een lead) shows four numbered time-stamps as a horizontal flow desktop, vertical mobile. Times are real and concrete:
```
09:11 Gevonden  →  09:13 Geclassificeerd  →  09:14 Geleverd  →  11:42 Gebeld door installateur
```

### 17.2 `/leads`

Five sections per `DESIGN-BRIEF.md` §5.2. Lead gallery is a 3×3 grid on desktop, 1-col on mobile, 24px gap. Niche filter is client-state pills (Alle · Warmtepomp · Airco · Zonnepanelen). No URL state in V1.

Empty state when filter yields zero results: a narrow column with `mono-sm` text in `--ink-mute`:
```
Geen voorbeelden in deze niche nog. Mail me of je toch wilt starten, dan kijken we naar volume.
```

### 17.3 `/prijzen`

Six sections per `DESIGN-BRIEF.md` §5.4. MoneyBackBlock sits on `--paper-inset`:

```
Als een geleverde lead onbereikbaar blijkt of nep is, mail me binnen 7 dagen. Refund binnen 24 uur. Geen formulier, geen toelichting nodig.
                                                                            [Voornaam]
```

The signed-off founder first name is right-aligned `mono-sm` `--ink-mute`.

### 17.4 `/pilot`

Four sections per `DESIGN-BRIEF.md` §5.5. Two-column desktop layout (form cols 1–6, trust block cols 7–12). Side trust block hidden on mobile.

**Form fields** (in order):

1. Bedrijfsnaam — text, required
2. Naam — text, required
3. E-mail — email, required, format-validated
4. Telefoon — tel, optional, NL/BE phone validation
5. Niche — select, required, options: `warmtepomp` / `airco` / `zonnepanelen` / `anders`
6. Regio — select, required, options: NL provincies + BE provincies grouped, plus `Anders / nog onbekend`
7. Opmerking — textarea, optional, max 500 chars
8. Honeypot (hidden) — field name `website`, must remain empty

**Submit button**: full-width on mobile, content-width on desktop, end of form. Primary variant. Label: `Vraag de pilot aan`.

**Post-submit destination** is `/bedankt`.

**API route**: `app/api/pilot/route.ts`. On POST:
1. Validate with zod schema (`lib/intake-schema.ts`).
2. Reject if honeypot has any value.
3. Rate-limit per IP via in-memory Map (V1): 3 requests per 10 minutes per IP. Reject with 429 on exceed.
4. Send 2 emails via Resend: (a) intake notification to founder email, (b) confirmation to applicant.
5. Return 200 with redirect to `/bedankt`.

### 17.5 `/bedankt`

Single section, centered narrow column max-width 560px.

H1 `display-lg`:
```
Je pilot staat in de lijst.
```

Body paragraph `body-lg` `--ink-soft`:
```
Ik mail je binnen 24 uur met je eerste batch leads. Vragen tussendoor? Mail direct.
```

Quiet link below: `→ [voornaam]@leadradar.nl`.

Small `body-sm` `--ink-mute` quiet link at the bottom: `← terug naar home`.

### 17.6 Accordion component

Used on `/` (FAQ), `/prijzen` (PricingFaq). Custom-built. No shadcn install.

- Each item: 1px `--rule` top border, 24px padding top + bottom.
- Last item adds a 1px `--rule` bottom border to close the stack.
- Question: `body-lg` weight 500.
- Chevron: lucide `ChevronDown`, 20×20, `--ink-mute`, right-aligned, rotates 180° on open via 200ms transform transition.
- Answer (closed): height 0, opacity 0, padding 0.
- Answer (open): natural height, opacity 1, 12px padding top. Transition: height 200ms `ease-out-quart`.
- Answer text: `body` `--ink-soft`, max-width 64ch.
- `aria-expanded` attribute correct on the trigger button.
- Single-open behavior: opening one closes the others.
- All items closed by default.

---

## 18. FAQ content (homepage, 7 items)

**1. Wat krijg ik precies per lead?**
Een mail met bron-URL, samenvatting van de intent, regio, profielcontext (woningtype, leeftijd cv, waar bekend), score, en een voorgestelde route naar contact (publieke reactie, DM, of e-mail als gevonden).

**2. Hoe weet ik dat de leads echt zijn?**
Bij elke lead krijg je de bron-URL. Klik erop en je leest het originele bericht. We sturen niets door dat we niet zelf kunnen aanwijzen op een publieke site.

**3. Mag dit juridisch, GDPR / AVG?**
Ja. Alle leads komen uit publieke bronnen. Geen scraping van besloten of betaalde groepen, geen privé-berichten. Je krijgt de bron-URL zodat je het zelf kunt verifiëren.

**4. Wat als er geen leads in mijn regio zijn?**
Dan betaal je niets. Pay-per-lead betekent letterlijk: alleen betalen bij levering. We rapporteren wekelijks transparant wat er gevonden is en waar.

**5. Hoe vaak komen er nieuwe leads?**
Onze scraper draait elke 4 uur. Volume per regio en niche verschilt. Warmtepomp NL heeft typisch 3 tot 8 HOT-leads per week.

**6. Kan ik stoppen wanneer ik wil?**
Ja. Pay-per-lead is geen contract. Je koopt per lead. Stoppen is gewoon stoppen.

**7. Wie zit hier achter?**
[Voornaam], solo founder. Mailadres en LinkedIn vind je onderaan deze pagina. Geen support-bot, geen ticketing.

---

## 19. Pricing FAQ content (`/prijzen`, 4 items)

**1. Krijg ik de leads in batches of één voor één?**
Eén voor één, zodra ze gevonden zijn. Geen wachtmoment, geen verzamelweek.

**2. Kan ik mijn regio of niche tijdens de maand wijzigen?**
Ja. Mail me, ik pas het binnen 24 uur aan. Geen administratie.

**3. Doen jullie facturatie per maand of per lead?**
Pay-per-lead: factuur achteraf. Eén per lead of gebundeld per maand, jouw keuze.

**4. Wat als een geleverde lead onbereikbaar of fake blijkt?**
Money-back. Mail me met de lead-ID binnen 7 dagen, ik refund.

---

## 20. Content Type Shapes

```ts
type Lead = {
  id: string;                                   // 'wp-nl-001'
  status: 'HOT' | 'WARM';
  country: 'NL' | 'BE';
  niche: 'warmtepomp' | 'airco' | 'zonnepanelen' | 'cv';
  city: string;
  sourceType: 'tweakers' | 'reddit' | 'facebook' | 'ouders'
            | 'bouwinfo' | 'klusidee';
  sourceLabel: string;                          // 'Tweakers — forum: 11k offerte'
  snippet: string;
  context?: string;
  route?: string;                               // 'publieke reactie, evt DM'
  score: number;                                // 0–100
  date: string;                                 // ISO 'YYYY-MM-DD'
};

type FaqItem = {
  id: string;
  question: string;
  answer: string;
};

type PricingTier = {
  id: 'pilot' | 'ppl';
  name: string;
  price: { amount: number; currency: 'EUR'; unit: string };
  tagline: string;
  features: string[];
  cta: { label: string; href: string };
  highlight: false;                             // hard-coded false in V1
};

type MethodeBlock = {
  id: string;
  title: string;
  body: string;
};
```

---

## 21. Code Conventions

- One component per file. Default export at the bottom.
- File names: PascalCase for components, kebab-case otherwise.
- **Server Components by default.** Opt into `'use client'` only when needed (forms, accordion, filter pills, mobile nav).
- Prefer composition over props-explosion. > 5 props = consider splitting.
- No prop-drilling deeper than 2 levels — lift to `content/` or context.
- Strict TypeScript. **No `any`. No `@ts-ignore`. No `@ts-expect-error`.**
- Imports grouped: (1) react/next, (2) external libs, (3) `@/components`, (4) `@/lib`, (5) `@/content`, (6) relative.
- Tailwind class order: layout → spacing → sizing → typography → colors → effects → responsive (mobile-first).
- Use `clsx` or template-literals for class composition. **No string concat for classes.**
- No `dangerouslySetInnerHTML`.
- No inline `style={{...}}` unless Tailwind cannot express it.
- No `useEffect` for data fetching. Use Server Components and Next data primitives.
- No `'use client'` at page level — push the boundary down to the interactive subtree.

---

## 22. Performance Budgets

- Lighthouse Mobile Performance ≥ 95 per route
- LCP < 1.8s
- CLS < 0.05
- First-load JS < 100kb (gzipped) per route
- Images: WebP/AVIF via `next/image`, explicit width/height, `priority` on hero photo only
- Fonts: variable, subset, `display: swap`, `preload` Inter only

---

## 23. Accessibility

- All interactive elements keyboard-reachable.
- `aria-expanded` on accordion triggers.
- `aria-label` on icon-only buttons (mobile menu hamburger, external-link arrows).
- Color contrast ≥ 4.5:1 for body, ≥ 3:1 for large text. The `--signal` button (`#1FB371`) with `--ink` text (`#0A0A0A`) passes AA easily.
- Skip-to-content link in `layout.tsx`.
- Focus rings visible on every focusable element. **Never `outline: none` without a replacement.**
- Form fields have associated labels via `htmlFor` / `id`. Helper text linked via `aria-describedby`.
- Lead-card snippets use `<blockquote>` semantically.

---

## 24. Testing Requirements

- `pnpm tsc --noEmit` passes on every commit.
- `pnpm lint` passes on every commit (0 errors, 0 warnings).
- `pnpm build` green on every commit.
- Manual on Vercel preview: 375px, 768px, 1440px viewports.
- Lighthouse CI configured by F10.
- Visual regression check against the wireframe before merge.

---

## 25. Commit Convention

```
<type>(<scope>): <imperative subject, ≤ 70 chars>

<optional body — what & why, not how>

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

Types: `feat` `fix` `refactor` `style` `docs` `chore` `perf` `test`
Scopes: `home` `methode` `leads` `prijzen` `pilot` `layout` `seo` `deploy` `agents` `tokens`

One PR per phase. Squash-merge to main.

---

## 26. Forbidden UI Patterns

If a diff contains any of the below, reject it.

### Visual

- Linear, radial, conic, or mesh gradient backgrounds, any color, any direction
- Aurora / glow effects behind text
- Dot-grid or grid background patterns
- 3D blob backgrounds, floating shapes
- Drop shadows on cards, buttons, or any element
- Glassmorphism (`backdrop-blur` + transparent fill) used decoratively
- Gradient text (`background-clip: text`)
- Pure `#FFFFFF` background — always `--paper`
- Pure `#000000` text — always `--ink`
- Black-filled buttons — always `--signal` for primary, outline `--ink` for secondary
- Side-stripe borders (`border-left` / `border-right` > 1px as colored accents)

### Layout

- Centered hero headline + button + sub-line
- Three-icon feature grid (icon + heading + 2 sentences × 3)
- Icons inside step/feature cards
- "Trusted by" customer logo strip
- "Most Popular" / "Recommended" highlight on a pricing card
- Pricing toggle (monthly / annual)
- Floating CTA button in the bottom corner
- Sticky chat widget
- Cookie consent banner blocking content
- Modal on page load
- Newsletter signup in footer or anywhere
- Hamburger menu on desktop

### Typography

- `Roboto`, `Open Sans`, `Poppins`, `Lato`, `Montserrat` — Inter only
- Italic text anywhere
- Serif font anywhere
- Bold weight 700+ on any heading — 500 is the maximum
- Em-dashes in body copy
- All-caps outside `mono-sm` labels
- Body text smaller than 14px
- Headings larger than 88px

### Content

- Stock photography (people, handshakes, buildings)
- AI-generated illustrations
- Logo strips of customers we don't have
- "AI-powered" / "Powered by AI" badges
- Animated count-up numbers ("10,000+ posts scanned")
- Buzzwords (see §15)
- Fake countdown timers
- "X people viewing this now"
- Built-with-Next.js badges or other framework badges

### Behavior

- Scroll-jacking, parallax, locomotive-scroll
- Scroll-triggered fade-ins on every section
- Carousels of any kind
- Hover-only navigation
- Auto-playing video hero
- Page-load animations
- Hover-scale on cards or images
- Loading spinners inside buttons

---

## 27. Anti-AI-Tells Checklist (per commit)

Before committing, ask:

1. Would I say this in a Slack message to an installer? If not, rewrite.
2. Have I seen this layout 100× on other landing pages? If yes, reduce ornamentation.
3. Does this feel like a product from a person, or a product from a prompt? It must feel like a person.

Then grep the diff for these tells:

```
✗ from-violet  ✗ to-cyan  ✗ from-blue  ✗ via-purple    (gradient classes)
✗ bg-gradient                                          (any tailwind gradient)
✗ shadow-lg  ✗ shadow-xl  ✗ drop-shadow                (drop shadows)
✗ animate-bounce  ✗ animate-pulse  ✗ motion.div        (motion lib or bounce)
✗ italic                                               (italics forbidden)
✗ font-serif                                           (serif forbidden)
✗ font-bold  ✗ font-extrabold  ✗ font-black            (weight ≥ 600 forbidden)
✗ bg-blue-  ✗ bg-violet-  ✗ bg-purple-  ✗ bg-cyan-     (Tailwind default accents)
✗ #ffffff  ✗ #fff  ✗ rgb(255,255,255)                  (pure white forbidden)
✗ #000000  ✗ #000  ✗ rgb(0,0,0)                        (pure black forbidden)
✗ "AI-powered"  ✗ "leverage"  ✗ "supercharge"          (buzzwords)
✗ —                                                    (em-dash in body copy)
✗ "Most Popular"  ✗ "Recommended"                      (pricing highlight)
✗ "Trusted by"                                         (fake social proof)
```

Empty grep results on all of the above = commit is clean.

---

## 28. When You Are Uncertain

- **Design ambiguity:** prefer simpler, more sober, less decorative. When in doubt, remove rather than add.
- **Copy ambiguity:** prefer concrete and short. Replace abstractions with specific nouns.
- **Color ambiguity:** if you're tempted to use a second accent, you're wrong. Use `--ink` or `--ink-soft`.
- **Spacing ambiguity:** use the next-larger gap from §8's scale, never improvise.
- **Structural ambiguity:** stop and ask. Do not invent.

---

## 29. Authority Hierarchy

1. `DESIGN-BRIEF.md` — strategic and visual direction. If this file (`AGENTS.md`) contradicts the brief, this file is wrong; fix this file.
2. `AGENTS.md` (this file) — implementation rules. Codex follows this on every prompt.
3. `ORCHESTRATION.md` — build-phase order and Codex prompts. Updated to reference the new routes and the light-theme rebuild.
4. Founder verbal approval — overrides any document on a per-decision basis, but must be reflected in a doc update before merge.
