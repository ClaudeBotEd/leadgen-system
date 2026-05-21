'use client';
import { useEffect, useState } from 'react';

const C: Record<string, string> = { green: 'bg-green-500', yellow: 'bg-yellow-500', orange: 'bg-orange-500', red: 'bg-red-500' };
type Status = 'green' | 'yellow' | 'orange' | 'red';

export function OperationalHeadroomWidget() {
  const [d, setD] = useState<{ pct: number; status: Status } | null>(null);
  useEffect(() => {
    fetch('/api/headroom').then(r => r.json()).then(setD).catch(() => setD(null));
  }, []);
  if (!d) return null;
  return (
    <div className="fixed top-2 right-2 bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-xs font-mono z-40">
      <span className={`inline-block w-2 h-2 rounded-full ${C[d.status]} mr-1`} />
      <span className="text-zinc-400">Headroom: {d.pct}%</span>
    </div>
  );
}
