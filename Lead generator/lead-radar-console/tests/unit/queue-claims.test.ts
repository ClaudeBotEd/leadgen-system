import { describe, it, expect, afterEach, afterAll } from 'vitest';
import { tryClaim, releaseClaim, getClaimer } from '@/lib/db/queue-claims';
import { getOperatorByEmail } from '@/lib/db/operators';
import { db, sql } from '@/lib/db/client';
import { sql as ds } from 'drizzle-orm';

const D1 = '11111111-1111-1111-1111-111111111111';

async function insertTestDecision(id: string) {
  await db.execute(ds`
    INSERT INTO decisions (decision_id, workflow_id, profile_version, tier_at_decision, inputs_hash, inputs_payload, decided_at)
    VALUES (${id}, 'lead_delivery_routing', 1, 'T1', 'h', '{}'::jsonb, now())
    ON CONFLICT DO NOTHING
  `);
}

afterEach(async () => {
  await db.execute(ds`DELETE FROM queue_claims WHERE decision_id = ${D1}`);
  await db.execute(ds`DELETE FROM decisions WHERE decision_id = ${D1}`);
});

afterAll(async () => {
  await sql.end();
});

describe('queue claims', () => {
  it('same operator can re-claim (idempotent)', async () => {
    await insertTestDecision(D1);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    expect(await tryClaim(D1, op!.operatorId)).toBe(true);
    expect(await tryClaim(D1, op!.operatorId)).toBe(true);
  });

  it('release allows reclaim', async () => {
    await insertTestDecision(D1);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    await tryClaim(D1, op!.operatorId);
    await releaseClaim(D1);
    expect(await getClaimer(D1)).toBeUndefined();
  });
});
