import { NextResponse } from 'next/server';
import { z } from 'zod';
import { writeDecision } from '@/lib/db/decisions';
import { releaseClaim } from '@/lib/db/queue-claims';
import { requireCurrentOperator } from '@/lib/db/operators';
import { isWorkflowKilled } from '@/lib/db/kill-state';

const schema = z.object({
  decisionId: z.string().uuid().optional(),
  workflowId: z.string(),
  profileVersion: z.number().int(),
  tierAtDecision: z.string(),
  inputsHash: z.string(),
  inputsPayload: z.record(z.string(), z.unknown()),
  agentRecommendation: z.record(z.string(), z.unknown()).optional(),
  agentConfidence: z.number().min(0).max(1).optional(),
  reviewerDecision: z.record(z.string(), z.unknown()),
  agreement: z.enum(['Y', 'N', 'NA']),
  overrideReason: z.string().max(200).optional(),
  overrideCategory: z.string().optional(),
  timeToDecideMs: z.number().int().nonnegative().optional(),
  leadId: z.string().optional(),
  signalId: z.string().optional(),
});

export async function POST(req: Request) {
  const op = await requireCurrentOperator();
  const body = await req.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: parsed.error.format() }, { status: 400 });
  if (await isWorkflowKilled(parsed.data.workflowId)) return NextResponse.json({ error: 'workflow_killed' }, { status: 409 });
  const { decisionId } = await writeDecision({ ...parsed.data, reviewerId: op.operatorId });
  if (parsed.data.decisionId) await releaseClaim(parsed.data.decisionId);
  return NextResponse.json({ decisionId });
}
