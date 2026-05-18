import { redirect, notFound } from 'next/navigation';
import { auth } from '@/../auth';
import { getQueueItems } from '@/lib/db/decisions';
import { getActiveProfile } from '@/lib/db/workflow-profiles';
import { isWorkflowKilled } from '@/lib/db/kill-state';
import { whyString } from '@/lib/why-string/generator';
import { RoutingCard } from '@/components/routing/RoutingCard';
import { getActiveOverrideCategories } from '@/lib/db/override-categories';

const LABELS: Record<string, string> = {
  lead_delivery_routing: 'Routing',
  signal_classification_ambiguous_band: 'Classification',
  conversion_registration: 'Conversion',
};

export default async function QueuePage({ params }: { params: Promise<{ workflow: string }> }) {
  const session = await auth();
  if (!session) redirect('/login');
  const { workflow } = await params;
  if (!LABELS[workflow]) notFound();

  if (await isWorkflowKilled(workflow)) {
    return (
      <main className="p-8 text-zinc-100 bg-zinc-950 min-h-screen font-mono">
        <p>Workflow paused. <a href="/triage" className="underline">Back</a></p>
      </main>
    );
  }

  const items = await getQueueItems(workflow, 50);
  if (items.length === 0) {
    return (
      <main className="p-8 text-zinc-100 bg-zinc-950 min-h-screen font-mono">
        <p>Queue empty. <a href="/triage" className="underline">Back to triage</a></p>
      </main>
    );
  }

  const profile = await getActiveProfile(workflow);
  if (!profile) throw new Error(`No active profile for ${workflow}`);

  const rawCategories = await getActiveOverrideCategories();
  const categories = rawCategories.map(c => ({ categoryKey: c.categoryKey, displayLabel: c.displayLabel }));

  const current = items[0];
  const decisionForWhy = {
    tierAtDecision: current.tierAtDecision,
    inputsPayload: (current.inputsPayload as Record<string, unknown>) ?? {},
  };
  const profileForWhy = { profile: (profile.profile as Record<string, unknown>) ?? {} };
  const why = whyString(decisionForWhy, profileForWhy);

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono">
      {workflow === 'lead_delivery_routing' && (
        <RoutingCard
          decision={{
            decisionId: current.decisionId,
            inputsHash: current.inputsHash,
            inputsPayload: current.inputsPayload as Record<string, unknown>,
            agentRecommendation: current.agentRecommendation as Record<string, unknown> | null,
            leadId: current.leadId,
          }}
          position={{ current: 1, total: items.length }}
          whyText={why}
          total={items.length}
          categories={categories}
        />
      )}
      {workflow !== 'lead_delivery_routing' && (
        <div className="p-8">
          <p className="text-zinc-400">[{LABELS[workflow]}] queue rendering pending.</p>
          <a href="/triage" className="underline text-sm">Back to triage</a>
        </div>
      )}
    </main>
  );
}
