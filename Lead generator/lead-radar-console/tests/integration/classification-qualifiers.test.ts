import { describe, it, expect, afterAll } from 'vitest';
import { writeDecision } from '@/lib/db/decisions';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

describe('classification qualifiers', () => {
  it('writes uncertain qualifier', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'signal_classification_ambiguous_band',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: 'q1',
      inputsPayload: { signal: { text: 'x' } },
      reviewerId: op!.operatorId,
      reviewerDecision: { category: 'research_intent', qualifier: 'uncertain', secondary_category: null, source: 'operator_pick' },
      agreement: 'Y',
    });
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect((row?.reviewerDecision as Record<string, unknown> | null)?.qualifier).toBe('uncertain');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
  });

  it('writes mixed with secondary', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    const r = await writeDecision({
      workflowId: 'signal_classification_ambiguous_band',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: 'q2',
      inputsPayload: { signal: { text: 'x' } },
      reviewerId: op!.operatorId,
      reviewerDecision: { category: 'research_intent', qualifier: 'mixed', secondary_category: 'purchase_intent_pre_quote', source: 'operator_pick' },
      agreement: 'N',
    });
    const row = await db.query.decisions.findFirst({ where: eq(decisions.decisionId, r.decisionId) });
    expect((row?.reviewerDecision as Record<string, unknown> | null)?.secondary_category).toBe('purchase_intent_pre_quote');
    await db.delete(decisions).where(eq(decisions.decisionId, r.decisionId));
  });
});

afterAll(async () => {
  await sql.end();
});
