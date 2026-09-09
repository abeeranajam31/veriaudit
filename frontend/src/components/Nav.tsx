"use client";

import Link from "next/link";
import { useState } from "react";
import { Menu, X, ShieldCheck } from "lucide-react";
import { Container } from "./ui/Container";
import { Button } from "./ui/Button";

const links = [
  { href: "/platform", label: "Platform" },
  { href: "/research", label: "Research" },
  { href: "/benchmark", label: "Benchmark" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/open-source", label: "Open Source" },
  { href: "/pricing", label: "Pricing" },
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
            <Button href="/contact" variant="primary">
              Request an Audit
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
