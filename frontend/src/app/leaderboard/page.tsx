import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { Clock3 } from "lucide-react";

export const metadata: Metadata = {
  title: "Leaderboard",
  description: "The VERIAUDIT cross-lingual safety leaderboard — structure and submission process.",
};

const columns = [
  "Model",
  "Languages tested",
  "Safety score",
  "Cross-Lingual Safety Gap",
  "Test set",
  "Evaluation date",
];

export default function LeaderboardPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Leaderboard</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        Cross-Lingual Safety Leaderboard
      </h1>

      <div className="mt-10 rounded-xl border border-border bg-bg-raised p-10 text-center">
        <Clock3 className="mx-auto h-6 w-6 text-ink-faint" />
        <p className="mt-4 text-lg font-medium text-ink">Leaderboard coming soon.</p>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">
          We are not publishing rankings until models have actually been evaluated against a
          human-verified test set. No scores are shown here to avoid implying results that
          don&apos;t yet exist.
        </p>
        <div className="mt-6">
          <Button href="/contact" variant="primary">
            Submit a Model
          </Button>
        </div>
      </div>

      <div className="mt-12">
        <h2 className="text-lg font-semibold text-ink">Intended structure</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Once populated, each row will report the following, with methodology and dataset version
          linked for reproducibility.
        </p>
        <div className="mt-4 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-bg-subtle text-ink-faint font-mono text-xs uppercase">
              <tr>
                {columns.map((c) => (
                  <th key={c} className="px-4 py-3 whitespace-nowrap">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-border">
                {columns.map((c) => (
                  <td key={c} className="px-4 py-4 text-ink-faint italic">
                    —
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Container>
  );
}
