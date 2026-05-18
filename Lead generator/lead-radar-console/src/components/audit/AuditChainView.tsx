'use client';
import { useEffect, useState } from 'react';
import { AuditTreeNode } from './AuditTreeNode';

type DecisionLike = Parameters<typeof AuditTreeNode>[0]['decision'];

export function AuditChainView({ leadId, onClose }: { leadId: string; onClose: () => void }) {
  const [chain, setChain] = useState<DecisionLike[]>([]);
  const [startedAt] = useState(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    fetch(`/api/audit/${leadId}`).then(r => r.json()).then(d => setChain(d.chain));
  }, [leadId]);

  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return (
    <div className="border border-zinc-700 rounded p-4 my-4 bg-zinc-900">
      <div className="flex justify-between text-xs text-zinc-500 mb-3">
        <span>Audit chain · {leadId}</span>
        <span>
          {elapsed > 60 && <span className="mr-2">⏱ {elapsed}s in audit</span>}
          <button onClick={onClose} className="underline">[Esc] back</button>
        </span>
      </div>
      {elapsed > 180 && (
        <div className="text-yellow-500 text-xs mb-3">
          Continue queue work? <button onClick={onClose} className="underline">[C]ontinue</button> · stay
        </div>
      )}
      {chain.length === 0 ? (
        <div className="text-zinc-500">Loading...</div>
      ) : (
        chain.map((d, i) => <AuditTreeNode key={d.decisionId} decision={d} depth={i} />)
      )}
    </div>
  );
}
