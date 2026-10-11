"use client";

type Candle = { t: string; o: number; h: number; l: number; c: number; v: number };
type Zone = {
  direction: string;
  distal: number;
  proximal: number;
  state: string;
  created_index: number;
};
type Fvg = { index: number; direction: string; upper: number; lower: number };
type Swing = { index: number; price: number; kind: string; label: string | null };

export type ChartData = {
  candles: Candle[];
  zones: Zone[];
  fvgs: Fvg[];
  swings: Swing[];
  events: { type: string; direction: string; index: number; level: number }[];
  provider?: string;
  feed_mode?: string;
  symbol?: string;
  timeframe?: string;
};

export default function Candles({
  data,
  overlay,
  height = 460,
}: {
  data: ChartData;
  overlay?: { entry?: number | null; stop?: number | null; target?: number | null };
  height?: number;
}) {
  const candles = data.candles;
  if (!candles.length) return <div className="p-6 text-sm text-muted">No data</div>;

  const cw = 9; // candle slot width
  const padL = 56;
  const padR = 64;
  const padT = 12;
  const padB = 24;
  const plotW = candles.length * cw;
  const width = padL + plotW + padR;
  const plotH = height - padT - padB;

  let lo = Math.min(...candles.map((c) => c.l));
  let hi = Math.max(...candles.map((c) => c.h));
  const extra = [overlay?.entry, overlay?.stop, overlay?.target].filter(
    (v): v is number => typeof v === "number"
  );
  for (const v of extra) {
    lo = Math.min(lo, v);
    hi = Math.max(hi, v);
  }
  const span = hi - lo || 1;
  const pad = span * 0.05;
  lo -= pad;
  hi += pad;
  const y = (p: number) => padT + ((hi - p) / (hi - lo)) * plotH;
  const x = (i: number) => padL + i * cw + cw / 2;

  const gridLines = 5;
  const grid = Array.from({ length: gridLines + 1 }, (_, i) => lo + ((hi - lo) * i) / gridLines);

  return (
    <div className="overflow-x-auto">
      <svg width={width} height={height} className="block">
        {/* grid */}
        {grid.map((p, i) => (
          <g key={i}>
            <line x1={padL} x2={padL + plotW} y1={y(p)} y2={y(p)} stroke="#1e2735" />
            <text x={6} y={y(p) + 3} fill="#8a97a8" fontSize={10}>
              {p.toFixed(2)}
            </text>
          </g>
        ))}

        {/* zones */}
        {data.zones.map((z, i) => {
          const top = y(Math.max(z.distal, z.proximal));
          const bot = y(Math.min(z.distal, z.proximal));
          const demand = z.direction === "demand";
          const dead = ["INVALIDATED", "EXPIRED", "MITIGATED"].includes(z.state);
          const color = demand ? "38,166,154" : "239,83,80";
          return (
            <rect
              key={`z${i}`}
              x={x(z.created_index)}
              y={top}
              width={padL + plotW - x(z.created_index)}
              height={Math.max(1, bot - top)}
              fill={`rgba(${color},${dead ? 0.05 : 0.13})`}
              stroke={`rgba(${color},${dead ? 0.2 : 0.5})`}
              strokeDasharray={dead ? "3 3" : undefined}
            />
          );
        })}

        {/* fvgs */}
        {data.fvgs.map((f, i) => {
          const top = y(f.upper);
          const bot = y(f.lower);
          return (
            <rect
              key={`f${i}`}
              x={x(f.index) - cw / 2}
              y={top}
              width={cw * 3}
              height={Math.max(1, bot - top)}
              fill="rgba(79,140,255,0.10)"
            />
          );
        })}

        {/* candles */}
        {candles.map((c, i) => {
          const up = c.c >= c.o;
          const col = up ? "#26a69a" : "#ef5350";
          const bodyTop = y(Math.max(c.o, c.c));
          const bodyBot = y(Math.min(c.o, c.c));
          return (
            <g key={i}>
              <line x1={x(i)} x2={x(i)} y1={y(c.h)} y2={y(c.l)} stroke={col} />
              <rect
                x={x(i) - cw * 0.35}
                y={bodyTop}
                width={cw * 0.7}
                height={Math.max(1, bodyBot - bodyTop)}
                fill={col}
              />
            </g>
          );
        })}

        {/* swing labels */}
        {data.swings.map((s, i) => (
          <text
            key={`s${i}`}
            x={x(s.index)}
            y={s.kind === "high" ? y(s.price) - 4 : y(s.price) + 10}
            fill="#8a97a8"
            fontSize={8}
            textAnchor="middle"
          >
            {s.label ?? (s.kind === "high" ? "H" : "L")}
          </text>
        ))}

        {/* overlay entry/stop/target */}
        {overlay &&
          (["entry", "stop", "target"] as const).map((k) => {
            const v = overlay[k];
            if (typeof v !== "number") return null;
            const color = k === "entry" ? "#4f8cff" : k === "stop" ? "#ef5350" : "#26a69a";
            return (
              <g key={k}>
                <line
                  x1={padL}
                  x2={padL + plotW}
                  y1={y(v)}
                  y2={y(v)}
                  stroke={color}
                  strokeDasharray="4 3"
                />
                <text x={padL + plotW + 4} y={y(v) + 3} fill={color} fontSize={10}>
                  {k} {v.toFixed(2)}
                </text>
              </g>
            );
          })}
      </svg>
    </div>
  );
}
