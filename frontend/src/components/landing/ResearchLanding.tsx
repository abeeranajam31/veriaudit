import Image from "next/image";
import { ArrowRight, FileText } from "lucide-react";
import { Container } from "../ui/Container";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { Eyebrow, SectionHeading } from "../ui/SectionHeading";
import { GithubIcon } from "../ui/GithubIcon";
import {
  REPO,
  PAPER_PDF,
  EXPLORATORY_DIR,
  PROTOCOL,
  STATS_VALIDATION,
  RECONSTRUCTION,
  findings,
  multiModel,
  judgeAgreement,
  built,
} from "@/data/research";

export function ResearchHero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="absolute inset-0 grid-overlay opacity-40 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_40%,transparent_100%)]" />
      <Container className="relative py-20 sm:py-28">
        <div className="max-w-3xl">
          <Badge tone="accent">Independent research · Open-source evaluation framework</Badge>
          <h1 className="mt-5 font-mono text-sm uppercase tracking-[0.2em] text-ink-faint">VERIAUDIT</h1>
          <p className="mt-3 text-4xl sm:text-6xl font-semibold tracking-tight text-ink text-balance">
            Measuring what multilingual AI safety evaluations actually measure.
          </p>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-ink-muted text-pretty">
            When a language model looks less safe in Urdu, is it producing harmful content, failing to understand
            the request, or being misjudged by an evaluator built for English? VeriAudit separates the three, across
            English, Urdu script, Roman Urdu and Urdu–English code-switching.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Button href={PAPER_PDF} variant="primary" external>
              <FileText className="h-4 w-4" /> Read the paper
            </Button>
            <Button href="#findings" variant="secondary">
              Key findings <ArrowRight className="h-4 w-4" />
            </Button>
            <Button href={REPO} variant="ghost" external>
              <GithubIcon className="h-4 w-4" /> Code &amp; data
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}

export function Findings() {
  return (
    <section id="findings" className="border-b border-border py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Findings"
          title="Cross-lingual safety gaps depend on how they are measured"
          description="Three connected measurement problems, each reproducible from the released outputs and code."
        />
        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {findings.map((f) => (
            <article key={f.label} className="flex flex-col rounded-xl border border-border bg-bg-raised p-6">
              <div className="font-mono text-3xl font-semibold tracking-tight text-accent tabular-nums">{f.stat}</div>
              <h3 className="mt-3 text-lg font-semibold text-ink">{f.label}</h3>
              <p className="mt-3 text-sm leading-6 text-ink-muted text-pretty">{f.body}</p>
              <a
                href={`${REPO}/tree/veriaudit-x-dataset/${f.source}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-auto pt-5 font-mono text-xs text-ink-faint hover:text-accent"
              >
                source: {f.source} ↗
              </a>
            </article>
          ))}
        </div>
      </Container>
    </section>
  );
}

export function MultiModel() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <SectionHeading
          eyebrow="Multi-model evaluation"
          title="Newer models, independent automated judges"
          description="Three open-weight models, 1,440 generations (greedy plus three samples per prompt), each response labelled by two automated judges from model families outside the panel. Gap in harmful compliance versus English, percentage points with 95% intervals, per judge."
        />
        <div className="mt-10 overflow-x-auto rounded-xl border border-border bg-bg-raised">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-ink-muted">
              <tr>
                {["Model", "Prompt form", "Judge A: Mistral-Nemo", "Judge B: Granite-3.3", "Note"].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {multiModel.map((r) => (
                <tr key={r.model} className="text-ink">
                  <td className="px-4 py-3 font-medium">{r.model}</td>
                  <td className="px-4 py-3">{r.form}</td>
                  <td className="px-4 py-3 tabular-nums">{r.nemo}</td>
                  <td className="px-4 py-3 tabular-nums">{r.granite}</td>
                  <td className="px-4 py-3 text-ink-muted">{r.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-border bg-bg-raised p-6">
            <Eyebrow>Evaluator reliability</Eyebrow>
            <p className="mt-3 text-sm leading-6 text-ink-muted">
              The two judges agree on whether a response is harmful {judgeAgreement.harmful}% of the time (κ ={" "}
              {judgeAgreement.kappaHarmful}), but on <em>how</em> a model refused only {judgeAgreement.behaviour}% of the
              time. Under a strict two-judge resolution rule most labels stay unresolved, so evaluator agreement is itself
              a research question, and human validation of the labels is the next step.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-bg-raised p-6">
            <Eyebrow>Reading these numbers</Eyebrow>
            <p className="mt-3 text-sm leading-6 text-ink-muted">
              Both judges see no harmful compliance in English for any model, and the same direction of gap for Aya in
              Urdu script and Qwen3-8B in Roman Urdu. These are exploratory, automatically judged results on 30 scenarios;
              one comparison survives multiple-testing correction. Gemma 4 could not be run on the available GPUs.
            </p>
            <a href={EXPLORATORY_DIR} target="_blank" rel="noopener noreferrer" className="mt-4 inline-block font-mono text-xs text-accent hover:underline">
              full tables and run manifest ↗
            </a>
          </div>
        </div>
      </Container>
    </section>
  );
}

export function Framework() {
  return (
    <section className="border-b border-border py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Open-source framework"
          title="Research infrastructure built to be checked"
          description="Everything needed to reproduce, audit and extend the results is public."
        />
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {built.map((b) => (
            <div key={b.title} className="bg-bg-raised p-6">
              <h3 className="font-semibold text-ink">{b.title}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-muted">{b.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-4 font-mono text-xs">
          <a href={RECONSTRUCTION} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">reproduction ↗</a>
          <a href={PROTOCOL} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">pre-registered protocol ↗</a>
          <a href={STATS_VALIDATION} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">statistical validation ↗</a>
        </div>
      </Container>
    </section>
  );
}

const next = [
  { phase: "Now", title: "Human validation of the judge labels", body: "Two independent Urdu readers label a stratified sample; a third adjudicates." },
  { phase: "Next", title: "VeriAudit-X benchmark", body: "200 scenarios with matched benign contrasts, human-written and independently verified in four forms, plus controlled Roman Urdu and code-switching variants." },
  { phase: "Then", title: "Pre-registered main study", body: "Calibration run, then the confirmatory comparison of four models with human-validated labels." },
];

export function NextSteps() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <SectionHeading eyebrow="Roadmap" title="From measurement study to benchmark" />
        <ol className="mt-12 grid gap-6 lg:grid-cols-3">
          {next.map((n) => (
            <li key={n.title} className="rounded-xl border border-border bg-bg-raised p-6">
              <div className="font-mono text-xs uppercase tracking-wide text-accent">{n.phase}</div>
              <h3 className="mt-2 font-semibold text-ink">{n.title}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-muted">{n.body}</p>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  );
}

export function Researcher() {
  return (
    <section className="py-20 sm:py-28">
      <Container>
        <div className="grid gap-8 lg:grid-cols-[1fr_320px] lg:items-start">
          <div>
            <Eyebrow>Researcher</Eyebrow>
            <p className="mt-4 text-xl sm:text-2xl leading-9 text-ink text-pretty max-w-2xl">
              VeriAudit is designed, built and run by Abeera Najam as independent research on trustworthy multilingual
              AI: how evaluation methods, language understanding and safety behaviour interact for languages that
              English-centric tools handle poorly.
            </p>
          </div>
          <aside className="rounded-xl border border-border bg-bg-raised p-6">
            <Image src="/founder.jpg" alt="Abeera Najam" width={112} height={112} className="h-28 w-28 rounded-full object-cover border border-border-strong" />
            <div className="mt-4 font-semibold text-ink">Abeera Najam</div>
            <div className="text-sm text-ink-muted">Lead Researcher</div>
            <div className="mt-1 text-sm text-ink-muted">BS Artificial Intelligence, GIKI</div>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <a href="https://github.com/abeeranajam31" target="_blank" rel="noopener noreferrer" className="font-medium text-accent hover:underline">GitHub</a>
              <a href="https://linkedin.com/in/abeeranajam" target="_blank" rel="noopener noreferrer" className="font-medium text-accent hover:underline">LinkedIn</a>
            </div>
          </aside>
        </div>
      </Container>
    </section>
  );
}
