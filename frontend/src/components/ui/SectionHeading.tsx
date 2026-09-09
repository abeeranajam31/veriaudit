import { ReactNode } from "react";
import clsx from "clsx";

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
      {children}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  align?: "left" | "center";
}) {
  return (
    <div className={clsx("max-w-2xl", align === "center" && "mx-auto text-center")}>
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-ink text-balance">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-base leading-7 text-ink-muted text-pretty">{description}</p>
      )}
    </div>
  );
}
