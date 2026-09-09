import { ReactNode } from "react";
import clsx from "clsx";

type Tone = "neutral" | "accent" | "warn" | "danger";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-bg-subtle text-ink-muted border-border-strong",
  accent: "bg-accent-soft text-accent border-accent/30",
  warn: "bg-warn-soft text-warn border-warn/30",
  danger: "bg-danger-soft text-danger border-danger/30",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide font-mono",
        toneClasses[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
