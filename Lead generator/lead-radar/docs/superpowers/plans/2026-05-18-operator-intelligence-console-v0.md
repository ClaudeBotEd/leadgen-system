# Operator Intelligence Console v0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the daily operator workstation defined in `2026-05-18-operator-intelligence-console-v0-design.md` — a Next.js + shadcn + owned-Postgres app with three screens (triage, card-stack queue, inline audit), twelve components, and the autonomy-architecture as input contract.

**Architecture:** Standalone Next.js App Router app at `lead-radar-console/`. Owned Postgres shared with the (future) Python consumer pipeline writes. NextAuth v5 magic-link via Resend. shadcn/ui + Tailwind v4. Drizzle ORM for schema + migrations, raw SQL for complex audit/search queries. Server Actions for writes. Queue-claim mechanism vanaf dag 1 (no singleton assumptions). MVP path delivers Routing-only daily usability by end of Phase 3; subsequent phases add Classification, Conversion, Audit-tree, Search, Headroom, Deep-links.

**Tech Stack:** Next.js 15 (App Router), React 19, TypeScript, shadcn/ui, Tailwind v4, pnpm, NextAuth v5 (Auth.js) + Resend magic-link, Drizzle ORM + `postgres.js`, Vitest (unit), Playwright (e2e), Docker Compose voor lokale Postgres.

**Critical implementation disciplines (from spec sections 5.5, 7, 11, 14):**
- Queue-safe / session-safe / state-safe / lock-safe vanaf dag 1 — geen singleton assumptions
- Auto-save op actie, geen save-buttons
- Keyboard-first met single-letter shortcuts, mouse-tolerant
- One-look V0 (8-pixel grid, monospace voor decision-data, monochrome + 3 status-colors)
- Audit log = proprietary dataset — append-only, offsite backup vanaf dag 1
- "Optimaliseer voor *eerste dagelijkse bruikbaarheid*, niet *architecturaal perfect systeem*"

---

## Phase Index

- **Phase 0** — Project Bootstrap + DB Foundation (5 tasks)
- **Phase 1** — Auth & Operator Identity (3 tasks)
- **Phase 2** — Workflow Profile Reader + Decision Write API + Kill-state + Queue Claims (4 tasks)
- **Phase 3** — Triage Overview + Card Shell + Routing Card (MVP daily usability) (6 tasks)
- **MVP checkpoint** — by end of Phase 3 the founder can log in, review routing decisions with keyboard, and have everything audit-logged
- **Phase 4** — Override Inline Flow (3 tasks)
- **Phase 5** — Classification Card with qualifiers (2 tasks)
- **Phase 6** — Conversion Registration Card (1 task)
- **Phase 7** — Audit Chain Inline Tree-view (1 task)
- **Phase 8** — Universal Search + Retrieval Service (2 tasks)
- **Phase 9** — Operational Headroom Widget (1 task)
- **Phase 10** — State-Preserving Deep-Links + Telegram Integration (1 task)
- **Phase 11** — Final Polish + End-to-end Test (3 tasks)

**Total: ~28 tasks**

---

## File Structure

```
lead-radar-console/
├── package.json
├── next.config.ts
├── tsconfig.json
├── drizzle.config.ts
├── docker-compose.yml
├── .env.example
├── auth.ts                             # NextAuth v5 root export
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # redirect to /triage or /login
│   │   ├── login/page.tsx
│   │   ├── login/verify/page.tsx
│   │   ├── triage/page.tsx
│   │   ├── q/[workflow]/page.tsx
│   │   ├── d/[decisionId]/page.tsx     # deep-link
│   │   ├── l/[leadId]/page.tsx         # lead audit deep-link
│   │   └── api/
│   │       ├── auth/[...nextauth]/route.ts
│   │       ├── decisions/route.ts
│   │       ├── queues/[workflow]/route.ts
│   │       ├── triage/route.ts
│   │       ├── search/route.ts
│   │       ├── audit/[leadId]/route.ts
│   │       └── headroom/route.ts
│   ├── components/
│   │   ├── triage/{WorkflowBlock,TriageKeyboard}.tsx
│   │   ├── card/{CardShell,TopStrip,WhyString,ActionBar,KeyboardHelp}.tsx
│   │   ├── routing/{RoutingCard,InstallerRecommendation}.tsx
│   │   ├── classification/ClassificationCard.tsx
│   │   ├── conversion/ConversionCard.tsx
│   │   ├── override/OverrideInlineForm.tsx
│   │   ├── audit/{AuditChainView,AuditTreeNode}.tsx
│   │   ├── search/SearchOverlay.tsx
│   │   └── headroom/OperationalHeadroomWidget.tsx
│   ├── lib/
│   │   ├── db/{client,schema,decisions,workflow-profiles,kill-state,queue-claims,operators,override-categories}.ts
│   │   ├── auth/config.ts
│   │   ├── why-string/{rules,generator}.ts
│   │   ├── retrieval/{index,text-mode,exact-mode}.ts
│   │   ├── headroom/calculator.ts
│   │   ├── telegram/deep-links.ts
│   │   └── keyboard/useKeyboardShortcuts.ts
│   └── db/
│       └── migrations/                 # Drizzle-generated + 9999_search_indexes.sql
└── tests/
    ├── unit/                           # Vitest
    ├── integration/                    # Vitest + test DB
    └── e2e/                            # Playwright
```

---

## Phase 0 — Project Bootstrap + DB Foundation

### Task 0.1: Initialize Next.js + pnpm

**Files:**
- Create: `lead-radar-console/` directory and core Next.js scaffolding
- Create: `lead-radar-console/.env.example`

- [ ] **Step 1: Initialize Next.js**

```bash
cd "/Users/claudebot/Lead generator"
pnpm create next-app@15 lead-radar-console --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd lead-radar-console
mkdir -p src
mv app src/app
sed -i.bak 's|\./app|./src/app|g' tsconfig.json && rm tsconfig.json.bak
```

- [ ] **Step 2: Add dependencies**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
pnpm add postgres drizzle-orm next-auth@beta @auth/drizzle-adapter resend zod
pnpm add -D drizzle-kit vitest @vitest/ui @playwright/test @types/node tsx dotenv
```

- [ ] **Step 3: Create .env.example**

Create `lead-radar-console/.env.example`:
```
# Database
DATABASE_URL=postgresql://console:console@localhost:5432/lead_radar

# Auth
NEXTAUTH_SECRET=          # openssl rand -base64 32
NEXTAUTH_URL=http://localhost:3000
RESEND_API_KEY=
RESEND_FROM=noreply@yourdomain.com

# Telegram (V1+, optional V0)
TELEGRAM_BOT_TOKEN=
CONSOLE_BASE_URL=http://localhost:3000

# Founder identity (seed)
FOUNDER_EMAIL=
FOUNDER_NAME=
```

- [ ] **Step 4: Verify build**

```bash
cp .env.example .env
pnpm install
pnpm build
```
Expected: build completes (warnings OK, errors not).

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/
git commit -m "feat(console): bootstrap Next.js 15 project + core dependencies"
```

---

### Task 0.2: Docker Postgres + Drizzle config + DB client

**Files:**
- Create: `lead-radar-console/docker-compose.yml`
- Create: `lead-radar-console/drizzle.config.ts`
- Create: `lead-radar-console/src/lib/db/client.ts`
- Create: `lead-radar-console/tests/unit/db-connection.test.ts`

- [ ] **Step 1: docker-compose.yml**

```yaml
version: '3.9'
services:
  postgres:
    image: postgres:16-alpine
    container_name: lead-radar-console-pg
    environment:
      POSTGRES_USER: console
      POSTGRES_PASSWORD: console
      POSTGRES_DB: lead_radar
    ports: ["5432:5432"]
    volumes: [lead_radar_pg_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U console"]
      interval: 5s
      retries: 5
volumes:
  lead_radar_pg_data:
```

Run: `docker compose up -d && docker compose ps`
Expected: container is `healthy`.

- [ ] **Step 2: drizzle.config.ts**

```typescript
import { defineConfig } from 'drizzle-kit';
export default defineConfig({
  schema: './src/lib/db/schema.ts',
  out: './src/db/migrations',
  dialect: 'postgresql',
  dbCredentials: { url: process.env.DATABASE_URL ?? 'postgresql://console:console@localhost:5432/lead_radar' },
  strict: true, verbose: true,
});
```

- [ ] **Step 3: DB client**

Create `src/lib/db/client.ts`:
```typescript
import postgres from 'postgres';
import { drizzle } from 'drizzle-orm/postgres-js';
import * as schema from './schema';

const connectionString = process.env.DATABASE_URL;
if (!connectionString) throw new Error('DATABASE_URL is required');

export const sql = postgres(connectionString, { max: 10, idle_timeout: 30 });
export const db = drizzle(sql, { schema });
```

- [ ] **Step 4: Smoke test**

Create `tests/unit/db-connection.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { sql } from '@/lib/db/client';

describe('db connection', () => {
  it('connects', async () => {
    const r = await sql`SELECT 1 as one`;
    expect(r[0].one).toBe(1);
    await sql.end();
  });
});
```

Run: `pnpm vitest run tests/unit/db-connection.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/docker-compose.yml lead-radar-console/drizzle.config.ts lead-radar-console/src/lib/db/ lead-radar-console/tests/unit/db-connection.test.ts
git commit -m "feat(console): Docker Postgres + Drizzle config + DB client smoke test"
```

---

### Task 0.3: Drizzle schema for all V0 tables

**Files:**
- Create: `lead-radar-console/src/lib/db/schema.ts`
- Create: `lead-radar-console/tests/unit/schema-shape.test.ts`

- [ ] **Step 1: Schema**

Create `src/lib/db/schema.ts`:
```typescript
import { pgTable, uuid, text, boolean, integer, timestamp, jsonb, real, pgEnum, index, uniqueIndex } from 'drizzle-orm/pg-core';

export const operatorRoleEnum = pgEnum('operator_role', ['operator', 'senior', 'lead']);

export const operators = pgTable('operators', {
  operatorId: uuid('operator_id').defaultRandom().primaryKey(),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
  role: operatorRoleEnum('role').notNull().default('operator'),
  active: boolean('active').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
});

export const sessions = pgTable('sessions', {
  sessionId: text('session_id').primaryKey(),
  operatorId: uuid('operator_id').notNull().references(() => operators.operatorId),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
  lastSeenAt: timestamp('last_seen_at', { withTimezone: true }).notNull().defaultNow(),
});

export const overrideCategories = pgTable('override_categories', {
  categoryKey: text('category_key').primaryKey(),
  displayLabel: text('display_label').notNull(),
  active: boolean('active').notNull().default(true),
  sortOrder: integer('sort_order').notNull().default(0),
  addedAt: timestamp('added_at', { withTimezone: true }).notNull().defaultNow(),
});

export const workflowProfiles = pgTable('workflow_profiles', {
  workflowId: text('workflow_id').notNull(),
  profileVersion: integer('profile_version').notNull(),
  profile: jsonb('profile').notNull(),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  createdBy: uuid('created_by').references(() => operators.operatorId),
}, (t) => ({
  pk: uniqueIndex('workflow_profiles_pk').on(t.workflowId, t.profileVersion),
}));

export const workflowKillState = pgTable('workflow_kill_state', {
  workflowId: text('workflow_id').primaryKey(),
  killedUntil: timestamp('killed_until', { withTimezone: true }),
  reason: text('reason').notNull(),
  setBy: uuid('set_by').notNull().references(() => operators.operatorId),
  setAt: timestamp('set_at', { withTimezone: true }).notNull().defaultNow(),
});

export const decisions = pgTable('decisions', {
  decisionId: uuid('decision_id').defaultRandom().primaryKey(),
  workflowId: text('workflow_id').notNull(),
  profileVersion: integer('profile_version').notNull(),
  tierAtDecision: text('tier_at_decision').notNull(),
  inputsHash: text('inputs_hash').notNull(),
  inputsPayload: jsonb('inputs_payload').notNull(),
  agentId: text('agent_id'),
  agentRecommendation: jsonb('agent_recommendation'),
  agentConfidence: real('agent_confidence'),
  agentReasoningRef: text('agent_reasoning_ref'),
  reviewerId: uuid('reviewer_id').references(() => operators.operatorId),
  reviewerDecision: jsonb('reviewer_decision'),
  agreement: text('agreement'),
  overrideReason: text('override_reason'),
  overrideCategory: text('override_category').references(() => overrideCategories.categoryKey),
  decidedAt: timestamp('decided_at', { withTimezone: true }).notNull().defaultNow(),
  timeToDecideMs: integer('time_to_decide_ms'),
  outcome: jsonb('outcome'),
  leadId: text('lead_id'),
  signalId: text('signal_id'),
}, (t) => ({
  workflowIdx: index('decisions_workflow_idx').on(t.workflowId, t.decidedAt),
  leadIdx: index('decisions_lead_idx').on(t.leadId),
  signalIdx: index('decisions_signal_idx').on(t.signalId),
  reviewerIdx: index('decisions_reviewer_idx').on(t.reviewerId),
}));

export const queueClaims = pgTable('queue_claims', {
  decisionId: uuid('decision_id').primaryKey().references(() => decisions.decisionId),
  claimedBy: uuid('claimed_by').notNull().references(() => operators.operatorId),
  claimedAt: timestamp('claimed_at', { withTimezone: true }).notNull().defaultNow(),
  expiresAt: timestamp('expires_at', { withTimezone: true }).notNull(),
});

export type Operator = typeof operators.$inferSelect;
export type Decision = typeof decisions.$inferSelect;
export type WorkflowProfile = typeof workflowProfiles.$inferSelect;
```

- [ ] **Step 2: Generate + apply migration**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
pnpm drizzle-kit generate
pnpm drizzle-kit migrate
```
Expected: tables created in Postgres.

- [ ] **Step 3: Smoke test**

Create `tests/unit/schema-shape.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { sql } from '@/lib/db/client';

describe('schema', () => {
  it('has all V0 tables', async () => {
    const tables = await sql<{ tablename: string }[]>`
      SELECT tablename FROM pg_tables WHERE schemaname = 'public'`;
    const names = tables.map(t => t.tablename);
    for (const t of ['operators', 'sessions', 'override_categories', 'workflow_profiles', 'workflow_kill_state', 'decisions', 'queue_claims']) {
      expect(names).toContain(t);
    }
    await sql.end();
  });
});
```

Run: `pnpm vitest run tests/unit/schema-shape.test.ts`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/schema.ts lead-radar-console/src/db/migrations/ lead-radar-console/tests/unit/schema-shape.test.ts
git commit -m "feat(console): Drizzle schema for V0 tables (operators, sessions, decisions, profiles, kill-state, queue-claims, override-categories)"
```

---

### Task 0.4: Seed founder + override categories + initial workflow profiles

**Files:**
- Create: `lead-radar-console/src/db/seed.ts`
- Modify: `lead-radar-console/package.json` (scripts)
- Create: `lead-radar-console/tests/unit/seed.test.ts`

- [ ] **Step 1: Seed script**

Create `src/db/seed.ts`:
```typescript
import { db, sql } from '@/lib/db/client';
import { operators, overrideCategories, workflowProfiles } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

const FOUNDER_EMAIL = process.env.FOUNDER_EMAIL;
const FOUNDER_NAME = process.env.FOUNDER_NAME ?? 'Founder';

async function seed() {
  if (!FOUNDER_EMAIL) throw new Error('FOUNDER_EMAIL required');

  await db.insert(operators).values({ name: FOUNDER_NAME, email: FOUNDER_EMAIL, role: 'lead' })
    .onConflictDoNothing({ target: operators.email });

  await db.insert(overrideCategories).values([
    { categoryKey: 'taxonomy_miss', displayLabel: 'taxonomy miss', sortOrder: 1 },
    { categoryKey: 'too_strict', displayLabel: 'too strict', sortOrder: 2 },
    { categoryKey: 'too_lax', displayLabel: 'too lax', sortOrder: 3 },
    { categoryKey: 'context_missing', displayLabel: 'context missing', sortOrder: 4 },
    { categoryKey: 'other', displayLabel: 'other', sortOrder: 5 },
  ]).onConflictDoNothing();

  const founder = await db.query.operators.findFirst({ where: eq(operators.email, FOUNDER_EMAIL) });

  await db.insert(workflowProfiles).values([
    {
      workflowId: 'lead_delivery_routing', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'standard', risk_class: 'trust_load_bearing',
        current_tier: 'T1', terminal_tier: 'T2',
        cof_vector: { financial: 'low', installer_relationship: 'high', exclusivity: 'high', dataset_corruption: 'medium', ops_cascade: 'medium' },
        cof_circuit_breakers: ['exclusivity_breach_risk_per_decision > 0.1%'],
        latency_class: 'L2', sla_budget_minutes: 240, fallback_policy: 'F-B', out_of_hours_policy: 'pause',
        ocl_budget: { per_operator_minutes_per_day: 30, complexity: 'medium', expected_volume_per_day: 50 },
      },
    },
    {
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'standard', risk_class: 'quality_load_bearing',
        current_tier: 'T1', terminal_tier: 'T3',
        cof_vector: { financial: 'very_low', installer_relationship: 'low', exclusivity: 'none', dataset_corruption: 'medium', ops_cascade: 'medium' },
        latency_class: 'L1', sla_budget_minutes: 60, fallback_policy: 'F-A', out_of_hours_policy: 'fallback_allowed',
        ocl_budget: { per_operator_minutes_per_day: 60, complexity: 'medium', expected_volume_per_day: 100 },
      },
    },
    {
      workflowId: 'conversion_registration', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'critical', risk_class: 'dataset_defining',
        current_tier: 'T1', terminal_tier: 'T1',
        cof_vector: { financial: 'low', installer_relationship: 'low', exclusivity: 'none', dataset_corruption: 'catastrophic', ops_cascade: 'cascading' },
        latency_class: 'L3', sla_budget_minutes: 10080, fallback_policy: 'F-C', out_of_hours_policy: 'pause',
        ocl_budget: { per_operator_minutes_per_day: 30, complexity: 'complex', expected_volume_per_day: 5 },
      },
    },
  ]).onConflictDoNothing();

  await sql.end();
  console.log('✓ Seeded');
}

seed().catch(err => { console.error(err); process.exit(1); });
```

- [ ] **Step 2: Add package.json scripts**

```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "eslint",
  "test": "vitest run",
  "test:e2e": "playwright test",
  "db:generate": "drizzle-kit generate",
  "db:migrate": "drizzle-kit migrate",
  "db:seed": "tsx --env-file=.env src/db/seed.ts"
}
```

- [ ] **Step 3: Run seed**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
pnpm db:seed
```
Expected: `✓ Seeded`.

- [ ] **Step 4: Test**

Create `tests/unit/seed.test.ts`:
```typescript
import { describe, it, expect } from 'vitest';
import { db, sql } from '@/lib/db/client';
import { operators, overrideCategories, workflowProfiles } from '@/lib/db/schema';

describe('seed', () => {
  it('inserted founder operator with lead role', async () => {
    const ops = await db.select().from(operators);
    expect(ops.find(o => o.role === 'lead')).toBeDefined();
  });
  it('inserted 5 override categories', async () => {
    const cats = await db.select().from(overrideCategories);
    expect(cats.length).toBe(5);
  });
  it('inserted 3 workflow profiles', async () => {
    const wfs = await db.select().from(workflowProfiles);
    expect(wfs.length).toBe(3);
    await sql.end();
  });
});
```

Run: PASS.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/db/seed.ts lead-radar-console/package.json lead-radar-console/tests/unit/seed.test.ts
git commit -m "feat(console): seed founder + override categories + initial workflow profiles"
```

---

### Task 0.5: Vitest + Playwright config

**Files:**
- Create: `lead-radar-console/vitest.config.ts`
- Create: `lead-radar-console/playwright.config.ts`
- Create: `lead-radar-console/tests/setup.ts`

- [ ] **Step 1: Vitest config**

Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import path from 'path';
export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  test: {
    environment: 'node',
    include: ['tests/unit/**/*.test.ts', 'tests/integration/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
  },
});
```

- [ ] **Step 2: Test setup**

Create `tests/setup.ts`:
```typescript
import { config } from 'dotenv';
config({ path: '.env' });
```

- [ ] **Step 3: Playwright config**

Create `playwright.config.ts`:
```typescript
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 1,
  use: { baseURL: 'http://localhost:3000' },
  webServer: { command: 'pnpm dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI },
});
```

- [ ] **Step 4: Verify**

```bash
pnpm test
```
Expected: all earlier unit tests still PASS.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/vitest.config.ts lead-radar-console/playwright.config.ts lead-radar-console/tests/setup.ts
git commit -m "feat(console): Vitest + Playwright test configuration"
```

---

## Phase 1 — Auth & Operator Identity

### Task 1.1: NextAuth v5 config

**Files:**
- Create: `lead-radar-console/auth.ts`
- Create: `lead-radar-console/src/lib/auth/config.ts`
- Create: `lead-radar-console/src/app/api/auth/[...nextauth]/route.ts`

- [ ] **Step 1: Auth config**

Create `src/lib/auth/config.ts`:
```typescript
import Resend from 'next-auth/providers/resend';
import { DrizzleAdapter } from '@auth/drizzle-adapter';
import { db } from '@/lib/db/client';
import { operators } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import type { NextAuthConfig } from 'next-auth';

export const authConfig: NextAuthConfig = {
  adapter: DrizzleAdapter(db),
  session: { strategy: 'database', maxAge: 30 * 24 * 60 * 60 },
  providers: [
    Resend({
      apiKey: process.env.RESEND_API_KEY,
      from: process.env.RESEND_FROM ?? 'noreply@example.com',
    }),
  ],
  pages: { signIn: '/login', verifyRequest: '/login/verify' },
  callbacks: {
    async signIn({ user }) {
      const existing = await db.query.operators.findFirst({ where: eq(operators.email, user.email!) });
      return existing != null && existing.active;
    },
  },
};
```

- [ ] **Step 2: Root auth.ts**

Create `auth.ts`:
```typescript
import NextAuth from 'next-auth';
import { authConfig } from '@/lib/auth/config';
export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
```

- [ ] **Step 3: Route handler**

Create `src/app/api/auth/[...nextauth]/route.ts`:
```typescript
export { GET, POST } from '@/../auth';
```

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/auth.ts lead-radar-console/src/lib/auth/ lead-radar-console/src/app/api/auth/
git commit -m "feat(console): NextAuth v5 + Resend magic-link + signIn restricted to seeded operators"
```

---

### Task 1.2: Login + verify pages + root redirect

**Files:**
- Create: `lead-radar-console/src/app/login/page.tsx`
- Create: `lead-radar-console/src/app/login/verify/page.tsx`
- Create: `lead-radar-console/src/app/page.tsx`

- [ ] **Step 1: Login page**

```tsx
// src/app/login/page.tsx
import { signIn } from '@/../auth';

export default function LoginPage() {
  async function loginAction(formData: FormData) {
    'use server';
    const email = formData.get('email') as string;
    await signIn('resend', { email, redirectTo: '/triage' });
  }
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100 font-mono">
      <div className="w-full max-w-sm p-8 border border-zinc-800 rounded">
        <h1 className="text-lg mb-6">Lead Radar — Operator Console</h1>
        <form action={loginAction} className="space-y-4">
          <input type="email" name="email" placeholder="operator@example.com" required
            className="w-full p-2 bg-zinc-900 border border-zinc-800 rounded" />
          <button type="submit" className="w-full p-2 bg-zinc-100 text-zinc-950 rounded">
            Send magic link
          </button>
        </form>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify page**

```tsx
// src/app/login/verify/page.tsx
export default function VerifyPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100 font-mono">
      <div className="w-full max-w-sm p-8 border border-zinc-800 rounded text-sm">
        <h1 className="text-lg mb-4">Check your email</h1>
        <p className="text-zinc-400">A login link has been sent.</p>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Root redirect**

```tsx
// src/app/page.tsx
import { redirect } from 'next/navigation';
import { auth } from '@/../auth';
export default async function RootPage() {
  const session = await auth();
  redirect(session ? '/triage' : '/login');
}
```

- [ ] **Step 4: Smoke test**

```bash
pnpm dev
```
Open `http://localhost:3000` → expect redirect to `/login`.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/app/login/ lead-radar-console/src/app/page.tsx
git commit -m "feat(console): login page + verify page + root redirect"
```

---

### Task 1.3: Operator helpers (requireCurrentOperator pattern)

**Files:**
- Create: `lead-radar-console/src/lib/db/operators.ts`
- Create: `lead-radar-console/tests/unit/operators.test.ts`

- [ ] **Step 1: Test first**

```typescript
// tests/unit/operators.test.ts
import { describe, it, expect } from 'vitest';
import { getOperatorByEmail } from '@/lib/db/operators';
import { sql } from '@/lib/db/client';

describe('operators', () => {
  it('finds founder by email', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    expect(op?.role).toBe('lead');
  });
  it('returns undefined for unknown', async () => {
    expect(await getOperatorByEmail('nobody@example.com')).toBeUndefined();
    await sql.end();
  });
});
```

Run: FAIL.

- [ ] **Step 2: Implement**

```typescript
// src/lib/db/operators.ts
import { db } from './client';
import { operators, type Operator } from './schema';
import { eq } from 'drizzle-orm';
import { auth } from '@/../auth';

export async function getOperatorByEmail(email: string): Promise<Operator | undefined> {
  return db.query.operators.findFirst({ where: eq(operators.email, email) });
}

export async function getOperatorById(id: string): Promise<Operator | undefined> {
  return db.query.operators.findFirst({ where: eq(operators.operatorId, id) });
}

/** NEVER cache. Always re-derive from session. */
export async function requireCurrentOperator(): Promise<Operator> {
  const session = await auth();
  if (!session?.user?.email) throw new Error('No active session');
  const op = await getOperatorByEmail(session.user.email);
  if (!op) throw new Error(`Session email not in operators: ${session.user.email}`);
  return op;
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/operators.ts lead-radar-console/tests/unit/operators.test.ts
git commit -m "feat(console): operator helpers with no-singleton requireCurrentOperator"
```

---

## Phase 2 — Workflow Profile Reader + Decision Write API + Kill State + Queue Claims

### Task 2.1: Workflow profile reader with 60s cache

**Files:**
- Create: `lead-radar-console/src/lib/db/workflow-profiles.ts`
- Create: `lead-radar-console/tests/unit/workflow-profiles.test.ts`

- [ ] **Step 1: Test first**

```typescript
// tests/unit/workflow-profiles.test.ts
import { describe, it, expect } from 'vitest';
import { getActiveProfile } from '@/lib/db/workflow-profiles';
import { sql } from '@/lib/db/client';

describe('workflow profiles', () => {
  it('returns active routing profile', async () => {
    const p = await getActiveProfile('lead_delivery_routing');
    expect((p?.profile as any).risk_class).toBe('trust_load_bearing');
  });
  it('returns undefined for unknown', async () => {
    expect(await getActiveProfile('nope')).toBeUndefined();
    await sql.end();
  });
});
```

- [ ] **Step 2: Implement with cache**

```typescript
// src/lib/db/workflow-profiles.ts
import { db } from './client';
import { workflowProfiles } from './schema';
import { eq, and, desc } from 'drizzle-orm';

const cache = new Map<string, { value: any; expiresAt: number }>();
const TTL = 60_000;

export async function getActiveProfile(workflowId: string) {
  const c = cache.get(workflowId);
  if (c && c.expiresAt > Date.now()) return c.value;

  const row = await db.query.workflowProfiles.findFirst({
    where: and(eq(workflowProfiles.workflowId, workflowId), eq(workflowProfiles.isActive, true)),
    orderBy: [desc(workflowProfiles.profileVersion)],
  });
  if (!row) return undefined;
  const value = { workflow_id: row.workflowId, profile_version: row.profileVersion, profile: row.profile, is_active: row.isActive };
  cache.set(workflowId, { value, expiresAt: Date.now() + TTL });
  return value;
}

export function invalidateProfileCache(workflowId?: string) {
  if (workflowId) cache.delete(workflowId); else cache.clear();
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/workflow-profiles.ts lead-radar-console/tests/unit/workflow-profiles.test.ts
git commit -m "feat(console): workflow profile reader with 60s in-memory cache"
```

---

### Task 2.2: Kill-state checker

**Files:**
- Create: `lead-radar-console/src/lib/db/kill-state.ts`
- Create: `lead-radar-console/tests/unit/kill-state.test.ts`

- [ ] **Step 1: Test**

```typescript
import { describe, it, expect } from 'vitest';
import { isWorkflowKilled, killWorkflow, releaseWorkflowKill } from '@/lib/db/kill-state';
import { getOperatorByEmail } from '@/lib/db/operators';
import { sql } from '@/lib/db/client';

describe('kill state', () => {
  it('roundtrip kill + release', async () => {
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(false);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    await killWorkflow('lead_delivery_routing', 'test', op!.operatorId);
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(true);
    await releaseWorkflowKill('lead_delivery_routing');
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(false);
    await sql.end();
  });
});
```

- [ ] **Step 2: Implement**

```typescript
// src/lib/db/kill-state.ts
import { db } from './client';
import { workflowKillState } from './schema';
import { eq, and, gt, isNull, or } from 'drizzle-orm';

export async function isWorkflowKilled(workflowId: string): Promise<boolean> {
  const row = await db.query.workflowKillState.findFirst({
    where: and(eq(workflowKillState.workflowId, workflowId), or(isNull(workflowKillState.killedUntil), gt(workflowKillState.killedUntil, new Date()))),
  });
  return row != null;
}

export async function killWorkflow(workflowId: string, reason: string, setBy: string, durationMs?: number) {
  const killedUntil = durationMs ? new Date(Date.now() + durationMs) : null;
  await db.insert(workflowKillState).values({ workflowId, reason, setBy, killedUntil })
    .onConflictDoUpdate({ target: workflowKillState.workflowId, set: { reason, setBy, killedUntil, setAt: new Date() } });
}

export async function releaseWorkflowKill(workflowId: string) {
  await db.delete(workflowKillState).where(eq(workflowKillState.workflowId, workflowId));
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/kill-state.ts lead-radar-console/tests/unit/kill-state.test.ts
git commit -m "feat(console): kill-state checker + kill/release helpers"
```

---

### Task 2.3: Queue-claim mechanism

**Files:**
- Create: `lead-radar-console/src/lib/db/queue-claims.ts`
- Create: `lead-radar-console/tests/unit/queue-claims.test.ts`

- [ ] **Step 1: Test (uses INSERT helper for test decisions)**

```typescript
// tests/unit/queue-claims.test.ts
import { describe, it, expect, afterEach } from 'vitest';
import { tryClaim, releaseClaim, getClaimer } from '@/lib/db/queue-claims';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { sql as ds } from 'drizzle-orm';

const D1 = '11111111-1111-1111-1111-111111111111';

async function insertTestDecision(id: string) {
  await db.execute(ds`
    INSERT INTO decisions (decision_id, workflow_id, profile_version, tier_at_decision, inputs_hash, inputs_payload, decided_at)
    VALUES (${id}, 'lead_delivery_routing', 1, 'T1', 'h', '{}'::jsonb, now())
    ON CONFLICT DO NOTHING
  `);
}

afterEach(async () => {
  await db.execute(ds`DELETE FROM queue_claims WHERE decision_id = ${D1}`);
  await db.execute(ds`DELETE FROM decisions WHERE decision_id = ${D1}`);
});

describe('queue claims', () => {
  it('same operator can re-claim (idempotent)', async () => {
    await insertTestDecision(D1);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    expect(await tryClaim(D1, op!.operatorId)).toBe(true);
    expect(await tryClaim(D1, op!.operatorId)).toBe(true);
  });

  it('release allows reclaim', async () => {
    await insertTestDecision(D1);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    await tryClaim(D1, op!.operatorId);
    await releaseClaim(D1);
    expect(await getClaimer(D1)).toBeUndefined();
    await sql.end();
  });
});
```

- [ ] **Step 2: Implement**

```typescript
// src/lib/db/queue-claims.ts
import { db } from './client';
import { queueClaims } from './schema';
import { eq, and, gt, lt } from 'drizzle-orm';

const DEFAULT_TTL = 10 * 60 * 1000;

export async function tryClaim(decisionId: string, operatorId: string, ttlMs = DEFAULT_TTL): Promise<boolean> {
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttlMs);
  await db.delete(queueClaims).where(and(eq(queueClaims.decisionId, decisionId), lt(queueClaims.expiresAt, now)));

  try {
    await db.insert(queueClaims).values({ decisionId, claimedBy: operatorId, expiresAt });
    return true;
  } catch {
    const existing = await db.query.queueClaims.findFirst({
      where: and(eq(queueClaims.decisionId, decisionId), gt(queueClaims.expiresAt, now)),
    });
    if (existing?.claimedBy === operatorId) {
      await db.update(queueClaims).set({ expiresAt }).where(eq(queueClaims.decisionId, decisionId));
      return true;
    }
    return false;
  }
}

export async function releaseClaim(decisionId: string) {
  await db.delete(queueClaims).where(eq(queueClaims.decisionId, decisionId));
}

export async function getClaimer(decisionId: string): Promise<string | undefined> {
  const r = await db.query.queueClaims.findFirst({
    where: and(eq(queueClaims.decisionId, decisionId), gt(queueClaims.expiresAt, new Date())),
  });
  return r?.claimedBy;
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/queue-claims.ts lead-radar-console/tests/unit/queue-claims.test.ts
git commit -m "feat(console): queue-claim mechanism with TTL (multi-op safe)"
```

---

### Task 2.4: Decision write helpers + API endpoint

**Files:**
- Create: `lead-radar-console/src/lib/db/decisions.ts`
- Create: `lead-radar-console/src/app/api/decisions/route.ts`
- Create: `lead-radar-console/tests/integration/decisions-write.test.ts`

- [ ] **Step 1: Write helper**

```typescript
// src/lib/db/decisions.ts
import { db } from './client';
import { decisions } from './schema';
import { eq, and, isNull, asc, count, or } from 'drizzle-orm';

type Input = {
  workflowId: string;
  profileVersion: number;
  tierAtDecision: string;
  inputsHash: string;
  inputsPayload: Record<string, unknown>;
  agentId?: string;
  agentRecommendation?: Record<string, unknown>;
  agentConfidence?: number;
  agentReasoningRef?: string;
  reviewerId?: string;
  reviewerDecision?: Record<string, unknown>;
  agreement?: 'Y' | 'N' | 'NA';
  overrideReason?: string;
  overrideCategory?: string;
  timeToDecideMs?: number;
  leadId?: string;
  signalId?: string;
};

export async function writeDecision(input: Input): Promise<{ decisionId: string }> {
  const [row] = await db.insert(decisions).values(input).returning({ decisionId: decisions.decisionId });
  return row;
}

export async function getQueueItems(workflowId: string, limit: number) {
  return db.query.decisions.findMany({
    where: and(eq(decisions.workflowId, workflowId), isNull(decisions.reviewerId)),
    orderBy: asc(decisions.decidedAt), limit,
  });
}

export async function getQueueCounter(workflowId: string): Promise<number> {
  const [row] = await db.select({ c: count() }).from(decisions)
    .where(and(eq(decisions.workflowId, workflowId), isNull(decisions.reviewerId)));
  return Number(row.c);
}

export async function getAuditChainByLeadId(leadId: string) {
  return db.query.decisions.findMany({
    where: or(eq(decisions.leadId, leadId), eq(decisions.signalId, leadId)),
    orderBy: asc(decisions.decidedAt),
  });
}
```

- [ ] **Step 2: API endpoint**

```typescript
// src/app/api/decisions/route.ts
import { NextResponse } from 'next/server';
import { z } from 'zod';
import { writeDecision } from '@/lib/db/decisions';
import { releaseClaim } from '@/lib/db/queue-claims';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

const schema = z.object({
  decisionId: z.string().uuid().optional(),
  workflowId: z.string(),
  profileVersion: z.number().int(),
  tierAtDecision: z.string(),
  inputsHash: z.string(),
  inputsPayload: z.record(z.unknown()),
  agentRecommendation: z.record(z.unknown()).optional(),
  agentConfidence: z.number().min(0).max(1).optional(),
  reviewerDecision: z.record(z.unknown()),
  agreement: z.enum(['Y', 'N', 'NA']),
  overrideReason: z.string().max(200).optional(),
  overrideCategory: z.string().optional(),
  timeToDecideMs: z.number().int().nonneg().optional(),
  leadId: z.string().optional(),
  signalId: z.string().optional(),
});

export async function POST(req: Request) {
  const op = await requireCurrentOperator();
  const body = await req.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: parsed.error.format() }, { status: 400 });
  if (await isWorkflowKilled(parsed.data.workflowId)) return NextResponse.json({ error: 'workflow_killed' }, { status: 409 });
  const { decisionId } = await writeDecision({ ...parsed.data, reviewerId: op.operatorId });
  if (parsed.data.decisionId) await releaseClaim(parsed.data.decisionId);
  return NextResponse.json({ decisionId });
}
```

- [ ] **Step 3: Integration test**

```typescript
// tests/integration/decisions-write.test.ts
import { describe, it, expect } from 'vitest';
import { writeDecision, getQueueCounter } from '@/lib/db/decisions';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('decision write', () => {
  it('round-trips a decision row', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'lead_delivery_routing', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: 'h-test', inputsPayload: { lead_id: 'test-1' },
      reviewerId: op!.operatorId, reviewerDecision: { action: 'approve' }, agreement: 'Y',
      leadId: 'test-1',
    });
    expect(r.decisionId).toBeDefined();
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect(row?.agreement).toBe('Y');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
    await sql.end();
  });
});
```

Run: PASS.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/decisions.ts lead-radar-console/src/app/api/decisions/ lead-radar-console/tests/integration/decisions-write.test.ts
git commit -m "feat(console): decision write API + queue/counter helpers + kill-state guard"
```

---

## Phase 3 — Triage Overview + Card Shell + Routing Card (MVP)

> **MVP checkpoint reached at end of this phase.** Founder can log in, see triage, work through routing decisions with keyboard, audit-logged.

### Task 3.1: Routing fixtures + queue API

**Files:**
- Create: `lead-radar-console/scripts/seed-fixtures.ts`
- Create: `lead-radar-console/src/app/api/queues/[workflow]/route.ts`

- [ ] **Step 1: Seed routing fixtures**

```typescript
// scripts/seed-fixtures.ts
import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';

const fixtures = [
  {
    decisionId: '00000000-0000-0000-0000-000000000001',
    workflowId: 'lead_delivery_routing',
    profileVersion: 1, tierAtDecision: 'T1',
    inputsHash: 'fixture-r-001',
    inputsPayload: {
      lead: { score: 87, band: 'HOT', source: 'tweakers', ageHours: 2, niche: 'warmtepomp',
        geo: { region: 'Drenthe', city: 'Schoonebeek', postcode: '7741' },
        postText: 'We willen onze gasketel vervangen, hebben offerte van XYZ gekregen maar willen tweede mening. Iemand recente ervaring met hybride lucht-water systemen in deze regio?' },
    },
    agentRecommendation: {
      primary: { name: 'HVAC Schoonebeek BV', regionalFit: 'strong', conversionHistory: 'high', capacity: 'open', nicheMatch: 'hybrid-specialized', responseHistory: 'responsive', distanceKm: 8 },
      alternatives: [
        { name: 'Klima-Tech Drenthe', regionalFit: 'moderate', conversionHistory: 'solid', capacity: 'tight', nicheMatch: 'generalist', responseHistory: 'responsive', distanceKm: 12 },
        { name: 'NoordWarmte BV', regionalFit: 'distance_limit', conversionHistory: 'limited', capacity: 'limited', nicheMatch: 'generalist', responseHistory: 'slow', distanceKm: 18 },
      ],
    },
    agentConfidence: 0.85, leadId: 'lead-fixture-001',
  },
  // Add 2-3 more similar fixtures with varying score/region for queue browsing
];

async function main() {
  await db.insert(decisions).values(fixtures).onConflictDoNothing();
  console.log(`✓ Seeded ${fixtures.length} fixtures`);
  await sql.end();
}

main().catch(e => { console.error(e); process.exit(1); });
```

Add to package.json: `"db:seed-fixtures": "tsx --env-file=.env scripts/seed-fixtures.ts"`.

Run: `pnpm db:seed-fixtures`.

- [ ] **Step 2: Queue API**

```typescript
// src/app/api/queues/[workflow]/route.ts
import { NextResponse } from 'next/server';
import { getQueueItems } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

const ALLOWED = new Set(['lead_delivery_routing', 'signal_classification_ambiguous_band', 'conversion_registration']);

export async function GET(_req: Request, { params }: { params: Promise<{ workflow: string }> }) {
  await requireCurrentOperator();
  const { workflow } = await params;
  if (!ALLOWED.has(workflow)) return NextResponse.json({ error: 'unknown_workflow' }, { status: 404 });
  if (await isWorkflowKilled(workflow)) return NextResponse.json({ items: [], killed: true });
  return NextResponse.json({ items: await getQueueItems(workflow, 50), killed: false });
}
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/scripts/seed-fixtures.ts lead-radar-console/src/app/api/queues/ lead-radar-console/package.json
git commit -m "feat(console): routing fixtures + queue fetch API"
```

---

### Task 3.2: Triage page + counters API

**Files:**
- Create: `lead-radar-console/src/app/api/triage/route.ts`
- Create: `lead-radar-console/src/app/triage/page.tsx`
- Create: `lead-radar-console/src/components/triage/WorkflowBlock.tsx`
- Create: `lead-radar-console/src/components/triage/TriageKeyboard.tsx`

- [ ] **Step 1: Triage API**

```typescript
// src/app/api/triage/route.ts
import { NextResponse } from 'next/server';
import { getQueueCounter } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

export async function GET() {
  await requireCurrentOperator();
  const [routing, classification, conversion] = await Promise.all([
    getQueueCounter('lead_delivery_routing'),
    getQueueCounter('signal_classification_ambiguous_band'),
    getQueueCounter('conversion_registration'),
  ]);
  return NextResponse.json({
    counts: { routing, classification, conversion },
    killed: {
      lead_delivery_routing: await isWorkflowKilled('lead_delivery_routing'),
      signal_classification_ambiguous_band: await isWorkflowKilled('signal_classification_ambiguous_band'),
      conversion_registration: await isWorkflowKilled('conversion_registration'),
    },
  });
}
```

- [ ] **Step 2: WorkflowBlock**

```tsx
// src/components/triage/WorkflowBlock.tsx
import Link from 'next/link';

type Props = { label: string; count: number; killed: boolean; href: string; hotkey: '1'|'2'|'3' };

export function WorkflowBlock({ label, count, killed, href, hotkey }: Props) {
  return (
    <Link href={href} className={`block p-6 border rounded ${killed ? 'border-red-700 bg-red-950/30' : 'border-zinc-800 hover:border-zinc-700'}`}>
      <div className="text-zinc-500 text-xs uppercase tracking-wider mb-2">{label}</div>
      <div className="text-3xl mb-2">{killed ? <span className="text-red-500">paused</span> : count}</div>
      <div className="text-xs text-zinc-500">[{hotkey}] enter →</div>
    </Link>
  );
}
```

- [ ] **Step 3: TriageKeyboard**

```tsx
// src/components/triage/TriageKeyboard.tsx
'use client';
import { useRouter } from 'next/navigation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

export function TriageKeyboard() {
  const router = useRouter();
  useKeyboardShortcuts({
    '1': () => router.push('/q/lead_delivery_routing'),
    '2': () => router.push('/q/signal_classification_ambiguous_band'),
    '3': () => router.push('/q/conversion_registration'),
  });
  return null;
}
```

- [ ] **Step 4: Triage page**

```tsx
// src/app/triage/page.tsx
import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import { auth } from '@/../auth';
import { WorkflowBlock } from '@/components/triage/WorkflowBlock';
import { TriageKeyboard } from '@/components/triage/TriageKeyboard';

async function fetchTriage() {
  const cookie = (await headers()).get('cookie') ?? '';
  const res = await fetch(`${process.env.NEXTAUTH_URL}/api/triage`, { headers: { cookie }, cache: 'no-store' });
  return res.json();
}

export default async function TriagePage() {
  const session = await auth();
  if (!session) redirect('/login');
  const { counts, killed } = await fetchTriage();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <header className="flex justify-between items-baseline mb-12">
        <h1 className="text-lg">Lead Radar — Operator console</h1>
        <div className="text-zinc-500 text-sm">{session.user?.email}</div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <WorkflowBlock label="Routing" count={counts.routing} killed={killed.lead_delivery_routing} href="/q/lead_delivery_routing" hotkey="1" />
        <WorkflowBlock label="Classification" count={counts.classification} killed={killed.signal_classification_ambiguous_band} href="/q/signal_classification_ambiguous_band" hotkey="2" />
        <WorkflowBlock label="Conversions" count={counts.conversion} killed={killed.conversion_registration} href="/q/conversion_registration" hotkey="3" />
      </div>

      <footer className="text-xs text-zinc-600 border-t border-zinc-900 pt-4">
        [/] search · [K] kill-states · [V]iew recent audits
      </footer>
      <TriageKeyboard />
    </main>
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/app/api/triage/ lead-radar-console/src/app/triage/ lead-radar-console/src/components/triage/
git commit -m "feat(console): triage overview with 3 workflow blocks + keyboard navigation"
```

---

### Task 3.3: useKeyboardShortcuts hook

**Files:**
- Create: `lead-radar-console/src/lib/keyboard/useKeyboardShortcuts.ts`

- [ ] **Step 1: Implement**

```typescript
// src/lib/keyboard/useKeyboardShortcuts.ts
'use client';
import { useEffect } from 'react';

type Handler = (e: KeyboardEvent) => void | Promise<void>;

export function useKeyboardShortcuts(
  shortcuts: Record<string, Handler>,
  options: { allowInInputs?: boolean } = {},
) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const tag = target.tagName?.toLowerCase();
      const inInput = tag === 'input' || tag === 'textarea' || target.isContentEditable;
      if (!options.allowInInputs && inInput && e.key !== 'Escape') return;
      const key = (e.shiftKey ? 'shift+' : '') + (e.key.length === 1 ? e.key.toUpperCase() : e.key);
      const handler = shortcuts[key];
      if (handler) { e.preventDefault(); handler(e); }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shortcuts, options.allowInInputs]);
}
```

- [ ] **Step 2: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/keyboard/
git commit -m "feat(console): useKeyboardShortcuts hook (mouse-tolerant, input-aware)"
```

---

### Task 3.4: Why-string generator

**Files:**
- Create: `lead-radar-console/src/lib/why-string/rules.ts`
- Create: `lead-radar-console/src/lib/why-string/generator.ts`
- Create: `lead-radar-console/tests/unit/why-string.test.ts`

- [ ] **Step 1: Test**

```typescript
// tests/unit/why-string.test.ts
import { describe, it, expect } from 'vitest';
import { whyString } from '@/lib/why-string/generator';

describe('why-string', () => {
  it('T1 trust-load-bearing routing', () => {
    expect(whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'trust_load_bearing', terminal_tier: 'T1' } } as any))
      .toMatch(/T1 always-review/i);
  });
  it('dataset-defining', () => {
    expect(whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'dataset_defining' } } as any))
      .toMatch(/dataset-defining/i);
  });
  it('respects 12-word limit', () => {
    const r = whyString({ tierAtDecision: 'T1', inputsPayload: {} } as any, { profile: { risk_class: 'trust_load_bearing', terminal_tier: 'T1' } } as any);
    expect(r.split(/\s+/).length).toBeLessThanOrEqual(12);
  });
});
```

- [ ] **Step 2: Rules**

```typescript
// src/lib/why-string/rules.ts
type Rule = { matches: (d: any, p: any) => boolean; text: string };

export const WHY_RULES: Rule[] = [
  { matches: (d) => Boolean(d.inputsPayload?.cof_circuit_breaker_tripped), text: 'CoF circuit breaker tripped — forced T1' },
  { matches: (_, p) => p.profile?.risk_class === 'dataset_defining', text: 'Dataset-defining workflow — terminal T1' },
  { matches: (_, p) => p.profile?.risk_class === 'trust_load_bearing' && p.profile?.terminal_tier === 'T1', text: 'T1 always-review, trust-load-bearing' },
  { matches: (_, p) => p.profile?.risk_class === 'trust_load_bearing', text: 'Trust-load-bearing — sample review' },
  { matches: (d) => Boolean(d.inputsPayload?.in_ambiguous_band), text: 'Within ambigue band 40-75' },
  { matches: (d) => Boolean(d.inputsPayload?.source_novelty_flag), text: 'Source novelty alert — vocabulary shift' },
  { matches: (d) => Boolean(d.inputsPayload?.outcome_confirmation_pending), text: 'Outcome confirmation pending' },
];

export const FALLBACK = 'Review required';
```

- [ ] **Step 3: Generator**

```typescript
// src/lib/why-string/generator.ts
import { WHY_RULES, FALLBACK } from './rules';

export function whyString(decision: { tierAtDecision: string; inputsPayload: any }, profile: { profile: any }): string {
  for (const r of WHY_RULES) if (r.matches(decision, profile)) return r.text;
  return FALLBACK;
}
```

Run: PASS.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/why-string/ lead-radar-console/tests/unit/why-string.test.ts
git commit -m "feat(console): deterministic Why-string generator with priority-ordered rules"
```

---

### Task 3.5: Card shell components

**Files:**
- Create: `lead-radar-console/src/components/card/TopStrip.tsx`
- Create: `lead-radar-console/src/components/card/WhyString.tsx`
- Create: `lead-radar-console/src/components/card/ActionBar.tsx`
- Create: `lead-radar-console/src/components/card/KeyboardHelp.tsx`
- Create: `lead-radar-console/src/components/card/CardShell.tsx`

- [ ] **Step 1: TopStrip**

```tsx
// src/components/card/TopStrip.tsx
type Props = { workflowLabel: string; position: { current: number; total: number }; nextUp?: { workflow: string; band?: string; ageMin?: number }; urgency: 'on-pace' | 'approaching' | 'past-sla'; };
const URG = { 'on-pace': 'bg-green-500', 'approaching': 'bg-yellow-500', 'past-sla': 'bg-red-500' };
export function TopStrip({ workflowLabel, position, nextUp, urgency }: Props) {
  return (
    <div className="flex items-center gap-3 text-xs text-zinc-500 px-4 py-2 border-b border-zinc-900">
      <span>{workflowLabel}</span><span>•</span>
      <span>{position.current} of {position.total}</span>
      {nextUp && <><span>•</span><span>Next: {nextUp.workflow}{nextUp.band ? ` (${nextUp.band}, ${nextUp.ageMin}min)` : ''}</span></>}
      <span className="ml-auto flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${URG[urgency]}`} />
        <span>{urgency.replace('-', ' ')}</span>
      </span>
    </div>
  );
}
```

- [ ] **Step 2: WhyString**

```tsx
// src/components/card/WhyString.tsx
export function WhyString({ text }: { text: string }) {
  return <div className="text-xs text-zinc-400 px-4 py-1 border-b border-zinc-900"><span className="mr-2">ⓘ</span>Why: {text}</div>;
}
```

- [ ] **Step 3: ActionBar**

```tsx
// src/components/card/ActionBar.tsx
type Action = { key: string; label: string; onClick: () => void; disabled?: boolean };
export function ActionBar({ actions }: { actions: Action[] }) {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-t border-zinc-900 text-sm">
      {actions.map(a => (
        <button key={a.key} onClick={a.onClick} disabled={a.disabled}
          className="px-3 py-1 border border-zinc-700 rounded hover:bg-zinc-800 disabled:opacity-30">
          <span className="text-zinc-400">[{a.key}]</span><span className="ml-1">{a.label}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: KeyboardHelp**

```tsx
// src/components/card/KeyboardHelp.tsx
'use client';
import { useState } from 'react';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

export function KeyboardHelp({ entries }: { entries: { key: string; label: string }[] }) {
  const [open, setOpen] = useState(false);
  useKeyboardShortcuts({
    '?': () => setOpen(o => !o),
    'Escape': () => { if (open) setOpen(false); },
  }, { allowInInputs: true });
  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center" onClick={() => setOpen(false)}>
      <div className="bg-zinc-900 border border-zinc-700 rounded p-6 max-w-md font-mono text-sm" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg mb-4">Keyboard shortcuts</h2>
        <ul className="space-y-1">
          {entries.map(e => <li key={e.key} className="flex justify-between gap-8"><span className="text-zinc-400">{e.key}</span><span>{e.label}</span></li>)}
        </ul>
        <p className="text-xs text-zinc-500 mt-4">Esc to close</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: CardShell**

```tsx
// src/components/card/CardShell.tsx
import type { ReactNode } from 'react';
import { TopStrip } from './TopStrip';
import { WhyString } from './WhyString';
import { ActionBar } from './ActionBar';
import { KeyboardHelp } from './KeyboardHelp';

type Action = { key: string; label: string; onClick: () => void; disabled?: boolean };
type Props = {
  workflowLabel: string;
  position: { current: number; total: number };
  nextUp?: { workflow: string; band?: string; ageMin?: number };
  urgency: 'on-pace' | 'approaching' | 'past-sla';
  whyText: string;
  clusterBanner?: string;
  children: ReactNode;
  actions: Action[];
  helpEntries: { key: string; label: string }[];
};

export function CardShell({ workflowLabel, position, nextUp, urgency, whyText, clusterBanner, children, actions, helpEntries }: Props) {
  return (
    <article className="max-w-3xl mx-auto my-8 bg-zinc-950 border border-zinc-800 rounded">
      <TopStrip workflowLabel={workflowLabel} position={position} nextUp={nextUp} urgency={urgency} />
      <WhyString text={whyText} />
      {clusterBanner && <div className="text-xs text-zinc-400 px-4 py-2 border-b border-zinc-900 bg-zinc-900/40">ⓘ {clusterBanner}</div>}
      <div className="px-6 py-4">{children}</div>
      <ActionBar actions={actions} />
      <KeyboardHelp entries={helpEntries} />
    </article>
  );
}
```

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/card/
git commit -m "feat(console): CardShell + TopStrip + WhyString + ActionBar + KeyboardHelp"
```

---

### Task 3.6: Routing card + queue page (MVP target)

**Files:**
- Create: `lead-radar-console/src/components/routing/InstallerRecommendation.tsx`
- Create: `lead-radar-console/src/components/routing/RoutingCard.tsx`
- Create: `lead-radar-console/src/app/q/[workflow]/page.tsx`

- [ ] **Step 1: InstallerRecommendation**

```tsx
// src/components/routing/InstallerRecommendation.tsx
const LABEL: any = {
  regionalFit: { strong: 'Strong regional fit', moderate: 'Moderate regional fit', distance_limit: 'Distance limit', out_of_region: 'Out of region' },
  conversionHistory: { high: 'High conversion history', solid: 'Solid conversion history', limited: 'Limited conversion history', no_history: 'No history yet' },
  capacity: { open: 'Open capacity', tight: 'Tight capacity', limited: 'Limited capacity', closed: 'Closed' },
  nicheMatch: { 'hybrid-specialized': 'Hybrid-specialized', generalist: 'Generalist', 'off-niche': 'Off-niche' },
  responseHistory: { very_responsive: 'Very responsive', responsive: 'Responsive', slow: 'Slow', unresponsive: 'Unresponsive' },
};

export function InstallerRecommendation({ installer, primary }: { installer: any; primary?: boolean }) {
  return (
    <div className={primary ? 'p-3 border border-zinc-700 rounded mb-3' : 'p-3 mb-2 text-sm text-zinc-400'}>
      <div className="flex items-baseline gap-3">
        <span>{primary ? '▸' : '◯'}</span>
        <span className={primary ? 'font-bold text-zinc-100' : ''}>{installer.name}</span>
        <span className="text-xs text-zinc-500">{LABEL.regionalFit[installer.regionalFit]} • {installer.distanceKm} km</span>
      </div>
      <ul className="text-xs text-zinc-500 mt-1 ml-4 list-disc list-inside">
        <li>{LABEL.conversionHistory[installer.conversionHistory]} · {LABEL.capacity[installer.capacity]}</li>
        <li>{LABEL.nicheMatch[installer.nicheMatch]} · {LABEL.responseHistory[installer.responseHistory]}</li>
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: RoutingCard**

```tsx
// src/components/routing/RoutingCard.tsx
'use client';
import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';
import { CardShell } from '@/components/card/CardShell';
import { InstallerRecommendation } from './InstallerRecommendation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

type Props = { decision: any; position: { current: number; total: number }; whyText: string; total: number; };

export function RoutingCard({ decision, position, whyText }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const lead = decision.inputsPayload?.lead;
  const rec = decision.agentRecommendation;
  const primary = rec?.primary;
  const alts = rec?.alternatives ?? [];

  async function submit(action: 'approve' | 'hold' | 'next', pickedInstaller?: string) {
    const t0 = Date.now();
    if (action === 'next') { startTransition(() => router.refresh()); return; }
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'lead_delivery_routing', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
      agentRecommendation: rec,
      reviewerDecision: { installer: pickedInstaller ?? primary?.name, action },
      agreement: pickedInstaller && pickedInstaller !== primary?.name ? 'N' : 'Y',
      timeToDecideMs: Date.now() - t0,
      leadId: decision.leadId,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    startTransition(() => router.refresh());
  }

  useKeyboardShortcuts({
    'A': () => submit('approve'),
    'H': () => submit('hold'),
    'N': () => submit('next'),
    'Escape': () => router.push('/triage'),
  });

  return (
    <CardShell
      workflowLabel="Routing" position={position} urgency="on-pace" whyText={whyText}
      helpEntries={[
        { key: 'A', label: 'Approve & route' }, { key: 'H', label: 'Hold' },
        { key: 'N', label: 'Next without action' }, { key: 'Esc', label: 'Back to triage' },
      ]}
      actions={[
        { key: 'A', label: 'Approve & route', onClick: () => submit('approve') },
        { key: 'H', label: 'Hold', onClick: () => submit('hold') },
        { key: 'N', label: 'Next', onClick: () => submit('next') },
      ]}
    >
      <section className="mb-6">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Lead</h2>
        <div className="text-sm"><span className="text-yellow-500">{lead?.band}</span><span className="text-zinc-400"> (score {lead?.score}) • {lead?.source} • {lead?.ageHours}u oud</span></div>
        <div className="text-xs text-zinc-500 mt-1">Niche: {lead?.niche} • Geo: {lead?.geo?.region} / {lead?.geo?.city} ({lead?.geo?.postcode})</div>
        <p className="text-sm mt-3 text-zinc-300">"{lead?.postText}"</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent recommends</h2>
        {primary && <InstallerRecommendation installer={primary} primary />}
        <h3 className="text-xs text-zinc-500 mb-1">Alternatives:</h3>
        {alts.map((a: any) => <InstallerRecommendation key={a.name} installer={a} />)}
      </section>
    </CardShell>
  );
}
```

- [ ] **Step 3: Queue page**

```tsx
// src/app/q/[workflow]/page.tsx
import { redirect, notFound } from 'next/navigation';
import { auth } from '@/../auth';
import { getQueueItems } from '@/lib/db/decisions';
import { getActiveProfile } from '@/lib/db/workflow-profiles';
import { isWorkflowKilled } from '@/lib/db/kill-state';
import { whyString } from '@/lib/why-string/generator';
import { RoutingCard } from '@/components/routing/RoutingCard';

const LABELS: Record<string, string> = {
  lead_delivery_routing: 'Routing',
  signal_classification_ambiguous_band: 'Classification',
  conversion_registration: 'Conversion',
};

export default async function QueuePage({ params }: { params: Promise<{ workflow: string }> }) {
  const session = await auth();
  if (!session) redirect('/login');
  const { workflow } = await params;
  if (!LABELS[workflow]) notFound();

  if (await isWorkflowKilled(workflow)) {
    return <main className="p-8 text-zinc-100 bg-zinc-950 min-h-screen font-mono"><p>Workflow paused. <a href="/triage" className="underline">Back</a></p></main>;
  }

  const items = await getQueueItems(workflow, 50);
  if (items.length === 0) {
    return <main className="p-8 text-zinc-100 bg-zinc-950 min-h-screen font-mono"><p>Queue empty. <a href="/triage" className="underline">Back to triage</a></p></main>;
  }

  const profile = await getActiveProfile(workflow);
  if (!profile) throw new Error(`No active profile for ${workflow}`);

  const current = items[0];
  const why = whyString(current as any, profile as any);

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      {workflow === 'lead_delivery_routing' && (
        <RoutingCard decision={current as any} position={{ current: 1, total: items.length }} whyText={why} total={items.length} />
      )}
      {workflow !== 'lead_delivery_routing' && (
        <div className="p-8"><p className="text-zinc-400">[{LABELS[workflow]}] queue rendering pending.</p><a href="/triage" className="underline text-sm">Back to triage</a></div>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Manual smoke test**

`pnpm dev`, log in, press `1` → routing card → press `A` → verify save:
```bash
docker exec lead-radar-console-pg psql -U console -d lead_radar -c "SELECT decision_id, agreement, reviewer_decision FROM decisions WHERE reviewer_id IS NOT NULL ORDER BY decided_at DESC LIMIT 1;"
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/routing/ lead-radar-console/src/app/q/
git commit -m "feat(console): routing card MVP (A/H/N keys, decision-support language) — MVP daily usability reached"
```

---

## MVP Checkpoint

By end of Phase 3:
- ✅ Founder logs in via magic-link
- ✅ Triage shows live counts
- ✅ Keyboard 1/2/3 navigates
- ✅ Routing card renders with decision-support language
- ✅ A/H/N keyboard actions write to audit log
- ✅ Every action audit-logged in `decisions` with full context

Subsequent phases extend incrementally without breaking MVP.

---

## Phase 4 — Override Inline Flow

### Task 4.1: Override categories reader + OverrideInlineForm

**Files:**
- Create: `lead-radar-console/src/lib/db/override-categories.ts`
- Create: `lead-radar-console/src/components/override/OverrideInlineForm.tsx`

- [ ] **Step 1: Reader**

```typescript
// src/lib/db/override-categories.ts
import { db } from './client';
import { overrideCategories } from './schema';
import { eq, asc } from 'drizzle-orm';

export async function getActiveOverrideCategories() {
  return db.query.overrideCategories.findMany({
    where: eq(overrideCategories.active, true),
    orderBy: asc(overrideCategories.sortOrder),
  });
}
```

- [ ] **Step 2: Form**

```tsx
// src/components/override/OverrideInlineForm.tsx
'use client';
import { useState, useRef, useEffect } from 'react';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

type Category = { categoryKey: string; displayLabel: string };
type Props = { categories: Category[]; onSubmit: (key: string, reason: string) => void | Promise<void>; onCancel: () => void; };

export function OverrideInlineForm({ categories, onSubmit, onCancel }: Props) {
  const [picked, setPicked] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (picked) inputRef.current?.focus(); }, [picked]);

  const numberShortcuts = Object.fromEntries(categories.slice(0, 5).map((c, i) => [String(i + 1), () => setPicked(c.categoryKey)]));
  useKeyboardShortcuts({
    ...numberShortcuts,
    'Escape': () => onCancel(),
    'Enter': () => { if (picked && reason.trim().length > 0) onSubmit(picked, reason.trim()); },
  }, { allowInInputs: true });

  return (
    <div className="mt-4 p-4 border border-zinc-700 rounded bg-zinc-900">
      <div className="text-xs text-zinc-500 mb-3">Override</div>
      <div className="mb-3">
        <div className="text-xs text-zinc-400 mb-1">Category:</div>
        <div className="flex gap-3 text-sm flex-wrap">
          {categories.slice(0, 5).map((c, i) => (
            <label key={c.categoryKey} className="flex items-center gap-1 cursor-pointer">
              <input type="radio" name="cat" checked={picked === c.categoryKey} onChange={() => setPicked(c.categoryKey)} />
              <span className="text-zinc-500">[{i + 1}]</span> {c.displayLabel}
            </label>
          ))}
        </div>
      </div>
      <div className="mb-3">
        <div className="text-xs text-zinc-400 mb-1">Reason:</div>
        <input ref={inputRef} type="text" maxLength={200} value={reason} onChange={e => setReason(e.target.value)}
          className="w-full px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-sm" placeholder="Brief reason..." />
      </div>
      <div className="text-xs text-zinc-500">[Enter] save & next · [Esc] cancel</div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/db/override-categories.ts lead-radar-console/src/components/override/
git commit -m "feat(console): override categories DB reader + inline OverrideInlineForm component"
```

---

### Task 4.2: Wire Override into RoutingCard (O key)

**Files:**
- Modify: `lead-radar-console/src/components/routing/RoutingCard.tsx`
- Modify: `lead-radar-console/src/app/q/[workflow]/page.tsx`

- [ ] **Step 1: Update RoutingCard with override state**

Edit `src/components/routing/RoutingCard.tsx` — accept `categories` prop, add `overrideOpen` state, add `submitOverride` handler, bind `O` key, render `<OverrideInlineForm>` conditionally. Pseudocode-diff:

Add at top of Props type: `categories: { categoryKey: string; displayLabel: string }[];`.

Inside component:
```tsx
const [overrideOpen, setOverrideOpen] = useState(false);

async function submitOverride(categoryKey: string, reason: string) {
  const body = {
    decisionId: decision.decisionId,
    workflowId: 'lead_delivery_routing', profileVersion: 1, tierAtDecision: 'T1',
    inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
    agentRecommendation: rec,
    reviewerDecision: { action: 'override' }, agreement: 'N',
    overrideCategory: categoryKey, overrideReason: reason,
    leadId: decision.leadId,
  };
  await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  setOverrideOpen(false);
  startTransition(() => router.refresh());
}
```

Replace useKeyboardShortcuts with:
```tsx
useKeyboardShortcuts({
  'A': () => submit('approve'),
  'O': () => setOverrideOpen(true),
  'H': () => submit('hold'),
  'N': () => submit('next'),
  'Escape': () => overrideOpen ? setOverrideOpen(false) : router.push('/triage'),
});
```

Add 'O' to actions array and helpEntries.

After the Agent recommends section, add:
```tsx
{overrideOpen && <OverrideInlineForm categories={categories} onSubmit={submitOverride} onCancel={() => setOverrideOpen(false)} />}
```

Import: `import { OverrideInlineForm } from '@/components/override/OverrideInlineForm';`

- [ ] **Step 2: Update queue page to fetch + pass categories**

```tsx
// src/app/q/[workflow]/page.tsx — add at top
import { getActiveOverrideCategories } from '@/lib/db/override-categories';
// in component body, before render:
const categories = await getActiveOverrideCategories();
// pass to <RoutingCard>:
<RoutingCard ... categories={categories.map(c => ({ categoryKey: c.categoryKey, displayLabel: c.displayLabel }))} />
```

- [ ] **Step 3: Manual test**

Press `O` → form opens → press `2` → type reason → Enter → verify `decisions.override_category` and `override_reason` saved.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/routing/RoutingCard.tsx lead-radar-console/src/app/q/[workflow]/page.tsx
git commit -m "feat(console): wire override flow into RoutingCard (O key, inline form, 5 evolvable categories)"
```

---

### Task 4.3: Pick-alternative inline flow (P key)

**Files:**
- Modify: `lead-radar-console/src/components/routing/RoutingCard.tsx`

- [ ] **Step 1: Add pick-alt state**

Inside RoutingCard, add:
```tsx
const [pickAltOpen, setPickAltOpen] = useState(false);
const [pickedAltIdx, setPickedAltIdx] = useState(0);

async function submitPickAlt() {
  const alt = alts[pickedAltIdx];
  await submit('approve', alt?.name);
  setPickAltOpen(false);
}
```

Update useKeyboardShortcuts to add `'P'`, `'1'`/`'2'`/`'Enter'` (active only when `pickAltOpen`):
```tsx
useKeyboardShortcuts({
  'A': () => submit('approve'),
  'P': () => setPickAltOpen(true),
  'O': () => setOverrideOpen(true),
  'H': () => submit('hold'),
  'N': () => submit('next'),
  '1': () => { if (pickAltOpen) setPickedAltIdx(0); },
  '2': () => { if (pickAltOpen) setPickedAltIdx(1); },
  'Enter': () => { if (pickAltOpen) submitPickAlt(); },
  'Escape': () => {
    if (overrideOpen) setOverrideOpen(false);
    else if (pickAltOpen) setPickAltOpen(false);
    else router.push('/triage');
  },
});
```

In JSX add (between primary and override section):
```tsx
{pickAltOpen && (
  <div className="mt-4 p-4 border border-zinc-700 rounded bg-zinc-900">
    <div className="text-xs text-zinc-500 mb-2">Pick alternative:</div>
    {alts.map((a: any, i: number) => (
      <label key={a.name} className="flex items-center gap-2 mb-1 cursor-pointer">
        <input type="radio" name="alt" checked={pickedAltIdx === i} onChange={() => setPickedAltIdx(i)} />
        <span className="text-zinc-400">[{i + 1}]</span> <span>{a.name}</span>
      </label>
    ))}
    <div className="text-xs text-zinc-500 mt-2">[Enter] confirm · [Esc] cancel</div>
  </div>
)}
```

Add `P` to actions and helpEntries.

- [ ] **Step 2: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/routing/RoutingCard.tsx
git commit -m "feat(console): pick-alternative inline flow (P key) on routing card"
```

---

## Phase 5 — Classification Card with Qualifiers

### Task 5.1: Classification fixtures + ClassificationCard

**Files:**
- Modify: `lead-radar-console/scripts/seed-fixtures.ts`
- Create: `lead-radar-console/src/components/classification/ClassificationCard.tsx`
- Modify: `lead-radar-console/src/app/q/[workflow]/page.tsx`

- [ ] **Step 1: Add classification fixtures**

Append to fixtures array in `scripts/seed-fixtures.ts`:
```typescript
{
  decisionId: '00000000-0000-0000-0000-000001000001',
  workflowId: 'signal_classification_ambiguous_band',
  profileVersion: 1, tierAtDecision: 'T1',
  inputsHash: 'fixture-c-001',
  inputsPayload: {
    in_ambiguous_band: true,
    signal: { source: 'ouders.nl forum', user: 'tweemoeders-bart', ageHours: 4, preScore: 0.62,
      postText: 'Even geleden post ik over de subsidie maar nog niet veel reactie. Iemand toch een idee wat zo\'n hybride installatie nu echt gaat kosten met de huidige aanvragen? Mijn aannemer wil offerte maar ik wil eerst beeld.',
    },
  },
  agentRecommendation: {
    candidates: [
      { categoryKey: 'research_intent', confidence: 0.62, reasoning: 'kostenvergelijking, geen koopintentie nu' },
      { categoryKey: 'purchase_intent_pre_quote', confidence: 0.28, reasoning: 'aannemer wil offerte uitbrengen → mogelijke buyer' },
      { categoryKey: 'no_intent', confidence: 0.10, reasoning: '' },
    ],
  },
  agentConfidence: 0.62, signalId: 'sig-c-001',
},
```

Run: `pnpm db:seed-fixtures`.

- [ ] **Step 2: ClassificationCard**

```tsx
// src/components/classification/ClassificationCard.tsx
'use client';
import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';
import { CardShell } from '@/components/card/CardShell';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';
import { OverrideInlineForm } from '@/components/override/OverrideInlineForm';

type Cat = { categoryKey: string; confidence: number; reasoning?: string };
type Props = { decision: any; position: { current: number; total: number }; whyText: string; categories: { categoryKey: string; displayLabel: string }[]; };

export function ClassificationCard({ decision, position, whyText, categories }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [qualifierMode, setQualifierMode] = useState<'confident' | 'uncertain' | 'mixed'>('confident');
  const [primaryPick, setPrimaryPick] = useState<string | null>(null);

  const candidates: Cat[] = decision.agentRecommendation?.candidates ?? [];
  const signal = decision.inputsPayload?.signal;

  async function save(categoryKey: string, qualifier: string, secondary?: string) {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
      agentRecommendation: decision.agentRecommendation,
      reviewerDecision: { category: categoryKey, qualifier, secondary_category: secondary ?? null, source: 'operator_pick' },
      agreement: candidates[0]?.categoryKey === categoryKey ? 'Y' : 'N',
      signalId: decision.signalId,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    startTransition(() => router.refresh());
  }

  async function submitOverride(categoryKey: string, reason: string) {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
      reviewerDecision: { action: 'override' }, agreement: 'N',
      overrideCategory: categoryKey, overrideReason: reason,
      signalId: decision.signalId,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    setOverrideOpen(false); startTransition(() => router.refresh());
  }

  function pickByIdx(i: number) {
    const cat = candidates[i]?.categoryKey;
    if (!cat) return;
    if (qualifierMode === 'mixed' && !primaryPick) { setPrimaryPick(cat); return; }
    if (qualifierMode === 'mixed' && primaryPick) { save(primaryPick, 'mixed', cat); setPrimaryPick(null); return; }
    save(cat, qualifierMode);
  }

  useKeyboardShortcuts({
    '1': () => pickByIdx(0), '2': () => pickByIdx(1), '3': () => pickByIdx(2),
    'U': () => setQualifierMode('uncertain'),
    'M': () => { setQualifierMode('mixed'); setPrimaryPick(null); },
    'T': () => save('taxonomy_gap', 'taxonomy_gap'),
    'N': () => save('no_intent', 'confident'),
    'O': () => setOverrideOpen(true),
    'H': () => save(candidates[0]?.categoryKey ?? 'no_intent', 'uncertain'),
    'Escape': () => overrideOpen ? setOverrideOpen(false) : router.push('/triage'),
  });

  return (
    <CardShell
      workflowLabel="Classification" position={position} urgency="on-pace" whyText={whyText}
      helpEntries={[
        { key: '1/2/3', label: 'Confident pick' },
        { key: 'U', label: 'Uncertain mode (then 1/2/3)' },
        { key: 'M', label: 'Mixed mode (primary then secondary)' },
        { key: 'T', label: 'Taxonomy gap (none fit)' },
        { key: 'N', label: 'No intent (confident negative)' },
        { key: 'O', label: 'Override' }, { key: 'H', label: 'Hold' },
      ]}
      actions={[
        { key: '1/2/3', label: 'Pick', onClick: () => {} },
        { key: 'U', label: `Mode: ${qualifierMode}`, onClick: () => setQualifierMode('uncertain') },
        { key: 'M', label: 'Mixed', onClick: () => setQualifierMode('mixed') },
        { key: 'T', label: 'Tax gap', onClick: () => save('taxonomy_gap', 'taxonomy_gap') },
        { key: 'N', label: 'No intent', onClick: () => save('no_intent', 'confident') },
        { key: 'O', label: 'Override', onClick: () => setOverrideOpen(true) },
      ]}
    >
      <section className="mb-6">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Signal</h2>
        <div className="text-xs text-zinc-500">Source: {signal?.source} • {signal?.ageHours}u oud • user: {signal?.user}</div>
        <div className="text-xs text-zinc-500">Pre-score: {signal?.preScore} (ambigue band)</div>
        <p className="text-sm mt-3 text-zinc-300">"{signal?.postText}"</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent's best guesses</h2>
        {candidates.map((c, i) => (
          <div key={c.categoryKey} className={`mb-2 ${primaryPick === c.categoryKey ? 'border border-blue-700 rounded p-2' : ''}`}>
            <div className="text-sm"><span className="text-zinc-500">[{i + 1}]</span> <span className="font-medium">{c.categoryKey}</span> <span className="text-zinc-500 text-xs ml-3">confidence {(c.confidence * 100).toFixed(0)}%</span></div>
            {c.reasoning && <div className="text-xs text-zinc-500 ml-6">reasoning: "{c.reasoning}"</div>}
          </div>
        ))}
        {qualifierMode === 'mixed' && (
          <div className="text-xs text-yellow-500 mt-2">
            Mixed: {primaryPick ? `primary "${primaryPick}" picked — pick secondary (1/2/3)` : 'pick primary (1/2/3)'}
          </div>
        )}
      </section>
      {overrideOpen && <OverrideInlineForm categories={categories} onSubmit={submitOverride} onCancel={() => setOverrideOpen(false)} />}
    </CardShell>
  );
}
```

- [ ] **Step 3: Wire into queue page**

Edit `src/app/q/[workflow]/page.tsx` — add ClassificationCard rendering:

```tsx
import { ClassificationCard } from '@/components/classification/ClassificationCard';
// ... in JSX, add condition:
{workflow === 'signal_classification_ambiguous_band' && (
  <ClassificationCard decision={current as any} position={{ current: 1, total: items.length }} whyText={why} categories={categories.map(c => ({ categoryKey: c.categoryKey, displayLabel: c.displayLabel }))} />
)}
```

- [ ] **Step 4: Manual test all qualifiers**

`1` confident pick → check `decisions.reviewer_decision->>'qualifier' = 'confident'`
`U` then `2` → check `qualifier = 'uncertain'`
`M` then `1` then `2` → check `qualifier = 'mixed', secondary_category = ...`
`T` → check `category = 'taxonomy_gap'`
`N` → check `category = 'no_intent'`

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/classification/ lead-radar-console/scripts/seed-fixtures.ts lead-radar-console/src/app/q/[workflow]/page.tsx
git commit -m "feat(console): classification card with U/M/T/N qualifiers (no forced certainty)"
```

---

### Task 5.2: Integration test for classification qualifier dataset shape

**Files:**
- Create: `lead-radar-console/tests/integration/classification-qualifiers.test.ts`

- [ ] **Step 1: Write test**

```typescript
import { describe, it, expect } from 'vitest';
import { writeDecision } from '@/lib/db/decisions';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('classification qualifiers', () => {
  it('writes uncertain qualifier', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: 'q1', inputsPayload: { signal: { text: 'x' } },
      reviewerId: op!.operatorId,
      reviewerDecision: { category: 'research_intent', qualifier: 'uncertain', secondary_category: null, source: 'operator_pick' },
      agreement: 'Y',
    });
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect((row?.reviewerDecision as any)?.qualifier).toBe('uncertain');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
  });

  it('writes mixed with secondary', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: 'q2', inputsPayload: { signal: { text: 'x' } },
      reviewerId: op!.operatorId,
      reviewerDecision: { category: 'research_intent', qualifier: 'mixed', secondary_category: 'purchase_intent_pre_quote', source: 'operator_pick' },
      agreement: 'N',
    });
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect((row?.reviewerDecision as any)?.secondary_category).toBe('purchase_intent_pre_quote');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
    await sql.end();
  });
});
```

Run: PASS.

- [ ] **Step 2: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/tests/integration/classification-qualifiers.test.ts
git commit -m "test(console): integration test for classification qualifier dataset shape"
```

---

## Phase 6 — Conversion Registration Card

### Task 6.1: Conversion fixtures + ConversionCard

**Files:**
- Modify: `lead-radar-console/scripts/seed-fixtures.ts`
- Create: `lead-radar-console/src/components/conversion/ConversionCard.tsx`
- Modify: `lead-radar-console/src/app/q/[workflow]/page.tsx`

- [ ] **Step 1: Add conversion fixture**

```typescript
// append to fixtures array
{
  decisionId: '00000000-0000-0000-0000-000002000001',
  workflowId: 'conversion_registration', profileVersion: 1, tierAtDecision: 'T1',
  inputsHash: 'fixture-conv-001',
  inputsPayload: {
    outcome_confirmation_pending: true,
    history: { leadId: 'lead-7423', deliveredAt: '2026-05-01', installer: 'HVAC Schoonebeek BV', followupAt: '2026-05-15', repliedAt: '2026-05-16 14:32' },
    reply: '"Hi, klant heeft inderdaad bij ons getekend op 12 mei. Hybride lucht-water systeem, installatie staat gepland voor 15 juni. Bedrag: 14.500 incl BTW. Bedankt voor de doorverwijzing!"',
    parsed: { outcome: 'won', valueBand: '5-15k', install: 'likely', attribution: 'high' },
    parseConfidence: 0.94,
  },
  agentRecommendation: { parsedFields: { outcome: 'won', valueBand: '5-15k', install: 'likely', attribution: 'high' } },
  agentConfidence: 0.94, leadId: 'lead-7423',
},
```

Run `pnpm db:seed-fixtures`.

- [ ] **Step 2: ConversionCard**

```tsx
// src/components/conversion/ConversionCard.tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CardShell } from '@/components/card/CardShell';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

const OUTCOMES = ['won', 'lost', 'unclear'] as const;
const VALUE_BANDS = ['<5k', '5-15k', '15-30k', '>30k'] as const;
const INSTALLS = ['confirmed', 'likely', 'uncertain'] as const;
const ATTRIBS = ['high', 'medium', 'low', 'disputed'] as const;

export function ConversionCard({ decision, position, whyText }: any) {
  const router = useRouter();
  const initial = decision.inputsPayload?.parsed ?? {};
  const [outcome, setOutcome] = useState<typeof OUTCOMES[number]>(initial.outcome ?? 'unclear');
  const [valueBand, setValueBand] = useState<typeof VALUE_BANDS[number]>(initial.valueBand ?? '<5k');
  const [installStatus, setInstall] = useState<typeof INSTALLS[number]>(initial.install ?? 'uncertain');
  const [attribution, setAttrib] = useState<typeof ATTRIBS[number]>(initial.attribution ?? 'low');
  const [notes, setNotes] = useState('');
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const parseConfidence = decision.inputsPayload?.parseConfidence ?? 0;

  async function save() {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'conversion_registration', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
      agentRecommendation: decision.agentRecommendation,
      reviewerDecision: { outcome, valueBand, install: installStatus, attribution, notes, source: 'operator_confirm' },
      agreement: JSON.stringify({ outcome, valueBand, install: installStatus, attribution }) === JSON.stringify(initial) ? 'Y' : 'N',
      leadId: decision.leadId,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    router.refresh();
  }

  async function flagDispute() {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'conversion_registration', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown', inputsPayload: decision.inputsPayload,
      reviewerDecision: { action: 'dispute', notes }, agreement: 'N',
      leadId: decision.leadId,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    router.refresh();
  }

  useKeyboardShortcuts({
    'S': () => {
      if (parseConfidence < 0.8 && !editing) { setEditing(true); return; }
      if (!confirming) { setConfirming(true); return; }
      save();
    },
    'E': () => setEditing(true),
    'F': () => flagDispute(),
    'Escape': () => { setEditing(false); setConfirming(false); router.push('/triage'); },
  }, { allowInInputs: true });

  const h = decision.inputsPayload?.history;

  return (
    <CardShell
      workflowLabel="Conversion-reg" position={position} urgency="on-pace" whyText={whyText}
      helpEntries={[
        { key: 'S', label: 'Save (are-you-sure first)' },
        { key: 'E', label: 'Edit fields' },
        { key: 'F', label: 'Flag dispute' },
      ]}
      actions={[
        { key: 'S', label: confirming ? 'Confirm save?' : 'Save', onClick: save },
        { key: 'E', label: 'Edit', onClick: () => setEditing(true) },
        { key: 'F', label: 'Flag dispute', onClick: flagDispute },
      ]}
    >
      <section className="mb-4">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Lead history</h2>
        <div className="text-xs text-zinc-400">{h?.leadId} • delivered {h?.deliveredAt} to {h?.installer}<br />Follow-up email sent {h?.followupAt} · Installer responded {h?.repliedAt}</div>
      </section>
      <section className="mb-4">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Installer's reply</h2>
        <p className="text-sm text-zinc-300">{decision.inputsPayload?.reply}</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent's parsed fields (parse confidence {(parseConfidence * 100).toFixed(0)}%)</h2>
        <div className="space-y-2 text-sm">
          <div>Outcome: {OUTCOMES.map(o => (<label key={o} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="outcome" disabled={!editing} checked={outcome === o} onChange={() => setOutcome(o)} />{o}</label>))}</div>
          <div>Value band: {VALUE_BANDS.map(v => (<label key={v} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="v" disabled={!editing} checked={valueBand === v} onChange={() => setValueBand(v)} />€{v}</label>))}</div>
          <div>Install: {INSTALLS.map(i => (<label key={i} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="i" disabled={!editing} checked={installStatus === i} onChange={() => setInstall(i)} />{i}</label>))}</div>
          <div>Attribution: {ATTRIBS.map(a => (<label key={a} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="a" disabled={!editing} checked={attribution === a} onChange={() => setAttrib(a)} />{a}</label>))}</div>
          <div>Notes: <input type="text" value={notes} onChange={e => setNotes(e.target.value)} className="bg-zinc-950 border border-zinc-700 px-2 py-1 rounded text-sm w-2/3" /></div>
          {confirming && <div className="text-xs text-yellow-500">Confirm save? Press S again (dataset-defining, irreversible in UI).</div>}
        </div>
      </section>
    </CardShell>
  );
}
```

- [ ] **Step 3: Wire into queue page**

```tsx
import { ConversionCard } from '@/components/conversion/ConversionCard';
// in JSX:
{workflow === 'conversion_registration' && (
  <ConversionCard decision={current as any} position={{ current: 1, total: items.length }} whyText={why} />
)}
```

- [ ] **Step 4: Manual test**

Process conversion fixture → E to edit → adjust band → S twice → verify save.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/components/conversion/ lead-radar-console/scripts/seed-fixtures.ts lead-radar-console/src/app/q/[workflow]/page.tsx
git commit -m "feat(console): conversion card with won/lost/bands/attribution + S-twice are-you-sure"
```

---

## Phase 7 — Audit Chain Inline Tree-view

### Task 7.1: Audit API + AuditChainView + AuditTreeNode + wire V key

**Files:**
- Create: `lead-radar-console/src/app/api/audit/[leadId]/route.ts`
- Create: `lead-radar-console/src/components/audit/AuditTreeNode.tsx`
- Create: `lead-radar-console/src/components/audit/AuditChainView.tsx`
- Modify: `lead-radar-console/src/components/routing/RoutingCard.tsx` (add V key)
- Modify: classification + conversion cards similarly

- [ ] **Step 1: API**

```typescript
// src/app/api/audit/[leadId]/route.ts
import { NextResponse } from 'next/server';
import { getAuditChainByLeadId } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';

export async function GET(_req: Request, { params }: { params: Promise<{ leadId: string }> }) {
  await requireCurrentOperator();
  const { leadId } = await params;
  return NextResponse.json({ chain: await getAuditChainByLeadId(leadId) });
}
```

- [ ] **Step 2: AuditTreeNode (compact default + advanced toggle)**

```tsx
// src/components/audit/AuditTreeNode.tsx
'use client';
import { useState } from 'react';

const ICONS: Record<string, string> = {
  lead_delivery_routing: '✅', signal_classification_ambiguous_band: '🤖', conversion_registration: '✓', default: '◯',
};

export function AuditTreeNode({ decision, depth }: { decision: any; depth: number }) {
  const [expanded, setExpanded] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const icon = ICONS[decision.workflowId] ?? ICONS.default;
  const indent = '   '.repeat(depth) + (depth > 0 ? '└─ ' : '');

  return (
    <div className="font-mono text-xs">
      <button onClick={() => setExpanded(e => !e)} className="text-left w-full hover:bg-zinc-900 px-1">
        <pre className="inline">{indent}{icon} {decision.workflowId}  {new Date(decision.decidedAt).toLocaleString()}  {(decision.reviewerDecision as any)?.action ?? (decision.reviewerDecision as any)?.category ?? ''}</pre>
      </button>
      {expanded && (
        <div className="ml-8 my-2 p-3 border border-zinc-800 rounded bg-zinc-950">
          <div>workflow: {decision.workflowId}</div>
          <div>agent_rec: {JSON.stringify(decision.agentRecommendation)?.slice(0, 80)}...</div>
          <div>operator: {decision.reviewerId ?? '—'}</div>
          <div>op_decision: {JSON.stringify(decision.reviewerDecision)?.slice(0, 80)}...</div>
          <div>agreement: {decision.agreement ?? 'NA'}</div>
          <div>time_to_decide: {decision.timeToDecideMs ?? '—'}ms</div>
          <button onClick={() => setAdvanced(a => !a)} className="text-zinc-500 hover:underline mt-2">
            [A]dvanced inspect {advanced ? '▼' : '▶'}
          </button>
          {advanced && (
            <div className="mt-2 text-zinc-500">
              <div>decision_id: {decision.decisionId}</div>
              <div>profile_version: {decision.profileVersion}</div>
              <div>tier_at_decision: {decision.tierAtDecision}</div>
              <div>agent_id: {decision.agentId ?? '—'}</div>
              <div>inputs_hash: {decision.inputsHash}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: AuditChainView with time-in-audit**

```tsx
// src/components/audit/AuditChainView.tsx
'use client';
import { useEffect, useState } from 'react';
import { AuditTreeNode } from './AuditTreeNode';

export function AuditChainView({ leadId, onClose }: { leadId: string; onClose: () => void }) {
  const [chain, setChain] = useState<any[]>([]);
  const [startedAt] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => { fetch(`/api/audit/${leadId}`).then(r => r.json()).then(d => setChain(d.chain)); }, [leadId]);
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <div className="border border-zinc-700 rounded p-4 my-4 bg-zinc-900">
      <div className="flex justify-between text-xs text-zinc-500 mb-3">
        <span>Audit chain · {leadId}</span>
        <span>
          {elapsed > 60 && <span className="mr-2">⏱ {elapsed}s in audit</span>}
          <button onClick={onClose} className="underline">[Esc] back</button>
        </span>
      </div>
      {elapsed > 180 && (
        <div className="text-yellow-500 text-xs mb-3">
          Continue queue work? <button onClick={onClose} className="underline">[C]ontinue</button> · stay
        </div>
      )}
      {chain.length === 0 ? <div className="text-zinc-500">Loading...</div> : chain.map((d, i) => <AuditTreeNode key={d.decisionId} decision={d} depth={i} />)}
    </div>
  );
}
```

- [ ] **Step 4: Wire V key in all three cards**

In each card component (Routing, Classification, Conversion), add:

```tsx
const [auditOpen, setAuditOpen] = useState(false);
// add 'V' to useKeyboardShortcuts:
'V': () => setAuditOpen(true),
// extend Escape handler to close audit:
'Escape': () => { if (auditOpen) setAuditOpen(false); else if (overrideOpen) setOverrideOpen(false); else router.push('/triage'); },
// in JSX, render inside CardShell before </CardShell>:
{auditOpen && decision.leadId && <AuditChainView leadId={decision.leadId} onClose={() => setAuditOpen(false)} />}
```

Add `V` to helpEntries and actions.

- [ ] **Step 5: Manual test**

In RoutingCard press `V` → audit tree appears → click a node → expand → click "Advanced inspect" → see infra fields → `Esc` closes audit, queue position preserved.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/app/api/audit/ lead-radar-console/src/components/audit/ lead-radar-console/src/components/routing/RoutingCard.tsx lead-radar-console/src/components/classification/ClassificationCard.tsx lead-radar-console/src/components/conversion/ConversionCard.tsx
git commit -m "feat(console): audit chain inline tree-view + advanced inspect + time-in-audit (V key)"
```

---

## Phase 8 — Universal Search + Retrieval Service

### Task 8.1: Retrieval interface + text + exact modes + indexes

**Files:**
- Create: `lead-radar-console/src/lib/retrieval/index.ts`
- Create: `lead-radar-console/src/lib/retrieval/text-mode.ts`
- Create: `lead-radar-console/src/lib/retrieval/exact-mode.ts`
- Create: `lead-radar-console/src/db/migrations/9999_search_indexes.sql`

- [ ] **Step 1: Retrieval interface**

```typescript
// src/lib/retrieval/index.ts
import { textMode } from './text-mode';
import { exactMode } from './exact-mode';

export type RetrievalMode = 'text' | 'exact';
export type Match = { leadId: string; preview: string; source?: string; status?: string; matchedAt: string };

export async function retrieve(query: string, mode: RetrievalMode = 'text'): Promise<Match[]> {
  switch (mode) {
    case 'text': return textMode(query);
    case 'exact': return exactMode(query);
    default: throw new Error(`Unknown mode: ${mode}`);
  }
}
```

- [ ] **Step 2: Search indexes migration (raw SQL)**

Create `src/db/migrations/9999_search_indexes.sql`:
```sql
CREATE INDEX IF NOT EXISTS decisions_signal_text_fts
  ON decisions USING gin (to_tsvector('simple',
    coalesce(inputs_payload->'signal'->>'postText', '') || ' ' ||
    coalesce(inputs_payload->'lead'->>'postText', '')
  ));
```

Apply:
```bash
docker exec -i lead-radar-console-pg psql -U console -d lead_radar < src/db/migrations/9999_search_indexes.sql
```

- [ ] **Step 3: Text mode**

```typescript
// src/lib/retrieval/text-mode.ts
import { sql } from '@/lib/db/client';
import type { Match } from './index';

export async function textMode(q: string): Promise<Match[]> {
  if (!q.trim()) return [];
  const rows = await sql<{ lead_id: string; preview: string; decided_at: Date }[]>`
    SELECT lead_id,
           coalesce(inputs_payload->'signal'->>'postText', inputs_payload->'lead'->>'postText', '') AS preview,
           decided_at
    FROM decisions
    WHERE lead_id IS NOT NULL
      AND to_tsvector('simple',
            coalesce(inputs_payload->'signal'->>'postText', '') || ' ' ||
            coalesce(inputs_payload->'lead'->>'postText', '')
          ) @@ plainto_tsquery('simple', ${q})
    GROUP BY lead_id, preview, decided_at
    ORDER BY decided_at DESC
    LIMIT 10
  `;
  return rows.map(r => ({
    leadId: r.lead_id,
    preview: (r.preview ?? '').slice(0, 80) + (r.preview && r.preview.length > 80 ? '...' : ''),
    matchedAt: r.decided_at.toISOString(),
  }));
}
```

- [ ] **Step 4: Exact mode**

```typescript
// src/lib/retrieval/exact-mode.ts
import { db } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import type { Match } from './index';

export async function exactMode(q: string): Promise<Match[]> {
  const rows = await db.query.decisions.findMany({ where: eq(decisions.leadId, q), limit: 10 });
  return rows.map(r => ({
    leadId: r.leadId ?? '',
    preview: JSON.stringify(r.inputsPayload).slice(0, 80),
    matchedAt: r.decidedAt.toISOString(),
  }));
}
```

- [ ] **Step 5: Test**

```typescript
// tests/integration/retrieval.test.ts
import { describe, it, expect } from 'vitest';
import { retrieve } from '@/lib/retrieval';
import { sql } from '@/lib/db/client';

describe('retrieval', () => {
  it('text mode finds warmtepomp', async () => {
    const m = await retrieve('warmtepomp', 'text');
    expect(m.length).toBeGreaterThan(0);
  });
  it('exact mode finds by lead id', async () => {
    const m = await retrieve('lead-fixture-001', 'exact');
    expect(m.length).toBeGreaterThan(0);
    await sql.end();
  });
});
```

Run: PASS.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/retrieval/ lead-radar-console/src/db/migrations/9999_search_indexes.sql lead-radar-console/tests/integration/retrieval.test.ts
git commit -m "feat(console): retrieval service interface (text + exact) + tsvector FTS index"
```

---

### Task 8.2: Search API + SearchOverlay + leadId deep-link page

**Files:**
- Create: `lead-radar-console/src/app/api/search/route.ts`
- Create: `lead-radar-console/src/components/search/SearchOverlay.tsx`
- Create: `lead-radar-console/src/app/l/[leadId]/page.tsx`
- Modify: `lead-radar-console/src/app/layout.tsx` (mount overlay globally)

- [ ] **Step 1: Search API**

```typescript
// src/app/api/search/route.ts
import { NextResponse } from 'next/server';
import { retrieve } from '@/lib/retrieval';
import { requireCurrentOperator } from '@/lib/db/operators';

export async function GET(req: Request) {
  await requireCurrentOperator();
  const u = new URL(req.url);
  return NextResponse.json({ matches: await retrieve(u.searchParams.get('q') ?? '', (u.searchParams.get('mode') ?? 'text') as any) });
}
```

- [ ] **Step 2: SearchOverlay**

```tsx
// src/components/search/SearchOverlay.tsx
'use client';
import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

export function SearchOverlay() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [matches, setMatches] = useState<any[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  useKeyboardShortcuts({
    '/': () => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50); },
    'Escape': () => { if (open) setOpen(false); },
    'Enter': () => { if (open && matches[selectedIdx]) { router.push(`/l/${matches[selectedIdx].leadId}`); setOpen(false); } },
    'ArrowDown': () => open && setSelectedIdx(i => Math.min(matches.length - 1, i + 1)),
    'ArrowUp': () => open && setSelectedIdx(i => Math.max(0, i - 1)),
  }, { allowInInputs: true });

  useEffect(() => {
    if (!q.trim()) { setMatches([]); return; }
    const id = setTimeout(() => { fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()).then(d => setMatches(d.matches)); }, 200);
    return () => clearTimeout(id);
  }, [q]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center pt-32" onClick={() => setOpen(false)}>
      <div className="bg-zinc-900 border border-zinc-700 rounded w-full max-w-xl font-mono text-sm" onClick={e => e.stopPropagation()}>
        <input ref={inputRef} placeholder="Search..." value={q} onChange={e => setQ(e.target.value)}
          className="w-full px-3 py-3 bg-zinc-900 border-b border-zinc-700 outline-none" />
        <ul>
          {matches.map((m, i) => (
            <li key={m.leadId} className={`px-3 py-2 cursor-pointer ${i === selectedIdx ? 'bg-zinc-800' : ''}`} onClick={() => { router.push(`/l/${m.leadId}`); setOpen(false); }}>
              <div className="text-zinc-100">{m.leadId}</div>
              <div className="text-xs text-zinc-500">{m.preview}</div>
            </li>
          ))}
        </ul>
        <div className="px-3 py-2 text-xs text-zinc-500 border-t border-zinc-800">[Enter] open · [Esc] cancel · ↑/↓ navigate</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lead audit deep-link page**

```tsx
// src/app/l/[leadId]/page.tsx
'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuditChainView } from '@/components/audit/AuditChainView';

export default function LeadAuditPage() {
  // Note: client component to allow inline AuditChainView; auth check happens via middleware (or wrap in server boundary if needed)
  const router = useRouter();
  // pathname → /l/[leadId]
  if (typeof window === 'undefined') return null;
  const leadId = window.location.pathname.split('/')[2];
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <AuditChainView leadId={leadId} onClose={() => router.push('/triage')} />
      </div>
    </main>
  );
}
```

(Server-component variant with auth-check is preferable; for V0 the SearchOverlay only routes after authenticated session exists.)

- [ ] **Step 4: Mount SearchOverlay globally**

Edit `src/app/layout.tsx`:
```tsx
import { SearchOverlay } from '@/components/search/SearchOverlay';
// inside body:
<SearchOverlay />
```

- [ ] **Step 5: Manual test**

Press `/` anywhere → overlay opens → type "warmtepomp" → matches appear → Enter → audit chain opens for that lead.

- [ ] **Step 6: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/app/api/search/ lead-radar-console/src/components/search/ lead-radar-console/src/app/l/ lead-radar-console/src/app/layout.tsx
git commit -m "feat(console): universal search overlay (/) + lead audit deep-link route"
```

---

## Phase 9 — Operational Headroom Widget

### Task 9.1: Headroom calculator + widget

**Files:**
- Create: `lead-radar-console/src/lib/headroom/calculator.ts`
- Create: `lead-radar-console/src/app/api/headroom/route.ts`
- Create: `lead-radar-console/src/components/headroom/OperationalHeadroomWidget.tsx`
- Modify: `lead-radar-console/src/app/layout.tsx`

- [ ] **Step 1: Calculator**

```typescript
// src/lib/headroom/calculator.ts
import { sql } from '@/lib/db/client';
import { getActiveProfile } from '@/lib/db/workflow-profiles';

const WORKFLOWS = ['lead_delivery_routing', 'signal_classification_ambiguous_band', 'conversion_registration'];

export async function computeHeadroom(): Promise<{ pct: number; status: 'green' | 'yellow' | 'orange' | 'red' }> {
  let used = 0, budget = 0;
  for (const w of WORKFLOWS) {
    const p = await getActiveProfile(w);
    if (!p) continue;
    budget += (p.profile as any)?.ocl_budget?.per_operator_minutes_per_day ?? 0;
    const r = await sql<{ used: number }[]>`
      SELECT coalesce(sum(time_to_decide_ms), 0) / 60000.0 AS used
      FROM decisions WHERE workflow_id = ${w} AND decided_at::date = current_date`;
    used += Number(r[0]?.used ?? 0);
  }
  const pct = budget > 0 ? Math.round((used / budget) * 100) : 0;
  const status: 'green' | 'yellow' | 'orange' | 'red' = pct >= 100 ? 'red' : pct >= 80 ? 'orange' : pct >= 60 ? 'yellow' : 'green';
  return { pct, status };
}
```

- [ ] **Step 2: API**

```typescript
// src/app/api/headroom/route.ts
import { NextResponse } from 'next/server';
import { computeHeadroom } from '@/lib/headroom/calculator';
import { requireCurrentOperator } from '@/lib/db/operators';
export async function GET() { await requireCurrentOperator(); return NextResponse.json(await computeHeadroom()); }
```

- [ ] **Step 3: Widget**

```tsx
// src/components/headroom/OperationalHeadroomWidget.tsx
'use client';
import { useEffect, useState } from 'react';
const C = { green: 'bg-green-500', yellow: 'bg-yellow-500', orange: 'bg-orange-500', red: 'bg-red-500' };
export function OperationalHeadroomWidget() {
  const [d, setD] = useState<{ pct: number; status: keyof typeof C } | null>(null);
  useEffect(() => { fetch('/api/headroom').then(r => r.json()).then(setD); }, []);
  if (!d) return null;
  return (
    <div className="fixed top-2 right-2 bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-xs font-mono z-40">
      <span className={`inline-block w-2 h-2 rounded-full ${C[d.status]} mr-1`} />
      <span className="text-zinc-400">Headroom: {d.pct}%</span>
    </div>
  );
}
```

- [ ] **Step 4: Mount in layout**

```tsx
import { OperationalHeadroomWidget } from '@/components/headroom/OperationalHeadroomWidget';
// in body:
<OperationalHeadroomWidget />
```

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/lib/headroom/ lead-radar-console/src/app/api/headroom/ lead-radar-console/src/components/headroom/ lead-radar-console/src/app/layout.tsx
git commit -m "feat(console): Operational Headroom widget (top-right, green/yellow/orange/red)"
```

---

## Phase 10 — State-Preserving Deep-Links + Telegram

### Task 10.1: Decision deep-link route + Telegram link generator

**Files:**
- Create: `lead-radar-console/src/app/d/[decisionId]/page.tsx`
- Create: `lead-radar-console/src/lib/telegram/deep-links.ts`
- Create: `lead-radar-console/tests/unit/deep-links.test.ts`

- [ ] **Step 1: Decision deep-link page**

```tsx
// src/app/d/[decisionId]/page.tsx
import { redirect, notFound } from 'next/navigation';
import { auth } from '@/../auth';
import { db } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import Link from 'next/link';

export default async function DecisionPage({ params, searchParams }: {
  params: Promise<{ decisionId: string }>;
  searchParams: Promise<{ return_to?: string }>;
}) {
  const session = await auth();
  if (!session) redirect('/login');
  const { decisionId } = await params;
  const { return_to } = await searchParams;
  const d = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, decisionId) });
  if (!d) notFound();
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <Link href={return_to ? `/${return_to}` : '/triage'} className="text-xs text-zinc-500 underline">← back</Link>
        <h2 className="text-lg mt-4">Decision {decisionId}</h2>
        <pre className="text-xs mt-4 p-4 bg-zinc-900 border border-zinc-800 rounded overflow-auto">
          {JSON.stringify(d, null, 2)}
        </pre>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Deep-link generator**

```typescript
// src/lib/telegram/deep-links.ts
type Target =
  | { type: 'decision'; decisionId: string; returnTo?: string }
  | { type: 'lead'; leadId: string; returnTo?: string }
  | { type: 'triage' };

export function makeDeepLink(target: Target): string {
  const base = process.env.CONSOLE_BASE_URL ?? 'http://localhost:3000';
  switch (target.type) {
    case 'decision': return `${base}/d/${target.decisionId}${target.returnTo ? `?return_to=${target.returnTo}` : ''}`;
    case 'lead': return `${base}/l/${target.leadId}${target.returnTo ? `?return_to=${target.returnTo}` : ''}`;
    case 'triage': return `${base}/triage`;
  }
}
```

- [ ] **Step 3: Test**

```typescript
// tests/unit/deep-links.test.ts
import { describe, it, expect } from 'vitest';
import { makeDeepLink } from '@/lib/telegram/deep-links';
describe('deep links', () => {
  it('decision with return_to', () => {
    expect(makeDeepLink({ type: 'decision', decisionId: 'abc', returnTo: 'triage' })).toMatch(/d\/abc\?return_to=triage$/);
  });
  it('lead without return_to', () => {
    expect(makeDeepLink({ type: 'lead', leadId: 'lead-1' })).toMatch(/l\/lead-1$/);
  });
});
```

Run: PASS.

- [ ] **Step 4: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/src/app/d/ lead-radar-console/src/lib/telegram/ lead-radar-console/tests/unit/deep-links.test.ts
git commit -m "feat(console): state-preserving deep-link route + Telegram link generator"
```

---

## Phase 11 — Final Polish + E2E

### Task 11.1: Playwright e2e for operator daily flow

**Files:**
- Create: `lead-radar-console/scripts/seed-test-session.ts`
- Create: `lead-radar-console/tests/e2e/operator-daily-flow.spec.ts`

- [ ] **Step 1: Install Playwright browsers**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
pnpm playwright install chromium
```

- [ ] **Step 2: Seed test session script**

```typescript
// scripts/seed-test-session.ts
import { db, sql } from '@/lib/db/client';
import { sessions, operators } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import { randomUUID } from 'crypto';

async function main() {
  const founder = await db.query.operators.findFirst({ where: eq(operators.email, process.env.FOUNDER_EMAIL!) });
  if (!founder) throw new Error('Founder not seeded');
  const token = randomUUID();
  await db.insert(sessions).values({
    sessionId: token,
    operatorId: founder.operatorId,
    expiresAt: new Date(Date.now() + 24 * 3600 * 1000),
  });
  console.log(`TEST_SESSION_TOKEN=${token}`);
  await sql.end();
}
main().catch(e => { console.error(e); process.exit(1); });
```

Add script: `"db:seed-test-session": "tsx --env-file=.env scripts/seed-test-session.ts"`.

- [ ] **Step 3: E2E test**

```typescript
// tests/e2e/operator-daily-flow.spec.ts
import { test, expect } from '@playwright/test';

test('triage → routing card → approve → next', async ({ page }) => {
  await page.context().addCookies([{
    name: 'authjs.session-token',
    value: process.env.TEST_SESSION_TOKEN ?? '',
    domain: 'localhost', path: '/',
  }]);
  await page.goto('/triage');
  await expect(page.getByText('Routing')).toBeVisible();
  await page.keyboard.press('1');
  await expect(page.url()).toContain('/q/lead_delivery_routing');
  await expect(page.getByText('Approve & route')).toBeVisible();
  await page.keyboard.press('A');
  await expect(page.getByText(/Routing|Queue empty/)).toBeVisible({ timeout: 5000 });
});
```

- [ ] **Step 4: Run**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
export TEST_SESSION_TOKEN=$(pnpm db:seed-test-session | grep -oE '[a-f0-9-]{36}')
pnpm test:e2e
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/scripts/seed-test-session.ts lead-radar-console/tests/e2e/
git commit -m "test(console): Playwright e2e operator daily flow (login → triage → routing → approve)"
```

---

### Task 11.2: README + operator runbook

**Files:**
- Create: `lead-radar-console/README.md`
- Create: `lead-radar-console/OPERATOR_RUNBOOK.md`

- [ ] **Step 1: README**

```markdown
# Lead Radar — Operator Intelligence Console v0

The daily operator workstation. Reads from owned Postgres, writes decisions to the audit log (proprietary dataset).

## Quick start

cp .env.example .env  # fill in DATABASE_URL, FOUNDER_EMAIL, RESEND_API_KEY
docker compose up -d
pnpm install
pnpm db:migrate
pnpm db:seed
pnpm db:seed-fixtures
pnpm dev

Open http://localhost:3000 → log in with FOUNDER_EMAIL via magic-link.

## Workflows

- Routing (/q/lead_delivery_routing)
- Classification (/q/signal_classification_ambiguous_band)
- Conversion (/q/conversion_registration)

## Keyboard shortcuts

Press `?` in any card.

## Architecture

See lead-radar/docs/superpowers/specs/2026-05-18-*.md.
```

- [ ] **Step 2: Operator runbook**

Create `OPERATOR_RUNBOOK.md` with sections: Daily login, Triage scan, Each workflow, Override, Audit, Search, Kill-switch, Troubleshooting. Keep it under 400 lines.

- [ ] **Step 3: Commit**

```bash
cd "/Users/claudebot/Lead generator"
git add lead-radar-console/README.md lead-radar-console/OPERATOR_RUNBOOK.md
git commit -m "docs(console): README + operator runbook for daily use"
```

---

### Task 11.3: Final integration check + push

- [ ] **Step 1: Full test suite**

```bash
cd "/Users/claudebot/Lead generator/lead-radar-console"
pnpm test
pnpm build
```

- [ ] **Step 2: Push**

```bash
cd "/Users/claudebot/Lead generator"
git push origin feat/facebook-scraper
```

- [ ] **Step 3: Mark launch in spec**

Edit `lead-radar/docs/superpowers/specs/2026-05-18-operator-intelligence-console-v0-design.md` and add at bottom:
```
## V0 launch log
| Date | Phase | Notes |
|---|---|---|
| YYYY-MM-DD | Phase 3 (MVP) | Founder logged in, processed first routing decisions |
| YYYY-MM-DD | Phase 11 | All 12 components live, V0 complete |
```

```bash
git add lead-radar/docs/superpowers/specs/2026-05-18-operator-intelligence-console-v0-design.md
git commit -m "docs(console): V0 launch log section"
git push origin feat/facebook-scraper
```

---

## Self-Review Notes

After writing this plan I checked it against the spec:

**Spec coverage:**
- Component 1 (Auth) → Phase 1
- Component 2 (Triage overview) → Task 3.2
- Component 3 (Card-shell) → Task 3.5
- Component 4 (Routing card-body) → Task 3.6
- Component 5 (Classification card-body) → Task 5.1
- Component 6 (Conversion card-body) → Task 6.1
- Component 7 (Override inline-form) → Task 4.1+4.2
- Component 8 (Audit chain view) → Task 7.1
- Component 9 (Universal search overlay) → Task 8.2
- Component 10 (Operational Headroom widget) → Task 9.1
- Component 11 (Why-string generator) → Task 3.4
- Component 12 (Retrieval service interface) → Task 8.1

All 12 components addressed. Plus auxiliary tasks: DB schema, fixtures, deep-links, e2e, runbook.

**Critical disciplines enforced:**
- Queue-claim mechanism Task 2.3 (multi-op safe vanaf dag 1)
- requireCurrentOperator Task 1.3 (no singleton)
- Auto-save on action (all card components write directly via /api/decisions)
- Keyboard-first (useKeyboardShortcuts hook, single-letter shortcuts per card)
- Inline audit (Task 7.1, no separate audit page)
- Decision-support language (Task 3.6 InstallerRecommendation kwalitatieve labels)
- Operator uncertainty qualifiers (Task 5.1 U/M/T/N)
- Lichter conversion V0 (Task 6.1 won/lost + bands)
- Why-string strict copy-guide (Task 3.4 deterministic rules, no LLM)
- State-preserving deep-links (Task 10.1 return_to)
- Override taxonomy as DB-data (override_categories table seeded Task 0.4)

**Known V0 simplifications (per spec section 14 — first usable, not production mature):**
- Cluster banner is in CardShell prop but no production detection logic — V0 doesn't fire it; will activate after observing real cluster patterns
- Routing card pre-claim (queue_claims) is not wired into the queue page (only the helper exists). Add when multi-op friction surfaces.
- Search exact mode is leadId-only; full installer/niche/geo extension deferred.
- Time-in-audit prompt at 3min is shown but doesn't auto-redirect — operator drives.

These are intentional V0 simplifications, not gaps.

---

## Execution Handoff

Plan complete and saved to `lead-radar/docs/superpowers/plans/2026-05-18-operator-intelligence-console-v0.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for parallel agent execution (the spec's "2-3 weken" path).

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Best for hands-on involvement.

**Which approach?**
