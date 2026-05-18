import { describe, it, expect, afterAll } from 'vitest';
import { retrieve } from '@/lib/retrieval';
import { sql } from '@/lib/db/client';

describe('retrieval', () => {
  afterAll(async () => { await sql.end(); });

  it('text mode finds warmtepomp', async () => {
    const m = await retrieve('warmtepomp', 'text');
    expect(m.length).toBeGreaterThan(0);
  });

  it('exact mode finds by lead id', async () => {
    const m = await retrieve('lead-fixture-001', 'exact');
    expect(m.length).toBeGreaterThan(0);
  });
});
