import Link from "next/link";
import { Container } from "../ui/Container";
import { Eyebrow } from "../ui/SectionHeading";
import { Badge } from "../ui/Badge";

export function MetricSection() {
  return (
    <section className="border-b border-border py-20 sm:py-28">
      <Container>
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <Eyebrow>The core metric</Eyebrow>
            <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-ink">
              Cross-Lingual Safety Gap (CLSG)
            </h2>
            <div className="mt-3">
              <Badge tone="warn">VERIAUDIT proposed metric — not yet independently validated</Badge>
            </div>
            <p className="mt-5 text-base leading-7 text-ink-muted">
              CLSG is the quantitative difference between a model&apos;s safety performance in a
              reference language and its safety performance in an evaluated language, on the same
              underlying intent set.
            </p>
            <p className="mt-4 text-sm leading-6 text-ink-faint">
              We do not claim CLSG is a scientifically validated, universal measure of cross-lingual
              safety. It is a transparent, first-pass formulation, published alongside its
              assumptions and limitations so it can be scrutinized and improved.
            </p>
            <Link
              href="/methodology"
              className="mt-5 inline-block text-sm font-medium text-accent hover:underline underline-offset-4"
            >
              Read the full methodology →
            </Link>
          </div>

          <div className="rounded-xl border border-border bg-bg-raised p-8">
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Formula</div>
            <div className="mt-3 rounded-lg bg-bg-subtle border border-border p-4 font-mono text-sm text-ink overflow-x-auto">
              CLSG(ref → eval) = safety(ref) − safety(eval)
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-ink-faint">Reference language</div>
                <div className="mt-1 text-lg font-semibold text-ink">English</div>
              </div>
              <div>
                <div className="text-xs text-ink-faint">Evaluation language</div>
                <div className="mt-1 text-lg font-semibold text-ink">Urdu</div>
              </div>
            </div>

            <div className="mt-6 flex items-end justify-between rounded-lg border border-border bg-bg-subtle p-5">
              <div>
                <div className="text-xs text-ink-faint">Example gap (demo data)</div>
                <div className="mt-1 text-4xl font-semibold tabular-nums text-danger">23 pts</div>
              </div>
              <span className="font-mono text-[11px] uppercase text-warn bg-warn-soft border border-warn/30 rounded-full px-2.5 py-1">
                demo
              </span>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
