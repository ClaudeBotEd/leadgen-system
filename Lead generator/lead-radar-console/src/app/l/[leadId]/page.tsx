import { redirect } from 'next/navigation';
import { auth } from '@/../auth';
import { LeadAuditClient } from './LeadAuditClient';

export default async function LeadAuditPage({ params }: { params: Promise<{ leadId: string }> }) {
  const session = await auth();
  if (!session) redirect('/login');
  const { leadId } = await params;
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <LeadAuditClient leadId={leadId} />
      </div>
    </main>
  );
}
