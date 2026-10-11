"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import Sparkline from "@/components/Sparkline";
import WhyButton, { Why } from "@/components/WhyButton";
import { AreaChart, Donut, ProgressBar } from "@/components/charts";

type Selected = {
  symbol: string; name: string; direction: string;
  entry: number | null; stop: number | null; target: number | null;
  reward_risk: number | null; score: number; why: Why;
};
type Hist = {
  symbol: string; direction: string; entry: number; stop: number; target: number;
  exit: number; outcome: string; pnl: number; reward_risk: number; bars_held: number;
};
type Rej = { symbol: string; name: string; score: number; rejection_reason: string; why: Why };
type Board = {
  provider: string; feed_mode: string; data_connected?: boolean;
  summary: { scanned: number; selected: number; rejected: number; resolved: number;
    wins: number; losses: number; accuracy: number | null; avg_reward_risk: number | null };
  selected: Selected[]; rejected: Rej[]; history: Hist[];
};

const UNIVERSES = [
  { k: "nifty500", label: "Nifty 500" },
  { k: "forex", label: "Forex" },
  { k: "metals", label: "Metals" },
  { k: "commodities", label: "Commodities" },
];
const ORANGE = "#ef7518", GREEN = "#36c76f", RED = "#ef5350";

export default function Dashboard() {
  const [universe, setUniverse] = useState("nifty500");
  const [scanLimit, setScanLimit] = useState(40);
  const [tab, setTab] = useState<"selected" | "rejected">("selected");
  const { data, loading, error, refresh } = usePoll<Board>(
    () => api.get(`/api/signals/board?universe=${universe}&scan_limit=${scanLimit}&eval_limit=8`),
    0,
    [universe, scanLimit]
  );
  const s = data?.summary;

  // rolling accuracy series for the area chart
  const accSeries = useMemo(() => {
    const h = (data?.history ?? []).filter((x) => x.outcome === "target" || x.outcome === "stop");
    const out: number[] = [];
    let w = 0;
    h.forEach((x, i) => { if (x.outcome === "target") w++; out.push(Math.round((w / (i + 1)) * 100)); });
    return out.length >= 2 ? out : [50, 50];
  }, [data]);

  const donut = useMemo(() => {
    const w = s?.wins ?? 0, l = s?.losses ?? 0, p = s?.selected ?? 0;
    return [
      { label: "Target hit", value: w, color: GREEN },
      { label: "SL hit", value: l, color: RED },
      { label: "Pending", value: p, color: ORANGE },
    ];
  }, [s]);

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Signal Dashboard</h1>
          <p className="mt-0.5 text-sm text-muted">
            Real-time SMC stock selection &amp; outcomes — analysis only, no live orders.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select className="input" value={universe} onChange={(e) => setUniverse(e.target.value)}>
            {UNIVERSES.map((u) => <option key={u.k} value={u.k}>{u.label}</option>)}
          </select>
          <select className="input" value={scanLimit} onChange={(e) => setScanLimit(Number(e.target.value))}>
            {[20, 40, 60, 80].map((n) => <option key={n} value={n}>Scan {n}</option>)}
          </select>
          <button className="btn btn-accent" onClick={refresh} disabled={loading}>
            {loading ? "Scanning…" : "↻ Run scan"}
          </button>
        </div>
      </div>

      {error && <div className="panel border-bear/40 bg-bear/5 p-3 text-sm text-bear">{error}</div>}

      {data && !data.data_connected && (
        <div className="panel flex flex-wrap items-center gap-2 border-warn/40 bg-warn/5 p-3 text-sm text-warn">
          <span>⚠ Dhan is not connected — no live data. Add your Client ID &amp; Access Token to load stocks.</span>
          <a href="/connections" className="ml-auto rounded-md border border-warn/50 px-2 py-1 text-xs hover:bg-warn/10">Connect Dhan →</a>
        </div>
      )}

      {/* stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Accuracy" value={s?.accuracy != null ? `${s.accuracy}%` : "—"}
          sub={<span className={(s?.accuracy ?? 0) >= 50 ? "text-bull" : "text-warn"}>{(s?.accuracy ?? 0) >= 50 ? "Healthy" : "Low sample"}</span>}
          chart={<Sparkline data={accSeries} color={ORANGE} width={96} height={34} />} />
        <Stat label="Stocks Selected" value={loading ? "…" : s?.selected ?? 0}
          sub={`of ${s?.scanned ?? 0} scanned`} icon="box" />
        <Stat label="Resolved Signals" value={loading ? "…" : s?.resolved ?? 0}
          sub={<span>{s?.wins ?? 0} target · {s?.losses ?? 0} SL</span>} icon="grid" />
        <Stat label="Scan Status" value={<span className="text-bull">Live ●</span>}
          sub={`feed: ${data?.provider ?? "…"}${data?.feed_mode === "synthetic" ? " (sim)" : ""}`} icon="radar" />
      </div>

      {/* overview table */}
      <div className="panel">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3.5">
          <div className="font-semibold">Setups Overview</div>
          <div className="flex gap-1 rounded-lg border border-border bg-panel2 p-0.5">
            {([["selected", `Selected ${s?.selected ?? 0}`], ["rejected", `Rejected ${s?.rejected ?? 0}`]] as const).map(([k, lbl]) => (
              <button key={k} onClick={() => setTab(k)}
                className={`rounded-md px-3 py-1 text-xs transition ${tab === k ? "bg-accent/15 text-accent" : "text-muted hover:text-txt"}`}>
                {lbl}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-auto">
          {tab === "selected" ? (
            <table className="w-full text-sm">
              <thead><tr>{["Symbol", "Direction", "Score", "Entry", "Stop-loss", "Target", "R:R", "Why"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>
                {loading && !data ? <SkelRows cols={8} /> :
                  (data?.selected.length ?? 0) === 0 ? (
                    <tr><td colSpan={8} className="td py-8 text-center text-muted">No setups meet the strategy right now.</td></tr>
                  ) : data!.selected.map((x) => (
                    <tr key={x.symbol} className="border-t border-border/60">
                      <td className="td">
                        <a href={`/chart?symbol=${x.symbol}`} className="font-medium hover:text-accent">{x.symbol}</a>
                        <div className="max-w-[160px] truncate text-xs text-muted">{x.name}</div>
                      </td>
                      <td className="td">
                        <span className={`inline-flex items-center gap-1.5 ${x.direction === "long" ? "text-bull" : "text-bear"}`}>
                          <span className="h-1.5 w-1.5 rounded-full" style={{ background: x.direction === "long" ? GREEN : RED }} />
                          {x.direction === "long" ? "Long" : "Short"}
                        </span>
                      </td>
                      <td className="td w-40">
                        <div className="flex items-center gap-2">
                          <ProgressBar value={x.score} />
                          <span className="w-8 text-right text-xs text-accent">{Math.round(x.score)}</span>
                        </div>
                      </td>
                      <td className="td">{num(x.entry)}</td>
                      <td className="td text-bear">{num(x.stop)}</td>
                      <td className="td text-bull">{num(x.target)}</td>
                      <td className="td font-medium text-accent">{num(x.reward_risk, 1)}</td>
                      <td className="td"><WhyButton why={x.why} symbol={x.symbol} /></td>
                    </tr>
                  ))}
              </tbody>
            </table>
          ) : (
            <table className="w-full text-sm">
              <thead><tr>{["Symbol", "Score", "Rejection reason", "Why"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
              <tbody>
                {data?.rejected.map((r) => (
                  <tr key={r.symbol} className="border-t border-border/60">
                    <td className="td font-medium">{r.symbol}</td>
                    <td className="td">{Math.round(r.score)}</td>
                    <td className="td text-xs text-muted">{r.rejection_reason}</td>
                    <td className="td"><WhyButton why={r.why} symbol={r.symbol} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="panel p-5">
          <div className="mb-3 font-semibold">Accuracy Performance</div>
          <AreaChart data={accSeries} yMin={0} yMax={100} />
          <div className="mt-4 grid grid-cols-4 gap-3 border-t border-border pt-4 text-center">
            <Mini label="Accuracy" value={s?.accuracy != null ? `${s.accuracy}%` : "—"} />
            <Mini label="Resolved" value={s?.resolved ?? 0} />
            <Mini label="SL hits" value={s?.losses ?? 0} tone="bear" />
            <Mini label="Avg R:R" value={s?.avg_reward_risk != null ? `${s.avg_reward_risk}:1` : "—"} />
          </div>
        </div>
        <div className="panel p-5">
          <div className="mb-4 font-semibold">Outcome Breakdown</div>
          <Donut
            segments={donut}
            centerValue={s?.resolved ?? 0}
            centerLabel="Resolved"
          />
        </div>
      </div>

      {/* signal log */}
      <div className="panel">
        <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
          <div className="font-semibold">Signal Log</div>
          <span className="text-xs text-muted">whichever of target / stop hit first</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead><tr>{["Signal", "Direction", "Status", "Detail", "R:R", "P&L", "Bars"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>
              {(data?.history ?? []).length === 0 ? (
                <tr><td colSpan={7} className="td py-8 text-center text-muted">No resolved signals.</td></tr>
              ) : data!.history.map((h, i) => (
                <tr key={i} className="border-t border-border/60">
                  <td className="td font-medium">{h.symbol}</td>
                  <td className="td">{h.direction === "long" ? "Long" : "Short"}</td>
                  <td className="td">
                    {h.outcome === "target" ? (
                      <span className="tag bg-bull/15 text-bull">Target hit</span>
                    ) : h.outcome === "stop" ? (
                      <span className="tag bg-warn/15 text-warn">SL hit</span>
                    ) : <span className="tag bg-border/60 text-muted">{h.outcome}</span>}
                  </td>
                  <td className="td text-xs text-muted">entry {num(h.entry)} → exit {num(h.exit)}</td>
                  <td className="td">{num(h.reward_risk, 1)}</td>
                  <td className={`td ${h.pnl >= 0 ? "text-bull" : "text-bear"}`}>{num(h.pnl, 0)}</td>
                  <td className="td text-muted">{h.bars_held}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="px-5 py-3 text-[11px] text-muted">
          Analysis only — no live orders are placed. Outcomes are computed by replaying the strategy
          over recent {data?.feed_mode === "synthetic" ? "simulated " : ""}data with a conservative intrabar assumption.
        </p>
      </div>
    </div>
  );
}

function Stat({ label, value, sub, chart, icon }: {
  label: string; value: React.ReactNode; sub: React.ReactNode; chart?: React.ReactNode; icon?: string;
}) {
  return (
    <div className="panel p-4">
      <div className="flex items-start justify-between">
        <span className="text-xs uppercase tracking-wide text-muted">{label}</span>
        {chart ?? <IconBadge kind={icon} />}
      </div>
      <div className="mt-2 text-3xl font-semibold text-accent">{value}</div>
      <div className="mt-1 text-xs text-muted">{sub}</div>
    </div>
  );
}

function IconBadge({ kind }: { kind?: string }) {
  const path: Record<string, JSX.Element> = {
    box: <path d="M21 8 12 3 3 8l9 5 9-5zM3 8v8l9 5 9-5V8" />,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    radar: <><circle cx="12" cy="12" r="9" /><path d="M12 12 18 6M12 3v3M12 18v3" /></>,
  };
  return (
    <span className="text-muted">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
        {path[kind ?? "grid"] ?? path.grid}
      </svg>
    </span>
  );
}

function Mini({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "bear" }) {
  return (
    <div>
      <div className={`text-lg font-semibold ${tone === "bear" ? "text-bear" : "text-txt"}`}>{value}</div>
      <div className="text-[11px] text-muted">{label}</div>
    </div>
  );
}

function SkelRows({ cols }: { cols: number }) {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i} className="border-t border-border/60">
          {Array.from({ length: cols }).map((__, j) => (
            <td key={j} className="td"><div className="h-4 animate-pulse rounded bg-panel2" /></td>
          ))}
        </tr>
      ))}
    </>
  );
}
