import { NextResponse } from 'next/server';
import { getQueueCounter } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

export async function GET() {
  await requireCurrentOperator();
  const [routing, classification, conversion] = await Promise.all([
    getQueueCounter('lead_delivery_routing'),
    getQueueCounter('signal_classification_ambiguous_band'),
    getQueueCounter('conversion_registration'),
  ]);
  return NextResponse.json({
    counts: { routing, classification, conversion },
    killed: {
      lead_delivery_routing: await isWorkflowKilled('lead_delivery_routing'),
      signal_classification_ambiguous_band: await isWorkflowKilled('signal_classification_ambiguous_band'),
      conversion_registration: await isWorkflowKilled('conversion_registration'),
    },
  });
}
