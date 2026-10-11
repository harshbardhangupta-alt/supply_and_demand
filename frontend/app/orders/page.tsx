"use client";

import { api } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { num } from "@/lib/format";
import { ErrorBox, Loading, PageHeader, Pill } from "@/components/ui";

const tone: Record<string, "bull" | "bear" | "warn" | "neutral"> = {
  filled: "bull",
  submitted: "warn",
  pending: "warn",
  cancelled: "neutral",
  rejected: "bear",
  expired: "neutral",
};

export default function OrdersPage() {
  const { data, error, loading } = usePoll<any>(() => api.get("/api/orders"), 4000);
  const rows = data?.orders ?? [];
  return (
    <div>
      <PageHeader title="Orders" desc="Pending, filled, cancelled and rejected orders with broker response." right={<Pill tone="warn">PAPER</Pill>} />
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : rows.length === 0 ? (
        <div className="panel p-6 text-sm text-muted">No orders yet. Run a paper evaluation pass from Automated Trading.</div>
      ) : (
        <div className="panel overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>{["Broker ID", "Symbol", "Side", "Type", "Qty", "Price", "Status", "Filled", "Reason"].map((h) => <th key={h} className="th">{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((o: any) => (
                <tr key={o.id} className="border-t border-border/50">
                  <td className="td font-mono text-xs">{o.broker_order_id}</td>
                  <td className="td font-medium">{o.symbol}</td>
                  <td className="td">{o.side}</td>
                  <td className="td">{o.type}</td>
                  <td className="td">{num(o.qty, 2)}</td>
                  <td className="td">{o.price ? num(o.price, 2) : "mkt"}</td>
                  <td className="td"><Pill tone={tone[o.status] ?? "neutral"}>{o.status}</Pill></td>
                  <td className="td">{o.avg_fill_price ? num(o.avg_fill_price, 2) : "—"}</td>
                  <td className="td text-xs text-muted">{o.reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
