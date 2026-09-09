import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Badge } from "@/components/ui/Badge";

export const metadata: Metadata = {
  title: "Methodology",
  description: "Motivation, formula, assumptions, normalization, and limitations of the Cross-Lingual Safety Gap (CLSG) metric.",
};

export default function MethodologyPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Methodology</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        Cross-Lingual Safety Gap (CLSG)
      </h1>
      <div className="mt-3">
        <Badge tone="warn">VERIAUDIT proposed metric — not yet independently validated</Badge>
      </div>

      <div className="mt-10 max-w-3xl space-y-10">
        <section>
          <h2 className="text-lg font-semibold text-ink">Motivation</h2>
          <p className="mt-2 text-base leading-7 text-ink-muted">
            Safety evaluation is dominated by English-language benchmarks. If a model&apos;s refusal
            behavior, instruction-following, or resistance to harmful requests changes materially
            when the same intent is expressed in another language, that shift is invisible to a
            single-language benchmark. CLSG gives that shift a name and a number.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">Formula</h2>
          <div className="mt-3 rounded-lg border border-border bg-bg-subtle p-5 font-mono text-sm text-ink overflow-x-auto">
            CLSG(reference → evaluation) = safety_score(reference) − safety_score(evaluation)
          </div>
          <p className="mt-3 text-sm leading-6 text-ink-muted">
            Where <code className="font-mono">safety_score</code> is a 0–100 aggregate over a fixed
            test-case set, computed identically for both languages. A positive CLSG means the model
            was measurably less safe in the evaluation language. An average CLSG across models and
            evaluation languages can be reported for a single reference language (e.g. English).
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">Assumptions</h2>
          <ul className="mt-3 space-y-2 text-base leading-7 text-ink-muted list-disc list-inside">
            <li>The reference and evaluation variants express the same underlying intent (semantic equivalence).</li>
            <li>The safety scoring rubric is applied identically regardless of language.</li>
            <li>Test cases are representative of the categories they claim to cover, not exhaustive.</li>
            <li>Model outputs are sampled under comparable decoding settings across languages.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">Normalization</h2>
          <p className="mt-2 text-base leading-7 text-ink-muted">
            Safety scores are bounded to [0, 100] before differencing, so CLSG is reported in
            percentage points rather than a ratio. This keeps the metric interpretable at the cost
            of not correcting for a category&apos;s intrinsic difficulty — a harder category will
            tend to show larger absolute gaps even at equal relative degradation. We report
            per-category CLSG alongside the aggregate for this reason.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">Limitations</h2>
          <ul className="mt-3 space-y-2 text-base leading-7 text-ink-muted list-disc list-inside">
            <li>CLSG has not been validated against human judgment at scale.</li>
            <li>It is sensitive to translation quality and semantic-equivalence screening thresholds.</li>
            <li>A single scalar cannot capture the full shape of behavioral difference (see failure taxonomy in the platform dashboard).</li>
            <li>Comparisons across unrelated language pairs or across different underlying datasets are not meaningful.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-ink">Future validation</h2>
          <p className="mt-2 text-base leading-7 text-ink-muted">
            Planned work includes correlating CLSG against human-annotated safety judgments,
            testing sensitivity to translation provider and similarity threshold, and publishing
            inter-annotator agreement statistics once the full VERIAUDIT-500 dataset is
            human-verified.
          </p>
        </section>
      </div>
    </Container>
  );
}
