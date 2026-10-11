"use client";

const ORANGE = "#ef7518";

export function ProgressBar({ value, color = ORANGE }: { value: number; color?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
      <div className="h-full rounded-full" style={{ width: `${v}%`, background: color }} />
    </div>
  );
}

export function AreaChart({
  data,
  height = 220,
  color = ORANGE,
  yMin,
  yMax,
  yTicks = 4,
}: {
  data: number[];
  height?: number;
  color?: string;
  yMin?: number;
  yMax?: number;
  yTicks?: number;
}) {
  const w = 600;
  const padL = 34;
  const padB = 18;
  const padT = 8;
  if (!data || data.length < 2) {
    return <div className="flex h-[220px] items-center justify-center text-sm text-muted">Not enough data yet</div>;
  }
  const lo = yMin ?? Math.min(...data);
  const hi = yMax ?? Math.max(...data);
  const span = hi - lo || 1;
  const plotH = height - padB - padT;
  const x = (i: number) => padL + (i / (data.length - 1)) * (w - padL - 6);
  const y = (v: number) => padT + (1 - (v - lo) / span) * plotH;
  const line = data.map((v, i) => `${x(i)},${y(v)}`);
  const area = `M ${line.join(" L ")} L ${x(data.length - 1)},${padT + plotH} L ${x(0)},${padT + plotH} Z`;
  const id = `ar-${Math.random().toString(36).slice(2, 7)}`;
  const ticks = Array.from({ length: yTicks + 1 }, (_, i) => lo + (span * i) / yTicks);

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" preserveAspectRatio="none" style={{ height }}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.45" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={w - 6} y1={y(t)} y2={y(t)} stroke="#25272d" strokeWidth={1} />
          <text x={4} y={y(t) + 3} fill="#878d98" fontSize={9}>
            {t.toFixed(0)}
          </text>
        </g>
      ))}
      <path d={area} fill={`url(#${id})`} />
      <path d={`M ${line.join(" L ")}`} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}

export function Donut({
  segments,
  centerValue,
  centerLabel,
  size = 200,
}: {
  segments: { label: string; value: number; color: string }[];
  centerValue: React.ReactNode;
  centerLabel: string;
  size?: number;
}) {
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  const r = size / 2 - 16;
  const cx = size / 2;
  const C = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="flex items-center gap-6">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="#25272d" strokeWidth={16} />
        {segments.map((s, i) => {
          const frac = s.value / total;
          const len = frac * C;
          const el = (
            <circle
              key={i}
              cx={cx}
              cy={cx}
              r={r}
              fill="none"
              stroke={s.color}
              strokeWidth={16}
              strokeDasharray={`${len} ${C - len}`}
              strokeDashoffset={-offset}
              transform={`rotate(-90 ${cx} ${cx})`}
              strokeLinecap="butt"
            />
          );
          offset += len;
          return el;
        })}
        <text x={cx} y={cx - 2} textAnchor="middle" fontSize={22} fontWeight={600} fill="#e9ebee">
          {centerValue}
        </text>
        <text x={cx} y={cx + 18} textAnchor="middle" fontSize={10} fill="#878d98">
          {centerLabel}
        </text>
      </svg>
      <div className="space-y-2.5">
        {segments.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="text-muted">{s.label}</span>
            <span className="ml-auto font-medium">
              {s.value}{" "}
              <span className="text-muted">({Math.round((s.value / total) * 100)}%)</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
