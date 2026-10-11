"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";

const GROUPS: { title: string; items: { href: string; label: string; icon: () => JSX.Element }[] }[] = [
  {
    title: "Main",
    items: [
      { href: "/", label: "Dashboard", icon: IconGrid },
      { href: "/scanner", label: "Scanner", icon: IconList },
      { href: "/chart", label: "Chart", icon: IconChart },
      { href: "/global", label: "Global Markets", icon: IconGlobe },
    ],
  },
  {
    title: "Analysis",
    items: [
      { href: "/backtest", label: "Backtesting", icon: IconClock },
      { href: "/analytics", label: "Analytics", icon: IconBars },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/connections", label: "Connections", icon: IconPlug },
      { href: "/settings", label: "Settings", icon: IconGear },
      { href: "/system", label: "System Health", icon: IconPulse },
      { href: "/audit", label: "Audit Logs", icon: IconDoc },
    ],
  },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [authed, setAuthed] = useState(false);
  const [open, setOpen] = useState(false);
  const [ov, setOv] = useState<any>(null);
  useEffect(() => {
    setAuthed(!!getToken());
    setOpen(false);
  }, [pathname]);
  useEffect(() => {
    let on = true;
    const load = () => api.get("/api/overview").then((d) => on && setOv(d)).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => { on = false; clearInterval(id); };
  }, []);

  return (
    <div className="flex min-h-screen">
      <aside
        className={`${open ? "fixed inset-y-0 left-0 z-40 flex" : "hidden"} w-60 shrink-0 flex-col border-r border-border bg-panel md:sticky md:top-0 md:flex md:h-screen`}
      >
        <div className="flex items-center gap-2.5 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-black">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h2l2 5 4-12 3 9 2-4h5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinejoin="round" /></svg>
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">SMC Engine</div>
            <div className="text-[11px] text-muted">Supply &amp; Demand</div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-4">
          {GROUPS.map((g) => (
            <div key={g.title} className="mb-4">
              <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted/70">
                {g.title}
              </div>
              {g.items.map((n) => {
                const active = pathname === n.href;
                const Icon = n.icon;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={`mb-0.5 flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition ${
                      active ? "bg-accent/10 text-accent" : "text-muted hover:bg-panel2 hover:text-txt"
                    }`}
                  >
                    <span className={active ? "text-accent" : "text-muted"}><Icon /></span>
                    {n.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* bottom status widgets */}
        <div className="space-y-3 border-t border-border p-4">
          <div className="rounded-lg border border-border bg-panel2 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted">System Status</span>
              <span className="h-2 w-2 rounded-full bg-bull" />
            </div>
            <div className="mt-1 text-sm text-bull">All Systems Operational</div>
          </div>
          <div className="rounded-lg border border-border bg-panel2 p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted">Data Feed</span>
              <span className={ov?.data_feed_mode === "synthetic" ? "text-warn" : "text-accent"}>
                {ov?.data_provider ?? "…"}
              </span>
            </div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border">
              <div className="h-full bg-accent" style={{ width: ov ? "100%" : "20%" }} />
            </div>
          </div>
          {authed ? (
            <button className="btn w-full" onClick={() => { setToken(null); setAuthed(false); location.reload(); }}>
              Sign out
            </button>
          ) : (
            <Link href="/login" className="btn btn-accent w-full justify-center">Sign in</Link>
          )}
        </div>
      </aside>

      {open && <div className="fixed inset-0 z-30 bg-black/60 md:hidden" onClick={() => setOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col">
        <button className="btn m-3 w-fit md:hidden" onClick={() => setOpen(true)}>☰ Menu</button>
        <main className="min-w-0 flex-1 p-5 md:p-7">{children}</main>
      </div>
    </div>
  );
}

function IconGrid() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></svg>; }
function IconList() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" /></svg>; }
function IconChart() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19V5M4 19h16M8 15v-4M12 15V8M16 15v-6" /></svg>; }
function IconGlobe() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18z" /></svg>; }
function IconBars() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2" /></svg>; }
function IconClock() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>; }
function IconPlug() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 0 1-10 0V8zM12 16v6" /></svg>; }
function IconGear() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.3 1a7 7 0 0 0-1.7-1l-.3-2.6H9.4l-.3 2.6a7 7 0 0 0-1.7 1l-2.3-1-2 3.4 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 1.7 1l.3 2.6h5.2l.3-2.6a7 7 0 0 0 1.7-1l2.3 1 2-3.4-2-1.5a7 7 0 0 0 .1-1z" /></svg>; }
function IconPulse() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h4l2 6 4-14 2 8h6" /></svg>; }
function IconDoc() { return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5" /></svg>; }
