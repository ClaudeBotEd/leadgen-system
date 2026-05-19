/**
 * Test-only sign-in endpoint.
 *
 * Accepts ?email=<address>, looks up the operator in DB, then signs a
 * NextAuth-compatible JWT and sets it as the session cookie directly.
 * Only active when ENABLE_TEST_AUTH === '1'. Returns 404 otherwise.
 *
 * NOTE: NODE_ENV cannot gate this because Next.js always overrides it to
 * 'development' in dev mode. Use ENABLE_TEST_AUTH=1 in .env for e2e runs.
 *
 * Why direct JWT signing instead of signIn():
 *   NextAuth's signIn() is designed for Server Actions — it sets cookies via
 *   the Server Action response mechanism which doesn't work in Route Handlers.
 *   Directly calling encode() from next-auth/jwt and setting the cookie header
 *   is the correct approach for Route Handler session injection.
 *
 * Usage (Playwright per-test):
 *   await page.goto('/api/test/sign-in?email=ClaudeBotEd@protonmail.com');
 *   // Cookie is set; subsequent page navigations are authenticated.
 */
import { NextRequest, NextResponse } from 'next/server';
import { encode } from 'next-auth/jwt';
import { db } from '@/lib/db/client';
import { operators } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

export async function GET(req: NextRequest): Promise<NextResponse> {
  if (process.env.ENABLE_TEST_AUTH !== '1') {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) {
    return NextResponse.json({ error: 'NEXTAUTH_SECRET not set' }, { status: 500 });
  }

  const email = req.nextUrl.searchParams.get('email');
  if (!email) {
    return NextResponse.json({ error: 'email param required' }, { status: 400 });
  }

  // Verify operator exists and is active
  const op = await db.query.operators.findFirst({
    where: eq(operators.email, email),
  });
  if (!op || !op.active) {
    return NextResponse.json({ error: 'Operator not found or inactive' }, { status: 401 });
  }

  const now = Math.floor(Date.now() / 1000);
  const maxAge = 30 * 24 * 60 * 60; // 30 days, matches authConfig

  // Encode a NextAuth-compatible JWT. The `salt` must match the cookie name
  // that NextAuth uses when reading it back (authjs.session-token in dev/test).
  const token = await encode({
    token: {
      email: op.email,
      name: op.name,
      sub: op.operatorId,
      iat: now,
      exp: now + maxAge,
    },
    secret,
    salt: 'authjs.session-token',
  });

  const response = NextResponse.redirect(new URL('/triage', req.url));
  response.cookies.set('authjs.session-token', token, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge,
    // secure: false in dev/test (localhost)
  });
  return response;
}
