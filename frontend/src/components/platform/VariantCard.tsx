import { FORM_LABELS, Variant } from "@/lib/types";
import { Badge } from "../ui/Badge";

const statusTone: Record<Variant["verificationStatus"], "accent" | "warn" | "danger" | "neutral"> = {
  verified: "accent",
  pending: "warn",
  flagged: "danger",
  unavailable: "neutral",
};

const statusLabel: Record<Variant["verificationStatus"], string> = {
  verified: "Verified",
  pending: "Pending review",
  flagged: "Flagged — low similarity",
  unavailable: "Unavailable",
};

export function VariantCard({ variant }: { variant: Variant }) {
  return (
    <div className="rounded-lg border border-border bg-bg-raised p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs uppercase tracking-wide text-ink-faint">
          {FORM_LABELS[variant.form]}
        </span>
        <Badge tone={statusTone[variant.verificationStatus]}>
          {statusLabel[variant.verificationStatus]}
        </Badge>
      </div>
      <p
        dir={variant.form === "urdu" ? "rtl" : "ltr"}
        className="mt-3 text-sm leading-6 text-ink"
      >
        {variant.text}
      </p>
      {variant.similarity !== null && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-[11px] text-ink-faint">
            <span>Semantic similarity to English (heuristic)</span>
            <span className="font-mono tabular-nums">{variant.similarity.toFixed(2)}</span>
          </div>
          <div className="mt-1 h-1.5 w-full rounded-full bg-bg-subtle overflow-hidden">
            <div
              className="h-full rounded-full bg-accent"
              style={{ width: `${Math.round(variant.similarity * 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
