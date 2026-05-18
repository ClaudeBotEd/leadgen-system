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
