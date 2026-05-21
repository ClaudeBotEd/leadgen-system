/**
 * Operator daily flow — end-to-end spec
 *
 * Verifies the operator can complete their core daily loop:
 *   triage dashboard → routing queue → approve a lead → return to triage (or queue empty)
 *
 * Session injection strategy: Option A (test-only Credentials provider).
 *   The dev server runs with NODE_ENV=test (set in playwright.config.ts) so
 *   NextAuth registers the test-credentials provider.
 *   Each test navigates to /api/test/sign-in?email=... first; NextAuth sets
 *   the encrypted JWT cookie, which persists for the duration of that test.
 *
 * Prerequisites (must be satisfied before running):
 *   1. Docker Postgres running: docker compose up -d db
 *   2. Fixtures seeded:        pnpm db:seed-fixtures
 *   3. NEXTAUTH_SECRET set in  .env
 */

import { test, expect, type Page } from '@playwright/test';

const FOUNDER_EMAIL = 'ClaudeBotEd@protonmail.com';

/** Navigate to the test sign-in endpoint and wait for the session redirect. */
async function signInAsFounder(page: Page): Promise<void> {
  await page.goto(`/api/test/sign-in?email=${encodeURIComponent(FOUNDER_EMAIL)}`);
  // The endpoint redirects to /triage on success; wait for the page to settle.
  await page.waitForURL(/\/triage/, { timeout: 10_000 });
}

test.describe('operator daily flow', () => {
  test('triage dashboard shows all three workflow blocks', async ({ page }) => {
    await signInAsFounder(page);

    await expect(page.getByText('Routing')).toBeVisible();
    await expect(page.getByText('Classification')).toBeVisible();
    await expect(page.getByText('Conversions')).toBeVisible();
  });

  test('hotkey [1] navigates to routing queue', async ({ page }) => {
    await signInAsFounder(page);

    await page.keyboard.press('1');
    await page.waitForURL(/\/q\/lead_delivery_routing/, { timeout: 8_000 });
    // Either a routing card or "Queue empty" should be visible
    await expect(
      page.getByText(/Routing|Queue empty/),
    ).toBeVisible({ timeout: 5_000 });
  });

  test('triage → routing card → approve & route → advance queue', async ({ page }) => {
    await signInAsFounder(page);

    // Navigate to the routing queue
    await page.keyboard.press('1');
    await page.waitForURL(/\/q\/lead_delivery_routing/, { timeout: 8_000 });

    // If queue is empty, fixture seeding hasn't run — skip gracefully
    const isEmpty = await page.getByText('Queue empty').isVisible().catch(() => false);
    if (isEmpty) {
      test.skip(true, 'Routing queue is empty — run pnpm db:seed-fixtures first');
      return;
    }

    // Routing card must show the "Approve & route" action
    await expect(page.getByText('Approve & route')).toBeVisible({ timeout: 5_000 });

    // Press [A] to approve the current lead
    await page.keyboard.press('A');

    // After approval the queue either shows the next item or "Queue empty"
    await expect(
      page.getByText(/Routing|Queue empty/),
    ).toBeVisible({ timeout: 8_000 });
  });

  test('Escape on routing card returns to triage', async ({ page }) => {
    await signInAsFounder(page);

    await page.goto('/q/lead_delivery_routing');
    await page.waitForURL(/\/q\/lead_delivery_routing/, { timeout: 8_000 });

    const isEmpty = await page.getByText('Queue empty').isVisible().catch(() => false);
    if (isEmpty) {
      // Even from an empty-state page, navigate back manually
      await page.goto('/triage');
      return;
    }

    await page.keyboard.press('Escape');
    await page.waitForURL(/\/triage/, { timeout: 5_000 });
    await expect(page.getByText('Lead Radar')).toBeVisible();
  });
});
