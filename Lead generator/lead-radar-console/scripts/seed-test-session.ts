/**
 * seed-test-session.ts
 *
 * Generates a NextAuth v5 JWT session cookie value for the founder email
 * using next-auth/jwt's encode() — the same signing path NextAuth uses
 * internally. Prints the raw cookie value so Playwright (or any test
 * harness) can inject it via context.addCookies().
 *
 * Usage:
 *   tsx --env-file=.env scripts/seed-test-session.ts
 *
 * Output:
 *   TEST_SESSION_TOKEN=<base64url-jwt>
 *
 * NOTE: Because lead-radar-console uses the JWT session strategy (not DB
 * sessions), this token IS the session — no database row is created.
 * The cookie name NextAuth v5 uses is "authjs.session-token" in
 * development/test and "__Secure-authjs.session-token" in production.
 */
import { encode } from 'next-auth/jwt';

const secret = process.env.NEXTAUTH_SECRET;
const email = process.env.FOUNDER_EMAIL ?? 'ClaudeBotEd@protonmail.com';

if (!secret) {
  console.error('NEXTAUTH_SECRET is not set — add it to .env');
  process.exit(1);
}

const token = await encode({
  token: {
    email,
    name: 'Founder',
    sub: 'test-founder',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60,
  },
  secret,
  // NextAuth v5 uses 'authjs.session-token' as the salt in non-production
  salt: 'authjs.session-token',
});

console.log(`TEST_SESSION_TOKEN=${token}`);
console.log(`\nAdd to .env.test or pass to Playwright via env:`);
console.log(`  TEST_SESSION_TOKEN="${token}"`);
