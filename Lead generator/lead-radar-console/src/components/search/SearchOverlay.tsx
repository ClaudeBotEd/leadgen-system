'use client';
import { useState, useEffect, useRef, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';
import type { Match } from '@/lib/retrieval';

export function SearchOverlay() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const [matches, setMatches] = useState<Match[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const shortcuts = useMemo(() => ({
    '/': () => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50); },
    'Escape': () => { if (open) setOpen(false); },
    'Enter': () => {
      if (open && matches[selectedIdx]) {
        router.push(`/l/${matches[selectedIdx].leadId}`);
        setOpen(false);
      }
    },
    'ArrowDown': () => { if (open) setSelectedIdx(i => Math.min(matches.length - 1, i + 1)); },
    'ArrowUp': () => { if (open) setSelectedIdx(i => Math.max(0, i - 1)); },
  }), [open, matches, selectedIdx, router]);
  useKeyboardShortcuts(shortcuts, { allowInInputs: true });

  useEffect(() => {
    if (!q.trim()) { setMatches([]); return; }
    const id = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()).then(d => setMatches(d.matches));
    }, 200);
    return () => clearTimeout(id);
  }, [q]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-start justify-center pt-32" onClick={() => setOpen(false)}>
      <div className="bg-zinc-900 border border-zinc-700 rounded w-full max-w-xl font-mono text-sm" onClick={e => e.stopPropagation()}>
        <input
          ref={inputRef}
          placeholder="Search..."
          value={q}
          onChange={e => setQ(e.target.value)}
          className="w-full px-3 py-3 bg-zinc-900 border-b border-zinc-700 outline-none"
        />
        <ul>
          {matches.map((m, i) => (
            <li
              key={m.leadId}
              className={`px-3 py-2 cursor-pointer ${i === selectedIdx ? 'bg-zinc-800' : ''}`}
              onClick={() => { router.push(`/l/${m.leadId}`); setOpen(false); }}
            >
              <div className="text-zinc-100">{m.leadId}</div>
              <div className="text-xs text-zinc-500">{m.preview}</div>
            </li>
          ))}
        </ul>
        <div className="px-3 py-2 text-xs text-zinc-500 border-t border-zinc-800">[Enter] open · [Esc] cancel · ↑/↓ navigate</div>
      </div>
    </div>
  );
}
