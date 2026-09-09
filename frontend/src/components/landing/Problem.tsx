import { Eye, GitCompareArrows, FileSearch } from "lucide-react";
import { Container } from "../ui/Container";
import { SectionHeading } from "../ui/SectionHeading";

const problems = [
  {
    icon: Eye,
    title: "Linguistic blind spots",
    body: "Safety benchmarks often underrepresent low-resource languages, so behavior outside English is rarely measured at all.",
  },
  {
    icon: GitCompareArrows,
    title: "Hidden behavioral shifts",
    body: "A translated prompt carrying the same intent may trigger a different model response — a different refusal, or none.",
  },
  {
    icon: FileSearch,
    title: "Missing evidence",
    body: "Researchers, developers, and policymakers need reproducible measurements of cross-lingual safety behavior, not assumptions.",
  },
];

export function Problem() {
  return (
    <section className="border-b border-border py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="The problem"
          title="AI safety is still overwhelmingly tested in English."
          description="A model can appear safe under English-language benchmarks while behaving differently when the same underlying intent is expressed in another language. VERIAUDIT focuses on measuring that behavioral difference rather than assuming safety transfers automatically across languages."
        />

        <div className="mt-14 grid gap-6 sm:grid-cols-3">
          {problems.map((p) => (
            <div key={p.title} className="rounded-xl border border-border bg-bg-raised p-6">
              <p.icon className="h-5 w-5 text-accent" strokeWidth={1.75} />
              <h3 className="mt-4 text-base font-semibold text-ink">{p.title}</h3>
              <p className="mt-2 text-sm leading-6 text-ink-muted">{p.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
