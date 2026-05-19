'use client';
import { useState } from 'react';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

export function KeyboardHelp({ entries }: { entries: { key: string; label: string }[] }) {
  const [open, setOpen] = useState(false);
  useKeyboardShortcuts({
    '?': () => setOpen(o => !o),
    'Escape': () => { if (open) setOpen(false); },
  }, { allowInInputs: true });
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center"
      onClick={() => setOpen(false)}
    >
      <div
        className="bg-zinc-900 border border-zinc-700 rounded p-6 max-w-md font-mono text-sm"
        onClick={e => e.stopPropagation()}
      >
        <h2 className="text-lg mb-4">Keyboard shortcuts</h2>
        <ul className="space-y-1">
          {entries.map(e => (
            <li key={e.key} className="flex justify-between gap-8">
              <span className="text-zinc-400">{e.key}</span>
              <span>{e.label}</span>
            </li>
          ))}
        </ul>
        <p className="text-xs text-zinc-500 mt-4">Esc to close</p>
      </div>
    </div>
  );
}
