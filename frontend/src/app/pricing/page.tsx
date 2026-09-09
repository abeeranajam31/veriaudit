import type { Metadata } from "next";
import { Check } from "lucide-react";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "Pricing",
  description: "VERIAUDIT pricing — free tier, researcher, startup, and enterprise / API access.",
};

const tiers = [
  {
    name: "Free",
    price: "$0",
    period: "",
    tagline: "Explore the platform and pilot dataset.",
    features: [
      "Limited evaluations per month",
      "Pilot dataset access (VERIAUDIT-500 sample)",
      "Interactive evaluation dashboard",
      "Community support (GitHub)",
    ],
    cta: "Explore the Platform",
    href: "/platform",
  },
  {
    name: "Researcher",
    price: "$49",
    period: "/mo",
    tagline: "For individual researchers and students.",
    features: [
      "Expanded evaluation quota",
      "CLSG evidence reports (PDF)",
      "CSV / JSON export",
      "Email support",
    ],
    cta: "Request an Audit",
    href: "/contact",
  },
  {
    name: "Startup",
    price: "$299",
    period: "/mo",
    tagline: "For teams shipping models to production.",
    features: [
      "Higher-volume evaluations",
      "Multiple models & languages",
      "Evidence reports for AI governance workflows",
      "Priority support",
    ],
    cta: "Request an Audit",
    href: "/contact",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$1,000+",
    period: "/mo",
    tagline: "Programmatic access and custom audits.",
    features: [
      "POST /evaluate API access",
      "Custom cross-lingual / cross-cultural audits",
      "Dedicated onboarding",
      "SLA-backed support",
    ],
    cta: "Request an Audit",
    href: "/contact",
  },
];

export default function PricingPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Pricing</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        From free exploration to enterprise audits
      </h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-ink-muted">
        The evaluation framework and dataset are open source. These plans cover hosted, large-scale
        evaluation and managed audits — nothing here should be read as a claim that billing or
        payment processing is live in this MVP.
      </p>

      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiers.map((t) => (
          <div
            key={t.name}
            className={`flex flex-col rounded-xl border p-6 ${
              t.highlighted ? "border-accent bg-bg-raised ring-1 ring-accent/30" : "border-border bg-bg-raised"
            }`}
          >
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">{t.name}</div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-semibold text-ink">{t.price}</span>
              {t.period && <span className="text-sm text-ink-faint">{t.period}</span>}
            </div>
            <p className="mt-2 text-sm text-ink-muted">{t.tagline}</p>
            <ul className="mt-5 space-y-2 flex-1">
              {t.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-ink-muted">
                  <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <Button href={t.href} variant={t.highlighted ? "primary" : "secondary"} className="mt-6 w-full">
              {t.cta}
            </Button>
          </div>
        ))}
      </div>

      <div className="mt-14 rounded-xl border border-border bg-bg-subtle p-6 max-w-2xl">
        <h2 className="text-sm font-semibold text-ink">API / infrastructure model</h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          Enterprise access is designed around <code className="font-mono text-xs">POST /evaluate</code> —
          submit a model configuration, VERIAUDIT runs it across English, Urdu, Roman Urdu, and
          code-switched variants (with more languages planned), and returns structured scores and an
          evidence report. Usage-based pricing is scoped per evaluation, per model, and per API call.
        </p>
      </div>
    </Container>
  );
}
