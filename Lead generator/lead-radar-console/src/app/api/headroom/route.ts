import { NextResponse } from 'next/server';
import { computeHeadroom } from '@/lib/headroom/calculator';
import { requireCurrentOperator } from '@/lib/db/operators';

export async function GET() {
  await requireCurrentOperator();
  return NextResponse.json(await computeHeadroom());
}
