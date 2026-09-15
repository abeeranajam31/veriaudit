# VeriAudit Website — Pilot Results Update Plan

**Status: planning only. No frontend file has been modified. Nothing has been deployed.**

## Scope

A minimal, additive update — not a rewrite of the site. One new section added to one existing page, plus one small status-badge update on a second page.

## File/component that needs modification

**`frontend/src/app/research/page.tsx`** — insert a new `<section>` (matching the existing `space-y-10` sections under `<Eyebrow>Research</Eyebrow>`) between the current "Methodology" and "Limitations" sections, using the same `Container`/`Badge` components already imported on this page. No new dependencies needed.

Secondary, optional touch (not required): **`frontend/src/app/benchmark/page.tsx`**'s `<Badge tone="warn">Pilot subset...</Badge>` line could be updated to reflect that the 30-intent pilot is now fully evaluated with results, rather than just "shipped." Left as optional since Phase 5 asks for a minimal update, not a full rewrite; the proposed copy for this optional change is included at the end of this document for the maintainer to accept or skip.

## Proposed website copy (to insert in `research/page.tsx`)

### Headline

> Pilot benchmark: 240 evaluations across 4 linguistic variants

### Key statistics (proposed as a stat grid, 4-6 items, consistent with the existing Badge/card visual style)

- 240 evaluations
- 30 intents
- 2 models
- 4 linguistic variants
- 6 safety categories
- Overall mean observed CLSG: **25.8 pp**
- Largest observed gap: **46.2 pp** (Aya Expanse 8B × Urdu)
- Roman Urdu: **36.0%** failure rate
- 18 ambiguous cases

### Methodology note (proposed body text, verbatim)

> Primary safety rates exclude ambiguous cases. SAFE = safe_refusal /
> safe_completion; UNSAFE = partial_compliance / unsafe_compliance.

### Limitations note (proposed body text, verbatim)

> This is a 30-intent pilot across two models. Results are descriptive and
> require replication with more models, intents, languages, and independent
> human annotation.

### Links/buttons to add

| Label | Target | Condition |
|---|---|---|
| Read the technical report | `/docs/veriaudit_pilot_report.md` (or a rendered `/report` route if the site later adds one — this plan does not add a new route) — for now, link directly to the GitHub-rendered file: `https://github.com/abeeranajam31/veriaudit/blob/main/docs/veriaudit_pilot_report.md` | Always (report exists now) |
| Full results table | `https://github.com/abeeranajam31/veriaudit/blob/main/docs/results_table.md` | Always (exists now) |
| View on GitHub | `https://github.com/abeeranajam31/veriaudit` | Always |
| Hugging Face dataset | *(not added yet)* | **Only once the dataset actually exists on the Hub** — per Phase 4, the HF dataset has not been published. Do not add this link or claim it is available until Phase 4's upload actually happens and the maintainer confirms the URL. |

## Full proposed JSX section (for the maintainer/implementer to drop in; not applied to any file by this task)

```tsx
<div>
  <h2 className="text-lg font-semibold text-ink">Pilot Benchmark: 240 evaluations across 4 linguistic variants</h2>
  <p className="mt-2 text-sm text-ink-muted">
    These are preliminary pilot results from VeriAudit v0.1 — a 30-intent,
    2-model pilot benchmark, not a validated general-purpose safety
    evaluation.
  </p>

  <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
    {[
      ["Evaluations", "240"],
      ["Intents", "30"],
      ["Models", "2"],
      ["Linguistic variants", "4"],
      ["Safety categories", "6"],
      ["Ambiguous cases", "18"],
    ].map(([label, value]) => (
      <div key={label} className="rounded-lg border border-border bg-bg-raised p-3">
        <dt className="font-mono text-xs uppercase tracking-wide text-ink-faint">{label}</dt>
        <dd className="mt-1 text-lg font-semibold text-ink">{value}</dd>
      </div>
    ))}
  </dl>

  <div className="mt-4 grid gap-3 sm:grid-cols-2">
    <div className="rounded-lg border border-border bg-bg-raised p-4">
      <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Overall mean observed CLSG</div>
      <div className="mt-1 text-2xl font-semibold text-ink">25.8 pp</div>
    </div>
    <div className="rounded-lg border border-border bg-bg-raised p-4">
      <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Largest observed gap</div>
      <div className="mt-1 text-2xl font-semibold text-ink">46.2 pp</div>
      <div className="mt-1 text-xs text-ink-muted">Aya Expanse 8B × Urdu</div>
    </div>
  </div>

  <p className="mt-4 text-sm text-ink-muted">
    Roman Urdu shows the highest observed failure rate (36.0%) and the
    largest concentration of ambiguous/undecidable outputs among the
    variants tested.
  </p>

  <p className="mt-4 text-xs text-ink-faint">
    Primary safety rates exclude ambiguous cases. SAFE = safe_refusal /
    safe_completion; UNSAFE = partial_compliance / unsafe_compliance.
  </p>
  <p className="mt-2 text-xs text-ink-faint">
    This is a 30-intent pilot across two models. Results are descriptive
    and require replication with more models, intents, languages, and
    independent human annotation.
  </p>

  <div className="mt-4 flex flex-wrap gap-4 text-sm">
    <a href="https://github.com/abeeranajam31/veriaudit/blob/main/docs/veriaudit_pilot_report.md"
       target="_blank" rel="noopener noreferrer"
       className="font-medium text-accent hover:underline underline-offset-4">
      Read the technical report →
    </a>
    <a href="https://github.com/abeeranajam31/veriaudit/blob/main/docs/results_table.md"
       target="_blank" rel="noopener noreferrer"
       className="font-medium text-accent hover:underline underline-offset-4">
      Full results table →
    </a>
    <a href="https://github.com/abeeranajam31/veriaudit"
       target="_blank" rel="noopener noreferrer"
       className="font-medium text-accent hover:underline underline-offset-4">
      View on GitHub →
    </a>
    {/* Hugging Face dataset link intentionally omitted until Phase 4 publishes */}
  </div>
</div>
```

## Optional secondary change — `benchmark/page.tsx` badge copy

Current: `Pilot subset: {pilotDataset.length} intents shipped today. Full VERIAUDIT-500 is under development.`

Proposed (optional, only if the maintainer wants this page updated too):
`v0.1 pilot: 30 intents × 4 languages × 2 models, 240 evaluations completed. Full VERIAUDIT-500 is under development.`

## Deployment status

**Not deployed.** No file has been edited. This document is the complete proposed change set; applying it (editing `research/page.tsx`, optionally `benchmark/page.tsx`) and deploying to Vercel both require separate explicit approval, per the task's gating instructions.
