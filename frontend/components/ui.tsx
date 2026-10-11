"use client";

import { biasColor, scoreColor } from "@/lib/format";

export function StatCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: "bull" | "bear" | "neutral";
}) {
  const color =
    tone === "bull" ? "text-bull" : tone === "bear" ? "text-bear" : "text-txt";
  return (
    <div className="panel p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${color}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}

export function PageHeader({
  title,
  desc,
  right,
}: {
  title: string;
  desc?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {desc && <p className="mt-0.5 text-sm text-muted">{desc}</p>}
      </div>
      {right}
    </div>
  );
}

export function Bias({ value }: { value?: string | null }) {
  return <span className={`font-medium ${biasColor(value)}`}>{value ?? "—"}</span>;
}

export function Score({ value }: { value?: number | null }) {
  return (
    <span className={`font-semibold ${scoreColor(value)}`}>
      {value === undefined || value === null ? "—" : value.toFixed(0)}
    </span>
  );
}

export function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "bull" | "bear" | "warn" | "neutral" | "accent";
}) {
  const map: Record<string, string> = {
    bull: "bg-bull/15 text-bull",
    bear: "bg-bear/15 text-bear",
    warn: "bg-warn/15 text-warn",
    accent: "bg-accent/15 text-accent",
    neutral: "bg-border/60 text-muted",
  };
  return <span className={`tag ${map[tone]}`}>{children}</span>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="p-6 text-sm text-muted">{label}</div>;
}

export function ErrorBox({ error }: { error: string }) {
  return (
    <div className="panel border-bear/40 bg-bear/5 p-4 text-sm text-bear">
      {error}
    </div>
  );
}
