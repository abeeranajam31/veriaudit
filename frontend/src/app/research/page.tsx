import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Badge } from "@/components/ui/Badge";

export const metadata: Metadata = {
  title: "Research",
  description:
    "The research question, hypothesis, methodology, and limitations behind VERIAUDIT's cross-lingual AI safety evaluation.",
};

const limitations = [
  "Translation artifacts — automated and human translation can shift connotation, formality, or intensity independent of the model being evaluated.",
  "Semantic similarity limitations — embedding-based similarity is a screening signal, not proof of equivalence; low-resource language embeddings are less reliable.",
  "Evaluator bias — automated safety scoring (model-graded or rule-based) can itself be biased or inconsistent across languages.",
  "Model randomness — sampling temperature and non-determinism mean a single run is not a stable estimate of behavior.",
  "Incomplete language coverage — the pilot covers Urdu, Roman Urdu, and code-switched forms only; findings should not be generalized to unrelated languages.",
  "Benchmark contamination — public test items may leak into model training data over time, inflating apparent safety.",
  "Limited sample size — the current pilot dataset is far smaller than the planned VERIAUDIT-500 and is not yet human-verified at scale.",
  "Difficulty defining safety universally — \"safety\" is context- and culture-dependent; VERIAUDIT's scoring rubric reflects specific operational definitions, not a universal standard.",
];

export default function ResearchPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Research</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        Does safety behavior transfer across linguistic boundaries?
      </h1>

      <div className="mt-10 grid gap-10 lg:grid-cols-3">
        <section className="lg:col-span-2 space-y-10">
          <div>
            <h2 className="text-lg font-semibold text-ink">Research Question</h2>
            <p className="mt-2 text-base leading-7 text-ink-muted">
              Does an AI system remain equally safe when the same underlying intent is expressed in
              different languages, including low-resource and code-switched forms?
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Hypothesis</h2>
            <p className="mt-2 text-base leading-7 text-ink-muted">
              Safety behavior may degrade under linguistic distribution shift, particularly in
              low-resource settings that are underrepresented in model training and alignment data.
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Methodology</h2>
            <ul className="mt-3 space-y-2.5 text-base leading-7 text-ink-muted list-disc list-inside">
              <li>Intent-level test case construction, independent of any one language.</li>
              <li>Generation of semantically equivalent multilingual variants (EquivEngine).</li>
              <li>Screening for semantic equivalence via embedding similarity, with human verification.</li>
              <li>Model evaluation against each variant under identical conditions (GapEvaluator).</li>
              <li>Structured behavioral scoring across refusal consistency, instruction following, and safety.</li>
              <li>Aggregation into the Cross-Lingual Safety Gap (CLSG) metric.</li>
            </ul>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Limitations</h2>
            <p className="mt-2 text-sm text-ink-muted">
              We list these deliberately and in detail — acknowledging limitations is part of making
              this project credible, not a weakness to hide.
            </p>
            <ul className="mt-4 space-y-3">
              {limitations.map((l) => (
                <li key={l} className="rounded-lg border border-border bg-bg-raised p-4 text-sm leading-6 text-ink-muted">
                  {l}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <Badge tone="warn">Status</Badge>
            <p className="mt-3 text-sm leading-6 text-ink-muted">
              This is an active, early-stage research prototype. No claims here should be read as
              peer-reviewed or independently validated findings.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">See also</div>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <a href="/methodology" className="text-accent hover:underline underline-offset-4">
                  Full CLSG methodology
                </a>
              </li>
              <li>
                <a href="/benchmark" className="text-accent hover:underline underline-offset-4">
                  Dataset &amp; benchmark
                </a>
              </li>
              <li>
                <a href="/open-source" className="text-accent hover:underline underline-offset-4">
                  Open-source release plan
                </a>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </Container>
  );
}
