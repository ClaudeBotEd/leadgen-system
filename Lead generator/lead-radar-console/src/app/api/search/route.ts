import { NextResponse } from 'next/server';
import { retrieve, type RetrievalMode } from '@/lib/retrieval';
import { requireCurrentOperator } from '@/lib/db/operators';

export async function GET(req: Request) {
  await requireCurrentOperator();
  const u = new URL(req.url);
  const q = u.searchParams.get('q') ?? '';
  const mode = (u.searchParams.get('mode') ?? 'text') as RetrievalMode;
  return NextResponse.json({ matches: await retrieve(q, mode) });
}
