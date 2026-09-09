import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "Open Source",
  description: "What VERIAUDIT releases as open source, and what stays part of the managed platform.",
};

const openItems = [
  "Evaluation framework (EquivEngine, GapEvaluator, model adapter interfaces)",
  "Pilot dataset and dataset schema, with the full VERIAUDIT-500 to follow after verification",
  "CLSG benchmark methodology and scoring framework",
  "Reproducibility documentation (environment, prompts, evaluation configs)",
];

const commercialItems = [
  "Hosted, large-scale evaluation runs",
  "Proprietary / closed-source model testing via API",
  "Automated continuous monitoring",
  "Custom enterprise audits and governance report packages",
];

export default function OpenSourcePage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Open Source</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        Open-source core, commercial scale
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-ink-muted">
        VERIAUDIT aims to release its evaluation code, dataset, benchmark methodology, and scoring
        framework openly, so the core measurement can be independently reproduced and scrutinized.
        Hosted infrastructure and large-scale or proprietary evaluations are commercial — see{" "}
        <a href="/pricing" className="text-accent hover:underline underline-offset-4">
          pricing
        </a>
        .
      </p>

      <div className="mt-12 grid gap-6 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-bg-raised p-6">
          <h2 className="text-sm font-semibold text-accent">Open source</h2>
          <ul className="mt-4 space-y-2.5 text-sm leading-6 text-ink-muted list-disc list-inside">
            {openItems.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-border bg-bg-raised p-6">
          <h2 className="text-sm font-semibold text-ink">Commercial / hosted</h2>
          <ul className="mt-4 space-y-2.5 text-sm leading-6 text-ink-muted list-disc list-inside">
            {commercialItems.map((i) => (
              <li key={i}>{i}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <Button href="https://github.com/abeeranajam31/veriaudit" variant="primary" external>
          GitHub
        </Button>
        <Button href="https://huggingface.co/veriaudit" variant="secondary" external>
          Hugging Face
        </Button>
        <Button href="/methodology" variant="ghost">
          Read Methodology
        </Button>
      </div>

      <p className="mt-4 text-xs text-ink-faint">
        Repository and Hugging Face organization links point to the intended namespaces and will be
        made public as they are populated.
      </p>
    </Container>
  );
}
