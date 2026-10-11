"use client";

import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import { ErrorBox, Loading, PageHeader, Pill } from "@/components/ui";

export default function PositionsPage() {
  const { data, error, loading } = usePoll<any>(() => api.get("/api/positions"), 4000);
  const rows = data?.positions ?? [];
  return (
    <div>
      <PageHeader title="Positions" desc="Broker-confirmed open positions (paper broker)." right={<Pill tone="warn">PAPER</Pill>} />
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <div className="panel p-6 text-sm text-muted">No open positions.</div>
      ) : (
        <div className="panel overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>{["Symbol", "Side", "Qty", "Entry", "Current", "Stop", "Target", "P&L", "Opened"].map((h) => <th key={h} className="th">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((p: any, i: number) => (
                <tr key={i} className="border-t border-border/50">
                  <td className="td font-medium">{p.symbol}</td>
                  <td className="td">{p.side}</td>
                  <td className="td">{num(p.qty, 2)}</td>
                  <td className="td">{num(p.avg_price, 2)}</td>
                  <td className="td">{num(p.current_price, 2)}</td>
                  <td className="td text-bear">{num(p.stop_loss, 2)}</td>
                  <td className="td text-bull">{num(p.take_profit, 2)}</td>
                  <td className={`td ${p.unrealized_pnl >= 0 ? "text-bull" : "text-bear"}`}>{num(p.unrealized_pnl, 2)}</td>
                  <td className="td text-xs text-muted">{new Date(p.opened_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
