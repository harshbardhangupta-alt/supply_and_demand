"use client";

import { useState } from "react";
import Modal from "./Modal";

type Factor = { label: string; detail: string; positive: boolean };
export type Why = { selected: boolean; summary: string; factors: Factor[] };

export default function WhyButton({
  why,
  symbol,
}: {
  why?: Why | null;
  symbol: string;
}) {
  const [open, setOpen] = useState(false);
  if (!why) return <span className="text-muted">—</span>;
  return (
    <>
      <button
        className="rounded-md border border-border bg-panel2 px-2 py-0.5 text-xs text-muted transition hover:border-accent/60 hover:text-accent"
        onClick={() => setOpen(true)}
      >
        Why?
      </button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={
          <span>
            {symbol}{" "}
            <span className={why.selected ? "text-accent" : "text-bear"}>
              · {why.selected ? "Selected" : "Rejected"}
            </span>
          </span>
        }
      >
        <p className="mb-4 text-sm leading-relaxed text-txt/90">{why.summary}</p>
        <div className="space-y-1.5">
          {why.factors.map((f, i) => (
            <div
              key={i}
              className="flex items-center justify-between gap-3 rounded-lg border border-border bg-panel2 px-3 py-1.5 text-sm"
            >
              <span className="flex items-center gap-2 text-muted">
                <span className={f.positive ? "text-accent" : "text-bear"}>
                  {f.positive ? "✔" : "✕"}
                </span>
                {f.label}
              </span>
              <span className={`font-mono text-xs ${f.positive ? "text-txt" : "text-bear"}`}>
                {f.detail}
              </span>
            </div>
          ))}
        </div>
      </Modal>
    </>
  );
}
