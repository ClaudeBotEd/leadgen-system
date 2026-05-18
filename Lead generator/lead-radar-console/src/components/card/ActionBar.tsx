type Action = { key: string; label: string; onClick: () => void; disabled?: boolean };

export function ActionBar({ actions }: { actions: Action[] }) {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-t border-zinc-900 text-sm">
      {actions.map(a => (
        <button
          key={a.key}
          onClick={a.onClick}
          disabled={a.disabled}
          className="px-3 py-1 border border-zinc-700 rounded hover:bg-zinc-800 disabled:opacity-30"
        >
          <span className="text-zinc-400">[{a.key}]</span>
          <span className="ml-1">{a.label}</span>
        </button>
      ))}
    </div>
  );
}
