import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Badge } from "@/components/ui/Badge";
import { pilotDataset } from "@/lib/pilotDataset";

export const metadata: Metadata = {
  title: "Benchmark",
  description: "The VERIAUDIT-500 benchmark dataset: schema, pilot subset, and verification status.",
};

const schemaExample = `{
  "id": "VA-001",
  "intent_category": "...",
  "intent": "...",
  "english": "...",
  "urdu": "...",
  "roman_urdu": "...",
  "code_switched": "...",
  "verification_status": "pending",
  "semantic_similarity": {
    "english_urdu": 0.0,
    "english_roman_urdu": 0.0,
    "english_code_switched": 0.0
  }
}`;

export default function BenchmarkPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Benchmark</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">VERIAUDIT-500</h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-ink-muted">
        The target benchmark is 125 core intents × 4 linguistic variants (English, Urdu, Roman
        Urdu, code-switched) = 500 test cases.
      </p>
      <div className="mt-4">
        <Badge tone="warn">
          Pilot subset: {pilotDataset.length} intents shipped today. Full VERIAUDIT-500 is under
          development.
        </Badge>
      </div>

      <div className="mt-6 rounded-xl border border-border bg-bg-raised p-6 max-w-2xl">
        <p className="text-sm leading-6 text-ink-muted">
          The public MVP contains a pilot subset, translated by the project&apos;s lead researcher
          as a first pass. The full VERIAUDIT-500 dataset is under development and will be released
          following independent bilingual human verification. Current verification status per case
          is shown below and in the raw dataset file.
        </p>
      </div>

      <div className="mt-12 grid gap-10 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-ink">Dataset schema</h2>
          <pre className="mt-3 overflow-x-auto rounded-lg border border-border bg-bg-subtle p-4 text-xs leading-6 text-ink font-mono">
{schemaExample}
          </pre>

          <h2 className="mt-10 text-lg font-semibold text-ink">Pilot cases</h2>
          <div className="mt-3 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-bg-subtle text-ink-faint font-mono text-xs uppercase">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Intent</th>
                  <th className="px-4 py-3">Verification</th>
                </tr>
              </thead>
              <tbody>
                {pilotDataset.map((c) => {
                  const statuses = c.variants.map((v) => v.verificationStatus);
                  const worst = statuses.includes("flagged")
                    ? "flagged"
                    : statuses.includes("pending")
                    ? "pending"
                    : "verified";
                  return (
                    <tr key={c.id} className="border-t border-border">
                      <td className="px-4 py-3 font-mono text-xs text-ink-faint">{c.id}</td>
                      <td className="px-4 py-3 text-ink-muted">{c.intentCategory}</td>
                      <td className="px-4 py-3 text-ink">{c.intent}</td>
                      <td className="px-4 py-3">
                        <Badge
                          tone={worst === "flagged" ? "danger" : worst === "pending" ? "warn" : "accent"}
                        >
                          {worst}
                        </Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Languages</div>
            <ul className="mt-3 space-y-1.5 text-sm text-ink-muted">
              <li>1. English</li>
              <li>2. Urdu</li>
              <li>3. Roman Urdu</li>
              <li>4. Code-switched Urdu/English</li>
            </ul>
          </div>
          <div className="rounded-xl border border-border bg-bg-raised p-5">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Get the data</div>
            <p className="mt-2 text-sm text-ink-muted">
              Raw dataset files live in{" "}
              <code className="font-mono text-xs">/dataset/examples</code> in the GitHub
              repository, alongside full documentation.
            </p>
            <a
              href="https://github.com/abeeranajam31/veriaudit"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-sm font-medium text-accent hover:underline underline-offset-4"
            >
              View on GitHub →
            </a>
          </div>
        </aside>
      </div>
    </Container>
  );
}
