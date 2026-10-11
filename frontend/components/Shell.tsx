"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getToken, setToken } from "@/lib/api";

type Item = { href: string; label: string };
const GROUPS: { title: string; items: Item[] }[] = [
  {
    title: "Markets",
    items: [
      { href: "/", label: "Overview" },
      { href: "/scanner", label: "Nifty 500 Scanner" },
      { href: "/global", label: "Global Markets" },
      { href: "/chart", label: "Chart" },
    ],
  },
  {
    title: "Trading",
    items: [
      { href: "/trading", label: "Automated Trading" },
      { href: "/positions", label: "Positions" },
      { href: "/orders", label: "Orders" },
    ],
  },
  {
    title: "Analysis",
    items: [
      { href: "/backtest", label: "Backtesting" },
      { href: "/analytics", label: "Analytics" },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/connections", label: "Connections" },
      { href: "/settings", label: "Settings" },
      { href: "/system", label: "System Health" },
      { href: "/audit", label: "Audit Logs" },
    ],
  },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [authed, setAuthed] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setAuthed(!!getToken());
    setOpen(false);
  }, [pathname]);

  return (
    <div className="flex min-h-screen">
      <aside
        className={`${
          open ? "fixed inset-y-0 left-0 z-40 block" : "hidden"
        } w-60 shrink-0 border-r border-border bg-panel2 md:sticky md:top-0 md:block md:h-screen`}
      >
        <div className="flex items-center gap-2.5 px-4 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-accent/40 bg-accent/10 font-bold text-accent shadow-neon">
            ⬢
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight tracking-wide">
              SMC<span className="text-accent"> ENGINE</span>
            </div>
            <div className="text-[11px] text-muted">Supply &amp; Demand</div>
          </div>
        </div>

        <nav className="mt-1 flex flex-col gap-3 px-2 pb-6 overflow-y-auto">
          {GROUPS.map((g) => (
            <div key={g.title}>
              <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-widest text-muted/70">
                {g.title}
              </div>
              {g.items.map((n) => {
                const active = pathname === n.href;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition ${
                      active
                        ? "bg-accent/10 text-accent shadow-neon"
                        : "text-muted hover:bg-panel hover:text-txt"
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        active ? "bg-accent" : "bg-border"
                      }`}
                    />
                    {n.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </aside>

      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-bg/80 px-4 py-2.5 backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              className="btn md:hidden"
              onClick={() => setOpen((v) => !v)}
              aria-label="Menu"
            >
              ☰
            </button>
            <span className="tag bg-warn/15 text-warn">PAPER MODE</span>
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
        <main className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
