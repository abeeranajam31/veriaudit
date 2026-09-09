import { findClosestPilotCase, pilotDataset } from "./pilotDataset";
import type { PilotTestCase, Variant } from "./types";

export interface EquivEngineResult {
  source: "pilot-dataset" | "unavailable";
  matchedCase: PilotTestCase | null;
  variants: Variant[];
  note: string;
}

/**
 * Client-side, static-hosting-safe stand-in for the EquivEngine backend service.
 *
 * IMPORTANT — this is NOT a translation engine. It looks up the closest matching
 * intent in the VERIAUDIT pilot dataset and returns its human-authored variants.
 * Arbitrary free text that doesn't match a pilot intent cannot be translated in
 * this static demo; the real EquivEngine (backend/app/evaluation/equiv_engine.py)
 * performs live translation + sentence-transformer similarity scoring.
 */
export function generateVariants(inputText: string): EquivEngineResult {
  const match = findClosestPilotCase(inputText);

  if (match) {
    return {
      source: "pilot-dataset",
      matchedCase: match,
      variants: match.variants,
      note:
        match.variants[0]?.text.trim().toLowerCase() === inputText.trim().toLowerCase()
          ? "Exact match against a VERIAUDIT pilot intent. Variants and similarity scores below are human-authored, not machine-translated."
          : "Closest match against a VERIAUDIT pilot intent (approximate). Showing that pilot case's human-authored variants.",
    };
  }

  return {
    source: "unavailable",
    matchedCase: null,
    variants: [],
    note:
      "This static demo only generates variants for the pilot intents in the VERIAUDIT-500 sample (try one of the examples below). Live translation of arbitrary text requires the EquivEngine backend service, which is not connected in this deployment.",
  };
}

export function pilotIntentOptions() {
  return pilotDataset.map((c) => ({
    id: c.id,
    category: c.intentCategory,
    intent: c.intent,
    english: c.variants.find((v) => v.form === "english")?.text ?? "",
  }));
}
