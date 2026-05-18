import { NextResponse } from 'next/server';
import { getAuditChainByLeadId } from '@/lib/db/decisions';
import { requireCurrentOperator } from '@/lib/db/operators';

export async function GET(_req: Request, { params }: { params: Promise<{ leadId: string }> }) {
  await requireCurrentOperator();
  const { leadId } = await params;
  return NextResponse.json({ chain: await getAuditChainByLeadId(leadId) });
}
