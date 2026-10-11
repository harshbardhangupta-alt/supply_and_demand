"use client";

export default function Sparkline({
  data,
  color = "#2bff88",
  width = 150,
  height = 46,
  fill = true,
}: {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
  fill?: boolean;
}) {
  if (!data || data.length < 2) {
    return (
      <svg width={width} height={height}>
        <line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#1f2a24" />
      </svg>
    );
  }
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pad = 3;
  const x = (i: number) => (i / (data.length - 1)) * (width - pad * 2) + pad;
  const y = (v: number) => height - pad - ((v - min) / span) * (height - pad * 2);
  const pts = data.map((v, i) => `${x(i)},${y(v)}`);
  const line = `M ${pts.join(" L ")}`;
  const area = `${line} L ${x(data.length - 1)},${height} L ${x(0)},${height} Z`;
  const id = `sg-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${id})`} />}
      <path d={line} fill="none" stroke={color} strokeWidth={1.75} strokeLinejoin="round" />
      <circle cx={x(data.length - 1)} cy={y(data[data.length - 1])} r={2.5} fill={color} />
    </svg>
  );
}
