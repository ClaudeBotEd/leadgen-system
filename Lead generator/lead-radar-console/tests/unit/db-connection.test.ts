import { describe, it, expect } from 'vitest';
import { sql } from '@/lib/db/client';

describe('db connection', () => {
  it('connects', async () => {
    const r = await sql`SELECT 1 as one`;
    expect(r[0].one).toBe(1);
    await sql.end();
  });
});
