import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Container } from "../ui/Container";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { GithubIcon } from "../ui/GithubIcon";
import { CrossLingualDiagram } from "./CrossLingualDiagram";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="absolute inset-0 grid-overlay opacity-40 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_40%,transparent_100%)]" />
      <Container className="relative py-20 sm:py-28">
        <div className="max-w-3xl">
          <Badge tone="accent">Open-source · AI safety research</Badge>
          <h1 className="mt-5 font-mono text-sm uppercase tracking-[0.2em] text-ink-faint">
            VERIAUDIT
          </h1>
          <p className="mt-3 text-4xl sm:text-6xl font-semibold tracking-tight text-ink text-balance">
            Does AI safety survive translation?
          </p>
          <p className="mt-6 max-w-xl text-lg leading-8 text-ink-muted text-pretty">
            An open-source red-teaming platform for cross-lingual AI safety evaluation —
            starting with English, Urdu, Roman Urdu, and code-switched inputs.
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Button href="/platform" variant="primary">
              Explore the Platform <ArrowRight className="h-4 w-4" />
            </Button>
            <Button href="/research" variant="secondary">
              View Research
            </Button>
            <Button href="https://github.com/abeeranajam31/veriaudit" variant="ghost" external>
              <GithubIcon className="h-4 w-4" /> GitHub
            </Button>
          </div>

          <div className="mt-5">
            <Link
              href="/contact"
              className="text-sm font-medium text-accent hover:underline underline-offset-4"
            >
              Request an Audit →
            </Link>
          </div>
        </div>

        <div className="mt-16">
          <CrossLingualDiagram />
        </div>
      </Container>
    </section>
  );
}
