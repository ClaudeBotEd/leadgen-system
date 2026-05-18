import { sql } from '@/lib/db/client';
import { getActiveProfile } from '@/lib/db/workflow-profiles';

const WORKFLOWS = ['lead_delivery_routing', 'signal_classification_ambiguous_band', 'conversion_registration'];

type ProfileWithBudget = { profile: { ocl_budget?: { per_operator_minutes_per_day?: number } } };

export async function computeHeadroom(): Promise<{ pct: number; status: 'green' | 'yellow' | 'orange' | 'red' }> {
  let used = 0, budget = 0;
  for (const w of WORKFLOWS) {
    const p = await getActiveProfile(w);
    if (!p) continue;
    const profile = p.profile as ProfileWithBudget['profile'];
    budget += profile?.ocl_budget?.per_operator_minutes_per_day ?? 0;
    const r = await sql<{ used: number }[]>`
      SELECT coalesce(sum(time_to_decide_ms), 0) / 60000.0 AS used
      FROM decisions WHERE workflow_id = ${w} AND decided_at::date = current_date`;
    used += Number(r[0]?.used ?? 0);
  }
  const pct = budget > 0 ? Math.round((used / budget) * 100) : 0;
  const status: 'green' | 'yellow' | 'orange' | 'red' = pct >= 100 ? 'red' : pct >= 80 ? 'orange' : pct >= 60 ? 'yellow' : 'green';
  return { pct, status };
}
