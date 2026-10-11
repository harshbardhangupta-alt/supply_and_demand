"use client";

import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import { ErrorBox, Loading, PageHeader, StatCard } from "@/components/ui";

export default function AnalyticsPage() {
  const { data, error, loading } = usePoll<any>(() => api.get("/api/analytics"), 6000);
  const m = data?.metrics;
  return (
    <div>
      <PageHeader title="Analytics" desc="Performance of completed paper trades." />
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : m && m.trades > 0 ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Trades" value={m.trades} />
            <StatCard label="Win rate" value={`${num(m.win_rate * 100, 1)}%`} />
            <StatCard label="Net profit" value={num(m.net_profit, 0)} tone={m.net_profit >= 0 ? "bull" : "bear"} />
            <StatCard label="Profit factor" value={m.profit_factor === null ? "—" : num(m.profit_factor, 2)} />
            <StatCard label="Avg win" value={num(m.avg_win, 0)} tone="bull" />
            <StatCard label="Avg loss" value={num(m.avg_loss, 0)} tone="bear" />
            <StatCard label="Expectancy" value={num(m.expectancy, 1)} />
            <StatCard label="Max drawdown" value={num(m.max_drawdown, 0)} tone="bear" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Breakdown title="By symbol" data={m.by_symbol} />
            <Breakdown title="By exit reason / entry model" data={m.by_entry_model} />
          </div>
        </>
      ) : (
        <div className="panel p-6 text-sm text-muted">
          No completed trades yet. Run a paper evaluation pass (Automated Trading) and let
          positions close, or use Backtesting for historical performance.
        </div>
      )}
    </div>
  );
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data || {});
  return (
    <div className="panel p-4">
      <div className="mb-2 text-sm font-semibold">{title}</div>
      {entries.length === 0 ? (
        <p className="text-sm text-muted">—</p>
      ) : (
        entries.map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-border/50 py-1 text-sm last:border-0">
            <span className="text-muted">{k}</span>
            <span className={v >= 0 ? "text-bull" : "text-bear"}>{num(v, 0)}</span>
          </div>
        ))
      )}
    </div>
  );
}
