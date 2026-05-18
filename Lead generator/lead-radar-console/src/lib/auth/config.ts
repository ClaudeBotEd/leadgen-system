import Resend from 'next-auth/providers/resend';
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
 */
export const authConfig: NextAuthConfig = {
  session: { strategy: 'jwt', maxAge: 30 * 24 * 60 * 60 },
  providers: [
    Resend({
      apiKey: process.env.RESEND_API_KEY,
      from: process.env.RESEND_FROM ?? 'noreply@example.com',
    }),
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
