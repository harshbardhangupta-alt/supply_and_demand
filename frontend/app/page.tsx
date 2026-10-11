"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import Sparkline from "@/components/Sparkline";
import WhyButton, { Why } from "@/components/WhyButton";

type Selected = {
  symbol: string; name: string; direction: string;
  entry: number | null; stop: number | null; target: number | null;
  reward_risk: number | null; score: number; status: string; why: Why;
};
type Hist = {
  symbol: string; name: string; direction: string; entry: number; stop: number;
  target: number; outcome: string; pnl: number; reward_risk: number; bars_held: number;
};
type Rej = { symbol: string; name: string; score: number; rejection_reason: string; why: Why };
type Board = {
  provider: string; feed_mode: string;
  summary: { scanned: number; selected: number; rejected: number; resolved: number;
    wins: number; losses: number; accuracy: number | null; avg_reward_risk: number | null };
  sparkline: number[];
  selected: Selected[];
  rejected: Rej[];
  history: Hist[];
};

const UNIVERSES = [
  { k: "nifty500", label: "Nifty 500" },
  { k: "forex", label: "Forex" },
  { k: "metals", label: "Metals" },
  { k: "commodities", label: "Commodities" },
];

export default function Dashboard() {
  const [universe, setUniverse] = useState("nifty500");
  const [scanLimit, setScanLimit] = useState(40);
  const { data, loading, error, refresh } = usePoll<Board>(
    () => api.get(`/api/signals/board?universe=${universe}&scan_limit=${scanLimit}&eval_limit=8`),
    0,
    [universe, scanLimit]
  );
  const [tab, setTab] = useState<"all" | "target" | "stop" | "rejected">("all");

  const s = data?.summary;
  const winPath = data?.sparkline?.length ? data.sparkline : [0, 0];

  const histRows = useMemo(() => {
    const h = data?.history ?? [];
    if (tab === "target") return h.filter((x) => x.outcome === "target");
    if (tab === "stop") return h.filter((x) => x.outcome === "stop");
    return h;
  }, [data, tab]);

  return (
    <div className="space-y-5">
      {/* controls */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1 rounded-xl border border-border bg-panel2 p-1">
          {UNIVERSES.map((u) => (
            <button key={u.k} onClick={() => setUniverse(u.k)}
              className={`rounded-lg px-3 py-1 text-sm transition ${universe === u.k ? "bg-accent/15 text-accent" : "text-muted hover:text-txt"}`}>
              {u.label}
            </button>
          ))}
        </div>
        <select className="input" value={scanLimit} onChange={(e) => setScanLimit(Number(e.target.value))}>
          {[20, 40, 60, 80].map((n) => <option key={n} value={n}>scan {n}</option>)}
        </select>
        <button className="btn btn-accent" onClick={refresh} disabled={loading}>
          {loading ? "Scanning…" : "↻ Run scan"}
        </button>
        {data && (
          <span className="ml-auto text-xs text-muted">
            feed: <span className={data.feed_mode === "synthetic" ? "text-warn" : "text-accent"}>{data.provider}</span>
            {data.feed_mode === "synthetic" && " (simulated)"}
          </span>
        )}
      </div>

      {error && <div className="panel border-bear/40 bg-bear/5 p-3 text-sm text-bear">{error}</div>}

      {/* cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="panel relative overflow-hidden border-accent/25 p-5">
          <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-accent/10 blur-2xl" />
          <div className="text-sm text-muted">Stocks Selected</div>
          <div className="mt-1 text-4xl font-semibold">{loading ? "…" : s?.selected ?? 0}</div>
          <div className="mt-1 text-xs text-muted">of {s?.scanned ?? 0} scanned · SMC strategy</div>
          <button className="btn btn-accent mt-4 w-full" onClick={refresh} disabled={loading}>
            {loading ? "Scanning…" : "Run scan"}
          </button>
        </div>

        <Card title="Accuracy" value={s?.accuracy != null ? `${s.accuracy}%` : "—"}
          sub={s ? `${s.wins}W · ${s.losses}L (resolved)` : ""} data={winPath}
          color={(s?.accuracy ?? 0) >= 50 ? "#2bff88" : "#ff4d5e"} />
        <Card title="Resolved Signals" value={loading ? "…" : s?.resolved ?? 0}
          sub="target vs SL replayed" data={winPath} color="#2bff88" />
        <Card title="Avg Reward:Risk" value={s?.avg_reward_risk != null ? `${s.avg_reward_risk}:1` : "—"}
          sub="selected setups" data={[1, 2, 2.5, 3, 3]} color="#2bff88" />
      </div>

      {/* two columns */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        {/* selected list */}
        <div className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">Selected Setups</div>
            <span className="tag bg-accent/15 text-accent">{data?.selected.length ?? 0}</span>
          </div>
          {loading && !data ? (
            <Skel rows={6} />
          ) : (data?.selected.length ?? 0) === 0 ? (
            <p className="py-6 text-center text-sm text-muted">No setups meet the strategy right now.</p>
          ) : (
            <div className="divide-y divide-border/60">
              {data!.selected.map((x) => (
                <div key={x.symbol} className="flex items-center justify-between gap-2 py-2.5">
                  <div className="min-w-0">
                    <a href={`/chart?symbol=${x.symbol}`} className="font-medium hover:text-accent">{x.symbol}</a>
                    <div className="truncate text-xs text-muted">{x.name}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-semibold ${x.direction === "long" ? "text-accent" : "text-bear"}`}>
                      {x.direction === "long" ? "Long" : "Short"}
                    </span>
                    <span className="w-9 text-right text-sm font-semibold text-accent">{Math.round(x.score)}</span>
                    <WhyButton why={x.why} symbol={x.symbol} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* history / rejected table */}
        <div className="panel p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold">Signal Outcomes</div>
            <div className="ml-auto flex gap-1 rounded-lg border border-border bg-panel2 p-0.5">
              {([["all", "All"], ["target", "Target hit"], ["stop", "SL hit"], ["rejected", "Rejected"]] as const).map(
                ([k, lbl]) => (
                  <button key={k} onClick={() => setTab(k)}
                    className={`rounded-md px-2.5 py-1 text-xs transition ${tab === k ? "bg-accent/15 text-accent" : "text-muted hover:text-txt"}`}>
                    {lbl}
                  </button>
                )
              )}
            </div>
          </div>

          {loading && !data ? (
            <Skel rows={8} />
          ) : tab === "rejected" ? (
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead><tr>{["Symbol", "Score", "Rejection reason", "Why"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                <tbody>
                  {data?.rejected.map((r) => (
                    <tr key={r.symbol} className="border-t border-border/50">
                      <td className="td font-medium">{r.symbol}</td>
                      <td className="td">{Math.round(r.score)}</td>
                      <td className="td text-xs text-muted">{r.rejection_reason}</td>
                      <td className="td"><WhyButton why={r.why} symbol={r.symbol} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead><tr>{["Symbol", "Dir", "Entry", "Stop-loss", "Target", "Outcome", "R:R", "P&L"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
                <tbody>
                  {histRows.length === 0 ? (
                    <tr><td colSpan={8} className="td py-6 text-center text-muted">No resolved signals in this view.</td></tr>
                  ) : histRows.map((h, i) => (
                    <tr key={i} className={`border-t border-border/40 ${h.outcome === "target" ? "bg-accent/[0.04]" : h.outcome === "stop" ? "bg-bear/[0.04]" : ""}`}>
                      <td className="td font-medium">{h.symbol}</td>
                      <td className="td">{h.direction === "long" ? "Long" : "Short"}</td>
                      <td className="td">{num(h.entry)}</td>
                      <td className="td text-bear">{num(h.stop)}</td>
                      <td className="td text-accent">{num(h.target)}</td>
                      <td className="td">
                        <span className={`tag ${h.outcome === "target" ? "bg-accent/15 text-accent" : h.outcome === "stop" ? "bg-bear/15 text-bear" : "bg-border/60 text-muted"}`}>
                          {h.outcome === "target" ? "Target hit" : h.outcome === "stop" ? "SL hit" : h.outcome}
                        </span>
                      </td>
                      <td className="td">{num(h.reward_risk, 1)}</td>
                      <td className={`td ${h.pnl >= 0 ? "text-accent" : "text-bear"}`}>{num(h.pnl, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-3 text-[11px] text-muted">
            Analysis only — no live orders are placed. Outcomes are computed by replaying the
            strategy over recent {data?.feed_mode === "synthetic" ? "simulated" : ""} data
            (whichever of target/stop is hit first, conservative intrabar assumption).
          </p>
        </div>
      </div>
    </div>
  );
}

function Card({ title, value, sub, data, color }: {
  title: string; value: React.ReactNode; sub: string; data: number[]; color: string;
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-start justify-between">
        <div className="text-sm text-muted">{title}</div>
        <Sparkline data={data} color={color} width={110} height={38} />
      </div>
      <div className="mt-1 text-3xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-muted">{sub}</div>
    </div>
  );
}

function Skel({ rows }: { rows: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-7 animate-pulse rounded-md bg-panel2" />
      ))}
    </div>
  );
}
