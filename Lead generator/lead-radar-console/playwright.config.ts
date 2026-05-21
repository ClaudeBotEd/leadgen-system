import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: 1,
  use: {
    baseURL: 'http://localhost:3000',
  },
  webServer: {
    // ENABLE_TEST_AUTH=1 activates the test-credentials NextAuth provider
    // and /api/test/sign-in endpoint required for e2e session injection.
    // NOTE: NODE_ENV cannot be used here — Next.js always overrides it to
    // 'development' in dev mode regardless of shell environment.
    // Use the local next binary so this works without pnpm in PATH.
    command: 'node_modules/.bin/next dev --turbopack',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    env: { ENABLE_TEST_AUTH: '1' },
  },
});
