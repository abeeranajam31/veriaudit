const branches = [
  { label: "English", outcome: "Refused", score: 96, ok: true },
  { label: "Urdu", outcome: "Refused", score: 89, ok: true },
  { label: "Roman Urdu", outcome: "Partial comply", score: 74, ok: false },
  { label: "Code-Switched", outcome: "Complied", score: 68, ok: false },
];

export function CrossLingualDiagram() {
  return (
    <div className="rounded-xl border border-border bg-bg-raised p-6 sm:p-8">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-6">
        <p className="font-mono text-xs uppercase tracking-wide text-ink-faint">
          Same intent, four linguistic forms
        </p>
        <span className="font-mono text-[11px] uppercase tracking-wide text-warn bg-warn-soft border border-warn/30 rounded-full px-2.5 py-1">
          Illustrative example — not a measured result
        </span>
      </div>

      <div className="flex flex-col items-center">
        <div className="rounded-lg border border-border-strong bg-bg-subtle px-5 py-3 text-sm font-medium text-ink">
          Same underlying test intent
        </div>

        <svg
          viewBox="0 0 800 60"
          className="w-full max-w-2xl h-10 text-border-strong"
          preserveAspectRatio="none"
        >
          <line x1="400" y1="0" x2="100" y2="60" stroke="currentColor" strokeWidth="1.5" />
          <line x1="400" y1="0" x2="300" y2="60" stroke="currentColor" strokeWidth="1.5" />
          <line x1="400" y1="0" x2="500" y2="60" stroke="currentColor" strokeWidth="1.5" />
          <line x1="400" y1="0" x2="700" y2="60" stroke="currentColor" strokeWidth="1.5" />
        </svg>

        <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-4">
          {branches.map((b) => (
            <div
              key={b.label}
              className="rounded-lg border border-border bg-bg p-4 text-center"
            >
              <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">
                {b.label}
              </div>
              <div
                className={`mt-2 text-2xl font-semibold tabular-nums ${
                  b.ok ? "text-accent" : "text-danger"
                }`}
              >
                {b.score}
              </div>
              <div className="text-[11px] text-ink-muted mt-0.5">safety score</div>
              <div
                className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ${
                  b.ok
                    ? "bg-accent-soft text-accent"
                    : "bg-danger-soft text-danger"
                }`}
              >
                {b.outcome}
              </div>
            </div>
          ))}
        </div>

        <p className="mt-6 font-mono text-sm text-ink-muted">
          SAME INTENT <span className="text-danger">≠</span> SAME SAFETY
        </p>
      </div>
    </div>
  );
}
