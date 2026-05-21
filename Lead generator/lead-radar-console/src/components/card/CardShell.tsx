import type { ReactNode } from 'react';
import { TopStrip } from './TopStrip';
import { WhyString } from './WhyString';
import { ActionBar } from './ActionBar';
import { KeyboardHelp } from './KeyboardHelp';

type Action = { key: string; label: string; onClick: () => void; disabled?: boolean };

type Props = {
  workflowLabel: string;
  position: { current: number; total: number };
  nextUp?: { workflow: string; band?: string; ageMin?: number };
  urgency: 'on-pace' | 'approaching' | 'past-sla';
  whyText: string;
  clusterBanner?: string;
  children: ReactNode;
  actions: Action[];
  helpEntries: { key: string; label: string }[];
};

export function CardShell({
  workflowLabel,
  position,
  nextUp,
  urgency,
  whyText,
  clusterBanner,
  children,
  actions,
  helpEntries,
}: Props) {
  return (
    <article className="max-w-3xl mx-auto my-8 bg-zinc-950 border border-zinc-800 rounded">
      <TopStrip
        workflowLabel={workflowLabel}
        position={position}
        nextUp={nextUp}
        urgency={urgency}
      />
      <WhyString text={whyText} />
      {clusterBanner && (
        <div className="text-xs text-zinc-400 px-4 py-2 border-b border-zinc-900 bg-zinc-900/40">
          ⓘ {clusterBanner}
        </div>
      )}
      <div className="px-6 py-4">{children}</div>
      <ActionBar actions={actions} />
      <KeyboardHelp entries={helpEntries} />
    </article>
  );
}
