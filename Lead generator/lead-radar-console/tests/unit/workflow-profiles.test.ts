import { describe, it, expect, afterAll } from 'vitest';
import { getActiveProfile } from '@/lib/db/workflow-profiles';
import { sql } from '@/lib/db/client';

describe('workflow profiles', () => {
  it('returns active routing profile', async () => {
    const p = await getActiveProfile('lead_delivery_routing');
    expect((p?.profile as any).risk_class).toBe('trust_load_bearing');
  });
  it('returns undefined for unknown', async () => {
    expect(await getActiveProfile('nope')).toBeUndefined();
  });

  afterAll(async () => {
    await sql.end();
  });
});
