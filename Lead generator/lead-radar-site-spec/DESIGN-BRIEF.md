# Lead Radar — Website Design Brief

**Status:** v2 redirect from dark theme to strict light theme
**Authority:** Overrides `AGENTS.md` where they conflict. `AGENTS.md` will be reissued after approval.
**Audience:** Codex (implementation), founder (approval).
**Locked content (do not rewrite):** Homepage H1, FAQ items, pricing structure, founder voice rules from existing `AGENTS.md`.

---

## 0 — Designer's note

This brief replaces the dark-theme direction in `AGENTS.md` with a strict light theme. The locked copy stays (the homepage H1, the sub-line, the FAQ, the pricing model). What changes is the visual register, the page count, and how the accent is allowed to behave.

The target register sits somewhere between Linear, Stripe Atlas, and Resend if those products were Dutch, sober, and pointed at installers instead of developers. Premium without luxury. Minimal without coldness. Trust earned through restraint, not through stock photography, trust-badges, or customer logo strips we don't have.

The brand's enemy on this site is not the competitor. It is the AI-template look. Every visual choice in this brief is calibrated to refuse the template.

---

## 1 — Audience & strategic intent

### Who reads this site

- Owner-operator or sales lead of an installation company (3–15 FTE).
- Heat-pump, airco, solar, or HVAC specialist in NL or BE.
- 35–55 years old. Practical. Hands dirty. Allergic to marketing speak.
- Already paying €40–€120 per lead to Werkspot, Slimster, Solvari.
- Has been burned by shared leads, bad-fit prospects, and "AI-revolutie" pitches.
- Decides in 90 seconds on the first visit. Returns to read pricing in detail.

### What they need to feel by minute one

1. *This is run by a person, not a content farm.* (Founder voice, real signals.)
2. *The leads are real and verifiable.* (Source URLs, redacted examples, no fluff.)
3. *I'm not the product. The installer next door isn't getting the same lead.* (Exclusivity, hammered.)
4. *I can stop whenever.* (No contract, no minimum, money-back.)

### What this site must do

- Convert cold visitors → pilot signups (5 free leads). One goal.
- Sustain trust through a long second visit before paid conversion.
- Read as built by an operator, not by an agency.

### Brand personality

Three words, in priority order: **sober, specific, operator.**

If a design choice feels charming, decorative, or "delightful," it is wrong for this brand. If it feels like a quietly competent person handing you a stapled PDF, it is right.

---

## 2 — Visual direction

**One-sentence mission:** *Read this like a serious B2B operations memo, not a SaaS landing page.*

### Register reference points

Studied for specific lessons, not for copying. See §8 for the detailed inspiration breakdown.

- Linear marketing pages — editorial restraint, mono accents, type as the only ornament.
- Stripe Atlas / Stripe Press — generous margins, paper-feel surfaces, magazine-rhythm long-form.
- Resend — developer-tool sobriety, one saturated accent reserved for conversion moments.
- Mercury Banking — clinical light surfaces, near-black ink, tiny details handled with care.
- Substack longform reading view — whitespace as luxury.

### Reject explicitly

- The "purple gradient hero + glowing dashboard mockup" SaaS template.
- The "three-icon feature grid" template.
- The "centered headline + button + customer logo strip" template.
- Light-theme Tailwind defaults (slate-50, slate-900, blue-500).
- Anything that suggests this site is aimed at VCs or developers. The visitor is a practical NL/BE business owner.

### Tone of the visual language

- Off-white paper, not screen-white.
- Near-black ink, not pure black.
- Hairline rules, not card shadows.
- Asymmetric and left-aligned, not centered-everything.
- One signal color used like a status light, not like brand paint.

---

## 3 — Information architecture

### Five primary routes

Promoting "How it works" to a dedicated page and pulling the pilot form out of the homepage anchor into its own route. Both changes against the older spec.

| Route              | Page name (NL)         | Purpose                                | Nav position |
| ------------------ | ---------------------- | -------------------------------------- | ------------ |
| `/`                | Homepage               | Convert cold visitors                  | (logo)       |
| `/zo-werkt-het`    | Hoe het werkt          | Deep methodology, trust-build          | 1            |
| `/leads`           | Voorbeeldleads         | Live proof gallery                     | 2            |
| `/prijzen`         | Prijzen                | Pricing detail, FAQ, money-back        | 3            |
| `/pilot`           | Start pilot            | Intake form with side trust artifact   | CTA          |

### Three utility routes (no nav placement)

- `/bedankt` — post-intake confirmation.
- `/privacy` — privacy policy, plain prose, no template.
- `/voorwaarden` — terms, plain prose, no template.

### Why a dedicated `/pilot` page

1. The homepage shouldn't end on a form. It ends on a story closure (Founder, then FinalCta). The form is a destination, not a fold.
2. Conversion pages with their own URL get better Plausible granularity.
3. A dedicated page lets the form sit alongside trust elements (sample lead card, money-back reminder, founder photo) without competing with the homepage narrative.

### Header anatomy (all routes)

- Left: wordmark `lead-radar` (no logomark; pure type).
- Center: three text links — Hoe het werkt · Voorbeeldleads · Prijzen.
- Right: one button — `Start pilot` → `/pilot`.
- Height: 72px desktop, 56px mobile.
- Background: paper (off-white), with a single 1px hairline at the bottom.
- Hairline only appears once the user has scrolled ≥ 40px. Above the fold the header is borderless. This is the only conditional visual behavior on the site.

### Footer anatomy (all routes)

- Three columns desktop, stacked mobile.
- Col 1: wordmark + one sentence: *Exclusieve intent-leads voor installateurs in NL & BE.*
- Col 2: nav (mirrors header) + utility links (Privacy, Voorwaarden).
- Col 3: contact — founder email, LinkedIn, KVK number once registered.
- One 1px hairline at the top.
- Closing line at the bottom: `© 2026 lead-radar · Eindhoven`.
- No newsletter signup, no language switcher, no social icon row beyond LinkedIn.

---

## 4 — Design system

### 4.1 Theme

Light only. No system-preference detection. No toggle.

**Why light.** Installers do not read business sites at 2am. They open the link from a Werkspot email on a 13" Lenovo at 10am, in a warm-tube-lit office. A bright surface reads as honest documentation. A dark surface reads as "tech product." This product is documentation about real prospects, not a SaaS dashboard.

### 4.2 Color

Four working surfaces, one ink, one signal. That is the entire palette.

| Token             | Hex       | Use                                                                              |
| ----------------- | --------- | -------------------------------------------------------------------------------- |
| `paper`           | `#FAFAF7` | Default page background. Slightly warm off-white. Never pure white.              |
| `paper-elevated`  | `#F4F4EF` | Single elevated surface (lead card, pricing card). Used sparingly per page.      |
| `paper-inset`     | `#EFEFEA` | Optional inset block (founder quote, money-back callout).                        |
| `ink`             | `#0A0A0A` | All primary text, all buttons, all links. Near-black, never pure black.          |
| `ink-soft`        | `#4A4A48` | Secondary text. Subhead, captions, mono labels at content scale.                 |
| `ink-mute`        | `#8A8A86` | Tertiary text. Timestamps, source labels.                                        |
| `rule`            | `#E4E4DF` | Hairlines and borders. 1px only.                                                 |
| `signal`          | `#1FB371` | Working accent. Deep electric green. Used on step numbers, accent rules, hovers. |
| `signal-bright`   | `#3EFFA1` | Reserved neon flash. ONLY on HOT badge fill and live-ticker pulse dot.           |

**Note on the green.** The earlier spec used neon `#3EFFA1` for everything (buttons, links, accents). On a white surface neon reads as cheap consumer-app (Robinhood, MoneyLion). The premium move is to **darken the working green to `#1FB371`** for hovers, step prefixes, and accent rules, and **reserve neon `#3EFFA1` exclusively** for the HOT badge fill and the pulse dot on the live ticker. The neon then reads as a *signal light*, not as decoration.

### Color usage rules

1. The page is 90% paper + ink. Everything else is rare.
2. Green is *reserved language.* It only appears where the meaning is "live signal" or "step marker." Never on dividers, never on icons, never on body text.
3. `signal` and `signal-bright` never touch — they are not adjacent within a single composition.
4. No second accent. No blue links. No red errors (form errors use `ink` weight 500 plus an `✕` glyph). No yellow warnings.
5. Charts or data visualizations, if any, use only `ink` at 100 / 60 / 30 / 10 % opacity.

### 4.3 Typography

#### Families

- `Inter` (variable), weights 400 / 500 / 600 only. Never 700+.
- `Geist Mono`, weight 400 only.
- Self-hosted via `next/font`. No Google CDN fetch.

#### Scale

These are the only sizes that exist on the site. No improvisation.

| Token         | Desktop size      | Mobile size | Weight | Line height | Tracking | Use                                                       |
| ------------- | ----------------- | ----------- | ------ | ----------- | -------- | --------------------------------------------------------- |
| `display-xl`  | clamp 64 → 88     | 48          | 500    | 1.02        | -0.025em | Homepage H1 only. One per site.                           |
| `display-lg`  | 56                | 38          | 500    | 1.05        | -0.022em | Page H1 on `/zo-werkt-het`, `/leads`, `/prijzen`, `/pilot`. |
| `display-md`  | 40                | 30          | 500    | 1.10        | -0.018em | Section H2.                                               |
| `display-sm`  | 28                | 24          | 500    | 1.20        | -0.012em | Subsection H3, pricing card name, founder name.           |
| `body-lg`     | 19                | 17          | 400    | 1.55        | 0        | Hero sub-line, long-form paragraphs, FAQ question.        |
| `body`        | 16                | 16          | 400    | 1.62        | 0        | Default body.                                             |
| `body-sm`     | 14                | 14          | 400    | 1.55        | 0        | Captions, footer body.                                    |
| `mono-md`     | 14                | 14          | 400    | 1.50        | 0        | Lead data values.                                         |
| `mono-sm`     | 12                | 12          | 400    | 1.45        | +0.04em UPPERCASE | Labels (REGIO, BRON, SCORE), ticker text, timestamps. |

#### Weight philosophy

Hierarchy comes from **size + tracking,** not from weight. Inter 500 is the heaviest weight on the site. Bold 700 reads as a Tailwind default and immediately destroys the premium register.

#### Line length

Body paragraphs cap at **64 characters per line.** Non-negotiable. Use a max-width that produces 60–64ch at the working body size (≈ 580–620px at 16px Inter).

#### Italics, serif, all-caps

- Italics: never.
- Serif: never.
- All-caps: only on `mono-sm` labels.

#### The em-dash rule

The "no em-dash in body" rule from `AGENTS.md` applies to its own copy too. Where the existing canonical sub-line uses an em-dash, the rendered version replaces it with a period or comma. The visual rhythm of a page with no em-dashes is calmer than the alternative. This is a real, perceptible craft signal.

### 4.4 Layout and vertical rhythm

#### Container widths

- Default content width: 1200px max, padding-x 32px desktop / 20px mobile.
- Narrow prose width (Why-exclusive, How-it-works long-form): 680px max.
- Form column on `/pilot`: 560px max.

#### Horizontal alignment

- **Hero: left-aligned** on every viewport. Centered hero is the single most common cheap-template tell. We refuse it.
- Section H2s: left-aligned, in the container's left gutter, never centered.
- Long-form body: left-aligned within its narrow column.
- Pricing cards, FAQ, ticker, founder block: left-aligned within their container.
- Centered alignment exists in two places only: the FinalCta block (centering signals "conclusion"), and inline status badges within a card.

#### Vertical rhythm scale

Use only these gaps. Never improvise.

- `4px` micro — icon-to-text.
- `8px` tight — label-to-value.
- `16px` default — within a block.
- `24px` medium — between paragraphs.
- `40px` loose — between blocks within a section.
- `64px` major — section-to-section on mobile, or under a section heading before content.
- `120px` section — between sections on desktop default.
- `160px` chapter — around the hero, around the FinalCta. Used twice per page maximum.

The asymmetry between `120` and `160` is intentional and audible. Same gap everywhere = monotone. Two scales of section-spacing create a visible page tempo.

#### Grid model

- 12 columns, 24px gutter desktop, 16px mobile.
- Most sections occupy columns 1–12 (full) or 1–8 (narrow content with asymmetric right whitespace).
- **Asymmetric rule:** at least one section per page uses an off-center layout (e.g. headline cols 1–6, body cols 7–12, or photo cols 1–3 + text cols 5–10). Default-left-aligned full-width sections become repetitive after the third in a row.

#### Surface treatment

- No drop shadows anywhere. Not on cards, not on buttons, not on the header.
- Elevation is shown by a single hairline (`rule` 1px) OR by a subtle background shift (`paper` → `paper-elevated`), never both at once.
- Cards use 8px radius. Hero, sections, and full-width blocks have no radius. The exception is the lead-card, which uses 12px radius so it reads as a discrete document.
- Borders are always `rule` 1px. There is no 2px border anywhere except the focus ring.

### 4.5 Buttons

Three variants. Nothing more.

#### Primary

`Start pilot`, `Vraag pilot aan`.

- Fill: `ink`.
- Text: `paper`.
- Weight: 500.
- Padding: 14×22px desktop, 14×20px mobile.
- Radius: 8px.
- Hover: fill shifts to `#1A1A1A` (one stop lighter). No scale, no shadow.
- Active: fill shifts to `#000000`.
- Focus ring: 2px `signal` outline at 4px offset.

#### Secondary

`Bekijk voorbeelden`, `Lees hoe het werkt`.

- Fill: `paper`.
- Border: 1px `ink`.
- Text: `ink`.
- Same padding, radius, focus ring as primary.
- Hover: fill `paper-elevated`. Border stays `ink`.

#### Quiet

Inline text-style CTAs — `→ alle voorbeelden bekijken`, `→ Volledige prijzen-pagina`.

- No border, no fill.
- Text: `ink`, weight 500.
- Underline 1px at 4px offset.
- Hover: underline shifts to `signal`. Text stays `ink`.

#### Button rules

- Button height is consistent: 48px desktop and mobile.
- The only state shift is fill-color. 50ms ease-out. No scale, no shadow, no glow.
- Pill-shaped buttons (radius > 12px) are forbidden — they read as consumer app.
- "Outline button with green text" is forbidden — reads as a discount coupon.
- Arrow icons glued to button labels are forbidden — context already implies action.
- Loading spinners inside buttons are forbidden — use a separate inline state line.

### 4.6 Forms

Inputs are quiet by default and become structural under focus.

- Background: `paper`. Form sits on `paper-elevated` so the input has contrast.
- Border: 1px `rule`.
- Radius: 6px.
- Padding: 12×14px.
- Label: above input, `mono-sm` (UPPERCASE), 8px gap to input.
- Helper text: below input, `body-sm` `ink-mute`, 6px gap.
- Focus: border becomes `ink`, plus 2px `signal` outline at 2px offset.
- Error: 1px `ink` border (no red). Helper text becomes `ink` weight 500, prefixed with a small `✕` glyph.
- Submit button: end of form, full-width mobile, content-width desktop.

### 4.7 Iconography

- Lucide icons only. Stroke-width 1.5px. Never filled, never colored — always `ink`.
- Maximum 16×16px in body, 20×20px in headers, 24×24px in hero affordances.
- **Permitted:** chevrons on accordion, hamburger on mobile nav, external-link arrow on outbound links, LinkedIn glyph in footer.
- **Forbidden:** icons inside feature cards, icons before every list item, icons as section decoration, Lottie animations, custom SVG illustrations of process diagrams.

### 4.8 Motion

The site barely moves. That is the point.

- Allowed: 150ms color and border-color transitions on hover and focus, with `ease-out-quart`.
- Allowed: 200ms height transition on accordion expand.
- Allowed: a single 1.6s opacity loop on the live-ticker pulse dot (`signal-bright`, 0.4 → 1 → 0.4). This is the only "alive" cue on the site.
- Forbidden: scroll-triggered fade-ins, parallax of any kind, hover scale on cards or images, count-up number animations, page-load animations, marquee strips.

If a transition needs more than 200ms, it is not a transition, it is a state change. Design the state change as a discrete render.

### 4.9 Lead card (the single most important component)

The lead card is the proof. Treat it like a redacted intelligence dossier, not a marketing card.

**Anatomy**

- Background: `paper-elevated`.
- Border: 1px `rule`.
- Radius: 12px.
- Padding: 28px desktop, 20px mobile.
- Header row: HOT badge (left) · source label · date (right). 16px gap below before body.
- Body: two-column label/value grid. `mono-sm` labels in `ink-mute`. `body` values in `ink`. 16px vertical gap between rows. Rows: Regio, Bron, Signaal, Context, Score, Route.
- Divider: 1px `rule` above the snippet block. 16px gap top and bottom.
- Snippet block: 3-line clamp on the homepage example, full on `/leads` detail. `body`, `ink-soft`, no italics, no quotation marks.
- Footer row: `mono-sm` `ink-mute` — `Geleverd aan: ███████ · 09 mei 2026`. The redacted recipient block is a stylistic asset — it visually proves someone got the lead.

**HOT badge** (the only saturated element on a card)

- Fill: `signal-bright`.
- Text: `ink`.
- Padding: 3×8px.
- Radius: 4px.
- `mono-sm` UPPERCASE.

**Source label** (top right)

- `mono-sm`, `ink-mute`.
- Format: `Warmtepomp · NL · vandaag 09:14`.

Lead cards have no "view details" affordance on the homepage example — this is an artifact, not navigation. On `/leads` each card is clickable into a static read-only detail view that just expands the snippet and shows the source URL un-clickable. We do not link to the original source — the URL is the product we sell.

---

## 5 — Page-by-page structure

### 5.1 Homepage (`/`)

Nine sections. The page is intentionally long. Long-form is part of the trust message.

| #  | Section                          | Purpose                                        | Vertical gap before |
| -- | -------------------------------- | ---------------------------------------------- | ------------------- |
| 1  | Hero                             | Position the proposition in 3 seconds          | 0 (sits below header) |
| 2  | Live signal strip                | "This is alive right now" proof                | 64px                |
| 3  | How it works (3-step teaser)     | Make the mechanism legible                     | 160px               |
| 4  | Lead example (single card)       | Prove the leads are real                       | 120px               |
| 5  | Why exclusive matters            | Frame the difference vs Werkspot, no naming    | 120px               |
| 6  | Pricing teaser (2 cards)         | Show transparency before they click pricing    | 120px               |
| 7  | FAQ (7 questions)                | Pre-answer the skeptical reader                | 120px               |
| 8  | Founder block                    | Make the seller human                          | 120px               |
| 9  | FinalCta                         | One last invitation to start the pilot         | 160px               |

Section-by-section deep dive in §6.

### 5.2 Leads (`/leads`)

Five sections. This is the page a skeptical visitor returns to.

| # | Section              | Content                                                                                                                                                          |
| - | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Page header          | H1 *Voorbeeldleads.* Sub: *Negen recente leads, geredigeerd. De volledige lead met directe bron-URL ontvangt alleen de koper.*                                  |
| 2 | Niche filter         | Four pills: Alle · Warmtepomp · Airco · Zonnepanelen. Client state, no URL persistence in V1.                                                                    |
| 3 | Lead gallery         | 3×3 grid desktop, 1-col mobile, gap 24px. Each card uses §4.9.                                                                                                  |
| 4 | Methodology footnote | One short paragraph in a narrow 680px column: *Wat je hier ziet is geredigeerd. De volledige lead, met directe bron-URL en route naar contact, gaat alleen naar de installateur die de lead koopt.* |
| 5 | CTA block            | Same treatment as homepage FinalCta but rephrased: *Lijkt er één bij jouw regio?* Sub: *Vraag de pilot aan, ik kijk welke open leads er nu voor jou liggen.*    |

**Empty state** when a filter yields zero results: a narrow column with mono-styled text — *Geen voorbeelden in deze niche nog. Mail me of je toch wilt starten, dan kijken we naar volume.* This signals real-volume honesty rather than fake "coming soon" copy.

### 5.3 How it works (`/zo-werkt-het`)

Seven sections. This is the trust-build page for the second visit.

| # | Section                  | Content                                                                                                                                                                            |
| - | ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Page header              | H1 *Hoe het werkt.* Sub: *De volledige werking, zonder marketingvocabulaire.*                                                                                                       |
| 2 | The mechanism (3 steps, deep) | Same 01 / 02 / 03 as the homepage teaser but with a full paragraph per step explaining the *how*, not the *what*. Includes the specific bronnen named (Tweakers, Reddit r/zonnepanelen, ouders.nl, bouwinfo.be, klusidee.nl, public FB-groepen). |
| 3 | What a lead looks like   | Embedded full-size lead card. Less redacted than the homepage example. Heading: *Wat de installateur écht ontvangt.* The source URL is the only field still redacted.                |
| 4 | Wat we niet doen         | Five short paragraphs: *Geen scraping achter login. Geen privébericht. Geen marketplace-formulier. Geen contract. Geen rebrand van Werkspot.* This section is the philosophical core. |
| 5 | Tijdlijn van een lead    | A four-step horizontal flow desktop, vertical mobile: *Gevonden 09:11 → Geclassificeerd 09:13 → Geleverd 09:14 → Gebeld door installateur 11:42.* Concrete, not generic.            |
| 6 | GDPR / AVG block         | Short paragraph: alleen publieke bronnen, bron-URL meegeleverd, opt-out mogelijk, geen DM-scraping. Contact via founder email.                                                       |
| 7 | CTA block                | Same pattern, sub: *Start de pilot. 5 leads, geen creditcard, geen contract.*                                                                                                       |

### 5.4 Pricing (`/prijzen`)

Six sections.

| # | Section            | Content                                                                                                                                                                       |
| - | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Page header        | H1 *Prijzen.* Sub: *Twee opties. Beide zonder contract. Beide met money-back.*                                                                                                |
| 2 | Two pricing cards  | Pilot (€0 eenmalig, 5 leads) and Pay-per-lead (€75 per lead). Visually identical weight. No "popular" highlight.                                                              |
| 3 | Money-back block   | Standalone paragraph on `paper-inset`: *Als een geleverde lead onbereikbaar blijkt of nep is, mail me binnen 7 dagen. Refund binnen 24 uur, geen formulier, geen toelichting.* Signed off with founder first name. |
| 4 | Wat zit er in een lead | One-line list of six concrete items: bron-URL, samenvatting, regio, profielcontext, score 0–100, route naar contact.                                                       |
| 5 | Pricing FAQ        | 4 items from existing `AGENTS.md`. Same accordion pattern as homepage FAQ.                                                                                                    |
| 6 | CTA block          | *Start met de pilot. €0, 5 leads, geen creditcard.*                                                                                                                            |

### 5.5 Pilot intake (`/pilot`)

Four sections. The only page with an intentional two-column desktop layout (form left, trust artifact right).

| # | Section            | Content                                                                                                                                                                                              |
| - | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | Page header        | H1 *Start je pilot.* Sub: *5 leads in je niche en regio, binnen 24 uur. Geen creditcard, geen contract.*                                                                                             |
| 2 | Form block (cols 1–6 desktop) | Six fields: Bedrijfsnaam, Naam, E-mail, Telefoon (optioneel), Niche (select: warmtepomp / airco / zonnepanelen / anders), Regio (select: provincie NL of BE), Opmerking (optioneel). Honeypot hidden field. Submit button bottom of form. |
| 3 | Side trust block (cols 7–12 desktop, hidden mobile) | Small lead-card preview + one line of mono-sm: *Zo ziet je eerste lead eruit. De echte heeft een werkende bron-URL.*                                  |
| 4 | Founder photo + 2 lines | Photo 120×120 circle, name as `display-sm`, email + LinkedIn as quiet text-links. Scaled-down version of homepage founder block.                                                                  |

**Post-submit destination** — `/bedankt`:

- H1 *Je pilot staat in de lijst.*
- One paragraph: *Ik mail je binnen 24 uur met je eerste batch leads. Vragen tussendoor? Mail direct.*
- Founder email as quiet link.
- Small text-link back to homepage at the bottom.

### 5.6 Utility pages (`/privacy`, `/voorwaarden`)

- Plain prose, single column at 680px max width.
- H1 `display-lg` + last-updated date in `mono-sm` directly below.
- Section headings: `display-sm`. Body: `body-lg` for readability.
- No table of contents (the page is short enough).
- Treat these as legitimate legal documents, not templated boilerplate. The privacy page in particular must mention the specific bronnen and the GDPR rationale (this is also a trust artifact).

---

## 6 — Homepage section-by-section deep dive

### Section 1 — Hero

**Purpose.** Position in three seconds. Make a skeptical visitor lean in instead of bouncing.

**Layout.**
- Left-aligned. Content occupies columns 1–8 on desktop, 1–12 on mobile.
- Top padding 96px (sits below the 72px header → total fold space ~ 168px).
- Bottom padding 0 (the live-signal strip immediately follows).
- Minimum height: 1 viewport on 1440×900. On mobile (< 768px), let it size to content; do not enforce 100vh on small screens.
- Right column on desktop (cols 9–12): **empty.** The whitespace is the design. No mockup, no illustration, no abstract shape.

**Content (locked).**
- H1 (`display-xl`): `Eén lead. Eén installateur. Geen concurrentie.`
- Sub-line (`body-lg`, `ink-soft`, max-width 540px, 32px below H1): `Exclusieve warmtepomp-leads voor installateurs in NL & BE. Gevonden waar klanten écht praten. Forums, communities, open social.`
  (Em-dash from the canonical original replaced with periods, per §4.3.)
- Buttons (48px below sub-line, 12px between):
  - Primary: `Start pilot — 5 gratis leads` → `/pilot`
  - Secondary: `Bekijk voorbeeldleads` → `/leads`

**Why no visual.** The H1 has to be the visual. Adding an illustration, mockup, or hero image at this stage immediately knocks the site into "AI landing page" register. A confident, naked headline on paper is the strongest position.

### Section 2 — Live signal strip

**Purpose.** One sentence, one pulse dot. Says "this is alive right now."

**Layout.**
- Full container width, left-aligned.
- 64px below hero, 64px above the next section.
- Single horizontal line in `mono-sm` `ink-mute`.
- A 6px diameter dot in `signal-bright` sits 12px to the left of the text, with a 1.6s opacity pulse (0.4 → 1 → 0.4 → ...).
- Line: `LIVE · vandaag 312 posts gescand · 17 HOT · NL + BE`

**Behavior.** Numbers are real, populated from the scraper output at build time or every 10 minutes via ISR. The line never lies. If volume is low, the line still tells the truth — *vandaag 84 posts gescand · 3 HOT · NL.*

This is the only animated element on the entire site.

### Section 3 — How it works (teaser)

**Purpose.** Make the mechanism legible. Pre-empt the "is this just another marketplace?" question.

**Layout.**
- Section H2 left-aligned in col 1: `Hoe het werkt`.
- Sub-line below (`body`, `ink-soft`, max 480px): `Drie stappen. Geen platform, geen biedoorlog.`
- 40px below the sub-line: three step blocks displayed as a single horizontal row on desktop, each spanning roughly 4 columns, 64px gap. Stacked on mobile.

**Each step block.**
- Step number in `mono-sm` `signal` — `01 ·`.
- Step title `display-sm`, 8px below the number.
- Step description `body`, `ink-soft`, 16px below the title, max-width 320px.
- **No icons.** No borders around the block. Just space.

**Content** (rewritten for the white-theme register, keeps the same meaning as `AGENTS.md`):

01 · *Wij scrapen publieke intent.* We monitoren forums, communities en open social platforms waar mensen vragen stellen over warmtepompen en airco. Alleen publiek, niets achter login.

02 · *Wij classificeren op HOT of WARM.* Elke post wordt door een taalmodel beoordeeld op intent, urgentie en regio. Alleen leads boven de drempel gaan eruit.

03 · *Jij ontvangt de lead exclusief.* Eén lead is één installateur. Met bron-URL, samenvatting, regio, en een voorgestelde route naar contact.

A quiet text-link at the bottom-right of the section: `Lees de volledige methodologie →` → `/zo-werkt-het`.

### Section 4 — Lead example

**Purpose.** Prove the leads are real, by showing one.

**Layout.**
- H2 left-aligned: `Zo ziet een lead eruit`.
- Sub: `Een echte lead uit mei 2026. De bron-URL gaat alleen naar de koper.`
- 40px below: a single lead card using the §4.9 pattern. Max-width 720px. Occupies columns 3–10 (off-center, extra whitespace on the right).
- Below the card, a quiet text-link: `→ Bekijk 8 andere voorbeelden`.

**Why the off-center placement.** The cols-3–10 placement is the homepage's first off-axis moment. It breaks the rhythm without breaking the grid. It also makes the card feel like a *clipping* the founder has pulled out of a folder, not a marketing tile.

### Section 5 — Why exclusive matters

**Purpose.** Frame the differentiator. Do not name competitors.

**Layout.**
- Narrow column, 680px max width, left-aligned in cols 1–6 desktop, cols 1–12 mobile.
- H2 left-aligned: `Waarom exclusief het verschil maakt`.
- A 64px wide × 1px `signal` rule directly below the H2, 24px gap top and bottom.
- Three short paragraphs in `body-lg` — earnest-essay typography.

**Content** (sober, Werkspot not named):

Veel leadplatforms werken vanuit een formulier. De klant vult iets in, en de aanvraag gaat naar drie of vier installateurs tegelijk. Je betaalt voor één lead, maar je deelt hem met je concurrenten.

Wij draaien het om. We vinden klanten op het moment dat ze nog vragen stellen, niet als ze al offertes verzamelen. Daardoor kunnen we elke lead aan exact één installateur leveren. Geen biedoorlog. Geen race om als eerste te bellen.

Het verschil zit niet in de prijs. Het zit in het mechaniek.

This section's typographic restraint is doing the heaviest lifting on the page. It needs to read like a paragraph in a serious business memo.

### Section 6 — Pricing teaser

**Purpose.** Show pricing transparency before the visitor clicks into the pricing page.

**Layout.**
- H2 left-aligned: `Eerlijke prijzen, zonder vooraf-risico`.
- Sub `body-lg` `ink-soft`, max 540px: `Eén lead gaat naar één installateur. Geen contract, geen minimum, money-back als de lead niet klopt.`
- 40px below: two cards side by side on desktop, each ~5 columns wide, occupying cols 1–11 with the rest as whitespace. Stacked on mobile. Gap 16px.
- Card surface: §4 treatment.
- Card name `display-sm`.
- Price in Inter 44px weight 500, with unit (`per lead` / `eenmalig`) in `mono-sm` `ink-mute` directly below the price.
- 1px hairline divider, 16px above and below.
- Five feature lines, each prefixed with a single `✓` glyph in `ink` (not green), `body`.
- Button at the bottom, full-width within the card:
  - Pilot card → Secondary button (outline ink): `Start pilot →`
  - PPL card → Primary button (filled ink): `Start pilot →`

Both CTAs go to `/pilot`. The reason both cards point to the same form: conversion happens through the pilot. Paid PPL is a downstream action emailed after the pilot completes.

Below the cards, centered: quiet text-link `→ Volledige prijzen-pagina`.

**No "Most Popular" highlight ever.** Cards have identical visual weight by design.

### Section 7 — FAQ

**Purpose.** Pre-answer skeptical-installer objections.

**Layout.**
- H2 left-aligned: `Veelgestelde vragen`.
- 40px below: accordion of 7 items (existing content from `AGENTS.md`).
- Max-width 720px, occupies cols 1–8 (off-center).
- Each item: 1px `rule` top border, 24px padding top + bottom, chevron right-aligned, 200ms height transition on expand.
- Question: `body-lg` weight 500.
- Answer: `body` `ink-soft`, max-width 64ch, no indent.
- All closed by default. Only one open at a time (single-open accordion).
- Last item has a 1px `rule` bottom border too.

### Section 8 — Founder block

**Purpose.** Make the seller human. Prove this is run by an operator.

**Layout** (off-center, deliberate asymmetry):
- Two columns desktop: photo cols 1–3, text cols 5–10.
- Photo: 160×160 circle, real photo of founder, `next/image` priority. Background of the photo subtly tinted to `paper-elevated` so it blends.
- Text column:
  - Founder name as `display-sm`: `Ik ben [Voornaam].`
  - One paragraph `body-lg` `ink-soft`: `Ik bouw lead-radar omdat installateurs nu nog geld betalen voor leads die ze met drie concurrenten delen. Ik laat dat anders werken. Vragen, klacht, of nieuwsgierig? Mail me direct.`
  - Two quiet links 12px below the paragraph: `→ [voornaam]@leadradar.nl` and `→ LinkedIn`.

**Mobile.** Photo above text, both left-aligned, 24px gap.

The asymmetric two-column layout is the second off-axis moment on the page. It signals "this part is personal, not corporate."

### Section 9 — FinalCta

**Purpose.** One last invitation. The story closes here. The form lives at `/pilot`.

**Layout.**
- Full-width container.
- 160px top padding, 160px bottom padding desktop. 96px mobile.
- Content centered (the one centered moment per page).
- H2 `display-md`: `Klaar om 5 leads te bekijken?`
- Sub `body-lg` `ink-soft`, max 480px, centered: `Geen creditcard. Geen contract. Ik mail je binnen 24 uur de eerste batch in je regio.`
- Single primary button: `Start pilot — gratis` → `/pilot`.
- 24px below the button, a `mono-sm` `ink-mute` line: `Of mail direct: [voornaam]@leadradar.nl`.

The mono email line is deliberate: the brave reader takes the email shortcut and bypasses the form. Some installers prefer email; let them.

---

## 7 — What NOT to do

Thirty anti-patterns. Each one destroys the premium register. Ordered roughly from "most common AI tell" to "more subtle craft failure."

1. **Centered hero headline + button + sub.** The single most common cheap-template signature. Left-align is non-negotiable.
2. **Linear, radial, conic, or mesh gradient backgrounds.** Any color, any direction. Use flat paper.
3. **Pure white `#FFFFFF` page background.** Always `#FAFAF7` or warmer.
4. **Pure black `#000000` text.** Always `#0A0A0A`.
5. **Drop shadows on cards or buttons.** Use 1px hairlines.
6. **Three-icon feature grid** (icon + heading + 2 sentences × 3). The most common AI tell. Replaced here with the asymmetric 01/02/03 row, no icons.
7. **"Trusted by" logo strip.** Lead Radar has no customers to brag about. A fake or aspirational logo strip is poison.
8. **Stock photography of smiling people.** Replace with the real founder photo, period.
9. **Gradient text** (background-clip text). Always solid `ink`.
10. **Glassmorphism / backdrop-blur cards.** Hairline borders only.
11. **"AI-powered" badge** or any "powered by" framing. AI is the *how*; the product is leads.
12. **Animated count-up numbers.** Use one real number, no animation.
13. **Scroll-triggered fade-ins** on every section. Static rendering.
14. **Parallax scrolling.** Disabled.
15. **Carousels of any kind.** Grid or stack.
16. **"Most Popular" / "Recommended" pricing highlight.** Both pricing cards visually identical.
17. **Pricing toggle** (monthly / annually). We have two prices, both static.
18. **Floating CTA button** in the bottom-right corner. Inline CTAs only.
19. **Sticky chat widget** or Intercom-style live chat. Founder email instead.
20. **Cookie consent banner** blocking content. Plausible doesn't require one.
21. **Modal on page load.** Never.
22. **Newsletter signup in footer.** No newsletter exists.
23. **`Roboto`, `Open Sans`, `Poppins`, `Lato`, `Montserrat`.** Inter only.
24. **Italic text** anywhere. Use weight contrast or quote marks for emphasis.
25. **Serif font** anywhere. Sans-serif only.
26. **Bold weight 700+** on any heading. Inter 500 is the heaviest weight on the site.
27. **Em-dash in body copy.** Use a period or a comma.
28. **Buzzwords** in any language: leverage, supercharge, robust, comprehensive, seamless, ecosystem, journey, unlock, empower, transform, revolutionary, game-changing, cutting-edge. Dutch equivalents (naadloos, krachtig, ontketenen, transformeren) idem.
29. **Hero illustration / 3D blob / floating mockup.** The H1 stands alone.
30. **Two accent colors.** One green only. No blue links. No red errors. No yellow warnings.

If a Codex output violates any of the above, reject the diff and re-prompt with the specific anti-pattern number.

---

## 8 — Inspiration direction

Three reference points. None copied; each studied for one specific lesson.

### 8.1 Linear

**Lesson: typography as the primary visual language.**

Linear's marketing pages use Inter at controlled weights (mostly 400 and 500), a single accent (the magnetic loop animation), and a tight column on body text. Headlines are not large — they're tight, generously kerned, with negative letter-spacing on display weights. They never decorate. They show product through screenshots that are themselves restrained — no shadow, no gradient frame, no glow.

**What we take.** The discipline. Tight type scale. One accent. Restraint as confidence.

**What we do differently.** Linear sells to designers and developers, so they can be dark, futuristic, dense. We sell to installers. We need paper, not screens. We need warmth in the off-white, not coolness in the navy.

### 8.2 Stripe Press / Atlas long-form pages

**Lesson: editorial whitespace and the "magazine spread" rhythm.**

Stripe's long-form pages — the Atlas guides especially — read like a serif magazine even though they're sans-serif on screen. Wide horizontal margins. Narrow text columns. Deliberate one-column passages alternating with two-column passages. Pull-quotes used sparingly. The page breathes.

**What we take.** The breath. Vertical rhythm at 120 and 160px between sections. Narrow body columns at 64ch. Generous container margins.

**What we do differently.** Stripe assumes the reader is a founder reading at a laptop in a coffee shop. We assume the reader is opening this on a phone between jobs or on a 13" Lenovo in a workshop office. So we shorten the prose, replace pull-quotes with `signal` rules, and never let the page get longer than necessary.

### 8.3 Resend (resend.com)

**Lesson: sober use of a single saturated accent.**

Resend uses orange — a louder color than ours — but uses it only at conversion moments. Their hero is not orange. Their feature grid is not orange. Their buttons are orange. The CTA banners are orange. The accent does work, not decoration.

**What we take.** This exact discipline applied to our two greens. Buttons are `ink`, cards are paper, the H1 is `ink`. The greens are reserved for status only — HOT badge fill, live ticker dot, the small step-number prefix in section 3. When the visitor's eye lands on green, they should know something specific is happening.

**What we do differently.** Resend sells to developers who read code. Their interface can be slightly nerdy (monospace numbers in their pricing). We use mono more sparingly — only on data labels and timestamps — because installers don't read monospace as "premium," they read it as "this looks technical." A small pinch is fine. An overload is not.

---

## 9 — Handoff notes for Codex

### Build order (revision against `ORCHESTRATION.md`)

| Phase | Deliverable                                                    | Note                                        |
| ----- | -------------------------------------------------------------- | ------------------------------------------- |
| F1    | Replace dark tokens with light tokens from §4.2                | Update `globals.css` + `@theme inline`.     |
| F2    | Hero + FinalCta                                                | Left-align hero. Period replaces em-dash.   |
| F3    | Live signal strip (NEW section)                                | Sits between Hero and HowItWorks.           |
| F4    | HowItWorks teaser (no icons) + Lead example card               | Off-center cols 3–10 for the card section.  |
| F5    | Why exclusive + Pricing teaser + FAQ + Founder + FinalCta      | Tighten copy + restrict accent usage.       |
| F6    | `/zo-werkt-het` page (NEW route)                               | Seven sections per §5.3.                    |
| F7    | `/leads` page                                                  | Existing plan, card visuals updated to §4.9.|
| F8    | `/prijzen` page                                                | Six sections per §5.4.                      |
| F9    | `/pilot` page (NEW route, replaces homepage anchor)            | Two-column form layout.                     |
| F10   | SEO + analytics + utility pages                                | Per existing `ORCHESTRATION.md`.            |
| F11   | Deploy                                                         | Per existing `ORCHESTRATION.md`.            |

### Definition of Done — visual review checklist

Run before every PR merge:

- [ ] Background is `#FAFAF7` everywhere. No white. No dark-mode artifacts.
- [ ] No drop shadows on any element.
- [ ] No gradients of any kind.
- [ ] No element uses both a fill-shift and a border (one or the other).
- [ ] All buttons are `ink` (filled or outline).
- [ ] Green appears only on: HOT badges, ticker dot, step-number prefixes (§6 §3), focus rings.
- [ ] No element animates beyond a 150ms color shift, except the ticker dot pulse.
- [ ] Hero is left-aligned on all viewports.
- [ ] Body line length ≤ 64ch on every paragraph.
- [ ] No italics, no serif, no weight ≥ 600 anywhere on the site.
- [ ] No em-dash in any body text.

### Reject-loop prompts for Codex

Use these verbatim against specific violations:

- *"Hero is centered. Switch to left-aligned, content in cols 1–8 desktop, cols 1–12 mobile. Headline H1 only. Do not center the sub-line."*
- *"Button has a drop shadow. Remove the shadow. Hover effect is a fill-color shift only, no shadow, no scale."*
- *"Green is being used as the primary button fill. Switch to `ink` fill, white text. Green is reserved for HOT badges, the ticker dot, and step number prefixes."*
- *"Section heading is centered. Move H2 to the left of the container at column 1. Do not center any section heading."*
- *"Three icons appear in the HowItWorks row. Remove the icons. The 01/02/03 mono-prefix is the only visual cue."*
- *"Two accent colors appear (green + blue). Remove the blue. Links are `ink` weight 500 with a 1px underline."*

### Decision authority

If anything in this brief conflicts with the current `AGENTS.md`, this brief overrides. After approval, `AGENTS.md` will be rewritten to align with this brief (light tokens, new routes, updated forbidden patterns).
