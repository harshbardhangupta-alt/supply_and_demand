"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import { Bias, ErrorBox, Loading, PageHeader, Pill, Score } from "@/components/ui";
import WhyButton, { Why } from "@/components/WhyButton";

type Row = {
  symbol: string;
  name: string;
  price: number | null;
  weekly_bias: string | null;
  daily_bias: string | null;
  h4_structure: string | null;
  h1_structure: string | null;
  direction: string | null;
  bos: string | null;
  fvg: string | null;
  zone_state: string | null;
  zone_fresh: boolean | null;
  score: number;
  entry: number | null;
  stop: number | null;
  target: number | null;
  reward_risk: number | null;
  qty: number | null;
  risk_pct: number | null;
  eligible: boolean;
  rejection_reason: string | null;
  why?: Why;
};

type ScanResult = {
  total: number;
  eligible: number;
  provider: string;
  feed_mode: string;
  last_update: string | null;
  rows: Row[];
};

export default function ScannerPage() {
  const [limit, setLimit] = useState(40);
  const [q, setQ] = useState("");
  const [onlyEligible, setOnlyEligible] = useState(false);
  const [sortKey, setSortKey] = useState<keyof Row>("score");
  const { data, error, loading, refresh } = usePoll<ScanResult>(
    () => api.get(`/api/scanner/nifty500?limit=${limit}`),
    0,
    [limit]
  );

  const rows = useMemo(() => {
    let r = data?.rows ?? [];
    if (q) r = r.filter((x) => (x.symbol + x.name).toLowerCase().includes(q.toLowerCase()));
    if (onlyEligible) r = r.filter((x) => x.eligible);
    r = [...r].sort((a, b) => {
      const av = a[sortKey] as number | null;
      const bv = b[sortKey] as number | null;
      if (typeof av === "number" && typeof bv === "number") return bv - av;
      return String(bv ?? "").localeCompare(String(av ?? ""));
    });
    return r;
  }, [data, q, onlyEligible, sortKey]);

  return (
    <div>
      <PageHeader
        title="Nifty 500 SMC Scanner"
        desc="Full constituent universe scanned by the shared SMC engine. Every stock stays visible with its exact rejection reason."
        right={
          <div className="flex flex-wrap items-center gap-2">
            {data && (
              <Pill tone="accent">
                {data.eligible}/{data.total} eligible
              </Pill>
            )}
            {data && <Pill tone={data.feed_mode === "synthetic" ? "warn" : "neutral"}>{data.provider}</Pill>}
            <button className="btn" onClick={refresh}>
              ↻ Rescan
            </button>
          </div>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          className="input w-56"
          placeholder="Search symbol / name…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="input" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
          {[20, 40, 60, 80].map((n) => (
            <option key={n} value={n}>
              Scan {n}
            </option>
          ))}
        </select>
        <select
          className="input"
          value={sortKey as string}
          onChange={(e) => setSortKey(e.target.value as keyof Row)}
        >
          <option value="score">Sort: Score</option>
          <option value="reward_risk">Sort: R:R</option>
          <option value="symbol">Sort: Symbol</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-muted">
          <input type="checkbox" checked={onlyEligible} onChange={(e) => setOnlyEligible(e.target.checked)} />
          Eligible only
        </label>
        {data?.last_update && (
          <span className="text-xs text-muted">Updated {new Date(data.last_update).toLocaleTimeString()}</span>
        )}
      </div>

      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading label="Scanning universe…" />
      ) : (
        <div className="panel overflow-auto" style={{ maxHeight: "72vh" }}>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {["Symbol", "Price", "Weekly", "Daily", "4H", "1H", "Dir", "BOS", "FVG", "Zone", "Score", "Entry", "Stop", "Target", "R:R", "Qty", "Risk%", "Status", "Why"].map(
                  (h) => (
                    <th key={h} className="th">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.symbol} className="border-t border-border/50 hover:bg-panel2/60">
                  <td className="td">
                    <a href={`/chart?symbol=${r.symbol}`} className="font-medium text-accent hover:underline">
                      {r.symbol}
                    </a>
                    <div className="max-w-[160px] truncate text-xs text-muted">{r.name}</div>
                  </td>
                  <td className="td">{num(r.price)}</td>
                  <td className="td"><Bias value={r.weekly_bias} /></td>
                  <td className="td"><Bias value={r.daily_bias} /></td>
                  <td className="td"><Bias value={r.h4_structure} /></td>
                  <td className="td"><Bias value={r.h1_structure} /></td>
                  <td className="td">{r.direction ?? "—"}</td>
                  <td className="td text-xs">{r.bos ?? "—"}</td>
                  <td className="td text-xs">{r.fvg ?? "—"}</td>
                  <td className="td text-xs">
                    {r.zone_state ? (
                      <span>
                        {r.zone_state}
                        {r.zone_fresh ? <span className="ml-1 text-bull">•fresh</span> : null}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="td"><Score value={r.score} /></td>
                  <td className="td">{num(r.entry)}</td>
                  <td className="td text-bear">{num(r.stop)}</td>
                  <td className="td text-bull">{num(r.target)}</td>
                  <td className="td">{r.reward_risk ? `${num(r.reward_risk, 1)}` : "—"}</td>
                  <td className="td">{r.qty ? num(r.qty, 0) : "—"}</td>
                  <td className="td">{r.risk_pct ? num(r.risk_pct, 2) : "—"}</td>
                  <td className="td">
                    {r.eligible ? (
                      <Pill tone="bull">eligible</Pill>
                    ) : (
                      <span className="text-xs text-muted" title={r.rejection_reason ?? ""}>
                        {(r.rejection_reason ?? "—").slice(0, 28)}
                      </span>
                    )}
                  </td>
                  <td className="td"><WhyButton why={r.why} symbol={r.symbol} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
