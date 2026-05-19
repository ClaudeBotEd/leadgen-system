# Lead Radar — Operator Intelligence Console v0

The daily operator workstation. Reads from owned Postgres, writes decisions to the audit log (proprietary dataset).

## Quick start

```bash
cp .env.example .env
# Edit .env: set DATABASE_URL, FOUNDER_EMAIL, RESEND_API_KEY, RESEND_FROM, NEXTAUTH_SECRET
docker compose up -d
pnpm install
pnpm db:migrate
pnpm db:seed
pnpm db:seed-fixtures  # optional: dev-time fixtures (3 routing + 3 classification + 1 conversion)
pnpm dev
```

Open http://localhost:3000 → log in with FOUNDER_EMAIL via magic-link.

## Workflows

- **Routing** (`/q/lead_delivery_routing`) — approve/route HOT leads to installers
- **Classification** (`/q/signal_classification_ambiguous_band`) — classify ambiguous signals (40-75 confidence band)
- **Conversion** (`/q/conversion_registration`) — register conversion outcomes

## Keyboard shortcuts

Press `?` in any card for the full list. Quick reference:

| Key | Action |
|---|---|
| `1` `2` `3` | Jump to workflow (from triage) |
| `A` | Approve agent recommendation (routing) |
| `P` | Pick alternative installer (routing) |
| `O` | Override (any card) |
| `H` | Hold |
| `N` | Next without action (or No-intent for classification) |
| `V` | View audit chain |
| `U` / `M` / `T` | Uncertain / Mixed / Taxonomy-gap qualifier (classification) |
| `S` / `E` / `F` | Save / Edit / Flag dispute (conversion) |
| `/` | Universal search |
| `Esc` | Back / cancel |
| `?` | Keyboard help overlay |

## Architecture

See `lead-radar/docs/superpowers/specs/`:
- `2026-05-18-autonomy-architecture-design.md` — the rule system (regelsysteem)
- `2026-05-18-operator-intelligence-console-v0-design.md` — this UI/UX design

## Testing

```bash
pnpm test           # vitest unit + integration
pnpm test:e2e       # playwright e2e (requires ENABLE_TEST_AUTH=1)
```

## Tech stack

Next.js 15 + React 19 + Drizzle ORM + postgres.js + NextAuth v5 + Resend + shadcn/Tailwind + Vitest + Playwright.
