"use client";

import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { ErrorBox, Loading, PageHeader, Pill } from "@/components/ui";

export default function SystemPage() {
  const { data, error, loading } = usePoll<any>(() => api.get("/api/system/health"), 5000);
  return (
    <div>
      <PageHeader title="System Health" desc="Live status of the engine subsystems, data feed and broker." />
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : data ? (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="panel p-4">
            <div className="mb-2 text-sm font-semibold">Subsystems</div>
            <Status k="Strategy engine" v={data.strategy_engine} ok />
            <Status k="Risk engine" v={data.risk_engine} ok />
            <Status k="Execution engine" v={data.execution_engine} ok={data.execution_engine === "paper"} />
            <Status k="Database" v={data.database} ok />
            <Status k="WebSocket" v={data.websocket} ok />
          </div>
          <div className="panel p-4">
            <div className="mb-2 text-sm font-semibold">Market data &amp; broker</div>
            <Status k="Provider" v={data.market_data.provider} ok={data.market_data.connected} />
            <Status k="Feed mode" v={data.market_data.mode} ok={data.market_data.mode !== "stale"} />
            <Status k="Broker" v={`${data.broker.name} (${data.broker.connected ? "connected" : "down"})`} ok={data.broker.connected} />
            <div className="mt-2 text-xs text-muted">
              Last data update: {data.market_data.last_update ? new Date(data.market_data.last_update).toLocaleString() : "—"}
            </div>
            <div className="text-xs text-muted">Started: {new Date(data.started_at).toLocaleString()}</div>
          </div>
          <div className="panel p-4 md:col-span-2">
            <div className="mb-2 text-sm font-semibold">Recent risk / error events</div>
            {(data.recent_errors ?? []).length === 0 ? (
              <p className="text-sm text-muted">No recent events.</p>
            ) : (
              data.recent_errors.map((e: any, i: number) => (
                <div key={i} className="border-b border-border/50 py-1 text-sm last:border-0">
                  <span className="text-warn">{e.kind}</span> — <span className="text-muted">{e.detail}</span>
                </div>
              ))
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Status({ k, v, ok }: { k: string; v: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-1.5 text-sm last:border-0">
      <span className="text-muted">{k}</span>
      <Pill tone={ok ? "bull" : "warn"}>{v}</Pill>
    </div>
  );
}
