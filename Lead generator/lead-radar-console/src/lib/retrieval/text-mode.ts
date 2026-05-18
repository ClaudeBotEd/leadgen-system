import { sql } from '@/lib/db/client';
import type { Match } from './index';

export async function textMode(q: string): Promise<Match[]> {
  if (!q.trim()) return [];
  const rows = await sql<{ lead_id: string | null; preview: string; decided_at: Date | string }[]>`
    SELECT lead_id,
           coalesce(inputs_payload->'signal'->>'postText', inputs_payload->'lead'->>'postText', '') AS preview,
           decided_at
    FROM decisions
    WHERE lead_id IS NOT NULL
      AND to_tsvector('simple',
            coalesce(inputs_payload->'signal'->>'postText', '') || ' ' ||
            coalesce(inputs_payload->'lead'->>'postText', '') || ' ' ||
            coalesce(inputs_payload->'lead'->>'niche', '')
          ) @@ plainto_tsquery('simple', ${q})
    GROUP BY lead_id, preview, decided_at
    ORDER BY decided_at DESC
    LIMIT 10
  `;
  return rows.map(r => ({
    leadId: r.lead_id ?? '',
    preview: (r.preview ?? '').slice(0, 80) + (r.preview && r.preview.length > 80 ? '...' : ''),
    matchedAt: r.decided_at instanceof Date ? r.decided_at.toISOString() : new Date(r.decided_at).toISOString(),
  }));
}
