"use client";

import { useState } from "react";
import { api, getToken } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { ErrorBox, PageHeader, Pill, StatCard } from "@/components/ui";
import { money } from "@/lib/format";

export default function TradingPage() {
  const { data, refresh } = usePoll<any>(() => api.get("/api/overview"), 4000);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [universe, setUniverse] = useState("nifty500");
  const authed = typeof window !== "undefined" && !!getToken();

  async function act(fn: () => Promise<any>, label: string) {
    setErr(null);
    setMsg(null);
    try {
      const r = await fn();
      setMsg(`${label}: ${JSON.stringify(r)}`);
      refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div>
      <PageHeader
        title="Automated Trading"
        desc="Start/stop the engine, toggle automatic entries, and run a paper evaluation pass. Live trading stays disabled until explicitly enabled server-side."
        right={
          <div className="flex gap-2">
            <Pill tone={data?.live_mode ? "bear" : "warn"}>{data?.live_mode ? "LIVE" : "PAPER"}</Pill>
            <Pill tone={data?.engine_running ? "bull" : "neutral"}>
              {data?.engine_running ? "running" : "stopped"}
            </Pill>
          </div>
        }
      />

      {!authed && (
        <div className="panel mb-3 border-warn/40 bg-warn/5 p-3 text-sm text-warn">
          Sign in (top-right) to use trading controls — they require authorization.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Equity" value={money(data?.equity ?? 0)} />
        <StatCard label="Open Positions" value={data?.open_positions ?? 0} />
        <StatCard label="Active Orders" value={data?.active_orders ?? 0} />
        <StatCard label="Auto Entries" value={data?.auto_entry ? "On" : "Off"} tone={data?.auto_entry ? "bull" : "neutral"} />
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="panel p-4">
          <div className="mb-3 text-sm font-semibold">Engine controls</div>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-accent" onClick={() => act(() => api.post("/api/trading/start"), "start")}>Start engine</button>
            <button className="btn" onClick={() => act(() => api.post("/api/trading/stop"), "stop")}>Stop engine</button>
            <button className="btn" onClick={() => act(() => api.post("/api/trading/auto-entry", { enabled: !data?.auto_entry }), "auto-entry")}>
              {data?.auto_entry ? "Disable" : "Enable"} auto entries
            </button>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <select className="input" value={universe} onChange={(e) => setUniverse(e.target.value)}>
              <option value="nifty500">Nifty 500</option>
              <option value="forex">Forex</option>
              <option value="metals">Metals</option>
              <option value="commodities">Commodities</option>
            </select>
            <button className="btn" onClick={() => act(() => api.post(`/api/trading/paper/run?universe=${universe}&limit=25`), "paper-run")}>
              Run paper evaluation pass
            </button>
          </div>
        </div>

        <div className="panel p-4">
          <div className="mb-3 text-sm font-semibold text-bear">Safety controls</div>
          <p className="mb-3 text-xs text-muted">
            Emergency stop disables new entries and cancels pending entry orders. It does
            <strong> not</strong> auto-liquidate open positions — that is a separate confirmed action.
          </p>
          <div className="flex flex-wrap gap-2">
            <button className="btn btn-danger" onClick={() => act(() => api.post("/api/trading/emergency-stop"), "emergency-stop")}>
              ⛔ Emergency stop
            </button>
            <button
              className="btn btn-danger"
              onClick={() => {
                if (confirm("Liquidate ALL open paper positions?"))
                  act(() => api.post("/api/trading/liquidate"), "liquidate");
              }}
            >
              Liquidate positions
            </button>
            <button
              className="btn"
              onClick={() => {
                if (confirm("Enable LIVE mode? This requires server configuration."))
                  act(() => api.post("/api/trading/live/enable", { confirm: true }), "live-enable");
              }}
            >
              Enable live mode
            </button>
          </div>
        </div>
      </div>

      {msg && <div className="panel mt-3 border-bull/40 bg-bull/5 p-3 text-xs text-bull break-all">{msg}</div>}
      {err && <div className="mt-3"><ErrorBox error={err} /></div>}
    </div>
  );
}
