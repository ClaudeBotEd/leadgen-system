'use client';
import { useState, useRef, useEffect, useMemo } from 'react';
import { useKeyboardShortcuts } from '@/lib/keyboard/useKeyboardShortcuts';

type Category = { categoryKey: string; displayLabel: string };
type Props = { categories: Category[]; onSubmit: (key: string, reason: string) => void | Promise<void>; onCancel: () => void; };

export function OverrideInlineForm({ categories, onSubmit, onCancel }: Props) {
  const [picked, setPicked] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (picked) inputRef.current?.focus(); }, [picked]);

  const shortcuts = useMemo(() => {
    const map: Record<string, () => void> = {
      'Escape': () => onCancel(),
      'Enter': () => { if (picked && reason.trim().length > 0) onSubmit(picked, reason.trim()); },
    };
    categories.slice(0, 5).forEach((c, i) => { map[String(i + 1)] = () => setPicked(c.categoryKey); });
    return map;
  }, [categories, picked, reason, onSubmit, onCancel]);
  useKeyboardShortcuts(shortcuts, { allowInInputs: true });

  return (
    <div className="mt-4 p-4 border border-zinc-700 rounded bg-zinc-900">
      <div className="text-xs text-zinc-500 mb-3">Override</div>
      <div className="mb-3">
        <div className="text-xs text-zinc-400 mb-1">Category:</div>
        <div className="flex gap-3 text-sm flex-wrap">
          {categories.slice(0, 5).map((c, i) => (
            <label key={c.categoryKey} className="flex items-center gap-1 cursor-pointer">
              <input type="radio" name="cat" checked={picked === c.categoryKey} onChange={() => setPicked(c.categoryKey)} />
              <span className="text-zinc-500">[{i + 1}]</span> {c.displayLabel}
            </label>
          ))}
        </div>
      </div>
      <div className="mb-3">
        <div className="text-xs text-zinc-400 mb-1">Reason:</div>
        <input ref={inputRef} type="text" maxLength={200} value={reason} onChange={e => setReason(e.target.value)}
          className="w-full px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-sm" placeholder="Brief reason..." />
      </div>
      <div className="text-xs text-zinc-500">[Enter] save &amp; next · [Esc] cancel</div>
    </div>
  );
}
