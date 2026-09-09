export type LinguisticForm = "english" | "urdu" | "roman_urdu" | "code_switched";

export const LINGUISTIC_FORMS: LinguisticForm[] = [
  "english",
  "urdu",
  "roman_urdu",
  "code_switched",
];

export const FORM_LABELS: Record<LinguisticForm, string> = {
  english: "English",
  urdu: "Urdu",
  roman_urdu: "Roman Urdu",
  code_switched: "Code-Switched",
};

export type VerificationStatus = "verified" | "pending" | "flagged" | "unavailable";

export interface Variant {
  form: LinguisticForm;
  text: string;
  /** Heuristic client-side screening score, or null when not computable in static demo mode. */
  similarity: number | null;
  verificationStatus: VerificationStatus;
}

export interface PilotTestCase {
  id: string;
  intentCategory: string;
  intent: string;
  variants: Variant[];
}

export interface DemoModel {
  id: string;
  name: string;
  modelClass: string;
}

export interface ModelLanguageResult {
  modelId: string;
  form: LinguisticForm;
  safetyScore: number;
  refusalConsistency: number;
  instructionFollowing: number;
}

export interface CLSGResult {
  referenceForm: LinguisticForm;
  evaluationForm: LinguisticForm;
  referenceScore: number;
  evaluationScore: number;
  gapPoints: number;
}
