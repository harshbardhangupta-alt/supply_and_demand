"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await api.login(username, password);
      router.push("/");
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <PageHeader title="Sign in" desc="Demo credentials: admin / admin (change via SMC_ADMIN_* env vars)." />
      <form onSubmit={submit} className="panel space-y-3 p-5">
        <label className="block text-xs text-muted">
          Username
          <input className="input mt-1 w-full" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="block text-xs text-muted">
          Password
          <input className="input mt-1 w-full" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {err && <div className="text-sm text-bear">{err}</div>}
        <button className="btn btn-accent w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}
