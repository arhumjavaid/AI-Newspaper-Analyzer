import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Modern semicircular arc gauge for the 0-100 Reputation Index.
// A soft full-width track with a single rounded value arc — no needle.
export default function ReputationGauge({ value }) {
  const v = Math.max(0, Math.min(100, value ?? 50));

  const cx = 130;
  const cy = 122;
  const r = 100;
  const stroke = 20;

  const band =
    v >= 66
      ? { color: "var(--positive)", label: "Favourable", variant: "positive" }
      : v >= 40
        ? { color: "var(--mixed)", label: "Mixed", variant: "mixed" }
        : { color: "var(--negative)", label: "At Risk", variant: "negative" };

  // Point on the semicircle for a 0..100 progress value (180° sweep, left→right).
  const point = (p) => {
    const a = Math.PI * (1 - p / 100);
    return [cx + r * Math.cos(a), cy - r * Math.sin(a)];
  };
  const [sx, sy] = point(0);
  const [ex, ey] = point(100);
  const [vx, vy] = point(v);
  const largeArc = v > 50 ? 1 : 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reputation Index</CardTitle>
        <Badge variant={band.variant}>{band.label}</Badge>
      </CardHeader>
      <CardContent className="flex flex-col items-center pt-2">
        <svg viewBox="0 0 260 150" width="100%" height="170" className="max-w-[320px]">
          {/* track */}
          <path
            d={`M ${sx} ${sy} A ${r} ${r} 0 0 1 ${ex} ${ey}`}
            fill="none"
            stroke="var(--secondary)"
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          {/* value arc */}
          <path
            d={`M ${sx} ${sy} A ${r} ${r} 0 ${largeArc} 1 ${vx} ${vy}`}
            fill="none"
            stroke={band.color}
            strokeWidth={stroke}
            strokeLinecap="round"
          />
          <text
            x={cx}
            y={cy - 22}
            textAnchor="middle"
            style={{
              fontSize: 54,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              fill: "var(--foreground)",
            }}
          >
            {v}
          </text>
          <text
            x={cx}
            y={cy}
            textAnchor="middle"
            style={{ fontSize: 13, fill: "var(--muted-foreground)" }}
          >
            out of 100
          </text>
        </svg>
        <div className="mt-1 flex w-full max-w-[320px] justify-between px-2 text-[11px] font-medium text-muted-foreground">
          <span>At Risk</span>
          <span>Mixed</span>
          <span>Favourable</span>
        </div>
      </CardContent>
    </Card>
  );
}
