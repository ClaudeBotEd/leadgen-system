import Resend from 'next-auth/providers/resend';
import Credentials from 'next-auth/providers/credentials';
import { db } from '@/lib/db/client';
import { operators } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import type { NextAuthConfig } from 'next-auth';

/**
 * JWT strategy — no adapter tables required for V0.
 * The signIn callback gates access to seeded operators only.
 * Sessions live in NextAuth's encrypted cookie (no DB session store).
 *
 * NOTE: DrizzleAdapter is intentionally omitted. Our `operators` table does
 * not match the shape expected by @auth/drizzle-adapter (which needs `user`,
 * `account`, `session`, `verificationToken` tables with specific column
 * names). A full adapter integration is deferred to a future task.
 *
 * TEST-ONLY: A Credentials provider is added when ENABLE_TEST_AUTH === '1'.
 * It accepts any email that matches a seeded active operator — no password
 * needed. Set ENABLE_TEST_AUTH=1 in .env only for local e2e runs.
 * Never set this variable in production or staging.
 *
 * NOTE: NODE_ENV cannot be used here because Next.js always sets
 * NODE_ENV='development' during `next dev` regardless of the shell env.
 */

const testCredentialsProvider =
  process.env.ENABLE_TEST_AUTH === '1'
    ? [
        Credentials({
          id: 'test-credentials',
          name: 'Test credentials',
          credentials: { email: { label: 'Email', type: 'text' } },
          async authorize({ email }) {
            if (!email || typeof email !== 'string') return null;
            const op = await db.query.operators.findFirst({
              where: eq(operators.email, email),
            });
            if (!op || !op.active) return null;
            return { id: op.operatorId, email: op.email, name: op.name };
          },
        }),
      ]
    : [];

// In e2e test runs (ENABLE_TEST_AUTH=1) the Resend email provider is excluded.
// Resend is an email provider and requires a database adapter (assertConfig
// returns MissingAdapter), which then causes NextAuth to bail out on every
// auth() call — blocking session reads. In test mode only the Credentials
// provider is used and Resend is not needed.
const resendProvider =
  process.env.ENABLE_TEST_AUTH !== '1'
    ? [
        Resend({
          apiKey: process.env.RESEND_API_KEY,
          from: process.env.RESEND_FROM ?? 'noreply@example.com',
        }),
      ]
    : [];

export const authConfig: NextAuthConfig = {
  session: { strategy: 'jwt', maxAge: 30 * 24 * 60 * 60 },
  providers: [
    ...resendProvider,
    ...testCredentialsProvider,
  ],
  pages: { signIn: '/login', verifyRequest: '/login/verify' },
  callbacks: {
    async signIn({ user }) {
      if (!user.email) return false;
      const existing = await db.query.operators.findFirst({
        where: eq(operators.email, user.email),
      });
      return existing != null && existing.active;
    },
    async jwt({ token, user }) {
      // Persist operator email into the token on first sign-in
      if (user?.email) {
        token.email = user.email;
      }
      return token;
    },
    async session({ session, token }) {
      // Expose email on the session object for server-side helpers
      if (token.email) {
        session.user.email = token.email as string;
      }
      return session;
    },
  },
};
