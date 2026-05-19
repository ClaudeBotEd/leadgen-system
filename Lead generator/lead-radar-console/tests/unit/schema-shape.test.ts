import { describe, it, expect } from 'vitest';
import { sql } from '@/lib/db/client';

describe('schema', () => {
  it('has all V0 tables', async () => {
    const tables = await sql<{ tablename: string }[]>`
      SELECT tablename FROM pg_tables WHERE schemaname = 'public'`;
    const names = tables.map(t => t.tablename);
    for (const t of ['operators', 'sessions', 'override_categories', 'workflow_profiles', 'workflow_kill_state', 'decisions', 'queue_claims']) {
      expect(names).toContain(t);
    }
    await sql.end();
  });
});
