import type { Metadata } from "next";
import { FileText } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { PAPER_PDF, REPO, EXPLORATORY_DIR, PROTOCOL, STATS_VALIDATION, findings } from "@/data/research";

export const metadata: Metadata = {
  title: "Research",
  description:
    "Comprehension, Not Only Compliance: how denominators and detectors shape cross-lingual safety gaps for Urdu, Roman Urdu and code-switched prompts.",
};

const questions = [
  { q: "Safety failure", a: "The model understood the request and produced harmful content." },
  { q: "Comprehension failure", a: "The model did not understand, and produced loops, off-topic text or an answer in another language." },
  { q: "Measurement failure", a: "The evaluator cannot read the response's language or script, and misclassifies it." },
];

const limitations = [
  "Findings 1–3 rest on 30 harmful requests in four forms, written by one author, with two models.",
  "The multi-model results are labelled by automated judges that do not document Urdu support; human validation is under way.",
  "Open-weight models of 8–9B parameters only; results may not transfer to larger or proprietary models.",
  "\"Safety\" follows an operational rubric (harmful compliance, refusal type, comprehension), not a universal definition.",
];

const citation = `@misc{najam2026veriaudit,
  author = {Najam, Abeera},
  title  = {Comprehension, Not Only Compliance: How Denominators and Detectors
            Shape Cross-Lingual Safety Gaps for Urdu, Roman Urdu and
            Code-Switched Prompts},
  year   = {2026},
  url    = {${REPO}}
}`;

export default function ResearchPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Research</Eyebrow>
      <h1 className="mt-3 max-w-3xl text-4xl font-semibold tracking-tight text-ink text-balance">
        Comprehension, Not Only Compliance
      </h1>
      <p className="mt-3 max-w-3xl text-lg text-ink-muted">
        How denominators and detectors shape cross-lingual safety gaps for Urdu, Roman Urdu and code-switched prompts
      </p>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button href={PAPER_PDF} variant="primary" external>
          <FileText className="h-4 w-4" /> Read the paper (PDF)
        </Button>
        <Button href={REPO} variant="secondary" external>Code &amp; reproduction</Button>
        <Badge>Preprint · Abeera Najam · 2026</Badge>
      </div>

      <div className="mt-14 grid gap-12 lg:grid-cols-[1fr_300px]">
        <section className="space-y-12">
          <div>
            <h2 className="text-lg font-semibold text-ink">The question</h2>
            <p className="mt-3 text-sm leading-7 text-ink-muted">
              Multilingual safety evaluations usually summarise a model with one number: the gap between its safety in
              English and in another language. For Urdu, which people mostly type as Roman Urdu or mix with English,
              a measured gap can come from three very different sources:
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {questions.map((x) => (
                <div key={x.q} className="rounded-lg border border-border bg-bg-raised p-4">
                  <div className="font-medium text-ink">{x.q}</div>
                  <p className="mt-1 text-sm leading-6 text-ink-muted">{x.a}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Findings</h2>
            <ul className="mt-4 space-y-4">
              {findings.map((f) => (
                <li key={f.label} className="rounded-lg border border-border bg-bg-raised p-5">
                  <div className="flex flex-wrap items-baseline gap-3">
                    <span className="font-mono text-xl font-semibold text-accent">{f.stat}</span>
                    <span className="font-medium text-ink">{f.label}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink-muted">{f.body}</p>
                </li>
              ))}
              <li className="rounded-lg border border-border bg-bg-raised p-5">
                <div className="font-medium text-ink">Multi-model evaluation with independent judges</div>
                <p className="mt-2 text-sm leading-6 text-ink-muted">
                  Across Qwen3-8B, Aya Expanse 8B and Qwen3.5-9B (1,440 generations), two automated judges agree on
                  harmfulness for 96% of responses but on refusal type for only 50%. Both find gaps for Aya Expanse in
                  Urdu script (+11 to +12 points) and Qwen3-8B in Roman Urdu (+10 to +20 points), and none for Qwen3.5-9B.{" "}
                  <a href={EXPLORATORY_DIR} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                    Tables ↗
                  </a>
                </p>
              </li>
            </ul>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Method</h2>
            <p className="mt-3 text-sm leading-7 text-ink-muted">
              Every published number of the original evaluation is recomputed from raw outputs (191 of 191 match). Gaps
              are re-estimated on the full set of scenario pairs, with bounds that count non-scoreable outputs as safe and
              as unsafe. Refusal detectors are scored against human-reviewed labels in each language form, and the language
              and script of every response are recorded. The follow-up study is pre-registered, and its primary test was
              chosen by simulation.{" "}
              <a href={PROTOCOL} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Protocol ↗</a>{" "}
              <a href={STATS_VALIDATION} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">Statistical validation ↗</a>
            </p>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-ink">Scope</h2>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-ink-muted list-disc pl-5">
              {limitations.map((l) => <li key={l}>{l}</li>)}
            </ul>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Cite</div>
            <pre className="mt-3 overflow-x-auto whitespace-pre text-[11px] leading-5 text-ink-muted">{citation}</pre>
          </div>
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">See also</div>
            <ul className="mt-3 space-y-2 text-sm">
              <li><a href="/results" className="text-accent hover:underline underline-offset-4">All results</a></li>
              <li><a href="/methodology" className="text-accent hover:underline underline-offset-4">Methodology</a></li>
              <li><a href="/benchmark" className="text-accent hover:underline underline-offset-4">VeriAudit-X benchmark</a></li>
            </ul>
          </div>
        </aside>
      </div>
    </Container>
  );
}
