import { sourceMonograms } from "@/content/leads";
import { getIntelligenceFeed, getLiveSignal } from "@/lib/signal";

export function IntelligencePanel() {
  const signal = getLiveSignal();
  const feed = getIntelligenceFeed();
  // Doctrine §02.2 + A8: bands, never numbers. Capacity ratio (was
  // shown as `${sourcePct}% capaciteit`) is now a qualitative phrase
  // and its visual bar has been removed.
  const sourcePct = Math.round((signal.activeSources / signal.totalSources) * 100);
  const capLabel =
    sourcePct >= 80
      ? "voldoende capaciteit"
      : sourcePct >= 50
        ? "gemiddelde capaciteit"
        : "weinig capaciteit";
  const maxScan = Math.max(...signal.regional.map((row) => row.scanned), 1);

  return (
    <aside
      aria-label="Detection feed"
      className="relative overflow-hidden rounded-xl border border-rule bg-paper-elevated shadow-[0_1px_0_rgba(10,10,10,0.02),0_0_0_1px_rgba(10,10,10,0.015)]"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.45] [background-image:linear-gradient(to_right,rgba(10,10,10,0.025)_1px,transparent_1px)] [background-size:48px_100%]"
      />

      <header className="relative flex items-center justify-between gap-3 border-b border-rule px-5 py-3">
        <div className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="pulse-dot inline-block size-[6px] rounded-full bg-signal-bright"
          />
          <span className="mono-sm text-ink">DETECTION FEED</span>
          <span className="mono-sm text-ink-mute">· LIVE</span>
        </div>
        <span className="mono-sm text-ink-mute">{signal.lastScanLabel}</span>
      </header>

      <div className="relative flex items-center justify-between gap-4 border-b border-rule px-5 py-3">
        <span className="mono-sm text-ink-soft">
          scanning · bron {signal.activeSources} / {signal.totalSources} actief
        </span>
        <span className="mono-sm text-ink-mute">{capLabel}</span>
      </div>

      <ol className="relative divide-y divide-rule">
        {feed.map((detection, index) => (
          <DetectionRow detection={detection} index={index} key={detection.id} />
        ))}
      </ol>

      <div className="relative border-t border-rule px-5 py-4">
        <div className="mono-sm flex items-center justify-between text-ink-mute">
          <span>REGIONALE ACTIVITEIT · 24h</span>
          <span>{signal.scannedPosts} posts</span>
        </div>
        <div className="mt-3 flex flex-col gap-2">
          {signal.regional.map((row) => {
            const pct = Math.round((row.scanned / maxScan) * 100);
            return (
              <div className="flex items-center gap-3" key={row.country}>
                <span className="mono-sm w-6 shrink-0 text-ink">
                  {row.country}
                </span>
                <div
                  aria-hidden="true"
                  className="relative h-[6px] flex-1 overflow-hidden rounded-full bg-paper-inset"
                >
                  <div
                    className="absolute inset-y-0 left-0 bg-ink"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="mono-sm w-12 shrink-0 text-right tabular-nums text-ink-soft">
                  {row.scanned}
                </span>
                <span className="mono-sm w-12 shrink-0 text-right tabular-nums text-ink-mute">
                  {row.hot} HOT
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <footer className="relative flex items-center justify-between border-t border-rule bg-paper px-5 py-3">
        <span className="mono-sm text-ink-mute">
          CLASSIFIER v2.4 · {signal.delivered} GELEVERD VANDAAG
        </span>
        <span className="mono-sm text-ink-mute">{signal.countries}</span>
      </footer>
    </aside>
  );
}

function DetectionRow({
  detection,
  index,
}: {
  detection: ReturnType<typeof getIntelligenceFeed>[number];
  index: number;
}) {
  const monogram = sourceMonograms[detection.sourceType];
  return (
    <li
      className="relative grid grid-cols-[44px_1fr_auto] items-center gap-3 px-5 py-3 detection-in"
      style={{ animationDelay: `${600 + index * 90}ms` }}
    >
      <span className="mono-sm text-ink-mute">{detection.timeLabel}</span>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {/* Doctrine §02.2 + A8: bands, never numbers. The numeric
              `{detection.score}/100` glyph has been removed; the band
              status pill is the only summary surface. */}
          <span
            className={`mono-sm inline-flex items-center rounded-sm px-1 py-[1px] tracking-[0.06em] ${
              detection.status === "HOT"
                ? "bg-signal-bright text-ink"
                : "border border-rule bg-paper text-ink-soft"
            }`}
          >
            {detection.status}
          </span>
          <span
            aria-hidden="true"
            className="mono-sm inline-flex size-[18px] shrink-0 items-center justify-center rounded-sm border border-rule bg-paper text-[9px] tracking-[0.04em] text-ink-soft"
          >
            {monogram}
          </span>
        </div>
        <div className="mt-1 truncate text-[13px] leading-[1.4] text-ink-soft">
          {detection.signal}
        </div>
      </div>
      <span className="mono-sm shrink-0 text-right text-ink-mute">
        {detection.country} · {detection.region}
      </span>
    </li>
  );
}
