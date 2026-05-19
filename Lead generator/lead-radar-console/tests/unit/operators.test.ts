import { describe, it, expect, afterAll } from 'vitest';
import { getOperatorByEmail } from '@/lib/db/operators';
import { sql } from '@/lib/db/client';

describe('operators', () => {
  it('finds founder by email', async () => {
    const op = await getOperatorByEmail(process.env.FOUNDER_EMAIL!);
    expect(op?.role).toBe('lead');
  });

  it('returns undefined for unknown', async () => {
    expect(await getOperatorByEmail('nobody@example.com')).toBeUndefined();
  });

  afterAll(async () => {
    await sql.end();
  });
});
