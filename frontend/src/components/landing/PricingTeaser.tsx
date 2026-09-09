import Link from "next/link";
import { Check } from "lucide-react";
import { Container } from "../ui/Container";
import { SectionHeading } from "../ui/SectionHeading";
import { Button } from "../ui/Button";

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "",
    tagline: "Explore the platform and pilot dataset.",
    features: ["Limited evaluations / month", "Pilot dataset access", "Interactive evaluation dashboard", "Community support"],
  },
  {
    name: "Researcher",
    price: "$49",
    period: "/mo",
    tagline: "For individual researchers and students.",
    features: ["Expanded evaluation quota", "CLSG reports (PDF)", "CSV / JSON export", "Email support"],
  },
  {
    name: "Startup",
    price: "$299",
    period: "/mo",
    tagline: "For teams shipping models to production.",
    features: ["Higher-volume evaluations", "Multiple models & languages", "Evidence reports for governance", "Priority support"],
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$1,000+",
    period: "/mo",
    tagline: "API access, custom audits, SLAs.",
    features: ["Programmatic API access", "Custom evaluation audits", "Dedicated onboarding", "Governance report packages"],
  },
];

export function PricingTeaser() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <SectionHeading
          eyebrow="For organizations"
          title="From open-source research to a managed evaluation platform"
          description="The evaluation framework, dataset, and methodology are open source. Hosted large-scale evaluation, proprietary model testing, and custom audits are commercial."
        />

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`flex flex-col rounded-xl border p-6 ${
                t.highlighted
                  ? "border-accent bg-bg-raised ring-1 ring-accent/30"
                  : "border-border bg-bg-raised"
              }`}
            >
              <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">
                {t.name}
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="text-2xl font-semibold text-ink">{t.price}</span>
                {t.period && <span className="text-sm text-ink-faint">{t.period}</span>}
              </div>
              <p className="mt-2 text-sm text-ink-muted">{t.tagline}</p>
              <ul className="mt-5 space-y-2 flex-1">
                {t.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-ink-muted">
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Button href="/pricing" variant="secondary">
            View full pricing
          </Button>
          <Link
            href="/open-source"
            className="inline-flex items-center px-2 text-sm font-medium text-accent hover:underline underline-offset-4"
          >
            What&apos;s open source →
          </Link>
        </div>
      </Container>
    </section>
  );
}
