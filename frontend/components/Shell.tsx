"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, setToken } from "@/lib/api";

const NAV = [
  { href: "/", label: "Overview", icon: "▦" },
  { href: "/scanner", label: "Nifty 500 Scanner", icon: "◎" },
  { href: "/global", label: "Global Markets", icon: "🌐" },
  { href: "/chart", label: "Chart", icon: "📈" },
  { href: "/trading", label: "Automated Trading", icon: "⚙" },
  { href: "/positions", label: "Positions", icon: "▣" },
  { href: "/orders", label: "Orders", icon: "☰" },
  { href: "/backtest", label: "Backtesting", icon: "⏱" },
  { href: "/analytics", label: "Analytics", icon: "∿" },
  { href: "/settings", label: "Settings", icon: "⛭" },
  { href: "/system", label: "System Health", icon: "✚" },
  { href: "/audit", label: "Audit Logs", icon: "🗐" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [authed, setAuthed] = useState(false);
  useEffect(() => setAuthed(!!getToken()), [pathname]);

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-r border-border bg-panel2 md:block">
        <div className="flex items-center gap-2 px-4 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/15 text-accent">
            S&amp;D
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">Institutional</div>
            <div className="text-xs text-muted">S&amp;D / SMC Engine</div>
          </div>
        </div>
        <nav className="mt-2 flex flex-col gap-0.5 px-2">
          {NAV.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm transition ${
                  active
                    ? "bg-accent/10 text-accent"
                    : "text-muted hover:bg-panel hover:text-txt"
                }`}
              >
                <span className="w-4 text-center opacity-80">{n.icon}</span>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-6 px-4 text-[11px] leading-relaxed text-muted">
          <span className="tag bg-warn/15 text-warn">PAPER MODE</span>
          <p className="mt-2">
            Live trading disabled by default. Data shown may be synthetic — check
            the provider on System Health.
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-border bg-panel2 px-4 py-2.5">
          <div className="text-sm text-muted md:hidden">S&amp;D / SMC Engine</div>
          <div className="hidden text-sm text-muted md:block">
            Institutional Supply &amp; Demand — multi-market SMC terminal
          </div>
          <div className="flex items-center gap-2">
            {authed ? (
              <button
                className="btn"
                onClick={() => {
                  setToken(null);
                  setAuthed(false);
                  location.reload();
                }}
              >
                Sign out
              </button>
            ) : (
              <Link href="/login" className="btn btn-accent">
                Sign in
              </Link>
            )}
          </div>
        </header>
        <main className="min-w-0 flex-1 p-4">{children}</main>
      </div>
    </div>
  );
}
