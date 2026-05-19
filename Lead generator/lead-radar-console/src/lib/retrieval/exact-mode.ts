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
