'use client';
import { useEffect } from 'react';

type Handler = (e: KeyboardEvent) => void | Promise<void>;

export function useKeyboardShortcuts(
  shortcuts: Record<string, Handler>,
  options: { allowInInputs?: boolean } = {},
) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const tag = target.tagName?.toLowerCase();
      const inInput = tag === 'input' || tag === 'textarea' || target.isContentEditable;
      if (!options.allowInInputs && inInput && e.key !== 'Escape') return;
      const key = (e.shiftKey ? 'shift+' : '') + (e.key.length === 1 ? e.key.toUpperCase() : e.key);
      const handler = shortcuts[key];
      if (handler) { e.preventDefault(); handler(e); }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [shortcuts, options.allowInInputs]);
}
