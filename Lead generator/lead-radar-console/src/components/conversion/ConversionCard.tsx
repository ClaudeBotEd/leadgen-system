'use client';
import { useState, useMemo, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { CardShell } from '@/components/card/CardShell';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

const OUTCOMES = ['won', 'lost', 'unclear'] as const;
const VALUE_BANDS = ['<5k', '5-15k', '15-30k', '>30k'] as const;
const INSTALLS = ['confirmed', 'likely', 'uncertain'] as const;
const ATTRIBS = ['high', 'medium', 'low', 'disputed'] as const;

type Outcome = typeof OUTCOMES[number];
type ValueBand = typeof VALUE_BANDS[number];
type InstallStatus = typeof INSTALLS[number];
type Attribution = typeof ATTRIBS[number];

type HistoryShape = { leadId?: string; deliveredAt?: string; installer?: string; followupAt?: string; repliedAt?: string };
type ParsedShape = { outcome?: Outcome; valueBand?: ValueBand; install?: InstallStatus; attribution?: Attribution };

type Props = {
  decision: {
    decisionId: string;
    inputsHash: string;
    inputsPayload: Record<string, unknown>;
    agentRecommendation: Record<string, unknown> | null;
    leadId: string | null;
  };
  position: { current: number; total: number };
  whyText: string;
};

export function ConversionCard({ decision, position, whyText }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const payload = decision.inputsPayload as { parsed?: ParsedShape; history?: HistoryShape; reply?: string; parseConfidence?: number };
  const initial = payload.parsed ?? {};
  const [outcome, setOutcome] = useState<Outcome>(initial.outcome ?? 'unclear');
  const [valueBand, setValueBand] = useState<ValueBand>(initial.valueBand ?? '<5k');
  const [installStatus, setInstall] = useState<InstallStatus>(initial.install ?? 'uncertain');
  const [attribution, setAttrib] = useState<Attribution>(initial.attribution ?? 'low');
  const [notes, setNotes] = useState('');
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const parseConfidence = payload.parseConfidence ?? 0;

  async function save() {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'conversion_registration',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      agentRecommendation: decision.agentRecommendation ?? undefined,
      reviewerDecision: { outcome, valueBand, install: installStatus, attribution, notes, source: 'operator_confirm' },
      agreement: (JSON.stringify({ outcome, valueBand, install: installStatus, attribution }) === JSON.stringify(initial) ? 'Y' : 'N') as 'Y' | 'N',
      leadId: decision.leadId ?? undefined,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    startTransition(() => router.refresh());
  }

  async function flagDispute() {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'conversion_registration',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      reviewerDecision: { action: 'dispute', notes },
      agreement: 'N' as const,
      leadId: decision.leadId ?? undefined,
    };
    await fetch('/api/decisions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    startTransition(() => router.refresh());
  }

  const shortcuts = useMemo(() => ({
    'S': () => {
      if (parseConfidence < 0.8 && !editing) { setEditing(true); return; }
      if (!confirming) { setConfirming(true); return; }
      save();
    },
    'E': () => setEditing(true),
    'F': () => flagDispute(),
    'Escape': () => { setEditing(false); setConfirming(false); router.push('/triage'); },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [parseConfidence, editing, confirming, outcome, valueBand, installStatus, attribution, notes]);
  useKeyboardShortcuts(shortcuts, { allowInInputs: true });

  const h = payload.history;

  return (
    <CardShell
      workflowLabel="Conversion-reg"
      position={position}
      urgency="on-pace"
      whyText={whyText}
      helpEntries={[
        { key: 'S', label: 'Save (are-you-sure first)' },
        { key: 'E', label: 'Edit fields' },
        { key: 'F', label: 'Flag dispute' },
      ]}
      actions={[
        { key: 'S', label: confirming ? 'Confirm save?' : 'Save', onClick: save },
        { key: 'E', label: 'Edit', onClick: () => setEditing(true) },
        { key: 'F', label: 'Flag dispute', onClick: flagDispute },
      ]}
    >
      <section className="mb-4">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Lead history</h2>
        <div className="text-xs text-zinc-400">
          {h?.leadId} &bull; delivered {h?.deliveredAt} to {h?.installer}<br />
          Follow-up email sent {h?.followupAt} &middot; Installer responded {h?.repliedAt}
        </div>
      </section>
      <section className="mb-4">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Installer&apos;s reply</h2>
        <p className="text-sm text-zinc-300">{payload.reply}</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent&apos;s parsed fields (parse confidence {(parseConfidence * 100).toFixed(0)}%)</h2>
        <div className="space-y-2 text-sm">
          <div>Outcome: {OUTCOMES.map(o => (<label key={o} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="outcome" disabled={!editing} checked={outcome === o} onChange={() => setOutcome(o)} />{o}</label>))}</div>
          <div>Value band: {VALUE_BANDS.map(v => (<label key={v} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="v" disabled={!editing} checked={valueBand === v} onChange={() => setValueBand(v)} />&euro;{v}</label>))}</div>
          <div>Install: {INSTALLS.map(i => (<label key={i} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="i" disabled={!editing} checked={installStatus === i} onChange={() => setInstall(i)} />{i}</label>))}</div>
          <div>Attribution: {ATTRIBS.map(a => (<label key={a} className="inline-flex items-center gap-1 mr-3"><input type="radio" name="a" disabled={!editing} checked={attribution === a} onChange={() => setAttrib(a)} />{a}</label>))}</div>
          <div>Notes: <input type="text" value={notes} onChange={e => setNotes(e.target.value)} className="bg-zinc-950 border border-zinc-700 px-2 py-1 rounded text-sm w-2/3" /></div>
          {confirming && <div className="text-xs text-yellow-500">Confirm save? Press S again (dataset-defining, irreversible in UI).</div>}
        </div>
      </section>
    </CardShell>
  );
}
