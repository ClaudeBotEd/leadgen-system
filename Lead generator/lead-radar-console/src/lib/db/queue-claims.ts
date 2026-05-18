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
