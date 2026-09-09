import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/SectionHeading";
import { ContactForm } from "@/components/ContactForm";

export const metadata: Metadata = {
  title: "Request an Audit",
  description: "Request a VERIAUDIT cross-lingual AI safety audit, or get in touch about collaboration.",
};

export default function ContactPage() {
  return (
    <Container className="py-16 sm:py-24">
      <Eyebrow>Request an Audit</Eyebrow>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink">
        Build safer AI across languages.
      </h1>
      <p className="mt-4 max-w-xl text-base leading-7 text-ink-muted">
        VERIAUDIT is open to collaboration with researchers, developers, policymakers, and
        organizations working on AI safety, multilingual NLP, evaluation, and governance.
      </p>

      <div className="mt-10">
        <ContactForm />
      </div>

      <div className="mt-14 max-w-xl border-t border-border pt-6 text-sm text-ink-muted">
        <p>Prefer email or LinkedIn directly?</p>
        <a href="mailto:veriiaudit@gmail.com" className="mt-1 inline-block text-accent hover:underline underline-offset-4">
          veriiaudit@gmail.com
        </a>
      </div>
    </Container>
  );
}
