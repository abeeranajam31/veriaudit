"use client";

import { useMemo, useState } from "react";
import { Sparkles, PlayCircle, FileDown } from "lucide-react";
import { Container } from "../ui/Container";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { VariantCard } from "./VariantCard";
import { SafetyByLanguageChart, ModelComparisonChart } from "./Charts";
import { pilotIntentOptions, generateVariants, EquivEngineResult } from "@/lib/equivEngine";
import { demoModels, evaluateTestCase } from "@/lib/gapEvaluator";
import { computeCLSGForModel, averageCLSG } from "@/lib/clsg";
import { FORM_LABELS, LinguisticForm, ModelLanguageResult } from "@/lib/types";

const options = pilotIntentOptions();

export function PlatformDashboard() {
  const [inputText, setInputText] = useState(options[0]?.english ?? "");
  const [result, setResult] = useState<EquivEngineResult | null>(null);
  const [evaluation, setEvaluation] = useState<ModelLanguageResult[] | null>(null);
  const [evalForm, setEvalForm] = useState<LinguisticForm>("urdu");

  function handleGenerate() {
    const r = generateVariants(inputText);
    setResult(r);
    setEvaluation(null);
  }

  function handleEvaluate() {
    if (!result?.matchedCase) return;
    setEvaluation(evaluateTestCase(result.matchedCase));
  }

  function handlePickExample(intent: string) {
    setInputText(intent);
    setResult(null);
    setEvaluation(null);
  }

  const clsgRows = useMemo(() => {
    if (!evaluation) return [];
    return demoModels.map((m) => ({
      model: m,
      clsg: computeCLSGForModel(evaluation, m.id, "english", evalForm),
    }));
  }, [evaluation, evalForm]);

  const avgGap = evaluation ? averageCLSG(evaluation, "english") : 0;

  return (
    <Container className="py-14">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Badge tone="warn">model evaluations below</Badge>
          <h1 className="mt-4 text-3xl sm:text-4xl font-semibold tracking-tight text-ink">
            Evaluation Platform
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-muted">
            TEST → COMPARE → SCORE → ANALYZE → REPORT.  Connect the EquivEngine / GapEvaluator
            backend for live translation and real model evaluation.
          </p>
        </div>
        <Button href="#" variant="secondary" className="opacity-60 pointer-events-none">
          <FileDown className="h-4 w-4" /> Evidence report (requires backend)
        </Button>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        {/* Left: input */}
        <div className="rounded-xl border border-border bg-bg-raised p-6">
          <h2 className="text-sm font-semibold text-ink">01 — Test Input</h2>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={4}
            placeholder="Enter an English test prompt..."
            className="mt-3 w-full resize-none rounded-lg border border-border bg-bg px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={handleGenerate} variant="primary">
              <Sparkles className="h-4 w-4" /> Generate Variants
            </Button>
            <Button onClick={handleEvaluate} variant="secondary" disabled={!result?.matchedCase}>
              <PlayCircle className="h-4 w-4" /> Run Evaluation
            </Button>
          </div>

          <div className="mt-6">
            <p className="font-mono text-xs uppercase tracking-wide text-ink-faint">
              Pilot intents (VERIAUDIT-500 sample)
            </p>
            <div className="mt-3 space-y-1.5 max-h-80 overflow-y-auto pr-1">
              {options.map((o) => (
                <button
                  key={o.id}
                  onClick={() => handlePickExample(o.english)}
                  className="w-full rounded-md border border-border px-3 py-2 text-left text-xs text-ink-muted hover:border-accent/40 hover:text-ink transition-colors"
                >
                  <span className="font-mono text-[10px] text-ink-faint">{o.id}</span>{" "}
                  <span className="text-ink-faint">· {o.category}</span>
                  <div className="mt-0.5 text-ink">{o.intent}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Middle: variants */}
        <div className="rounded-xl border border-border bg-bg-raised p-6">
          <h2 className="text-sm font-semibold text-ink">02 — Linguistic Variants</h2>
          {!result && (
            <p className="mt-4 text-sm text-ink-muted">
              Generate variants to see English, Urdu, Roman Urdu, and code-switched forms of this
              intent side by side.
            </p>
          )}
          {result && result.source === "unavailable" && (
            <div className="mt-4 rounded-lg border border-warn/30 bg-warn-soft p-4 text-sm text-warn">
              {result.note}
            </div>
          )}
          {result && result.matchedCase && (
            <>
              <p className="mt-3 text-xs text-ink-faint">{result.note}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {result.variants.map((v) => (
                  <VariantCard key={v.form} variant={v} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Evaluation + CLSG */}
      <div className="mt-6 rounded-xl border border-border bg-bg-raised p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink">03 — Evaluation &amp; 04 — Cross-Lingual Safety Gap</h2>
          {evaluation && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-ink-faint">Compare English against</span>
              <select
                value={evalForm}
                onChange={(e) => setEvalForm(e.target.value as LinguisticForm)}
                className="rounded-md border border-border bg-bg px-2 py-1 text-xs text-ink"
              >
                {(["urdu", "roman_urdu", "code_switched"] as LinguisticForm[]).map((f) => (
                  <option key={f} value={f}>
                    {FORM_LABELS[f]}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {!evaluation && (
          <p className="mt-4 text-sm text-ink-muted">
            Run the evaluation to see  model cards and the Cross-Lingual Safety Gap for this
            intent.
          </p>
        )}

        {evaluation && (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <div className="grid gap-3 sm:grid-cols-3">
                {clsgRows.map(({ model, clsg }) => (
                  <div key={model.id} className="rounded-lg border border-border bg-bg p-4">
                    <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">
                      {model.name}
                    </div>
                    <div className="text-[11px] text-ink-faint">{model.modelClass}</div>
                    <div className="mt-3 flex items-baseline justify-between">
                      <span className="text-xs text-ink-muted">English</span>
                      <span className="font-mono tabular-nums text-ink">{clsg?.referenceScore.toFixed(1)}%</span>
                    </div>
                    <div className="mt-1 flex items-baseline justify-between">
                      <span className="text-xs text-ink-muted">{FORM_LABELS[evalForm]}</span>
                      <span className="font-mono tabular-nums text-ink">{clsg?.evaluationScore.toFixed(1)}%</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6">
                <p className="font-mono text-xs uppercase tracking-wide text-ink-faint mb-2">
                  Safety score by language (demo data)
                </p>
                <SafetyByLanguageChart results={evaluation} />
              </div>
            </div>

            <div className="rounded-lg border border-border bg-bg p-6 flex flex-col items-center justify-center text-center">
              <span className="font-mono text-[11px] uppercase text-warn bg-warn-soft border border-warn/30 rounded-full px-2.5 py-1">
                demo data
              </span>
              <div className="mt-3 text-5xl font-semibold tabular-nums text-danger">
                {avgGap} pts
              </div>
              <div className="mt-1 text-sm text-ink-muted">Average Cross-Lingual Safety Gap</div>
              <div className="mt-4 text-xs text-ink-faint">
                Reference: English · Evaluated: Urdu, Roman Urdu, Code-Switched
                <br />
                Averaged across {demoModels.length} demo models on this intent.
              </div>
            </div>
          </div>
        )}
      </div>

      {evaluation && (
        <div className="mt-6 rounded-xl border border-border bg-bg-raised p-6">
          <p className="font-mono text-xs uppercase tracking-wide text-ink-faint mb-2">
            Model comparison across languages (demo data)
          </p>
          <ModelComparisonChart results={evaluation} />
        </div>
      )}
    </Container>
  );
}
