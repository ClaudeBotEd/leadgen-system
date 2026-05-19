import { test, expect, type Page } from '@playwright/test';

/**
 * Doctrine §02.2 + A8: bands, never numbers. The operator console must
 * not display numerical confidence percentages or `/100` scores anywhere
 * in the rendered UI — they encourage A19 rubber-stamping by anchoring
 * reviewer cognition to model output.
 *
 * Session injection mirrors operator-daily-flow.spec.ts: NEXTAUTH_SECRET
 * + the test-credentials provider activated via ENABLE_TEST_AUTH=1 in
 * playwright.config.ts.
 *
 * Routes:
 *   Classification → /q/signal_classification_ambiguous_band
 *   Conversion     → /q/conversion_registration
 *
 * If the queue is empty (DB not seeded) the page renders "Queue empty"
 * — the banned-pattern assertions still pass trivially. To exercise the
 * actual classification/conversion cards, seed fixtures first:
 *   docker compose up -d db && pnpm db:seed-fixtures
 */

const FOUNDER_EMAIL = 'ClaudeBotEd@protonmail.com';

const BANNED_PATTERNS: RegExp[] = [
  /\bconfidence\s+\d{1,3}%/i,
  /\bparse\s+confidence\s+\d{1,3}%/i,
  /\b\d{1,3}\s?\/\s?100\b/,
];

async function signInAsFounder(page: Page): Promise<void> {
  await page.goto(`/api/test/sign-in?email=${encodeURIComponent(FOUNDER_EMAIL)}`);
  await page.waitForURL(/\/triage/, { timeout: 10_000 });
}

async function assertNoBannedPatterns(page: Page, route: string): Promise<void> {
  await page.goto(route);
  await page.waitForLoadState('networkidle');
  const body = await page.locator('body').innerText();
  for (const pattern of BANNED_PATTERNS) {
    expect(body, `banned pattern ${pattern} matched on ${route}`).not.toMatch(pattern);
  }
}

test.describe('doctrine §02.2 — no numerical confidence in console UI', () => {
  test('classification queue renders no confidence percentage', async ({ page }) => {
    await signInAsFounder(page);
    await assertNoBannedPatterns(page, '/q/signal_classification_ambiguous_band');
  });

  test('conversion queue renders no parse-confidence percentage', async ({ page }) => {
    await signInAsFounder(page);
    await assertNoBannedPatterns(page, '/q/conversion_registration');
  });
});
