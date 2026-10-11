"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import { Bias, ErrorBox, Loading, PageHeader, Pill, Score } from "@/components/ui";

const UNIVERSES = [
  { key: "forex", label: "Forex" },
  { key: "metals", label: "Metals" },
  { key: "commodities", label: "Crude & Commodities" },
  { key: "indian_indices", label: "Indian Indices" },
];

export default function GlobalPage() {
  const [universe, setUniverse] = useState("forex");
  const { data, error, loading, refresh } = usePoll<any>(
    () => api.get(`/api/scanner/${universe}`),
    0,
    [universe]
  );

  return (
    <div>
      <PageHeader
        title="Global Market Scanner"
        desc="Separate configurable watchlists per asset class — kept independent from the Nifty 500 stock universe."
        right={<button className="btn" onClick={refresh}>↻ Rescan</button>}
      />
      <div className="mb-3 flex flex-wrap gap-2">
        {UNIVERSES.map((u) => (
          <button
            key={u.key}
            className={`btn ${universe === u.key ? "btn-accent" : ""}`}
            onClick={() => setUniverse(u.key)}
          >
            {u.label}
          </button>
        ))}
      </div>
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : (
        <div className="panel overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                {["Symbol", "Price", "Daily", "4H", "Dir", "BOS", "Zone", "Score", "Entry", "Stop", "Target", "R:R", "Status"].map((h) => (
                  <th key={h} className="th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data?.rows ?? []).map((r: any) => (
                <tr key={r.symbol} className="border-t border-border/50 hover:bg-panel2/60">
                  <td className="td">
                    <a href={`/chart?symbol=${r.symbol}`} className="font-medium text-accent hover:underline">{r.symbol}</a>
                    <div className="text-xs text-muted">{r.name}</div>
                  </td>
                  <td className="td">{num(r.price, 4)}</td>
                  <td className="td"><Bias value={r.daily_bias} /></td>
                  <td className="td"><Bias value={r.h4_structure} /></td>
                  <td className="td">{r.direction ?? "—"}</td>
                  <td className="td text-xs">{r.bos ?? "—"}</td>
                  <td className="td text-xs">{r.zone_state ?? "—"}</td>
                  <td className="td"><Score value={r.score} /></td>
                  <td className="td">{num(r.entry, 4)}</td>
                  <td className="td text-bear">{num(r.stop, 4)}</td>
                  <td className="td text-bull">{num(r.target, 4)}</td>
                  <td className="td">{r.reward_risk ? num(r.reward_risk, 1) : "—"}</td>
                  <td className="td">
                    {r.eligible ? <Pill tone="bull">eligible</Pill> : (
                      <span className="text-xs text-muted">{(r.rejection_reason ?? "—").slice(0, 26)}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
