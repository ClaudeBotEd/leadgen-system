import { describe, it, expect } from 'vitest';
import { db, sql } from '@/lib/db/client';
import { operators, overrideCategories, workflowProfiles } from '@/lib/db/schema';

describe('seed', () => {
  it('inserted founder operator with lead role', async () => {
    const ops = await db.select().from(operators);
    expect(ops.find(o => o.role === 'lead')).toBeDefined();
  });
  it('inserted 5 override categories', async () => {
    const cats = await db.select().from(overrideCategories);
    expect(cats.length).toBe(5);
  });
  it('inserted 3 workflow profiles', async () => {
    const wfs = await db.select().from(workflowProfiles);
    expect(wfs.length).toBe(3);
    await sql.end();
  });
});
