import React from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART, tooltipStyle } from "../chartTheme";

function clamp(v) {
  return Math.max(0, Math.min(100, v));
}

export default function CoverageRadar({ analysis }) {
  const m = analysis?.metrics;
  if (!m) return null;

  const dist = m.sentiment_distribution || {};
  const total = Object.values(dist).reduce((s, v) => s + v, 0);

  const reputation   = clamp(m.reputation_index ?? 50);
  const sentiment    = clamp(Math.round(((m.average_sentiment ?? 0) + 100) / 2));
  const positiveRate = total > 0 ? Math.round(((dist.positive || 0) / total) * 100) : 0;
  const coverage     = clamp(Math.round((analysis.articles.length / 10) * 100));
  const crisisSafety = clamp(100 - m.crisis_alerts.length * 25);

  const radarData = [
    { axis: "Reputation",    score: reputation },
    { axis: "Sentiment",     score: sentiment },
    { axis: "Positive Rate", score: positiveRate },
    { axis: "Coverage",      score: coverage },
    { axis: "Crisis Safety", score: crisisSafety },
  ];

  const stats = [
    {
      label: "Reputation Index",
      value: reputation,
      display: `${reputation}`,
      suffix: "/ 100",
      desc: "Overall brand standing",
    },
    {
      label: "Avg Sentiment",
      value: sentiment,
      display: m.average_sentiment > 0 ? `+${m.average_sentiment}` : `${m.average_sentiment ?? 0}`,
      suffix: "",
      desc: "Scale −100 to +100",
    },
    {
      label: "Positive Rate",
      value: positiveRate,
      display: `${positiveRate}`,
      suffix: "%",
      desc: `${dist.positive || 0} of ${total} articles`,
    },
    {
      label: "Coverage",
      value: coverage,
      display: `${analysis.articles.length}`,
      suffix: " articles",
      desc: `${analysis.page_count} page${analysis.page_count === 1 ? "" : "s"} scanned`,
    },
    {
      label: "Crisis Safety",
      value: crisisSafety,
      display: `${crisisSafety}`,
      suffix: "/ 100",
      desc: m.crisis_alerts.length === 0
        ? "No alerts raised"
        : `${m.crisis_alerts.length} alert${m.crisis_alerts.length > 1 ? "s" : ""} detected`,
    },
  ];

  return (
    <Card className="mt-[18px]">
      <CardHeader>
        <CardTitle>Coverage Intelligence Overview</CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:gap-10">

          {/* ── Radar chart ── */}
          <div className="h-[300px] w-full shrink-0 lg:w-[52%]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData} outerRadius="70%">
                <PolarGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
                <PolarAngleAxis
                  dataKey="axis"
                  tick={{
                    fill: "var(--chart-axis)",
                    fontSize: 12,
                    fontWeight: 500,
                  }}
                />
                <Radar
                  dataKey="score"
                  stroke={CHART.primary}
                  fill={CHART.primary}
                  fillOpacity={0.15}
                  strokeWidth={2}
                  dot={{ r: 4, fill: CHART.primary, strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: CHART.primary }}
                />
                <Tooltip
                  contentStyle={tooltipStyle}
                  formatter={(v) => [`${v} / 100`, "Score"]}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* ── Stat list ── */}
          <div className="flex w-full flex-col divide-y divide-border lg:w-[48%]">
            {stats.map((s) => (
              <div key={s.label} className="flex items-center gap-4 py-3 first:pt-0 last:pb-0">
                {/* Progress bar column */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-2 mb-1.5">
                    <span className="text-[13px] font-medium text-foreground truncate">
                      {s.label}
                    </span>
                    <span className="shrink-0 text-[11px] text-muted-foreground">
                      {s.desc}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${s.value}%`,
                        background: "var(--primary)",
                        opacity: 0.7 + s.value * 0.003,
                      }}
                    />
                  </div>
                </div>
                {/* Value */}
                <div className="shrink-0 text-right w-16">
                  <span className="text-[20px] font-bold tabular-nums leading-none text-foreground">
                    {s.display}
                  </span>
                  {s.suffix && (
                    <span className="text-[10px] text-muted-foreground ml-0.5">
                      {s.suffix}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

        </div>
      </CardContent>
    </Card>
  );
}
