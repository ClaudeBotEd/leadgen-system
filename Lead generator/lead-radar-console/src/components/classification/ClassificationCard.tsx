'use client';
import { useRouter } from 'next/navigation';
import { useState, useTransition, useMemo } from 'react';
import { CardShell } from '@/components/card/CardShell';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';
import { OverrideInlineForm } from '@/components/override/OverrideInlineForm';

type Cat = { categoryKey: string; confidence: number; reasoning?: string };

type SignalShape = {
  source?: string;
  user?: string;
  ageHours?: number;
  preScore?: number;
  postText?: string;
};

type AgentRec = { candidates?: Cat[] };

type Props = {
  decision: {
    decisionId: string;
    inputsHash: string;
    inputsPayload: Record<string, unknown>;
    agentRecommendation: Record<string, unknown> | null;
    signalId: string | null;
  };
  position: { current: number; total: number };
  whyText: string;
  categories: { categoryKey: string; displayLabel: string }[];
};

type Qualifier = 'confident' | 'uncertain' | 'mixed' | 'taxonomy_gap';

export function ClassificationCard({ decision, position, whyText, categories }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [qualifierMode, setQualifierMode] = useState<Qualifier>('confident');
  const [primaryPick, setPrimaryPick] = useState<string | null>(null);

  const rec = decision.agentRecommendation as AgentRec | null;
  const candidates: Cat[] = rec?.candidates ?? [];
  const signal = (decision.inputsPayload as { signal?: SignalShape }).signal;

  async function save(categoryKey: string, qualifier: Qualifier, secondary?: string) {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'signal_classification_ambiguous_band',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      agentRecommendation: rec ?? undefined,
      reviewerDecision: { category: categoryKey, qualifier, secondary_category: secondary ?? null, source: 'operator_pick' },
      agreement: (candidates[0]?.categoryKey === categoryKey ? 'Y' : 'N') as 'Y' | 'N',
      signalId: decision.signalId ?? undefined,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    startTransition(() => router.refresh());
  }

  async function submitOverride(categoryKey: string, reason: string) {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'signal_classification_ambiguous_band',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      reviewerDecision: { action: 'override' },
      agreement: 'N' as const,
      overrideCategory: categoryKey,
      overrideReason: reason,
      signalId: decision.signalId ?? undefined,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    setOverrideOpen(false);
    startTransition(() => router.refresh());
  }

  function pickByIdx(i: number) {
    const cat = candidates[i]?.categoryKey;
    if (!cat) return;
    if (qualifierMode === 'mixed' && !primaryPick) { setPrimaryPick(cat); return; }
    if (qualifierMode === 'mixed' && primaryPick) {
      void save(primaryPick, 'mixed', cat);
      setPrimaryPick(null);
      return;
    }
    void save(cat, qualifierMode);
  }

  const shortcuts = useMemo(() => ({
    '1': () => pickByIdx(0),
    '2': () => pickByIdx(1),
    '3': () => pickByIdx(2),
    'U': () => setQualifierMode('uncertain'),
    'M': () => { setQualifierMode('mixed'); setPrimaryPick(null); },
    'T': () => { void save('taxonomy_gap', 'taxonomy_gap'); },
    'N': () => { void save('no_intent', 'confident'); },
    'O': () => setOverrideOpen(true),
    'H': () => { void save(candidates[0]?.categoryKey ?? 'no_intent', 'uncertain'); },
    'Escape': () => {
      if (overrideOpen) { setOverrideOpen(false); return; }
      router.push('/triage');
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [candidates, qualifierMode, primaryPick, overrideOpen]);
  useKeyboardShortcuts(shortcuts);

  return (
    <CardShell
      workflowLabel="Classification"
      position={position}
      urgency="on-pace"
      whyText={whyText}
      helpEntries={[
        { key: '1/2/3', label: 'Confident pick' },
        { key: 'U', label: 'Uncertain mode (then 1/2/3)' },
        { key: 'M', label: 'Mixed mode (primary then secondary)' },
        { key: 'T', label: 'Taxonomy gap (none fit)' },
        { key: 'N', label: 'No intent (confident negative)' },
        { key: 'O', label: 'Override' },
        { key: 'H', label: 'Hold' },
      ]}
      actions={[
        { key: '1/2/3', label: 'Pick', onClick: () => {} },
        { key: 'U', label: `Mode: ${qualifierMode}`, onClick: () => setQualifierMode('uncertain') },
        { key: 'M', label: 'Mixed', onClick: () => setQualifierMode('mixed') },
        { key: 'T', label: 'Tax gap', onClick: () => { void save('taxonomy_gap', 'taxonomy_gap'); } },
        { key: 'N', label: 'No intent', onClick: () => { void save('no_intent', 'confident'); } },
        { key: 'O', label: 'Override', onClick: () => setOverrideOpen(true) },
      ]}
    >
      <section className="mb-6">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Signal</h2>
        <div className="text-xs text-zinc-500">Source: {signal?.source} &bull; {signal?.ageHours}u oud &bull; user: {signal?.user}</div>
        <div className="text-xs text-zinc-500">Pre-score: {signal?.preScore} (ambigue band)</div>
        <p className="text-sm mt-3 text-zinc-300">&quot;{signal?.postText}&quot;</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent&apos;s best guesses</h2>
        {candidates.map((c, i) => (
          <div key={c.categoryKey} className={`mb-2 ${primaryPick === c.categoryKey ? 'border border-blue-700 rounded p-2' : ''}`}>
            <div className="text-sm">
              <span className="text-zinc-500">[{i + 1}]</span>{' '}
              <span className="font-medium">{c.categoryKey}</span>{' '}
              <span className="text-zinc-500 text-xs ml-3">confidence {(c.confidence * 100).toFixed(0)}%</span>
            </div>
            {c.reasoning && <div className="text-xs text-zinc-500 ml-6">reasoning: &quot;{c.reasoning}&quot;</div>}
          </div>
        ))}
        {qualifierMode === 'mixed' && (
          <div className="text-xs text-yellow-500 mt-2">
            Mixed: {primaryPick ? `primary &quot;${primaryPick}&quot; picked — pick secondary (1/2/3)` : 'pick primary (1/2/3)'}
          </div>
        )}
      </section>
      {overrideOpen && (
        <OverrideInlineForm
          categories={categories}
          onSubmit={(key, reason) => { void submitOverride(key, reason); }}
          onCancel={() => setOverrideOpen(false)}
        />
      )}
    </CardShell>
  );
}
