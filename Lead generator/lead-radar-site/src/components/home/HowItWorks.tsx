import { ButtonLink } from "@/components/ui/Button";
import { Reveal } from "@/components/ui/Reveal";
import { SectionLabel } from "@/components/ui/SectionLabel";

const steps = [
  {
    prefix: "01",
    operation: "INGEST",
    title: "Wij scrapen publieke intent.",
    body:
      "We monitoren forums, communities en open social platforms waar mensen vragen stellen over warmtepompen en airco. Alleen publiek, niets achter login.",
    meta: "11 bronnen · scan 4u",
  },
  {
    prefix: "02",
    operation: "CLASSIFY",
    title: "Wij classificeren op HOT of WARM.",
    body:
      "Elke post wordt door een taalmodel beoordeeld op intent, urgentie en regio. Alleen leads boven de drempel gaan eruit.",
    // Doctrine §02.2 + A8: bands, never numbers. Threshold expressed
    // qualitatively rather than as a numeric cutoff.
    meta: "v2.4 · drempel boven WARM",
  },
  {
    prefix: "03",
    operation: "DELIVER",
    title: "Jij ontvangt de lead exclusief.",
    body:
      "Eén lead is één installateur. Met bron-URL, samenvatting, regio, en een voorgestelde route naar contact.",
    meta: "exclusief · 1 koper",
  },
];

export function HowItWorks() {
  return (
    <section className="container-site mt-16 md:mt-gap-section">
      <Reveal>
        <SectionLabel number="01">METHODE</SectionLabel>
      </Reveal>

      <div className="mt-6 grid grid-cols-1 gap-y-4 md:grid-cols-12 md:items-end md:gap-x-10">
        <Reveal className="md:col-span-7">
          <h2 className="display-md text-ink">Hoe het werkt</h2>
        </Reveal>
        <Reveal className="md:col-span-5" delay={120}>
          <p className="body-lg text-ink-soft md:text-right">
            Drie stappen. Geen platform, geen biedoorlog.
          </p>
        </Reveal>
      </div>

      <div className="mt-12 grid grid-cols-1 gap-12 md:mt-16 md:grid-cols-3 md:gap-16 lg:gap-24">
        {steps.map((step, index) => (
          <Reveal delay={120 + index * 120} key={step.prefix}>
            <article className="relative">
              <div aria-hidden="true" className="h-px w-full bg-rule" />
              <div className="mt-4 flex items-center justify-between">
                <span className="mono-sm text-signal">{step.prefix}</span>
                <span className="mono-sm text-ink-mute">{step.operation}</span>
              </div>
              <h3 className="display-sm mt-4 text-ink">{step.title}</h3>
              <p className="body mt-4 max-w-[340px] text-ink-soft">
                {step.body}
              </p>
              <div className="mono-sm mt-5 text-ink-mute">↳ {step.meta}</div>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal delay={500}>
        <div className="mt-12 flex justify-end md:mt-16">
          <ButtonLink href="/zo-werkt-het" variant="quiet">
            → Lees de volledige methodologie
          </ButtonLink>
        </div>
      </Reveal>
    </section>
  );
}
