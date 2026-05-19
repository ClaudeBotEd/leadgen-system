type Props = {
  workflowLabel: string;
  position: { current: number; total: number };
  nextUp?: { workflow: string; band?: string; ageMin?: number };
  urgency: 'on-pace' | 'approaching' | 'past-sla';
};

const URG = {
  'on-pace': 'bg-green-500',
  'approaching': 'bg-yellow-500',
  'past-sla': 'bg-red-500',
};

export function TopStrip({ workflowLabel, position, nextUp, urgency }: Props) {
  return (
    <div className="flex items-center gap-3 text-xs text-zinc-500 px-4 py-2 border-b border-zinc-900">
      <span>{workflowLabel}</span><span>•</span>
      <span>{position.current} of {position.total}</span>
      {nextUp && (
        <>
          <span>•</span>
          <span>Next: {nextUp.workflow}{nextUp.band ? ` (${nextUp.band}, ${nextUp.ageMin}min)` : ''}</span>
        </>
      )}
      <span className="ml-auto flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${URG[urgency]}`} />
        <span>{urgency.replace('-', ' ')}</span>
      </span>
    </div>
  );
}
