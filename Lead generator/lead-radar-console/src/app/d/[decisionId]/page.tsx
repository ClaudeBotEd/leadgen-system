import { redirect, notFound } from 'next/navigation';
import { auth } from '@/../auth';
import { db } from '@/lib/db/client';
import { decisions } from '@/lib/db/schema';
import { eq } from 'drizzle-orm';
import Link from 'next/link';

export default async function DecisionPage({
  params,
  searchParams,
}: {
  params: Promise<{ decisionId: string }>;
  searchParams: Promise<{ return_to?: string }>;
}) {
  const session = await auth();
  if (!session) redirect('/login');

  const { decisionId } = await params;
  const { return_to } = await searchParams;

  const d = await db.query.decisions.findFirst({
    where: eq(decisions.decisionId, decisionId),
  });

  if (!d) notFound();

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 font-mono p-8">
      <div className="max-w-3xl mx-auto">
        <Link
          href={return_to ? `/${return_to}` : '/triage'}
          className="text-xs text-zinc-500 underline"
        >
          ← back
        </Link>
        <h2 className="text-lg mt-4">Decision {decisionId}</h2>
        <pre className="text-xs mt-4 p-4 bg-zinc-900 border border-zinc-800 rounded overflow-auto">
          {JSON.stringify(d, null, 2)}
        </pre>
      </div>
    </main>
  );
}
