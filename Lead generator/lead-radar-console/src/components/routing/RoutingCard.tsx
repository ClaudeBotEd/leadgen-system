'use client';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { CardShell } from '@/components/card/CardShell';
import { InstallerRecommendation } from './InstallerRecommendation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

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
};

export function RoutingCard({ decision, position, whyText }: Props) {
  const router = useRouter();
  const [, startTransition] = useTransition();

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

  useKeyboardShortcuts({
    'A': () => { void submit('approve'); },
    'H': () => { void submit('hold'); },
    'N': () => { void submit('next'); },
    'Escape': () => router.push('/triage'),
  });

  return (
    <CardShell
      workflowLabel="Routing"
      position={position}
      urgency="on-pace"
      whyText={whyText}
      helpEntries={[
        { key: 'A', label: 'Approve & route' },
        { key: 'H', label: 'Hold' },
        { key: 'N', label: 'Next without action' },
        { key: 'Esc', label: 'Back to triage' },
      ]}
      actions={[
        { key: 'A', label: 'Approve & route', onClick: () => { void submit('approve'); } },
        { key: 'H', label: 'Hold', onClick: () => { void submit('hold'); } },
        { key: 'N', label: 'Next', onClick: () => { void submit('next'); } },
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
    </CardShell>
  );
}
