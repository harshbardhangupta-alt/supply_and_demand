"use client";

import { useState } from "react";
import { api, getToken } from "@/lib/api";
import { usePoll } from "@/lib/hooks";
import { ErrorBox, PageHeader, Pill } from "@/components/ui";

type Conn = {
  data_provider: string;
  available_providers: string[];
  dhan: {
    configured: boolean;
    client_id: string | null;
    access_token: string | null;
    token_updated_at: string | null;
    token_age_hours: number | null;
    token_expired: boolean;
    expires_in_hours: number | null;
    ttl_hours: number;
  };
  openai: { configured: boolean; api_key: string | null; model: string };
};

export default function ConnectionsPage() {
  const authed = typeof window !== "undefined" && !!getToken();
  const { data, refresh } = usePoll<Conn>(() => api.get("/api/connections"), 0);

  return (
    <div>
      <PageHeader
        title="Connections"
        desc="Add your Dhan and OpenAI credentials. Stored server-side (never exposed to the browser) and masked here."
        right={data && <Pill tone={data.data_provider === "dhan" ? "bull" : "warn"}>feed: {data.data_provider}</Pill>}
      />
      {!authed && (
        <div className="panel mb-4 border-warn/40 bg-warn/5 p-3 text-sm text-warn">
          Sign in as admin (top-right) to add or change credentials.
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <DhanCard data={data} onChange={refresh} />
        <OpenAICard data={data} onChange={refresh} />
      </div>
    </div>
  );
}

function DhanCard({ data, onChange }: { data: Conn | null; onChange: () => void }) {
  const d = data?.dhan;
  const [clientId, setClientId] = useState("");
  const [token, setToken] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [test, setTest] = useState<{ ok: boolean; detail: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setErr(null); setMsg(null); setBusy(true);
    try {
      const body: any = { access_token: token };
      if (clientId.trim()) body.client_id = clientId.trim();
      await api.put("/api/connections/dhan", body);
      setMsg("Saved. Access token updated.");
      setToken("");
      onChange();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  async function runTest() {
    setTest(null); setErr(null);
    try {
      const r = await api.post<{ ok: boolean; detail: string }>("/api/connections/dhan/test");
      setTest(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  async function useDhanFeed() {
    setErr(null);
    try {
      await api.put("/api/connections/provider", { provider: "dhan" });
      onChange();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  async function useSynthetic() {
    await api.put("/api/connections/provider", { provider: "synthetic" });
    onChange();
  }

  const age = d?.token_age_hours;
  const expired = d?.token_expired;
  return (
    <div className="panel p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-base font-semibold">Dhan</div>
        <Pill tone={d?.configured ? "bull" : "neutral"}>{d?.configured ? "configured" : "not set"}</Pill>
      </div>
      <p className="mb-4 text-xs text-muted">
        Indian market data &amp; execution. Client ID is fixed; the access token
        expires every {d?.ttl_hours ?? 24}h — paste a fresh token here daily.
      </p>

      {d?.configured && (
        <div className="mb-4 space-y-1 rounded-lg border border-border bg-panel2 p-3 text-sm">
          <Row k="Client ID" v={<span className="font-mono">{d.client_id}</span>} />
          <Row k="Access token" v={<span className="font-mono">{d.access_token}</span>} />
          <Row
            k="Token status"
            v={
              d.token_updated_at ? (
                <span className={expired ? "text-bear" : "text-bull"}>
                  {expired
                    ? `expired (${age}h old)`
                    : `valid · ~${d.expires_in_hours}h left`}
                </span>
              ) : "—"
            }
          />
        </div>
      )}

      <div className="space-y-2">
        <label className="block text-xs text-muted">
          Client ID {d?.configured && <span className="text-muted/60">(leave blank to keep)</span>}
          <input className="input mt-1 w-full font-mono" placeholder={d?.client_id ?? "1100XXXXXX"}
                 value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </label>
        <label className="block text-xs text-muted">
          Access Token <span className="text-accent">(update every 24h)</span>
          <input className="input mt-1 w-full font-mono" type="password" placeholder="paste fresh token"
                 value={token} onChange={(e) => setToken(e.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2 pt-1">
          <button className="btn btn-accent" onClick={save} disabled={busy || !token}>
            {busy ? "Saving…" : d?.configured ? "Update token" : "Save credentials"}
          </button>
          <button className="btn" onClick={runTest} disabled={!d?.configured}>Test connection</button>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 border-t border-border pt-3">
        <span className="text-xs text-muted">Market data feed:</span>
        <button className={`btn ${data?.data_provider === "dhan" ? "btn-accent" : ""}`}
                onClick={useDhanFeed} disabled={!d?.configured}>Dhan (live)</button>
        <button className={`btn ${data?.data_provider === "synthetic" ? "btn-accent" : ""}`}
                onClick={useSynthetic}>Synthetic</button>
      </div>

      {test && (
        <div className={`mt-3 rounded-lg border p-2 text-sm ${test.ok ? "border-bull/40 bg-bull/5 text-bull" : "border-bear/40 bg-bear/5 text-bear"}`}>
          {test.ok ? "✓ " : "✕ "}{test.detail}
        </div>
      )}
      {msg && <div className="mt-2 text-sm text-bull">{msg}</div>}
      {err && <div className="mt-2"><ErrorBox error={err} /></div>}
    </div>
  );
}

function OpenAICard({ data, onChange }: { data: Conn | null; onChange: () => void }) {
  const o = data?.openai;
  const [key, setKey] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [test, setTest] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setErr(null); setMsg(null); setBusy(true);
    try {
      await api.put("/api/connections/openai", { api_key: key, model });
      setMsg("Saved."); setKey(""); onChange();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function runTest() {
    setTest(null); setErr(null);
    try { setTest(await api.post("/api/connections/openai/test")); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }

  return (
    <div className="panel p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-base font-semibold">OpenAI</div>
        <Pill tone={o?.configured ? "bull" : "neutral"}>{o?.configured ? "configured" : "not set"}</Pill>
      </div>
      <p className="mb-4 text-xs text-muted">
        Optional — powers natural-language research &amp; explanations of setups.
        The platform works fully without it; it never computes prices or risk.
      </p>
      {o?.configured && (
        <div className="mb-4 space-y-1 rounded-lg border border-border bg-panel2 p-3 text-sm">
          <Row k="API key" v={<span className="font-mono">{o.api_key}</span>} />
          <Row k="Model" v={o.model} />
        </div>
      )}
      <div className="space-y-2">
        <label className="block text-xs text-muted">
          API Key
          <input className="input mt-1 w-full font-mono" type="password" placeholder="sk-…"
                 value={key} onChange={(e) => setKey(e.target.value)} />
        </label>
        <label className="block text-xs text-muted">
          Model
          <input className="input mt-1 w-full font-mono" value={model}
                 onChange={(e) => setModel(e.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2 pt-1">
          <button className="btn btn-accent" onClick={save} disabled={busy || !key}>
            {busy ? "Saving…" : "Save key"}
          </button>
          <button className="btn" onClick={runTest} disabled={!o?.configured}>Test connection</button>
        </div>
      </div>
      {test && (
        <div className={`mt-3 rounded-lg border p-2 text-sm ${test.ok ? "border-bull/40 bg-bull/5 text-bull" : "border-bear/40 bg-bear/5 text-bear"}`}>
          {test.ok ? `✓ Connected — ${test.model_count} models available` : `✕ ${test.detail}`}
        </div>
      )}
      {msg && <div className="mt-2 text-sm text-bull">{msg}</div>}
      {err && <div className="mt-2"><ErrorBox error={err} /></div>}
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-muted">{k}</span>
      <span className="truncate">{v}</span>
    </div>
  );
}
