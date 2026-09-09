import { ArrowRight } from "lucide-react";
import { Container } from "../ui/Container";
import { Button } from "../ui/Button";

export function FinalCta() {
  return (
    <section className="py-20 sm:py-28">
      <Container>
        <div className="rounded-2xl border border-border bg-ink px-8 py-14 text-center sm:px-16">
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-bg text-balance">
            Build safer AI across languages.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-bg/70 text-pretty">
            VERIAUDIT is open to collaboration with researchers, developers, policymakers, and
            organizations working on AI safety, multilingual NLP, evaluation, and governance.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button href="/platform" variant="secondary" className="!bg-bg !text-ink !border-bg">
              Explore the Platform <ArrowRight className="h-4 w-4" />
            </Button>
            <Button href="/contact" variant="ghost" className="!text-bg hover:!text-bg/70">
              Request an Audit
            </Button>
          </div>
        </div>
      </Container>
    </section>
  );
}
