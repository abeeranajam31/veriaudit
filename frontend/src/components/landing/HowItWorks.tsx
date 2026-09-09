import { Container } from "../ui/Container";
import { SectionHeading } from "../ui/SectionHeading";

const steps = [
  {
    n: "01",
    title: "Define Intent",
    body: "Start with an intent-level test case — a single underlying request, independent of language.",
  },
  {
    n: "02",
    title: "Generate Variants",
    body: "Create semantically equivalent English, Urdu, Roman Urdu, and code-switched variants via EquivEngine.",
  },
  {
    n: "03",
    title: "Evaluate",
    body: "Run configured models against each variant and record structured behavioral outcomes.",
  },
  {
    n: "04",
    title: "Measure the Gap",
    body: "Compare safety behavior across linguistic variants and compute the Cross-Lingual Safety Gap.",
  },
];

export function HowItWorks() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <SectionHeading
          eyebrow="How VERIAUDIT works"
          title="A reproducible four-step evaluation pipeline"
          description="TEST → COMPARE → SCORE → ANALYZE → REPORT."
        />

        <div className="mt-14 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-4">
          {steps.map((s) => (
            <div key={s.n} className="bg-bg-raised p-6">
              <div className="font-mono text-xs text-ink-faint">{s.n}</div>
              <h3 className="mt-3 text-base font-semibold text-ink">{s.title}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-muted">{s.body}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-2 font-mono text-xs text-ink-faint">
          {["INTENT", "LINGUISTIC VARIANTS", "MODEL EVALUATION", "SAFETY SCORES", "CROSS-LINGUAL SAFETY GAP"].map(
            (t, i, arr) => (
              <span key={t} className="flex items-center gap-2">
                <span className="rounded-full border border-border-strong px-3 py-1">{t}</span>
                {i < arr.length - 1 && <span>→</span>}
              </span>
            )
          )}
        </div>
      </Container>
    </section>
  );
}
