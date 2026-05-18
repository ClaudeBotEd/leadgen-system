const LABEL: Record<string, Record<string, string>> = {
  regionalFit: {
    strong: 'Strong regional fit',
    moderate: 'Moderate regional fit',
    distance_limit: 'Distance limit',
    out_of_region: 'Out of region',
  },
  conversionHistory: {
    high: 'High conversion history',
    solid: 'Solid conversion history',
    limited: 'Limited conversion history',
    no_history: 'No history yet',
  },
  capacity: {
    open: 'Open capacity',
    tight: 'Tight capacity',
    limited: 'Limited capacity',
    closed: 'Closed',
  },
  nicheMatch: {
    'hybrid-specialized': 'Hybrid-specialized',
    generalist: 'Generalist',
    'off-niche': 'Off-niche',
  },
  responseHistory: {
    very_responsive: 'Very responsive',
    responsive: 'Responsive',
    slow: 'Slow',
    unresponsive: 'Unresponsive',
  },
};

type InstallerProps = {
  installer: {
    name: string;
    regionalFit: string;
    conversionHistory: string;
    capacity: string;
    nicheMatch: string;
    responseHistory: string;
    distanceKm: number;
  };
  primary?: boolean;
};

export function InstallerRecommendation({ installer, primary }: InstallerProps) {
  return (
    <div className={primary ? 'p-3 border border-zinc-700 rounded mb-3' : 'p-3 mb-2 text-sm text-zinc-400'}>
      <div className="flex items-baseline gap-3">
        <span>{primary ? '▸' : '◯'}</span>
        <span className={primary ? 'font-bold text-zinc-100' : ''}>{installer.name}</span>
        <span className="text-xs text-zinc-500">
          {LABEL.regionalFit[installer.regionalFit] ?? installer.regionalFit} &bull; {installer.distanceKm} km
        </span>
      </div>
      <ul className="text-xs text-zinc-500 mt-1 ml-4 list-disc list-inside">
        <li>
          {LABEL.conversionHistory[installer.conversionHistory] ?? installer.conversionHistory}
          {' · '}
          {LABEL.capacity[installer.capacity] ?? installer.capacity}
        </li>
        <li>
          {LABEL.nicheMatch[installer.nicheMatch] ?? installer.nicheMatch}
          {' · '}
          {LABEL.responseHistory[installer.responseHistory] ?? installer.responseHistory}
        </li>
      </ul>
    </div>
  );
}
