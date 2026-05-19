import { Reveal } from "@/components/ui/Reveal";
import { getLiveSignal } from "@/lib/signal";

export function LiveSignalStrip() {
  const signal = getLiveSignal();
  const sourcePct = Math.round((signal.activeSources / signal.totalSources) * 100);
  // Doctrine §02.2 + A8: bands, never numbers. Capacity is shown as a
  // qualitative phrase rather than a percentage.
  const capLabel =
    sourcePct >= 80
      ? "voldoende capaciteit"
      : sourcePct >= 50
        ? "gemiddelde capaciteit"
        : "weinig capaciteit";

  const cells = [
    {
      label: "STATUS",
      value: (
        <span className="flex items-center gap-2 text-ink">
          <span
            aria-hidden="true"
            className="pulse-dot inline-block size-[6px] rounded-full bg-signal-bright"
          />
          <span>scanning</span>
        </span>
      ),
      meta: `bron ${signal.activeSources}/${signal.totalSources}`,
    },
    {
      label: "POSTS · 24h",
      value: <span className="tabular-nums text-ink">{signal.scannedPosts}</span>,
      meta: signal.countries,
    },
    {
      label: "HOT",
      value: <span className="tabular-nums text-ink">{signal.hotLeads}</span>,
      meta: `${signal.warmLeads} warm`,
    },
    {
      label: "GELEVERD",
      value: (
        <span className="tabular-nums text-ink">{signal.delivered} vandaag</span>
      ),
      meta: capLabel,
    },
  ];

  return (
    <section className="container-site mt-10 md:mt-12">
      <Reveal delay={420}>
        <div className="overflow-hidden rounded-lg border border-rule bg-paper-elevated">
          <div className="grid grid-cols-2 sm:grid-cols-4 sm:divide-x sm:divide-rule">
            {cells.map((cell, index) => (
              <div
                className={`flex flex-col gap-1 px-5 py-4 ${
                  index >= 2 ? "border-t border-rule sm:border-t-0" : ""
                } ${index % 2 === 1 ? "border-l border-rule sm:border-l-0" : ""}`}
                key={cell.label}
              >
                <span className="mono-sm text-ink-mute">{cell.label}</span>
                <span className="text-[15px] font-medium leading-[1.3] tracking-[-0.005em]">
                  {cell.value}
                </span>
                <span className="mono-sm text-ink-mute">{cell.meta}</span>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  );
}
