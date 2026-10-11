"use client";

import { api, getToken } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { ErrorBox, Loading, PageHeader } from "@/components/ui";

export default function AuditPage() {
  const authed = true;
  const { data, error, loading } = usePoll<any>(() => api.get("/api/audit"), 5000, [authed]);
  const events = data?.events ?? [];
  return (
    <div>
      <PageHeader title="Audit Logs" desc="Configuration changes, trading start/stop, order requests and risk events." />
      {!authed && <div className="panel mb-3 border-warn/40 bg-warn/5 p-3 text-sm text-warn">Sign in to view the audit trail.</div>}
      {error && <ErrorBox error={error} />}
      {loading && !data ? (
        <Loading />
      ) : events.length === 0 ? (
        <div className="panel p-6 text-sm text-muted">No audit events recorded.</div>
      ) : (
        <div className="panel overflow-auto">
          <table className="w-full text-sm">
            <thead><tr>{["Time", "Actor", "Action", "Detail"].map((h) => <th key={h} className="th">{h}</th>)}</tr></thead>
            <tbody>
              {events.map((e: any, i: number) => (
                <tr key={i} className="border-t border-border/50">
                  <td className="td text-xs text-muted">{new Date(e.ts).toLocaleString()}</td>
                  <td className="td">{e.actor}</td>
                  <td className="td font-medium">{e.action}</td>
                  <td className="td font-mono text-xs text-muted">{JSON.stringify(e.detail)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
