import type { Metadata } from "next";
import Image from "next/image";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";

export const metadata: Metadata = {
  title: "About",
  description: "About VERIAUDIT and its founder, Abeera Najam.",
};

export default function AboutPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>About</Eyebrow>
      <div className="mt-3 flex flex-col sm:flex-row sm:items-center gap-5">
        <Image
          src="/founder.jpg"
          alt="Abeera Najam"
          width={128}
          height={128}
          className="h-32 w-32 rounded-full object-cover border border-border-strong"
        />
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-ink">Abeera Najam</h1>
          <p className="mt-1 text-sm text-ink-muted">Founder &amp; Lead Researcher, VERIAUDIT</p>
        </div>
      </div>

      <div className="mt-10 max-w-2xl space-y-6 text-base leading-7 text-ink-muted">
        <p>
          I build open-source infrastructure for measuring whether AI safety survives linguistic
          distribution shift. My work sits at the intersection of AI safety, multilingual NLP,
          evaluation, and AI governance, beginning with Urdu and other underrepresented linguistic
          settings.
        </p>
        <p>
          VERIAUDIT started from a simple observation: almost all public AI safety evaluation
          happens in English, while a large share of the world&apos;s AI users interact with these
          systems in low-resource languages, transliterated scripts, and code-switched speech.
          Measuring that gap — rather than assuming it doesn&apos;t exist — is the project&apos;s
          starting point.
        </p>
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <Button href="https://www.linkedin.com/" variant="secondary" external>
          LinkedIn
        </Button>
        <Button href="https://github.com/abeeranajam31/veriaudit" variant="secondary" external>
          GitHub
        </Button>
        <Button href="https://huggingface.co/abeeranajam31" variant="secondary" external>
          Hugging Face
        </Button>
      </div>
      <div className="mt-14 rounded-xl border border-border bg-bg-subtle p-6 max-w-2xl">
        <h2 className="text-sm font-semibold text-ink">Get in touch</h2>
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          Open to collaboration with researchers, developers, policymakers, and organizations
          working on AI safety, multilingual NLP, evaluation, and governance.
        </p>
        <a
          href="mailto:veriiaudit@gmail.com"
          className="mt-3 inline-block text-sm font-medium text-accent hover:underline underline-offset-4"
        >
          veriiaudit@gmail.com
        </a>
      </div>
    </Container>
  );
}
