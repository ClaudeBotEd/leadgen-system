'use client';
import { useRouter } from 'next/navigation';
import { useTransition, useState, useMemo } from 'react';
import { CardShell } from '@/components/card/CardShell';
import { InstallerRecommendation } from './InstallerRecommendation';
import { OverrideInlineForm } from '@/components/override/OverrideInlineForm';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';
import { AuditChainView } from '@/components/audit/AuditChainView';

type InstallerShape = {
  name: string;
  regionalFit: string;
  conversionHistory: string;
  capacity: string;
  nicheMatch: string;
  responseHistory: string;
  distanceKm: number;
};

type AgentRec = {
  primary?: InstallerShape;
  alternatives?: InstallerShape[];
};

type LeadShape = {
  score?: number;
  band?: string;
  source?: string;
  ageHours?: number;
  niche?: string;
  geo?: { region?: string; city?: string; postcode?: string };
  postText?: string;
};

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
  total: number;
  categories: { categoryKey: string; displayLabel: string }[];
};

export function RoutingCard({ decision, position, whyText, categories }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [pickAltOpen, setPickAltOpen] = useState(false);
  const [pickedAltIdx, setPickedAltIdx] = useState(0);
  const [auditOpen, setAuditOpen] = useState(false);

  const lead = (decision.inputsPayload as Record<string, unknown>).lead as LeadShape | undefined;
  const rec = decision.agentRecommendation as AgentRec | null;
  const primary = rec?.primary;
  const alts = rec?.alternatives ?? [];

  async function submit(action: 'approve' | 'hold' | 'next', pickedInstaller?: string) {
    const t0 = Date.now();
    if (action === 'next') {
      startTransition(() => router.refresh());
      return;
    }
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'lead_delivery_routing',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      agentRecommendation: rec ?? undefined,
      reviewerDecision: { installer: pickedInstaller ?? primary?.name, action },
      agreement: (pickedInstaller && pickedInstaller !== primary?.name ? 'N' : 'Y') as 'Y' | 'N',
      timeToDecideMs: Date.now() - t0,
      leadId: decision.leadId ?? undefined,
    };
    await fetch('/api/decisions', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    startTransition(() => router.refresh());
  }

  async function submitOverride(categoryKey: string, reason: string) {
    const body = {
      decisionId: decision.decisionId,
      workflowId: 'lead_delivery_routing',
      profileVersion: 1,
      tierAtDecision: 'T1',
      inputsHash: decision.inputsHash ?? 'unknown',
      inputsPayload: decision.inputsPayload,
      agentRecommendation: rec ?? undefined,
      reviewerDecision: { action: 'override' },
      agreement: 'N' as const,
      overrideCategory: categoryKey,
      overrideReason: reason,
      leadId: decision.leadId ?? undefined,
    };
    await fetch('/api/decisions', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    setOverrideOpen(false);
    startTransition(() => router.refresh());
  }

  async function submitPickAlt() {
    const alt = alts[pickedAltIdx];
    if (!alt) return;
    await submit('approve', alt.name);
    setPickAltOpen(false);
    setPickedAltIdx(0);
  }

  const shortcuts = useMemo(() => ({
    'A': () => { void submit('approve'); },
    'P': () => setPickAltOpen(true),
    'O': () => setOverrideOpen(true),
    'H': () => { void submit('hold'); },
    'N': () => { void submit('next'); },
    'V': () => setAuditOpen(true),
    '1': () => { if (pickAltOpen) setPickedAltIdx(0); },
    '2': () => { if (pickAltOpen) setPickedAltIdx(1); },
    'Enter': () => { if (pickAltOpen) { void submitPickAlt(); } },
    'Escape': () => {
      if (auditOpen) { setAuditOpen(false); return; }
      if (overrideOpen) { setOverrideOpen(false); return; }
      if (pickAltOpen) { setPickAltOpen(false); return; }
      router.push('/triage');
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [auditOpen, overrideOpen, pickAltOpen, pickedAltIdx]);

  useKeyboardShortcuts(shortcuts);

  return (
    <CardShell
      workflowLabel="Routing"
      position={position}
      urgency="on-pace"
      whyText={whyText}
      helpEntries={[
        { key: 'A', label: 'Approve & route' },
        { key: 'P', label: 'Pick alternative installer' },
        { key: 'O', label: 'Override' },
        { key: 'H', label: 'Hold' },
        { key: 'N', label: 'Next without action' },
        { key: 'V', label: 'View audit chain' },
        { key: 'Esc', label: auditOpen ? 'Close audit' : overrideOpen ? 'Close override' : pickAltOpen ? 'Close picker' : 'Back to triage' },
      ]}
      actions={[
        { key: 'A', label: 'Approve & route', onClick: () => { void submit('approve'); } },
        { key: 'P', label: 'Pick alt', onClick: () => setPickAltOpen(true) },
        { key: 'O', label: 'Override', onClick: () => setOverrideOpen(true) },
        { key: 'H', label: 'Hold', onClick: () => { void submit('hold'); } },
        { key: 'N', label: 'Next', onClick: () => { void submit('next'); } },
        { key: 'V', label: 'View audit', onClick: () => setAuditOpen(true) },
      ]}
    >
      <section className="mb-6">
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Lead</h2>
        <div className="text-sm">
          <span className="text-yellow-500">{lead?.band}</span>
          <span className="text-zinc-400">{' '}(score {lead?.score}) &bull; {lead?.source} &bull; {lead?.ageHours}u oud</span>
        </div>
        <div className="text-xs text-zinc-500 mt-1">
          Niche: {lead?.niche} &bull; Geo: {lead?.geo?.region} / {lead?.geo?.city} ({lead?.geo?.postcode})
        </div>
        <p className="text-sm mt-3 text-zinc-300">&quot;{lead?.postText}&quot;</p>
      </section>
      <section>
        <h2 className="text-xs uppercase text-zinc-500 mb-2">Agent recommends</h2>
        {primary && <InstallerRecommendation installer={primary} primary />}
        <h3 className="text-xs text-zinc-500 mb-1">Alternatives:</h3>
        {alts.map((a) => <InstallerRecommendation key={a.name} installer={a} />)}
      </section>
      {pickAltOpen && (
        <div className="mt-4 p-4 border border-zinc-700 rounded bg-zinc-900">
          <div className="text-xs text-zinc-500 mb-2">Pick alternative:</div>
          {alts.map((a: InstallerShape, i: number) => (
            <label key={a.name} className="flex items-center gap-2 mb-1 cursor-pointer">
              <input type="radio" name="alt" checked={pickedAltIdx === i} onChange={() => setPickedAltIdx(i)} />
              <span className="text-zinc-400">[{i + 1}]</span>
              <span>{a.name}</span>
            </label>
          ))}
          <div className="text-xs text-zinc-500 mt-2">[Enter] confirm · [Esc] cancel</div>
        </div>
      )}
      {overrideOpen && (
        <OverrideInlineForm
          categories={categories}
          onSubmit={(key, reason) => { void submitOverride(key, reason); }}
          onCancel={() => setOverrideOpen(false)}
        />
      )}
      {auditOpen && decision.leadId && (
        <AuditChainView
          leadId={decision.leadId}
          onClose={() => setAuditOpen(false)}
        />
      )}
    </CardShell>
  );
}
