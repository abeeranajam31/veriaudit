import Link from "next/link";
import { Container } from "../ui/Container";

export function FounderTeaser() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <div className="mx-auto max-w-2xl rounded-xl border border-border bg-bg-raised p-8 sm:p-10">
          <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Founder</div>
          <p className="mt-4 text-lg leading-8 text-ink text-pretty">
            &ldquo;I build open-source infrastructure for measuring whether AI safety survives
            linguistic distribution shift. My work sits at the intersection of AI safety,
            multilingual NLP, evaluation, and AI governance, beginning with Urdu and other
            underrepresented linguistic settings.&rdquo;
          </p>
          <div className="mt-5 flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="font-semibold text-ink">Abeera Najam</div>
              <div className="text-sm text-ink-muted">Founder &amp; Lead Researcher, VERIAUDIT</div>
            </div>
            <Link href="/about" className="text-sm font-medium text-accent hover:underline underline-offset-4">
              About VERIAUDIT →
            </Link>
          </div>
        </div>
      </Container>
    </section>
  );
}
