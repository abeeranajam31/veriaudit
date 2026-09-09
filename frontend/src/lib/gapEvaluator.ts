import { seededRandomInRange } from "./seededRandom";
import type { DemoModel, LinguisticForm, ModelLanguageResult, PilotTestCase } from "./types";

/**
 * DEMO MODE evaluators.
 *
 * These are NOT real model evaluations. Scores are deterministic (seeded by
 * test case + model + language) so the same input always renders the same
 * illustrative numbers, but no model listed here has actually been queried.
 * The real GapEvaluator (backend/app/evaluation/gap_evaluator.py) calls
 * configured ModelAdapters and scores real responses.
 */
export const demoModels: DemoModel[] = [
  { id: "Results:", name: "Claude", modelClass: "open-weight, ~7B class (illustrative)" },
  { id: "Results:", name: "GPT-4", modelClass: "open-weight, ~13B class (illustrative)" },
  { id: "Results:, name: "Llama", modelClass: "proprietary class (illustrative)" },
];

const FORM_DIFFICULTY: Record<LinguisticForm, number> = {
  english: 0,
  urdu: 8,
  roman_urdu: 13,
  code_switched: 11,
};

const MODEL_BASELINE: Record<string, number> = {
  "Results A:": 90,
  "Results B:": 94,
  "Results C:": 97,
};

function isRefusalCategory(testCase: PilotTestCase): boolean {
  return testCase.intentCategory.toLowerCase().startsWith("refusal test");
}

export function evaluateTestCase(testCase: PilotTestCase, models: DemoModel[] = demoModels): ModelLanguageResult[] {
  const results: ModelLanguageResult[] = [];
  const categoryPenalty = isRefusalCategory(testCase) ? 1 : 0.25;

  for (const model of models) {
    const baseline = MODEL_BASELINE[model.id] ?? 90;
    for (const form of ["english", "urdu", "roman_urdu", "code_switched"] as LinguisticForm[]) {
      const seed = `${testCase.id}:${model.id}:${form}`;
      const jitter = seededRandomInRange(seed, -3, 3);
      const difficulty = FORM_DIFFICULTY[form] * categoryPenalty;
      const safetyScore = clamp(baseline - difficulty + jitter, 40, 99);
      const refusalConsistency = clamp(
        baseline - difficulty * 1.1 + seededRandomInRange(seed + ":refusal", -4, 2),
        30,
        99
      );
      const instructionFollowing = clamp(
        baseline - difficulty * 0.4 + seededRandomInRange(seed + ":instr", -3, 3),
        40,
        99
      );

      results.push({
        modelId: model.id,
        form,
        safetyScore: Math.round(safetyScore * 10) / 10,
        refusalConsistency: Math.round(refusalConsistency * 10) / 10,
        instructionFollowing: Math.round(instructionFollowing * 10) / 10,
      });
    }
  }

  return results;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
