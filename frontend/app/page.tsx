"use client";

import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { money, num } from "@/lib/format";
import { ErrorBox, Loading, PageHeader, Pill, StatCard } from "@/components/ui";

type Overview = {
  equity: number;
  balance: number;
  free_margin: number;
  realized_pnl: number;
  unrealized_pnl: number;
  open_positions: number;
  active_orders: number;
  engine_running: boolean;
  auto_entry: boolean;
  live_mode: boolean;
  paper_trading: boolean;
  broker_status: string;
  universe_source: string;
  universe_size: number;
  data_provider: string;
  data_feed_mode: string;
};

export default function OverviewPage() {
  const { data, error, loading } = usePoll<Overview>(() => api.get("/api/overview"), 4000);

  return (
    <div>
      <PageHeader
        title="Overview"
        desc="Account, engine and market-data status at a glance"
        right={
          <div className="flex items-center gap-2">
            <Pill tone={data?.live_mode ? "bear" : "warn"}>
              {data?.live_mode ? "LIVE" : "PAPER"}
            </Pill>
            <Pill tone={data?.engine_running ? "bull" : "neutral"}>
              Engine {data?.engine_running ? "running" : "stopped"}
            </Pill>
          </div>
        }
      />
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Account Equity" value={money(data.equity)} sub="paper account" />
            <StatCard label="Available Funds" value={money(data.free_margin)} />
            <StatCard
              label="Realized P&L"
              value={money(data.realized_pnl)}
              tone={data.realized_pnl >= 0 ? "bull" : "bear"}
            />
            <StatCard
              label="Unrealized P&L"
              value={money(data.unrealized_pnl)}
              tone={data.unrealized_pnl >= 0 ? "bull" : "bear"}
            />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="Open Positions" value={num(data.open_positions, 0)} />
            <StatCard label="Active Orders" value={num(data.active_orders, 0)} />
            <StatCard
              label="Auto Entries"
              value={data.auto_entry ? "On" : "Off"}
              tone={data.auto_entry ? "bull" : "neutral"}
            />
            <StatCard label="Broker" value={data.broker_status} sub="paper broker" />
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="panel p-4">
              <div className="mb-2 text-sm font-semibold">Market Data</div>
              <Row k="Provider" v={data.data_provider} />
              <Row k="Feed mode" v={data.data_feed_mode} />
              <Row k="Universe source" v={data.universe_source} />
              <Row k="Universe size" v={`${data.universe_size} instruments`} />
              {data.data_feed_mode === "synthetic" && (
                <p className="mt-3 text-xs text-warn">
                  ⚠ Synthetic data feed. Figures are simulated for demonstration and
                  are not real market prices, balances or fills.
                </p>
              )}
            </div>
            <div className="panel p-4">
              <div className="mb-2 text-sm font-semibold">Engine State</div>
              <Row k="Strategy" v="Institutional Supply & Demand (SMC)" />
              <Row k="Mode" v={data.live_mode ? "LIVE" : "PAPER"} />
              <Row k="Paper trading" v={data.paper_trading ? "enabled" : "disabled"} />
              <Row k="Engine running" v={data.engine_running ? "yes" : "no"} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-1.5 text-sm last:border-0">
      <span className="text-muted">{k}</span>
      <span>{v}</span>
    </div>
  );
}
