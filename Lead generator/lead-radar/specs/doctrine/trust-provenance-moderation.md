---
title: Trust, Provenance, and Moderation Doctrine
version: v0.1
date: 2026-05-18
status: frozen
namespace: doctrine
owner: lead-radar
supersedes: none
---

# Trust, Provenance, and Moderation Doctrine

This document is the foundational doctrine for Lead-radar. It codifies
the rules that make Lead-radar a trust-heavy operational intelligence
service for installateurs — not a generic AI lead-generation product.

The doctrine is non-negotiable within a version. Operational defaults
(cadence, thresholds, queue sorting) may vary; constitutional rules
(the five-thing rule, exclusivity, reviewer accountability) may not.

## How to use this document

- **Sections 00–04** are constitutional. Changing them requires an
  explicit doctrine revision and a version bump.
- **Appendix A** is the citable anti-pattern catalog. Cite by item
  number (A19, A28, etc.) in PR reviews, code comments, design
  critiques. If a change hits an A-item, the change is wrong.
- **Appendix B** is the vocabulary. Treat as linter input for every
  UI string, email template, copy block, and docstring.

## Four roles touch this document

| Role                  | Responsibility                                  |
|-----------------------|-------------------------------------------------|
| doctrine author       | defines and revises (founder + Claude)          |
| implementer           | executes within the doctrine (Codex)            |
| accountable reviewer  | applies the doctrine daily (founder, by name)   |
| auditor               | checks compliance post-hoc (founder)            |

---

## 00. First principles

### 00.1 What we sell
We do not sell leads. We do not sell AI.
We sell verifiable public intent: a sentence written by a homeowner
in a public place, captured with a URL that resolves, delivered to
exactly one installateur.

The product is the trail, not the prediction.

### 00.2 The five-thing rule
A lead does not exist unless it carries all five:

```
1. source_url        canonical, resolves to the original post
2. captured_at       ISO-8601 UTC, second precision
3. snippet           verbatim, ≤280 chars, never paraphrased
4. confidence_band   HOT / WARM / OPP — no decimals exposed
5. reviewed_by       accountable reviewer, by name
```

Missing any one → the lead cannot transition to DELIVERED.
There is no "shipped with caveat."

### 00.3 The verification invariant
A lead must remain independently verifiable by the installateur
after delivery.

If provenance cannot be independently revisited and understood,
the lead fails delivery requirements.

### 00.4 Division of accountability
Models assist detection and classification.
Humans remain accountable for delivery.

The word "AI" never appears in installateur-facing copy unless
the installateur uses it first.

### 00.5 Honesty constraints
- We never round confidence up.
- We never paraphrase a homeowner to sound more buying-ready.
- We never claim certainty we don't have.
- We mark decayed sources DECAYED, not removed.
- If we cannot explain HOT in one sentence the installateur could
  repeat to their accountant, the lead is not HOT.

### 00.6 The moat is the audit trail
Werkspot competes on volume.
Apollo competes on model brand.
We compete on traceability — and traceability compounds: every
reviewed lead adds to a private corpus of "this sentence converted,
this one did not" that no scraper can replicate and no competitor
can buy.

---

## 01. Provenance system

The data contract behind every lead. Every field exists to make
the trail walkable, alone, weeks later (00.3).

### 01.1 The lead record (canonical fields)

```
source_url           required   URL, canonical form, resolves
source_platform      required   "gathering-of-tweakers",
                                "reddit-r-Verbouwen", etc.
captured_at          required   ISO-8601 UTC, second precision
snippet              required   verbatim, ≤280 chars
snippet_lang         required   nl | en | other
signal_type          required   see 01.4
confidence_band      required   HOT | WARM | OPP
reviewed_by          required   name of accountable reviewer
reviewed_at          required   ISO-8601 UTC
region               required   province or city

delivery_condition   optional   FRESH (default) | DECAYED | EDITED
                                visible to installateur at delivery

capture_evidence     internal   path to archived HTML snapshot
source_hash          internal   SHA-256 of normalized snippet+url
state                managed    NEW | APPROVED | DELIVERED
                              | OUTCOME | REJECTED | EXPIRED
```

### 01.2 Normalization
URLs: canonical form. Strip `utm_*` / `fbclid` / tracking params,
normalize protocol, drop trailing slashes, preserve targeted
fragments.

Snippets: stored verbatim. Dedup compared via case-fold +
whitespace-collapse + accent-fold. Display is always verbatim.

### 01.3 The archive obligation
For every lead we keep an offline snapshot of the source page at
the moment of capture (HTML + timestamp).

`capture_evidence` is internal-only by default. It is not exposed
in the lead record sent to the installateur. It becomes visible
only when:

- the installateur disputes a delivered lead, or
- `delivery_condition` is DECAYED or EDITED (the archive is the
  only remaining trail).

The archive is the auditor's safety net, not a customer surface.

### 01.4 Signal taxonomy (v0)

```
INTENT_DIRECT    explicit purchase question
INTENT_RESEARCH  comparison threads, deep dives
INTENT_QUOTE     asking for quote/offerte advice
INTENT_PROBLEM   failing system, replacement looming
INTENT_TIMELINE  explicit deadline or window
```

Conversion is tracked per signal type, not just per lead.

Taxonomy revisions are versioned (this is v0). New types require
explicit migration and back-classification of recent corpus.

### 01.5 Confidence bands
Bands are assigned by the reviewer, not by the model.

```
model_score      → queue priority
reviewer band    → delivery classification
```

We do not sell model confidence. We sell human-accountable
judgement.

```
HOT   verified explicit intent + identity hook for routing
WARM  clear research intent, no immediate purchase signal
OPP   plausible signal needing investigation
```

### 01.6 Decay rules
A lead decays. The trail must be walked while fresh.

```
HOT  → 7 days       WARM → 14 days       OPP → 30 days
```

After the window: state = EXPIRED. The record stays — it joins
the corpus (00.6).

If the source changes before delivery:

- `delivery_condition` = DECAYED when the URL no longer resolves
  (404, deleted, taken down).
- `delivery_condition` = EDITED when the URL still resolves but
  the post content no longer matches the captured snippet.
- In either case: the lead's state remains in its current PCS
  lane; the archive (01.3) is attached as the surviving evidence.
- The reviewer may APPROVE → DELIVERED with the DECAYED or
  EDITED stamp visible to the installateur, or REJECT with
  `reason="source_decayed"` / `reason="source_edited"`.

DECAYED is metadata, not a workflow state. PCS-v0 STATES stays
at six (`pcs.py:STATES`).

### 01.7 Anti-patterns
- Scores without snippets
- Snippets without source_url
- Editing snippets to "clean up grammar"
- Deleting decayed leads from the corpus
- Letting the model assign confidence_band directly
- Routing without a regional fit
- Treating capture_evidence as optional

---

## 02. Intelligence UX language

How Section 01 data renders as interface. Section 01 says what we
store; Section 02 says how it appears. This is the ground truth
for every UI Codex builds — site, dashboard, email, all of it.

### 02.1 The citation surface
Every lead, in every interface, renders these five fields in
this order:

```
┌─────────────────────────────────────────────────┐
│ {snippet}                                       │
│                                                 │
│ — {source_platform}, {captured_at:relative}    │
│                                                 │
│ [open source ↗]   {confidence_band}            │
│                                                 │
│ reviewed by {reviewed_by}, {reviewed_at:rel}   │
└─────────────────────────────────────────────────┘
```

Snippet first. Source link one click away. Reviewer's name
always visible.

Incomplete leads fail moderation and never reach the citation
surface. (Enforcement lives in the five-thing rule (00.2) and
the moderation discipline of Section 03, not in fallback UI code.)

(Layout above is v0 sketch; element order is doctrine.)

### 02.2 Uncertainty rendering
Bands, never numbers.

```
HOT   solid     single accent, no gradient
WARM  outlined  same accent, hollow
OPP   muted     gray, no accent
```

We never display: "87% confidence", "high probability",
"model score: 4.2/5", progress bars, gauges, percentages.

**The band is the summary. The trail is the proof.**

### 02.3 Vocabulary

```
We say:                    We never say:
─────────────────────────────────────────────────
signal                     lead score
reviewed                   approved by AI
captured from {platform}   scraped from the web
public post                scraped data
verifiable intent          qualified lead
the reviewer               our AI / our algorithm
the trail                  the pipeline
installateur               customer / user
```

Vocabulary changes require doctrine revision. Codex treats this
table as linter input for UI copy. The full vocabulary lives in
Appendix B.

### 02.4 Anti-AI tells (what we don't do)
- Model names in the chrome ("Powered by GPT-4")
- Anthropomorphized scanners ("AI is thinking…")
- Paraphrased snippets ("This homeowner is interested in…")
- Suggested-action lists without citations
- Auto-text that completes the homeowner's intent
- Generic stock-illustration empty states
- Gradient-on-everything visual style

### 02.5 The credibility test
**Credibility collapses when verification requires effort.**

A lead feels credible — not AI-generated — when the installateur
can do all three without leaving the surface:

1. Read the homeowner's own sentence.
2. Click through to the original post.
3. See who reviewed it, and when.

If any of these requires effort, the screen has failed.

### 02.6 Empty & error states
Empty states say exactly what is missing, with timing:

> No new HOT signals this hour. Scanner last ran 4m ago.
> Next scan in 56m.

Not:

> Take a break! 🌱

Errors name the failure, the cause, and the next action:

> Lead not delivered: installer X reached their weekly cap (5/5).
> Choose another installer or wait until Monday.

Not:

> Oops! Something went wrong.

### 02.7 Anti-patterns
- Numerical scores anywhere a band fits
- Hero animations on the lead detail screen
- Suggesting actions without a cited reason
- Empty states with mascots/illustrations
- Auto-generated email subject lines
- Paraphrased delivery emails
- "AI" anywhere in the chrome unless installateur typed it first
- Showing a band without provenance in one view

---

## 03. Moderation operating model

The operational layer. Section 01 = data; Section 02 = interface;
Section 03 = what the accountable reviewer does in their daily
window.

### 03.1 The review window
The accountable reviewer moderates leads for at most 60 minutes
per day, in one or two sittings.

60 minutes is a constraint, not a goal. Beyond that, judgement
decays and the corpus suffers. If the queue needs more than 60
minutes, the queue is the problem (too noisy, wrong thresholds)
— not the reviewer.

**Moderation protects corpus quality, not throughput.**

### 03.2 The review queue
The queue is sorted by `model_score`, descending.

Each queue item shows:

- the snippet (the homeowner's sentence, verbatim)
- the source URL (one-click open)
- the signal_type (01.4)
- the model's suggested confidence_band
- the region
- the regional installer this would route to

**Queue order is advisory, not authoritative.** Reviewers are
free to skip items the model ranked high when judgement disagrees.

### 03.3 The four reviewer verbs
A reviewer can do exactly four things to a lead:

```
PROMOTE   accept at a band higher than the model suggested
ACCEPT    accept at the suggested band
DEMOTE    accept at a band lower than suggested
REJECT    refuse, with a reason from 03.4
```

**NEW is the only allowed holding state.** There is no MAYBE,
no FOLLOW_UP, no LATER. A lead is either being decided, decided,
or decayed (01.6). Indecision means leaving the lead in NEW for
the next sitting — but never past the decay window.

### 03.4 Rejection reasons (closed enum, v0)

```
NOT_INTENT     poster is not a homeowner / not buying
WRONG_REGION   no installer covers this area
DUPLICATE      same person seen before in corpus
PRIVACY        routing would clearly embarrass the poster
STALE          older than the band's decay window
UNCLEAR        not enough context to band confidently
```

Each rejection appends a row to `lead_log` with the reason.
Conversion analytics aggregate by reason — this is how the queue
tunes itself over time.

A rejected lead joins the corpus for reviewer learning and
threshold tuning. **It never becomes deliverable. Corpus retention
≠ delivery eligibility.**

Rejection reasons are versioned. New reasons require doctrine
revision.

### 03.5 Banding heuristics

HOT requires both:

> **A.** Explicit purchase intent — the homeowner is asking about
> buying, installing, or comparing offers (not researching in the
> abstract).
>
> **B.** Either:
>
> - **B.1** a timeline hook (months, "asap", "voor de winter"),
>   OR
> - **B.2** routing-grade identity context (region + system size
>   + specific needs that point to a single installer).

Timeline (B.1) remains the heaviest single signal — but explicit
purchase intent with strong identity context qualifies as HOT
even without an explicit window.

WARM requires A without B, or research intent (signal_type
INTENT_RESEARCH per 01.4) with enough context to band confidently
even when explicit purchase intent is absent.

OPP is anything weaker that still meets the five-thing rule (00.2).

### 03.6 The signature semantics
`reviewed_by` is a name, not a role.

When you sign a lead, you are saying:

- I read the snippet.
- I opened the source.
- I checked the region against the installer.
- I would defend this lead if the installateur called.

If any of these is not true, do not sign. Leave the lead in NEW.

### 03.7 The privacy gate
We capture from public posts. Public is a legal status, not a
moral license.

The test: would the homeowner be **relieved or angry** if they
learned an installateur saw their post and called?

If the answer isn't "relieved," REJECT with reason PRIVACY.

The corpus keeps the lead; the installateur never sees it.

### 03.8 Anti-patterns
- Approving a lead without opening the source
- Rubber-stamping the model's suggested band
- Banding by gut instead of the three heuristics (03.5)
- Adding a fifth verb (no MAYBE, no FOLLOW_UP, no LATER)
- Leaving leads in NEW past the decay window
- Skipping the privacy gate because the snippet is "interesting"
- Naming the role instead of the human in `reviewed_by`

---

## 04. Trust patterns for installateurs

The felt-experience. Everything else exists to produce this
feeling. This is what installateurs unconsciously test every
time they receive a lead.

### 04.1 The trust contract
Every installateur signs the same six-line contract, implicitly,
the first time they receive a lead:

1. You are the only installateur who saw this lead.
2. The lead carries a public source URL you can open.
3. A named human reviewed it before it reached you.
4. We will not re-route this lead to anyone else.
5. We will not paraphrase what the homeowner wrote.
6. If the lead is wrong, you tell us, and we make it right.

**This contract is the product.** Everything we build is in
service of keeping it.

### 04.2 The five trust events
Trust is earned or broken at five moments:

```
ARRIVAL       first sight of the lead
              → citation surface (02.1) within one view

VERIFICATION  click-through to source
              → source resolves, or archive (01.3) substitutes
                with a DECAYED stamp

CONVERSATION  the call/email to the homeowner
              → snippet accurately represents intent
                (no paraphrase, no embellishment)

OUTCOME       report-back (deal / no-deal)
              → recorded as fuel for the corpus, not paperwork

DISPUTE       a lead failed them
              → archive opened, trail walked together,
                credit issued if our discipline failed
```

### 04.3 The exclusivity guarantee
"One lead, one installateur, no competition" is not a slogan.
It is an operational invariant.

- A lead in state DELIVERED cannot be re-DELIVERED to another
  installateur. Ever.
- If the deal falls through, the lead transitions to OUTCOME
  (with reason), not back to APPROVED.
- It does not return to the deliverable pool.

Exclusivity is binding from the moment of DELIVERED. There are
no exceptions for "the homeowner ghosted them."

### 04.4 The dispute right
Every installateur can dispute any delivered lead within 14 days,
for any reason.

A dispute opens the archive (01.3). The reviewer and the
installateur walk the trail together against four checks:

- Was the snippet representative?
- Did the source URL resolve at capture?
- Was the region right?
- Was the band honest?

**Disputes are evaluated against doctrine, not customer
satisfaction alone.** If our discipline failed (sections 01–03),
the lead is credited. If discipline held but the deal didn't,
it is not — and we say so plainly.

### 04.5 The receipt
**Every delivered lead arrives as a receipt, not a ping.**

A receipt names:

- the snippet (verbatim)
- the source platform and URL
- the capture time
- the band, with one sentence explaining why
- the reviewer, by name, with a reply address

If we cannot produce all five, we cannot deliver.

### 04.6 The corpus relationship
Every OUTCOME the installateur reports back joins a private
corpus: "this sentence converted, this one did not."

The installateur contributes to the corpus and benefits from
its improvement. We commit:

- The corpus is used only to improve lead quality and reviewer
  judgement within Lead-radar.
- We never sell the corpus to a third party.
- If an installateur leaves, we delete their outcome reports
  and dispute history. The underlying signal records (snippet,
  source, band) stay — they are not derived from the
  installateur's participation.

### 04.7 Silence breaks the contract
The relationship is collaborative, not transactional.

**Silence breaks the contract faster than a bad lead does.**
If a week passes without a lead, the installateur should hear
from us anyway.

Operational defaults (revisable, not constitutional):

```
Weekly      written summary: leads delivered + outcomes
Monthly     voice call: corpus + thresholds + complaints
Always      a dispute reaches the reviewer within
            one business day
```

### 04.8 Anti-patterns
- Routing the same lead twice
- Paraphrasing the snippet in the delivery email
- Hiding the reviewer behind a generic alias
- "We've sent you 12 leads this month" without outcomes
- Disputes that go to a support queue instead of the reviewer
- Charging for leads the installateur disputed and won
- Selling the corpus
- Letting a week pass without contact

---

## Appendix A — Anti-pattern catalog

One-page card. Cite by item number (A19, A28, etc.) in PR
reviews and code comments. If a change hits one of these
items, the change is wrong. No explanation required.

### Provenance violations (01)
```
A1   Storing a score without a snippet
A2   Storing a snippet without source_url
A3   Editing snippets to "clean up grammar"
A4   Letting the model assign confidence_band directly
A5   Treating capture_evidence as optional
A6   Deleting decayed leads from the corpus
A7   Routing without a regional fit
```

### Interface violations (02)
```
A8   Numerical scores anywhere a band fits
A9   Paraphrased snippets in delivery, UI, or email
A10  Hero animations on the lead detail screen
A11  Empty states with mascots/illustrations
A12  Suggesting actions without a cited reason
A13  Auto-generated email subject lines
A14  "AI" in chrome unless installateur typed it first
A15  Model names in chrome ("Powered by GPT-4")
A16  Anthropomorphized scanners ("AI is thinking…")
A17  Showing a band without provenance in one view
```

### Moderation violations (03)
```
A18  Approving a lead without opening the source
A19  Rubber-stamping the model's suggested band
A20  Banding by gut instead of the 03.5 heuristics
A21  Adding a fifth reviewer verb (MAYBE/FOLLOW_UP/LATER)
A22  Leaving leads in NEW past the decay window
A23  Skipping the privacy gate because the snippet is "interesting"
A24  Naming a role instead of a human in reviewed_by
```

### Trust violations (04)
```
A25  Routing the same lead twice
A26  Hiding the reviewer behind a generic alias
A27  Reporting volume ("12 leads this month") without outcomes
A28  Disputes that route to a support queue instead of the reviewer
A29  Charging for leads the installateur disputed and won
A30  Selling the corpus
A31  Letting a week pass without contact
```

---

## Appendix B — Vocabulary

Canonical terms with definitions, plus banned synonyms with their
preferred replacements. Vocabulary changes require doctrine
revision (02.3). Codex treats this as linter input for every UI
string, email template, copy block, and docstring.

### B.1 Terms we use

```
signal              a public sentence with verifiable intent
                    that we have captured and may band

lead                a signal that has been reviewed, banded,
                    and is eligible for delivery

snippet             the verbatim sentence the homeowner wrote
                    (≤280 chars, never edited)

source              the public page where the snippet lives;
                    always a resolvable URL

trail               the chain of evidence behind a lead:
                    source + snippet + capture time + reviewer

provenance          the verifiable chain linking a lead to its
                    original public source and review trail;
                    every other commitment compiles down to this

reviewer            the named human who banded the lead and
                    would defend it on a call

band                the delivery classification — HOT, WARM, OPP
                    (assigned by the reviewer, never the model)

model_score         the model's numeric priority hint; used only
                    to order the queue (03.2)

corpus              the private archive of every reviewed signal
                    + every reported outcome

archive             the offline snapshot of a source page at
                    capture time; auditor's safety net (01.3)

reviewed_by         the name of the accountable reviewer;
                    present on every delivered lead

delivery_condition  metadata on a delivered lead —
                    FRESH, DECAYED, or EDITED

receipt             a delivered lead with all five citation
                    fields present and rendered (04.5)

routing             the exclusive assignment of a reviewed lead
                    to exactly one installateur; binding from
                    DELIVERED onward (04.3)

dispute             an installateur's challenge to a delivered
                    lead; opens the archive (04.4)

decayed             a source that 404'd or was edited after
                    capture; metadata, not a workflow state (01.6)

doctrine            this document; revision-controlled

installateur        the partner who receives and acts on leads
                    (never "customer", never "user")

homeowner           the person whose public post became a signal
                    (never "lead", never "user", never "prospect")
```

### B.2 Terms we never use

```
Never say              Say instead              Why
─────────────────────────────────────────────────────────────────
lead score             model_score + band       collapses two
                                                different things
qualified lead         reviewed lead            "qualified" is
                                                industry hype
lead quality score     band + reviewer name     same as above
scraped data           captured from {platform} extractive framing
AI lead                signal                   misnames what
                                                we sell
high probability       band (HOT/WARM/OPP)      false precision
87% confidence         band                     false precision
customer               installateur             relationship is
                                                collaborative
user                   installateur / homeowner depends on which
                                                human we mean
algorithm              model (internal) /       "algorithm" hides
                       reviewer (external)      who decided
pipeline               the trail (external) /   "pipeline" hides
                       the queue (internal)     human steps
approved by AI         reviewed by {name}       accountability is
                                                the product
marketplace            routing service          we are not one
ai-powered             reviewer-led             wrong stance
smart leads            reviewed leads           empty marketing word
magic                  traceability             anti-doctrine
```

---

## Revision policy

This document is frozen at v0.1. Once frozen:

- Sections 00–04 change only with an explicit version bump
  (v0.2, v1.0, etc.) and a revision rationale committed alongside.
- Appendix A may add new items at the end (A32, A33, …) without a
  version bump, but must never renumber existing items.
- Appendix B may add new entries to B.1 and B.2 without a version
  bump, but must never change existing definitions or remove
  entries without one.
- Vocabulary deletions, definition changes, or rule removals
  require a version bump.

**Doctrine freeze prevents expansion drift.** Endless doctrine
revision before operational reality has spoken is itself an
anti-pattern: it substitutes intellectual production for the
feedback loop the doctrine exists to enable.

The doctrine compiles down to one test, applied to every product
decision:

> Helpt dit ons bewijzen dat installateurs deze leads blijven
> kopen?

If the answer isn't a clear yes, the change is not aligned with
doctrine, regardless of which section it appears to satisfy.
