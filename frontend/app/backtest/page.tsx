"use client";

import { useState } from "react";
import { api, getToken } from "@/lib/api";
import { num } from "@/lib/format";
import { ErrorBox, PageHeader, StatCard } from "@/components/ui";

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("RELIANCE");
  const [universe, setUniverse] = useState("nifty500");
  const [bars, setBars] = useState(400);
  const [warmup, setWarmup] = useState(120);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const authed = true;

  async function run() {
    setErr(null);
    setBusy(true);
    setRes(null);
    try {
      const r = await api.post("/api/backtest", { symbol, universe, bars, warmup });
      setRes(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const m = res?.metrics;
  return (
    <div>
      <PageHeader
        title="Backtesting"
        desc="Runs the same SMC pipeline bar-by-bar with look-ahead protection and a conservative intrabar assumption."
      />
      {!authed && (
        <div className="panel mb-3 border-warn/40 bg-warn/5 p-3 text-sm text-warn">Sign in to run backtests.</div>
      )}
      <div className="panel mb-4 flex flex-wrap items-end gap-3 p-4">
        <Field label="Symbol"><input className="input w-32" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} /></Field>
        <Field label="Universe">
          <select className="input" value={universe} onChange={(e) => setUniverse(e.target.value)}>
            <option value="nifty500">Nifty 500</option>
            <option value="forex">Forex</option>
            <option value="metals">Metals</option>
            <option value="commodities">Commodities</option>
          </select>
        </Field>
        <Field label="Bars"><input className="input w-24" type="number" value={bars} onChange={(e) => setBars(Number(e.target.value))} /></Field>
        <Field label="Warmup"><input className="input w-24" type="number" value={warmup} onChange={(e) => setWarmup(Number(e.target.value))} /></Field>
        <button className="btn btn-accent" onClick={run} disabled={busy}>{busy ? "Running…" : "Run backtest"}</button>
      </div>

      {err && <ErrorBox error={err} />}

      {m && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Trades" value={m.trades} />
            <StatCard label="Win rate" value={`${num(m.win_rate * 100, 1)}%`} />
            <StatCard label="Net profit" value={num(m.net_profit, 0)} tone={m.net_profit >= 0 ? "bull" : "bear"} />
            <StatCard label="Profit factor" value={m.profit_factor === null ? "—" : num(m.profit_factor, 2)} />
            <StatCard label="Expectancy" value={num(m.expectancy, 1)} />
            <StatCard label="Max drawdown" value={num(m.max_drawdown, 0)} tone="bear" />
            <StatCard label="Avg R:R" value={num(m.avg_reward_risk, 2)} />
            <StatCard label="Max cons. losses" value={m.max_consecutive_losses} />
          </div>
          <p className="mt-2 text-xs text-muted">{res.disclaimer}</p>

          <div className="panel mt-4 overflow-auto">
            <table className="w-full text-sm">
              <thead><tr>{["#", "Symbol", "Dir", "Entry", "Exit", "Qty", "P&L", "R:R", "Reason", "Bars"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>
                {(res.trades ?? []).map((t: any, i: number) => (
                  <tr key={i} className="border-t border-border/50">
                    <td className="td">{i + 1}</td>
                    <td className="td">{t.symbol}</td>
                    <td className="td">{t.direction}</td>
                    <td className="td">{num(t.entry, 2)}</td>
                    <td className="td">{num(t.exit, 2)}</td>
                    <td className="td">{num(t.qty, 2)}</td>
                    <td className={`td ${t.pnl >= 0 ? "text-bull" : "text-bear"}`}>{num(t.pnl, 0)}</td>
                    <td className="td">{num(t.reward_risk_planned, 1)}</td>
                    <td className="td text-xs text-muted">{t.exit_reason}</td>
                    <td className="td">{t.bars_held}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      {children}
    </label>
  );
}
