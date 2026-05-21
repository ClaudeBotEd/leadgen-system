import { db } from './client';
import { decisions } from './schema';
import { eq, and, isNull, asc, count, or } from 'drizzle-orm';

type Input = {
  workflowId: string;
  profileVersion: number;
  tierAtDecision: string;
  inputsHash: string;
  inputsPayload: Record<string, unknown>;
  agentId?: string;
  agentRecommendation?: Record<string, unknown>;
  agentConfidence?: number;
  agentReasoningRef?: string;
  reviewerId?: string;
  reviewerDecision?: Record<string, unknown>;
  agreement?: 'Y' | 'N' | 'NA';
  overrideReason?: string;
  overrideCategory?: string;
  timeToDecideMs?: number;
  leadId?: string;
  signalId?: string;
};

export async function writeDecision(input: Input): Promise<{ decisionId: string }> {
  const [row] = await db.insert(decisions).values(input).returning({ decisionId: decisions.decisionId });
  return row;
}

export async function getQueueItems(workflowId: string, limit: number) {
  return db.query.decisions.findMany({
    where: and(eq(decisions.workflowId, workflowId), isNull(decisions.reviewerId)),
    orderBy: asc(decisions.decidedAt), limit,
  });
}

export async function getQueueCounter(workflowId: string): Promise<number> {
  const [row] = await db.select({ c: count() }).from(decisions)
    .where(and(eq(decisions.workflowId, workflowId), isNull(decisions.reviewerId)));
  return Number(row.c);
}

export async function getAuditChainByLeadId(leadId: string) {
  return db.query.decisions.findMany({
    where: or(eq(decisions.leadId, leadId), eq(decisions.signalId, leadId)),
    orderBy: asc(decisions.decidedAt),
  });
}
