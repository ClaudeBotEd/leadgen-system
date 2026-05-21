import { describe, it, expect, afterAll } from 'vitest';
import { writeDecision, getQueueCounter } from '@/lib/db/decisions';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('decision write', () => {
  it('round-trips a decision row', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'lead_delivery_routing', profileVersion: 1, tierAtDecision: 'T1',
      inputsHash: 'h-test', inputsPayload: { lead_id: 'test-1' },
      reviewerId: op!.operatorId, reviewerDecision: { action: 'approve' }, agreement: 'Y',
      leadId: 'test-1',
    });
    expect(r.decisionId).toBeDefined();
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect(row?.agreement).toBe('Y');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
  });
});

afterAll(async () => {
  await sql.end();
});
