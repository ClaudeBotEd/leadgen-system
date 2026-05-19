import type { Lead } from "@/content/leads";
import { nicheLabels, sourceMonograms, urgencyLabels } from "@/content/leads";

type LeadCardProps = {
  lead: Lead;
  clampSnippet?: boolean;
};

// Doctrine §02.2 + A8: bands, never numbers. Thresholds mirror
// consumer/__init__.py:intent_from_score (>=70 HOT, 40-69 WARM, <40 OPP).
// `lead.band` is not yet in the data model; derive client-side until a
// separate sprint migrates the data layer.
type Band = "HOT" | "WARM" | "OPP";
function bandFromScore(score: number): Band {
  if (score >= 70) return "HOT";
  if (score >= 40) return "WARM";
  return "OPP";
}

export function LeadCard({ lead, clampSnippet = true }: LeadCardProps) {
  const monogram = sourceMonograms[lead.sourceType];
  const band = bandFromScore(lead.score);

  return (
    <article
      className="relative overflow-hidden rounded-xl border border-rule bg-paper-elevated shadow-[0_1px_0_rgba(10,10,10,0.02),0_0_0_1px_rgba(10,10,10,0.015)]"
      data-lead-id={lead.id}
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rule px-6 py-4 md:px-8">
        <div className="flex items-center gap-3">
          <span className="mono-sm inline-flex items-center rounded-sm bg-signal-bright px-1.5 py-[3px] tracking-[0.06em] text-ink">
            {lead.status}
          </span>
          <span className="mono-sm text-ink-mute">
            LEAD #{lead.id.toUpperCase()}
          </span>
        </div>
        <span className="mono-sm text-ink-mute">
          {lead.country} · {lead.city} · {lead.displayDate}
        </span>
      </header>

      <div className="px-6 py-6 md:px-8 md:py-7">
        <dl className="grid grid-cols-[92px_1fr] gap-x-6 gap-y-3 md:grid-cols-[108px_1fr]">
          <dt className="mono-sm pt-[3px] text-ink-mute">DETECTIE</dt>
          <dd className="text-[15px] leading-[1.5] text-ink">
            {lead.detectedAt}
          </dd>

          <dt className="mono-sm pt-[3px] text-ink-mute">SCANNER</dt>
          <dd className="mono-md text-ink-soft">{lead.scannerVersion}</dd>

          <dt className="mono-sm pt-[3px] text-ink-mute">BRON</dt>
          <dd className="flex items-center gap-2 text-[15px] leading-[1.5] text-ink">
            <span
              aria-hidden="true"
              className="mono-sm inline-flex size-6 shrink-0 items-center justify-center rounded-sm border border-rule bg-paper text-[10px] tracking-[0.04em] text-ink-soft"
            >
              {monogram}
            </span>
            <span>{lead.sourceLabel}</span>
          </dd>

          <dt className="mono-sm pt-[3px] text-ink-mute">CATEGORIE</dt>
          <dd className="text-[15px] leading-[1.5] text-ink-soft">
            {nicheLabels[lead.niche]}
          </dd>
        </dl>
      </div>

      <div className="border-t border-rule px-6 py-6 md:px-8 md:py-7">
        <div className="mono-sm mb-3 text-ink-mute">FRAGMENT</div>
        <blockquote
          className={`text-[18px] leading-[1.55] text-ink ${
            clampSnippet ? "line-clamp-3" : ""
          }`}
        >
          <span aria-hidden="true">“</span>
          {lead.snippet}
          <span aria-hidden="true">”</span>
        </blockquote>
      </div>

      <div className="border-t border-rule px-6 py-6 md:px-8 md:py-7">
        <dl className="grid grid-cols-[92px_1fr] gap-x-6 gap-y-3 md:grid-cols-[108px_1fr]">
          <dt className="mono-sm pt-[3px] text-ink-mute">INTENT</dt>
          <dd className="text-[15px] font-medium leading-[1.5] text-ink">
            {lead.signal}
          </dd>

          {lead.context ? (
            <>
              <dt className="mono-sm pt-[3px] text-ink-mute">CONTEXT</dt>
              <dd className="text-[15px] leading-[1.5] text-ink-soft">
                {lead.context}
              </dd>
            </>
          ) : null}

          {lead.route ? (
            <>
              <dt className="mono-sm pt-[3px] text-ink-mute">ROUTE</dt>
              <dd className="text-[15px] leading-[1.5] text-ink-soft">
                {lead.route}
              </dd>
            </>
          ) : null}

          <dt className="mono-sm pt-[3px] text-ink-mute">URGENTIE</dt>
          <dd>
            <UrgencyPill urgency={lead.urgency} />
          </dd>

          <dt className="mono-sm pt-[3px] text-ink-mute">EXTRACTIE</dt>
          <dd className="flex flex-wrap gap-1.5">
            {lead.extractionTags.map((tag) => (
              <span
                key={tag}
                className="mono-sm inline-flex items-center rounded-sm border border-rule bg-paper px-1.5 py-[2px] tracking-[0.04em] text-ink-soft"
              >
                {tag}
              </span>
            ))}
          </dd>
        </dl>
      </div>

      {/*
        Doctrine §02.2 + A8: bands, never numbers. The numerical SCORE
        (`{lead.score}/100`) and CONFIDENCE percentage/bar have been
        removed — they encourage A19 rubber-stamping by anchoring
        reviewer cognition to model output. Band glyph is the only
        summary surface.
      */}
      <div className="border-t border-rule px-6 py-6 md:px-8 md:py-7">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="mono-sm text-ink-mute">BAND</div>
            <div className="mt-1">
              <BandPill band={band} />
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-rule bg-paper px-6 py-4 md:px-8">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1">
            <ModerationItem label="publieke bron" />
            <ModerationItem label="AVG-conform" />
            <ModerationItem label="identiteit beschermd" />
          </div>
          <span className="mono-sm text-ink-mute">
            EXCLUSIEF · ███████ · {lead.deliveredOn}
          </span>
        </div>
      </div>
    </article>
  );
}

function BandPill({ band }: { band: Band }) {
  // HOT  → solid pill, single accent (ink on paper, like UrgencyPill acute)
  // WARM → outlined pill, same accent
  // OPP  → muted pill, gray
  const styles: Record<Band, string> = {
    HOT: "border-ink/20 bg-ink text-paper",
    WARM: "border-ink/40 bg-paper text-ink",
    OPP: "border-rule bg-paper text-ink-mute",
  };
  return (
    <span
      data-band={band}
      className={`mono-sm inline-flex items-center gap-1.5 rounded-sm border px-2 py-[3px] tracking-[0.06em] ${styles[band]}`}
    >
      {band}
    </span>
  );
}

function UrgencyPill({ urgency }: { urgency: Lead["urgency"] }) {
  const isAcute = urgency === "acute";
  return (
    <span
      className={`mono-sm inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-[2px] tracking-[0.04em] ${
        isAcute
          ? "border-ink/20 bg-ink text-paper"
          : "border-rule bg-paper text-ink-soft"
      }`}
    >
      {isAcute ? (
        <span
          aria-hidden="true"
          className="pulse-dot inline-block size-[5px] rounded-full bg-signal-bright"
        />
      ) : null}
      {urgencyLabels[urgency]}
    </span>
  );
}

function ModerationItem({ label }: { label: string }) {
  return (
    <span className="mono-sm inline-flex items-center gap-1.5 text-ink-soft">
      <svg
        aria-hidden="true"
        viewBox="0 0 12 12"
        className="size-3 text-signal-active"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M2.5 6.5 5 9l4.5-5" />
      </svg>
      <span>{label}</span>
    </span>
  );
}
