import { describe, it, expect, afterAll } from 'vitest';
import { isWorkflowKilled, killWorkflow, releaseWorkflowKill } from '@/lib/db/kill-state';
import { getOperatorByEmail } from '@/lib/db/operators';
import { sql } from '@/lib/db/client';

describe('kill state', () => {
  it('roundtrip kill + release', async () => {
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(false);
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    await killWorkflow('lead_delivery_routing', 'test', op!.operatorId);
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(true);
    await releaseWorkflowKill('lead_delivery_routing');
    expect(await isWorkflowKilled('lead_delivery_routing')).toBe(false);
  });

  afterAll(async () => {
    await sql.end();
  });
});
