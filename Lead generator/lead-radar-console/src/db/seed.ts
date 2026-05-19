import { db, sql } from '@/lib/db/client';
import { operators, overrideCategories, workflowProfiles } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';

const FOUNDER_EMAIL = process.env.FOUNDER_EMAIL;
const FOUNDER_NAME = process.env.FOUNDER_NAME ?? 'Founder';

async function seed() {
  if (!FOUNDER_EMAIL) throw new Error('FOUNDER_EMAIL required');

  await db.insert(operators).values({ name: FOUNDER_NAME, email: FOUNDER_EMAIL, role: 'lead' })
    .onConflictDoNothing({ target: operators.email });

  await db.insert(overrideCategories).values([
    { categoryKey: 'taxonomy_miss', displayLabel: 'taxonomy miss', sortOrder: 1 },
    { categoryKey: 'too_strict', displayLabel: 'too strict', sortOrder: 2 },
    { categoryKey: 'too_lax', displayLabel: 'too lax', sortOrder: 3 },
    { categoryKey: 'context_missing', displayLabel: 'context missing', sortOrder: 4 },
    { categoryKey: 'other', displayLabel: 'other', sortOrder: 5 },
  ]).onConflictDoNothing();

  const founder = await db.query.operators.findFirst({ where: eq(operators.email, FOUNDER_EMAIL) });

  await db.insert(workflowProfiles).values([
    {
      workflowId: 'lead_delivery_routing', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'standard', risk_class: 'trust_load_bearing',
        current_tier: 'T1', terminal_tier: 'T2',
        cof_vector: { financial: 'low', installer_relationship: 'high', exclusivity: 'high', dataset_corruption: 'medium', ops_cascade: 'medium' },
        cof_circuit_breakers: ['exclusivity_breach_risk_per_decision > 0.1%'],
        latency_class: 'L2', sla_budget_minutes: 240, fallback_policy: 'F-B', out_of_hours_policy: 'pause',
        ocl_budget: { per_operator_minutes_per_day: 30, complexity: 'medium', expected_volume_per_day: 50 },
      },
    },
    {
      workflowId: 'signal_classification_ambiguous_band', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'standard', risk_class: 'quality_load_bearing',
        current_tier: 'T1', terminal_tier: 'T3',
        cof_vector: { financial: 'very_low', installer_relationship: 'low', exclusivity: 'none', dataset_corruption: 'medium', ops_cascade: 'medium' },
        latency_class: 'L1', sla_budget_minutes: 60, fallback_policy: 'F-A', out_of_hours_policy: 'fallback_allowed',
        ocl_budget: { per_operator_minutes_per_day: 60, complexity: 'medium', expected_volume_per_day: 100 },
      },
    },
    {
      workflowId: 'conversion_registration', profileVersion: 1, isActive: true, createdBy: founder!.operatorId,
      profile: {
        profile_level: 'critical', risk_class: 'dataset_defining',
        current_tier: 'T1', terminal_tier: 'T1',
        cof_vector: { financial: 'low', installer_relationship: 'low', exclusivity: 'none', dataset_corruption: 'catastrophic', ops_cascade: 'cascading' },
        latency_class: 'L3', sla_budget_minutes: 10080, fallback_policy: 'F-C', out_of_hours_policy: 'pause',
        ocl_budget: { per_operator_minutes_per_day: 30, complexity: 'complex', expected_volume_per_day: 5 },
      },
    },
  ]).onConflictDoNothing();

  await sql.end();
  console.log('✓ Seeded');
}

seed().catch(err => { console.error(err); process.exit(1); });
