import { NextResponse } from 'next/server';
import { getQueueItems } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

const ALLOWED = new Set(['lead_delivery_routing', 'signal_classification_ambiguous_band', 'conversion_registration']);

export async function GET(_req: Request, { params }: { params: Promise<{ workflow: string }> }) {
  await requireCurrentOperator();
  const { workflow } = await params;
  if (!ALLOWED.has(workflow)) return NextResponse.json({ error: 'unknown_workflow' }, { status: 404 });
  if (await isWorkflowKilled(workflow)) return NextResponse.json({ items: [], killed: true });
  return NextResponse.json({ items: await getQueueItems(workflow, 50), killed: false });
}
