export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function money(v: number | null | undefined, ccy = "₹"): string {
  if (v === null || v === undefined) return "—";
  return `${ccy}${num(v, 0)}`;
}

export function pct(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return `${num(v, digits)}%`;
}

export function biasColor(b?: string | null): string {
  switch (b) {
    case "bullish":
      return "text-bull";
    case "bearish":
      return "text-bear";
    case "transitional":
      return "text-warn";
    default:
      return "text-muted";
  }
}

export function scoreColor(s?: number | null): string {
  if (s === undefined || s === null) return "text-muted";
  if (s >= 80) return "text-bull";
  if (s >= 70) return "text-warn";
  return "text-muted";
}
