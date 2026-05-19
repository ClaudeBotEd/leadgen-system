'use client';
import { useState } from 'react';

const ICONS: Record<string, string> = {
  lead_delivery_routing: '✅',
  signal_classification_ambiguous_band: '🤖',
  conversion_registration: '✓',
  default: '◯',
};

type DecisionLike = {
  decisionId: string;
  workflowId: string;
  decidedAt: string | Date;
  reviewerId?: string | null;
  reviewerDecision?: Record<string, unknown> | null;
  agentRecommendation?: Record<string, unknown> | null;
  agreement?: string | null;
  timeToDecideMs?: number | null;
  profileVersion?: number;
  tierAtDecision?: string;
  agentId?: string | null;
  inputsHash?: string;
};

export function AuditTreeNode({ decision, depth }: { decision: DecisionLike; depth: number }) {
  const [expanded, setExpanded] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const icon = ICONS[decision.workflowId] ?? ICONS.default;
  const indent = '   '.repeat(depth) + (depth > 0 ? '└─ ' : '');
  const rd = decision.reviewerDecision as Record<string, unknown> | null | undefined;
  const action = (rd?.action as string | undefined) ?? (rd?.category as string | undefined) ?? '';

  return (
    <div className="font-mono text-xs">
      <button onClick={() => setExpanded(e => !e)} className="text-left w-full hover:bg-zinc-900 px-1">
        <pre className="inline">{indent}{icon} {decision.workflowId}  {new Date(decision.decidedAt).toLocaleString()}  {action}</pre>
      </button>
      {expanded && (
        <div className="ml-8 my-2 p-3 border border-zinc-800 rounded bg-zinc-950">
          <div>workflow: {decision.workflowId}</div>
          <div>agent_rec: {JSON.stringify(decision.agentRecommendation)?.slice(0, 80)}...</div>
          <div>operator: {decision.reviewerId ?? '—'}</div>
          <div>op_decision: {JSON.stringify(decision.reviewerDecision)?.slice(0, 80)}...</div>
          <div>agreement: {decision.agreement ?? 'NA'}</div>
          <div>time_to_decide: {decision.timeToDecideMs ?? '—'}ms</div>
          <button onClick={() => setAdvanced(a => !a)} className="text-zinc-500 hover:underline mt-2">
            [A]dvanced inspect {advanced ? '▼' : '▶'}
          </button>
          {advanced && (
            <div className="mt-2 text-zinc-500">
              <div>decision_id: {decision.decisionId}</div>
              <div>profile_version: {decision.profileVersion}</div>
              <div>tier_at_decision: {decision.tierAtDecision}</div>
              <div>agent_id: {decision.agentId ?? '—'}</div>
              <div>inputs_hash: {decision.inputsHash}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
