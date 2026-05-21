import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import { auth } from '@/../auth';
import { WorkflowBlock } from '@/components/triage/WorkflowBlock';
import { TriageKeyboard } from '@/components/triage/TriageKeyboard';

async function fetchTriage() {
  const cookie = (await headers()).get('cookie') ?? '';
  const res = await fetch(`${process.env.NEXTAUTH_URL}/api/triage`, { headers: { cookie }, cache: 'no-store' });
  return res.json();
}

export default async function TriagePage() {
  const session = await auth();
  if (!session) redirect('/login');
  const { counts, killed } = await fetchTriage();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <header className="flex justify-between items-baseline mb-12">
        <h1 className="text-lg">Lead Radar — Operator console</h1>
        <div className="text-zinc-500 text-sm">{session.user?.email}</div>
      </header>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <WorkflowBlock label="Routing" count={counts.routing} killed={killed.lead_delivery_routing} href="/q/lead_delivery_routing" hotkey="1" />
        <WorkflowBlock label="Classification" count={counts.classification} killed={killed.signal_classification_ambiguous_band} href="/q/signal_classification_ambiguous_band" hotkey="2" />
        <WorkflowBlock label="Conversions" count={counts.conversion} killed={killed.conversion_registration} href="/q/conversion_registration" hotkey="3" />
      </div>

      <footer className="text-xs text-zinc-600 border-t border-zinc-900 pt-4">
        [/] search · [K] kill-states · [V]iew recent audits
      </footer>
      <TriageKeyboard />
    </main>
  );
}
