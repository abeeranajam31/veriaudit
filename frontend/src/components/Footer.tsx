import Link from "next/link";
import { ShieldCheck, Mail } from "lucide-react";
import { Container } from "./ui/Container";
import { GithubIcon } from "./ui/GithubIcon";

const columns = [
  {
    title: "Platform",
    links: [
      { href: "/platform", label: "Platform" },
      { href: "/research", label: "Research" },
      { href: "/benchmark", label: "Benchmark" },
      { href: "/leaderboard", label: "Leaderboard" },
    ],
  },
  {
    title: "Project",
    links: [
      { href: "/open-source", label: "Open Source" },
      { href: "/methodology", label: "Methodology" },
      { href: "/pricing", label: "Pricing" },
      { href: "/about", label: "About" },
    ],
  },
  {
    title: "Contact",
    links: [
      { href: "/contact", label: "Request an Audit" },
      { href: "mailto:veriiaudit@gmail.com", label: "veriiaudit@gmail.com" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-bg-subtle mt-24">
      <Container className="py-14">
        <div className="grid grid-cols-2 gap-10 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-1">
            <Link href="/" className="flex items-center gap-2 font-semibold text-ink">
              <ShieldCheck className="h-5 w-5 text-accent" strokeWidth={1.75} />
              <span className="font-mono text-[15px]">VERIAUDIT</span>
            </Link>
            <p className="mt-3 text-sm leading-6 text-ink-muted max-w-[22ch]">
              Does AI safety survive translation?
            </p>
            <div className="mt-4 flex items-center gap-3">
              <a
                href="https://github.com/abeeranajam31/veriaudit"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub"
                className="text-ink-muted hover:text-ink"
              >
                <GithubIcon className="h-4 w-4" />
              </a>
              <a
                href="mailto:veriiaudit@gmail.com"
                aria-label="Email"
                className="text-ink-muted hover:text-ink"
              >
                <Mail className="h-4 w-4" />
              </a>
            </div>
          </div>

          {columns.map((col) => (
            <div key={col.title}>
              <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">
                {col.title}
              </div>
              <ul className="mt-3 space-y-2.5">
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link href={l.href} className="text-sm text-ink-muted hover:text-ink">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-2 border-t border-border pt-6 text-xs text-ink-faint sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 VERIAUDIT. Open-source AI safety evaluation infrastructure.</p>
          <p>Research prototype. Results shown are illustrative unless explicitly labeled verified.</p>
        </div>
      </Container>
    </footer>
  );
}
