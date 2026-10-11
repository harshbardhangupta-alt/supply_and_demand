"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, setToken } from "@/lib/api";

const NAV = [
  { href: "/", label: "Dashboard", icon: IconGrid },
  { href: "/scanner", label: "Scanner", icon: IconPulse },
  { href: "/chart", label: "Chart", icon: IconChart },
  { href: "/analytics", label: "Analytics", icon: IconBars },
  { href: "/backtest", label: "Backtest", icon: IconClock },
  { href: "/connections", label: "Connections", icon: IconPlug },
  { href: "/settings", label: "Settings", icon: IconGear },
];
const TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/scanner": "Nifty 500 Scanner",
  "/chart": "Chart",
  "/analytics": "Analytics",
  "/backtest": "Backtesting",
  "/connections": "Connections",
  "/settings": "Settings",
  "/system": "System Health",
  "/global": "Global Markets",
  "/audit": "Audit Logs",
};

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authed, setAuthed] = useState(false);
  const [q, setQ] = useState("");
  useEffect(() => setAuthed(!!getToken()), [pathname]);

  return (
    <div className="flex min-h-screen">
      {/* slim icon rail */}
      <aside className="sticky top-0 flex h-screen w-16 shrink-0 flex-col items-center border-r border-border bg-panel2 py-4">
        <Link href="/" className="mb-6 flex h-9 w-9 items-center justify-center rounded-xl bg-accent text-black shadow-neon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3 2 20h20L12 3z" /></svg>
        </Link>
        <nav className="flex flex-1 flex-col items-center gap-1.5">
          {NAV.map((n) => {
            const active = pathname === n.href;
            const Icon = n.icon;
            return (
              <Link
                key={n.href}
                href={n.href}
                title={n.label}
                className={`group relative flex h-10 w-10 items-center justify-center rounded-xl transition ${
                  active ? "bg-accent/15 text-accent" : "text-muted hover:bg-panel hover:text-txt"
                }`}
              >
                <Icon />
                <span className="pointer-events-none absolute left-12 z-30 whitespace-nowrap rounded-md border border-border bg-panel px-2 py-1 text-xs text-txt opacity-0 shadow-lg transition group-hover:opacity-100">
                  {n.label}
                </span>
              </Link>
            );
          })}
        </nav>
        <Link href="/system" title="System" className="mt-2 flex h-10 w-10 items-center justify-center rounded-xl text-muted hover:text-txt">
          <IconPulse />
        </Link>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* top bar */}
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-border bg-bg/80 px-5 py-3 backdrop-blur">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted">»</span>
            <span className="font-semibold">{TITLES[pathname] ?? "SMC Engine"}</span>
          </div>
          <div className="flex items-center gap-2.5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (q.trim()) router.push(`/chart?symbol=${q.trim().toUpperCase()}`);
              }}
              className="hidden items-center gap-2 rounded-xl border border-border bg-panel2 px-3 py-1.5 sm:flex"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted"><circle cx="11" cy="11" r="7" /><path d="m21 21-4-4" /></svg>
              <input
                className="w-32 bg-transparent text-sm outline-none placeholder:text-muted"
                placeholder="Search symbol…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
            </form>
            <span className="tag bg-warn/15 text-warn">PAPER</span>
            {authed ? (
              <button
                className="flex items-center gap-2 rounded-xl border border-border bg-panel2 px-2.5 py-1.5 text-sm hover:border-accent/50"
                onClick={() => { setToken(null); setAuthed(false); location.reload(); }}
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-accent/20 text-xs text-accent">A</span>
                <span className="hidden md:inline">Sign out</span>
              </button>
            ) : (
              <Link href="/login" className="btn btn-accent">Sign in</Link>
            )}
          </div>
        </header>
        <main className="min-w-0 flex-1 p-5 md:p-6">{children}</main>
      </div>
    </div>
  );
}

function IconGrid() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>; }
function IconPulse() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h4l2 6 4-14 2 8h6" /></svg>; }
function IconChart() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19V5M4 19h16M8 15v-4M12 15V8M16 15v-6" /></svg>; }
function IconBars() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2" /></svg>; }
function IconClock() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>; }
function IconPlug() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 0 1-10 0V8zM12 16v6" /></svg>; }
function IconGear() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H1a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 2.6 7a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 7 2.6h.1A1.6 1.6 0 0 0 9 1.1V1a2 2 0 1 1 4 0v.1A1.6 1.6 0 0 0 17 2.6a1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0 1.1 2.7H23a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z" /></svg>; }
