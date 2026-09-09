import Image from "next/image";
import Link from "next/link";
import { Container } from "../ui/Container";
import { Eyebrow } from "../ui/SectionHeading";

export function FounderTeaser() {
  return (
    <section className="border-b border-border py-20 sm:py-28 bg-bg-subtle">
      <Container>
        <div className="grid gap-8 lg:grid-cols-[1fr_320px] lg:items-start">
          <div>
            <Eyebrow>Founder</Eyebrow>
            <p className="mt-4 text-xl sm:text-2xl leading-9 text-ink text-pretty max-w-2xl">
              &ldquo;I build open-source infrastructure for measuring whether AI safety
              survives linguistic distribution shift. My work sits at the intersection of
              AI safety, multilingual NLP, evaluation, and AI governance, beginning with
              Urdu and other underrepresented linguistic settings.&rdquo;
            </p>
          </div>

          <aside className="lg:sticky lg:top-24 rounded-xl border border-border bg-bg-raised p-6">
            <Image
              src="/founder.jpg"
              alt="Abeera Najam"
              width={112}
              height={112}
              className="h-28 w-28 rounded-full object-cover border border-border-strong"
            />
            <div className="mt-4 font-semibold text-ink">Abeera Najam</div>
            <div className="text-sm text-ink-muted">Founder &amp; Lead Researcher</div>
            <div className="mt-1 font-mono text-xs uppercase tracking-wide text-ink-faint">
              VERIAUDIT
            </div>
            <Link
              href="/about"
              className="mt-4 inline-block text-sm font-medium text-accent hover:underline underline-offset-4"
            >
              About VERIAUDIT →
            </Link>
          </aside>
        </div>
      </Container>
    </section>
  );
}
