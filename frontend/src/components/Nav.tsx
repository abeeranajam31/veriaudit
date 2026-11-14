"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X, ShieldCheck } from "lucide-react";
import { Container } from "./ui/Container";
import { Button } from "./ui/Button";

const links = [
  { href: "/#findings", label: "Findings" },
  { href: "/results", label: "Results" },
  { href: "/research", label: "Research" },
  { href: "/methodology", label: "Methodology" },
  { href: "/benchmark", label: "Benchmark" },
  { href: "/open-source", label: "Open Source" },
  { href: "/about", label: "About" },
];

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/85 backdrop-blur">
      <Container>
        <div className="flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight text-ink">
            <ShieldCheck className="h-5 w-5 text-accent" strokeWidth={1.75} />
            <span className="font-mono text-[15px]">VERIAUDIT</span>
          </Link>

          <nav className="hidden lg:flex items-center gap-7">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-ink-muted hover:text-ink transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="hidden lg:block">
            <Button href="https://github.com/abeeranajam31/veriaudit/blob/veriaudit-x-dataset/paper/v01_reanalysis/main.pdf" variant="primary" external>
              Read the paper
            </Button>
          </div>

          <button
            className="lg:hidden text-ink"
            onClick={() => setOpen((v) => !v)}
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
      </Container>

      {open && (
        <div className="lg:hidden border-t border-border bg-bg">
          <Container className="py-4 flex flex-col gap-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-md px-3 py-2.5 text-sm text-ink-muted hover:bg-bg-subtle hover:text-ink"
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-2 px-3">
              <Button href="/contact" variant="primary" className="w-full">
                Request an Audit
              </Button>
            </div>
          </Container>
        </div>
      )}
    </header>
  );
}
