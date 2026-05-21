import Link from 'next/link';

type Props = { label: string; count: number; killed: boolean; href: string; hotkey: '1'|'2'|'3' };

export function WorkflowBlock({ label, count, killed, href, hotkey }: Props) {
  return (
    <Link href={href} className={`block p-6 border rounded ${killed ? 'border-red-700 bg-red-950/30' : 'border-zinc-800 hover:border-zinc-700'}`}>
      <div className="text-zinc-500 text-xs uppercase tracking-wider mb-2">{label}</div>
      <div className="text-3xl mb-2">{killed ? <span className="text-red-500">paused</span> : count}</div>
      <div className="text-xs text-zinc-500">[{hotkey}] enter →</div>
    </Link>
  );
}
