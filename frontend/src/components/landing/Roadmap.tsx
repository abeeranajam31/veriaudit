import { Container } from "../ui/Container";
import { SectionHeading } from "../ui/SectionHeading";

const roadmap = [
  {
    label: "Now",
    tone: "text-accent",
    items: ["Cross-lingual evaluation prototype", "English → Urdu → Roman Urdu → code-switched"],
  },
  {
    label: "Next",
    tone: "text-ink",
    items: ["Human-verified benchmark dataset", "More open models", "More evaluation categories"],
  },
  {
    label: "Later",
    tone: "text-ink-muted",
    items: [
      "Arabic, Hindi, Bengali, Punjabi, and other low-resource languages",
      "Agent evaluation",
      "Multimodal evaluation",
      "Continuous model monitoring",
      "API for organizations",
    ],
  },
];

export function Roadmap() {
  return (
    <section className="border-b border-border py-20 sm:py-28">
      <Container>
        <SectionHeading eyebrow="Roadmap" title="Current, next, and later" />
        <div className="mt-14 grid gap-6 sm:grid-cols-3">
          {roadmap.map((col) => (
            <div key={col.label} className="rounded-xl border border-border bg-bg-raised p-6">
              <div className={`font-mono text-xs uppercase tracking-wide ${col.tone}`}>
                {col.label}
              </div>
              <ul className="mt-4 space-y-3">
                {col.items.map((item) => (
                  <li key={item} className="text-sm leading-6 text-ink-muted border-t border-border pt-3 first:border-t-0 first:pt-0">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
