"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import Candles, { ChartData } from "@/components/Candles";
import { ErrorBox, Loading, PageHeader, Pill } from "@/components/ui";

const TFS = ["15m", "1h", "4h", "1d", "1w"];

function ChartInner() {
  const sp = useSearchParams();
  const [symbol, setSymbol] = useState(sp.get("symbol") || "RELIANCE");
  const [input, setInput] = useState(symbol);
  const [tf, setTf] = useState("4h");
  const [data, setData] = useState<ChartData | null>(null);
  const [setup, setSetup] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [ai, setAi] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState<string | null>(null);

  async function runAI() {
    setAiBusy(true);
    setAiErr(null);
    setAi(null);
    try {
      const r = await api.post<{ analysis: string }>("/api/ai/analyze", { symbol });
      setAi(r.analysis);
    } catch (e) {
      setAiErr(e instanceof Error ? e.message : String(e));
    } finally {
      setAiBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    setLoading(true);
    setAi(null);
    setAiErr(null);
    Promise.all([
      api.get<ChartData>(`/api/chart/${symbol}?timeframe=${tf}&count=240`),
      api
        .get<any>(`/api/signals?universe=nifty500`)
        .then((s) => s.signals.find((x: any) => x.symbol === symbol) || null)
        .catch(() => null),
    ])
      .then(([c, s]) => {
        if (!active) return;
        setData(c);
        setSetup(s);
        setError(null);
      })
      .catch((e) => active && setError(String(e)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [symbol, tf]);

  return (
    <div>
      <PageHeader
        title="Interactive Chart"
        desc="Candles with supply/demand zones, FVGs, swing structure and (when present) the planned entry, stop and target."
        right={
          data && (
            <div className="flex items-center gap-2">
              <Pill tone={data.feed_mode === "synthetic" ? "warn" : "neutral"}>
                {data.provider ?? "data"}
              </Pill>
            </div>
          )
        }
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSymbol(input.toUpperCase());
          }}
          className="flex gap-2"
        >
          <input className="input w-40" value={input} onChange={(e) => setInput(e.target.value)} />
          <button className="btn" type="submit">Load</button>
        </form>
        <div className="flex gap-1">
          {TFS.map((t) => (
            <button key={t} className={`btn ${tf === t ? "btn-accent" : ""}`} onClick={() => setTf(t)}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading label="Loading chart…" />
      ) : data ? (
        <div className="grid gap-3 lg:grid-cols-[1fr_280px]">
          <div className="panel p-2">
            <Candles
              data={data}
              overlay={
                setup
                  ? { entry: setup.entry, stop: setup.stop, target: setup.target }
                  : undefined
              }
            />
            <div className="flex flex-wrap gap-3 px-2 py-2 text-xs text-muted">
              <Legend color="rgba(38,166,154,0.5)" label="Demand zone" />
              <Legend color="rgba(239,83,80,0.5)" label="Supply zone" />
              <Legend color="rgba(79,140,255,0.3)" label="FVG" />
            </div>
          </div>
          <div className="panel p-4">
            <div className="text-sm font-semibold">{symbol} — current setup</div>
            {setup ? (
              <div className="mt-2 space-y-1.5 text-sm">
                <Row k="Direction" v={setup.direction} />
                <Row k="Entry model" v={setup.entry_model} />
                <Row k="Score" v={setup.score} />
                <Row k="Entry" v={setup.entry} />
                <Row k="Stop" v={setup.stop} />
                <Row k="Target" v={setup.target} />
                <Row k="R:R" v={setup.reward_risk} />
                <Row k="Qty" v={setup.qty} />
                {setup.score_breakdown && (
                  <div className="mt-3">
                    <div className="mb-1 text-xs uppercase text-muted">Score breakdown</div>
                    {Object.entries(setup.score_breakdown.components || {}).map(([k, v]) => (
                      <Row key={k} k={k} v={v as number} />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="mt-2 text-sm text-muted">
                No qualifying setup for {symbol} right now. Structure, zones and FVGs are
                still drawn on the chart.
              </p>
            )}

            <div className="mt-4 border-t border-border pt-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted">
                  AI Research
                </span>
                <button className="btn btn-accent !py-1 !text-xs" onClick={runAI} disabled={aiBusy}>
                  {aiBusy ? "Analyzing…" : "✦ Analyze"}
                </button>
              </div>
              {aiErr && <p className="text-xs text-bear">{aiErr}</p>}
              {ai ? (
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-txt/90">{ai}</p>
              ) : (
                !aiErr && (
                  <p className="text-xs text-muted">
                    Uses OpenAI to explain this setup. Add a key on the Connections page.
                  </p>
                )
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-3 w-3 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between border-b border-border/50 py-1 last:border-0">
      <span className="text-muted">{k}</span>
      <span className="font-mono">{v ?? "—"}</span>
    </div>
  );
}

export default function ChartPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ChartInner />
    </Suspense>
  );
}
