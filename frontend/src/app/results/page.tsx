import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Badge } from "@/components/ui/Badge";
import data from "@/data/v2/dashboard.json";

export const metadata: Metadata = {
  title: "Results (real data)",
  description:
    "VeriAudit research results computed from real model outputs: the reproduced v0.1 pilot, corrected analyses, and the v2 study status.",
};

const LANG: Record<string, string> = {
  english: "English",
  urdu: "Urdu script",
  roman_urdu: "Roman Urdu",
  code_switched: "Code-switched",
  all: "All forms",
};
const MODEL: Record<string, string> = { "qwen3-8b": "Qwen3-8B", "aya-expanse-8b": "Aya Expanse 8B" };

type Comparison = (typeof data.v1.comparisons)[number];

function fmt(x: number | null | undefined, digits = 1) {
  return x === null || x === undefined ? "—" : x.toFixed(digits);
}
function pfmt(p: number | null | undefined) {
  if (p === null || p === undefined) return "—";
  return p < 0.001 ? "<.001" : p.toFixed(3).replace(/^0/, "");
}

/** Gap with 95% CI drawn on a 0–80 pp axis. */
function GapBar({ gap, lo, hi }: { gap: number | null; lo: number | null; hi: number | null }) {
  if (gap === null) return null;
  const scale = (v: number) => `${Math.max(0, Math.min(100, ((v + 10) / 90) * 100))}%`;
  return (
    <div className="relative h-3 w-40 rounded bg-bg-subtle" aria-hidden>
      <div className="absolute top-0 h-3 w-px bg-border-strong" style={{ left: scale(0) }} />
      {lo !== null && hi !== null && (
        <div
          className="absolute top-1 h-1 rounded bg-accent/40"
          style={{ left: scale(lo), width: `calc(${scale(hi)} - ${scale(lo)})` }}
        />
      )}
      <div className="absolute top-0 h-3 w-1 rounded bg-accent" style={{ left: scale(gap) }} />
    </div>
  );
}

function Section({ eyebrow, title, provenance, children }: { eyebrow: string; title: string; provenance?: string; children: React.ReactNode }) {
  return (
    <section className="mt-16">
      <Eyebrow>{eyebrow}</Eyebrow>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink">{title}</h2>
      {provenance && (
        <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-ink-muted">
          <Badge tone="accent">Real data</Badge>
          <span>{provenance}</span>
        </p>
      )}
      <div className="mt-6">{children}</div>
    </section>
  );
}

function Table({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="bg-bg-subtle text-xs uppercase tracking-wide text-ink-muted">
          <tr>{head.map((h) => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r, i) => (
            <tr key={i} className="text-ink">
              {r.map((c, j) => <td key={j} className="px-4 py-3 align-middle tabular-nums">{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ResultsPage() {
  const v1 = data.v1;
  const comps: Comparison[] = v1.comparisons;
  const cls = data.classifier_baseline.rows;
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Results</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">Research results</h1>
      <p className="mt-4 max-w-3xl text-base leading-7 text-ink-muted">
        Everything on this page is computed from real model outputs and labels committed to the repository. The
        interactive <a href="/platform" className="underline">Platform</a> page is a demonstration with illustrative
        numbers and is kept separate. Generated {data.generated_utc}.
      </p>

      <Section eyebrow="Study status" title="VeriAudit v2 — what has and has not been run">
        <ul className="space-y-2">
          {data.status.map((s) => (
            <li key={s.item} className="flex flex-wrap items-center gap-3 text-sm">
              <Badge tone={s.state === "done" ? "accent" : s.state === "blocked" ? "danger" : "warn"}>{s.state}</Badge>
              <span className="font-medium text-ink">{s.item}</span>
              <span className="text-ink-muted">{s.detail}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        eyebrow="v0.1 pilot · reproduced"
        title={`Cross-lingual gaps, three ways (${v1.verification.matched}/${v1.verification.checks} published numbers reproduced)`}
        provenance={v1.provenance}
      >
        <p className="mb-4 max-w-3xl text-sm leading-6 text-ink-muted">
          The published v0.1 metric drops unscoreable responses from the denominator. Keeping all 30 pairs and counting
          only actual harmful compliance shrinks Qwen3-8B&apos;s Roman Urdu gap and removes its significance: much of it was
          comprehension failure, not unsafe behaviour. Gaps in percentage points vs English; bars show the harmful-compliance
          gap with its 95% Newcombe interval. p-values are Holm-adjusted within each definition.
        </p>
        <Table
          head={["Model", "Form", "v0.1 CLSG", "Holm p", "Harmful-compliance gap [95% CI]", "", "Holm p", "Safe-rate gap (unscoreable = not safe)", "Holm p"]}
          rows={comps.map((c) => [
            MODEL[c.model] ?? c.model,
            LANG[c.language] ?? c.language,
            fmt(c.v1_gap_pp),
            pfmt(c.v1_p_holm),
            `${fmt(c.hc_gap_pp)} [${fmt(c.hc_ci_low_pp)}, ${fmt(c.hc_ci_high_pp)}]`,
            <GapBar key="b" gap={c.hc_gap_pp} lo={c.hc_ci_low_pp} hi={c.hc_ci_high_pp} />,
            pfmt(c.hc_p_holm),
            `${fmt(c.safe_gap_pp)} [${fmt(c.safe_ci_low_pp)}, ${fmt(c.safe_ci_high_pp)}]`,
            pfmt(c.safe_p_holm),
          ])}
        />
        <p className="mt-3 text-sm text-ink-muted">
          Mean over the six comparisons (intent-cluster bootstrap, 95%): v0.1 CLSG {fmt(v1.bootstrap_mean_v1_pp.estimate)} pp [
          {fmt(v1.bootstrap_mean_v1_pp.low)}, {fmt(v1.bootstrap_mean_v1_pp.high)}]; harmful-compliance gap{" "}
          {fmt(v1.bootstrap_mean_hc_pp.estimate)} pp [{fmt(v1.bootstrap_mean_hc_pp.low)}, {fmt(v1.bootstrap_mean_hc_pp.high)}].
        </p>
      </Section>

      <Section eyebrow="Scoring" title="Refusal detection fails outside English" provenance="Real data: the 240 v0.1 responses scored by two rule-based detectors against the final labels.">
        <Table
          head={["Form", "Safe responses", "v1 backend detector recall", "v2 multilingual rule judge recall"]}
          rows={(["english", "urdu", "roman_urdu", "code_switched"] as const).map((l) => {
            const a = v1.scoring_correction.v1_backend_RefusalConsistencyEvaluator[l];
            const b = v1.scoring_correction.v2_rule_judge[l];
            return [LANG[l], a.n_SAFE, `${fmt((a.refusal_recall_on_SAFE ?? 0) * 100)}%`, `${fmt((b.refusal_recall_on_SAFE ?? 0) * 100)}%`];
          })}
        />
        <p className="mt-3 max-w-3xl text-sm text-ink-muted">
          Neither detector is used as a safety metric in v2; both are triage only. The v1 API&apos;s heuristic would have
          reported gaps of {Math.min(...Object.values(v1.backend_heuristic_clsg))}–{Math.max(...Object.values(v1.backend_heuristic_clsg))} points on these
          same responses — an artefact of English-only refusal patterns.
        </p>
      </Section>

      <Section eyebrow="Response language" title="Which language did the model answer in?" provenance="Real data: detected response script/language for non-English prompts in v0.1.">
        <Table
          head={["Model", "Prompt form", "Response language", "n", "Safe", "Harmful", "Unscoreable"]}
          rows={v1.language_drift.map((d) => [MODEL[d.model] ?? d.model, LANG[d.prompt_language], d.response_language.replace(/_/g, " "), d.n, d.safe, d.harmful, d.non_scoreable])}
        />
      </Section>

      <Section eyebrow="RQ5 · preliminary" title="Does a harmful-response classifier transfer across forms?" provenance={data.classifier_baseline.provenance}>
        <Table
          head={["Setting", "Test form", "Model", "Macro-F1 [95% CI]", "Recall (unsafe)", "FPR", "n (unsafe)"]}
          rows={cls.map((r) => [
            r.setting === "leave_one_form_out" ? "Leave one form out" : "Intent-grouped 5-fold",
            LANG[r.test_form] ?? r.test_form,
            r.model === "char_ngram_lr" ? "char n-gram LR" : "rule judge",
            `${fmt(r.macro_f1, 2)} [${fmt(r.macro_f1_ci_low, 2)}, ${fmt(r.macro_f1_ci_high, 2)}]`,
            fmt(r.recall_unsafe, 2),
            fmt(r.fpr, 2),
            `${r.n} (${r.n_unsafe})`,
          ])}
        />
        <p className="mt-3 max-w-3xl text-sm text-ink-muted">
          Exploratory and small (44 unsafe responses, one in English). The rule judge&apos;s patterns were built from these
          same responses, so its scores are in-sample.
        </p>
      </Section>

      <Section eyebrow="VeriAudit-X" title={`Main-study design: ${data.dataset.total} scenarios selected`}>
        <p className="mb-4 text-sm text-ink-muted">{data.dataset.provenance}</p>
        <Table
          head={["Category", "Source", "Scenarios"]}
          rows={data.dataset.counts.map((c) => [c.category.replace(/_/g, " "), c.source, c.n])}
        />
        <p className="mt-6 mb-4 text-sm text-ink-muted">{data.power.provenance}</p>
        <Table
          head={["Planning scenario", "Net gap (pp)", "n scenarios", "Power"]}
          rows={data.power.rows.map((r) => [r.scenario, r.net_gap_pp, r.n_scenarios, fmt(r.power_bonferroni_family, 2)])}
        />
      </Section>
    </Container>
  );
}
