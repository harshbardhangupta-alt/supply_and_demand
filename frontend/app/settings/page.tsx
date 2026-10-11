"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { ErrorBox, PageHeader, Pill } from "@/components/ui";

export default function SettingsPage() {
  const { data, refresh } = usePoll<any>(() => api.get("/api/settings"), 0);
  const [universe, setUniverse] = useState("nifty500");
  const [risk, setRisk] = useState(0.005);
  const [rr, setRr] = useState(3);
  const [score, setScore] = useState(70);
  const [model, setModel] = useState("normal");
  const [direction, setDirection] = useState("long");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const authed = typeof window !== "undefined" && !!getToken();

  useEffect(() => {
    const cfg = data?.configs?.[universe];
    if (cfg) {
      setRisk(cfg.risk.risk_per_trade);
      setRr(cfg.risk.min_reward_risk);
      setScore(cfg.score.min_score);
      setModel(cfg.entry.model);
      setDirection(cfg.direction);
    }
  }, [data, universe]);

  async function save() {
    setErr(null);
    setMsg(null);
    try {
      const r = await api.put<{ version: number }>("/api/settings/config", {
        universe,
        risk_per_trade: risk,
        min_reward_risk: rr,
        min_score: score,
        entry_model: model,
        direction,
      });
      setMsg(`Saved config v${r.version} (risk capped at hard limit).`);
      refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function refreshUniverse() {
    setErr(null);
    try {
      const r = await api.post<{ ok: boolean; warning?: string; source?: string }>(
        "/api/universe/nifty500/refresh"
      );
      setMsg(`Universe refresh: ${r.ok ? "ok" : "failed"} — ${r.warning ?? r.source}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <div>
      <PageHeader title="Settings" desc="Strategy, risk and universe configuration. Changes are versioned; the per-trade risk is always clamped to the hard cap." />
      {!authed && <div className="panel mb-3 border-warn/40 bg-warn/5 p-3 text-sm text-warn">Sign in (admin) to change settings.</div>}

      <div className="grid gap-3 md:grid-cols-2">
        <div className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold">Strategy config</div>
            <select className="input" value={universe} onChange={(e) => setUniverse(e.target.value)}>
              {(data?.universes ?? ["nifty500"]).map((u: string) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          <Field label={`Risk per trade (${(risk * 100).toFixed(2)}%)`}>
            <input type="range" min={0.001} max={0.01} step={0.001} value={risk} onChange={(e) => setRisk(Number(e.target.value))} className="w-full" />
          </Field>
          <Field label="Min reward:risk"><input className="input w-full" type="number" step={0.5} value={rr} onChange={(e) => setRr(Number(e.target.value))} /></Field>
          <Field label="Min setup score"><input className="input w-full" type="number" value={score} onChange={(e) => setScore(Number(e.target.value))} /></Field>
          <Field label="Entry model">
            <select className="input w-full" value={model} onChange={(e) => setModel(e.target.value)}>
              {["normal", "conservative", "aggressive"].map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="Direction">
            <select className="input w-full" value={direction} onChange={(e) => setDirection(e.target.value)}>
              {["long", "short", "both"].map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </Field>
          <button className="btn btn-accent mt-2" onClick={save}>Save config</button>
        </div>

        <div className="panel p-4">
          <div className="mb-3 text-sm font-semibold">Universe &amp; data</div>
          <div className="space-y-1.5 text-sm">
            <Row k="Data provider" v={data?.data_provider} />
            <Row k="Default equity" v={data?.default_equity} />
            <Row k="Live trading" v={<Pill tone={data?.live_trading_enabled ? "bear" : "neutral"}>{String(data?.live_trading_enabled)}</Pill>} />
            <Row k="Paper trading" v={<Pill tone="bull">{String(data?.paper_trading_enabled)}</Pill>} />
          </div>
          <button className="btn mt-3" onClick={refreshUniverse}>↻ Refresh Nifty 500 constituents</button>
          <p className="mt-2 text-xs text-muted">
            Refresh fetches the live NSE list; on failure the last verified list is kept with a warning.
          </p>
        </div>
      </div>

      {msg && <div className="panel mt-3 border-bull/40 bg-bull/5 p-3 text-sm text-bull">{msg}</div>}
      {err && <div className="mt-3"><ErrorBox error={err} /></div>}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="mb-3 block text-xs text-muted">{label}<div className="mt-1">{children}</div></label>;
}
function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex justify-between border-b border-border/50 py-1 last:border-0"><span className="text-muted">{k}</span><span>{v ?? "—"}</span></div>;
}
