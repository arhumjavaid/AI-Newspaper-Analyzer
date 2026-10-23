import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { AlertTriangle, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SENTIMENT } from "../chartTheme";

const RANK = { minor: 1, standard: 2, prominent: 3, front_page: 4 };
const PROM_LABEL = { 1: "Minor", 2: "Standard", 3: "Prominent", 4: "Front page" };
const SENT = [
  { key: "positive", label: "Positive" },
  { key: "neutral", label: "Neutral" },
  { key: "mixed", label: "Mixed" },
  { key: "negative", label: "Negative" },
];

const isProminent = (a) =>
  a.prominence === "front_page" || a.prominence === "prominent";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      style={{
        background: "var(--popover)",
        border: "1px solid var(--border)",
        borderRadius: 12,
        boxShadow: "var(--shadow-md)",
        padding: "8px 12px",
        maxWidth: 260,
      }}
    >
      <div
        style={{ fontWeight: 600, fontSize: 13, color: "var(--foreground)" }}
      >
        {d.label}
      </div>
      <div
        style={{
          marginTop: 2,
          fontSize: 12,
          color: "var(--muted-foreground)",
          textTransform: "capitalize",
        }}
      >
        {d.sentiment} · {PROM_LABEL[Math.round(d.x)]} ·{" "}
        {d.y > 0 ? `+${d.y}` : d.y}
      </div>
    </div>
  );
}

export default function CoverageImpactMap({ articles }) {
  const rows = articles || [];
  if (rows.length === 0) return null;

  const data = rows.map((a, i) => ({
    // deterministic jitter so stories in the same column don't fully overlap
    x: (RANK[a.prominence] || 2) + (((i % 5) - 2) * 0.07),
    y: typeof a.sentiment_score === "number" ? a.sentiment_score : 0,
    label: a.headline,
    sentiment: a.sentiment_label || "neutral",
    prominence: a.prominence,
  }));

  const highRisk = rows.filter(
    (a) =>
      isProminent(a) &&
      (a.sentiment_label === "negative" || a.risk_level === "critical")
  );
  const wins = rows.filter(
    (a) => isProminent(a) && a.sentiment_label === "positive"
  );

  return (
    <Card className="mt-[18px] break-inside-avoid">
      <CardHeader>
        <CardTitle>Coverage Impact Map</CardTitle>
        <span className="text-[13px] text-muted-foreground">
          Each story by visibility × sentiment
        </span>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="relative">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 10, right: 16, bottom: 8, left: 0 }}>
              <ReferenceArea
                x1={2.5}
                x2={4.5}
                y1={0}
                y2={100}
                fill="var(--positive)"
                fillOpacity={0.06}
              />
              <ReferenceArea
                x1={2.5}
                x2={4.5}
                y1={-100}
                y2={0}
                fill="var(--negative)"
                fillOpacity={0.06}
              />
              <XAxis
                type="number"
                dataKey="x"
                domain={[0.5, 4.5]}
                ticks={[1, 2, 3, 4]}
                tickFormatter={(v) => PROM_LABEL[v]}
                tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                type="number"
                dataKey="y"
                domain={[-100, 100]}
                ticks={[-100, -50, 0, 50, 100]}
                tick={{ fill: "var(--chart-axis)", fontSize: 12 }}
                tickLine={false}
                axisLine={false}
                width={40}
              />
              <ZAxis range={[130, 130]} />
              <ReferenceLine y={0} stroke="var(--chart-grid)" strokeWidth={1} />
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ strokeDasharray: "3 3", stroke: "var(--chart-grid)" }}
              />
              <Scatter data={data}>
                {data.map((d, i) => (
                  <Cell
                    key={i}
                    fill={SENTIMENT[d.sentiment] || SENTIMENT.neutral}
                    fillOpacity={0.85}
                    stroke="var(--card)"
                    strokeWidth={1.5}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <span className="pointer-events-none absolute right-4 top-2 text-[11px] font-semibold text-positive">
            Wins ↗
          </span>
          <span className="pointer-events-none absolute bottom-10 right-4 text-[11px] font-semibold text-negative">
            Needs response ↘
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
          {SENT.map((s) => (
            <div
              key={s.key}
              className="flex items-center gap-2 text-[12.5px] text-muted-foreground"
            >
              <span
                className="size-2.5 rounded-full"
                style={{ background: SENTIMENT[s.key] }}
              />
              {s.label}
            </div>
          ))}
        </div>

        {(highRisk.length > 0 || wins.length > 0) && (
          <div className="mt-4 flex flex-col gap-2 border-t border-border pt-4">
            {highRisk.length > 0 && (
              <div className="flex items-start gap-2 rounded-lg border border-negative/30 bg-negative-soft px-3 py-2.5 text-[13px]">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-negative" />
                <div className="text-ink2">
                  <b className="text-negative">
                    {highRisk.length} high-impact{" "}
                    {highRisk.length === 1 ? "story" : "stories"}
                  </b>{" "}
                  — negative coverage in prominent positions:{" "}
                  <span className="text-foreground">
                    {highRisk
                      .slice(0, 3)
                      .map((a) => a.headline)
                      .join("; ")}
                    {highRisk.length > 3 && ` +${highRisk.length - 3} more`}
                  </span>
                </div>
              </div>
            )}
            {wins.length > 0 && (
              <div className="flex items-start gap-2 rounded-lg border border-positive/30 bg-positive-soft px-3 py-2.5 text-[13px]">
                <Star className="mt-0.5 size-4 shrink-0 text-positive" />
                <div className="text-ink2">
                  <b className="text-positive">
                    {wins.length} PR {wins.length === 1 ? "win" : "wins"}
                  </b>{" "}
                  — positive coverage in prominent positions.
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
