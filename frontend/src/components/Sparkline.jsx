import React from "react";

// Tiny inline-SVG reputation sparkline (0–100 domain). No chart lib.
export default function Sparkline({ values, width = 132, height = 36 }) {
  const vals = values || [];
  if (vals.length < 2) return null;

  const min = 0;
  const max = 100;
  const pad = 3;
  const x = (i) => (i / (vals.length - 1)) * (width - pad * 2) + pad;
  const y = (v) => height - pad - ((v - min) / (max - min)) * (height - pad * 2);

  const line = vals
    .map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`)
    .join(" ");
  const area = `${line} L${x(vals.length - 1).toFixed(1)} ${height} L${x(0).toFixed(
    1
  )} ${height} Z`;
  const lastX = x(vals.length - 1);
  const lastY = y(vals[vals.length - 1]);

  return (
    <svg width={width} height={height} className="shrink-0">
      <defs>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.2" />
          <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#sparkFill)" />
      <path
        d={line}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle
        cx={lastX}
        cy={lastY}
        r="3"
        fill="var(--primary)"
        stroke="var(--card)"
        strokeWidth="1.5"
      />
    </svg>
  );
}
