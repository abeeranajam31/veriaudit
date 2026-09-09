"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FORM_LABELS, LinguisticForm, ModelLanguageResult } from "@/lib/types";
import { demoModels } from "@/lib/gapEvaluator";

const gridColor = "var(--border)";
const inkMuted = "var(--ink-muted)";
const modelColors = ["#0f6b52", "#2f8f6f", "#8fb9a8"];

export function SafetyByLanguageChart({ results }: { results: ModelLanguageResult[] }) {
  const forms: LinguisticForm[] = ["english", "urdu", "roman_urdu", "code_switched"];
  const data = forms.map((form) => {
    const scores = results.filter((r) => r.form === form).map((r) => r.safetyScore);
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    return { form: FORM_LABELS[form], "Average safety score": Math.round(avg * 10) / 10 };
  });

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
        <XAxis dataKey="form" tick={{ fill: inkMuted, fontSize: 12 }} axisLine={{ stroke: gridColor }} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fill: inkMuted, fontSize: 12 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "var(--bg-raised)", border: `1px solid var(--border)`, borderRadius: 8, fontSize: 12 }}
        />
        <Bar dataKey="Average safety score" fill="#0f6b52" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ModelComparisonChart({ results }: { results: ModelLanguageResult[] }) {
  const forms: LinguisticForm[] = ["english", "urdu", "roman_urdu", "code_switched"];
  const data = forms.map((form) => {
    const row: Record<string, string | number> = { form: FORM_LABELS[form] };
    demoModels.forEach((m) => {
      const r = results.find((x) => x.modelId === m.id && x.form === form);
      row[m.name] = r ? r.safetyScore : 0;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} vertical={false} />
        <XAxis dataKey="form" tick={{ fill: inkMuted, fontSize: 12 }} axisLine={{ stroke: gridColor }} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fill: inkMuted, fontSize: 12 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{ background: "var(--bg-raised)", border: `1px solid var(--border)`, borderRadius: 8, fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: inkMuted }} />
        {demoModels.map((m, i) => (
          <Bar key={m.id} dataKey={m.name} fill={modelColors[i % modelColors.length]} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
