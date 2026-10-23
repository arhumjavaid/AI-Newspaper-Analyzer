import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SENTIMENT, CHART, tooltipStyle, tooltipLabelStyle } from "../chartTheme";

export default function SentimentDonut({ distribution }) {
  const data = Object.entries(distribution || {})
    .map(([name, value]) => ({ name, value }))
    .filter((d) => d.value > 0);
  const total = data.reduce((n, d) => n + d.value, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sentiment Breakdown</CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        {data.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted-foreground">
            No data yet
          </div>
        ) : data.length === 1 ? (
          // A donut around a single 100% slice is noise — show a clean stat.
          <div className="flex items-center gap-4 py-2">
            <div className="flex flex-col items-center justify-center rounded-2xl border border-border bg-secondary/50 px-6 py-4">
              <span
                className="text-4xl font-bold leading-none tabular-nums"
                style={{ color: SENTIMENT[data[0].name] || CHART.primary }}
              >
                {total}
              </span>
              <span className="mt-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                {total === 1 ? "article" : "articles"}
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2 text-base font-semibold capitalize text-foreground">
                <span
                  className="size-3 rounded-full"
                  style={{ background: SENTIMENT[data[0].name] || CHART.primary }}
                />
                {data[0].name}
              </div>
              <div className="mt-1 text-[13px] text-muted-foreground">
                100% of coverage in this report
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:gap-2">
            <div className="relative h-[200px] w-full sm:w-1/2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={62}
                    outerRadius={88}
                    paddingAngle={data.length > 1 ? 2 : 0}
                    cornerRadius={6}
                    stroke="none"
                  >
                    {data.map((d) => (
                      <Cell key={d.name} fill={SENTIMENT[d.name] || CHART.primary} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={tooltipStyle}
                    labelStyle={tooltipLabelStyle}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold leading-none tracking-tight tabular-nums text-foreground">
                  {total}
                </span>
                <span className="mt-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  articles
                </span>
              </div>
            </div>
            <ul className="flex w-full flex-col gap-2 sm:w-1/2">
              {data.map((d) => (
                <li
                  key={d.name}
                  className="flex items-center justify-between gap-3 text-sm"
                >
                  <span className="flex items-center gap-2 capitalize text-ink2">
                    <span
                      className="size-2.5 rounded-full"
                      style={{ background: SENTIMENT[d.name] || CHART.primary }}
                    />
                    {d.name}
                  </span>
                  <span className="font-semibold tabular-nums text-foreground">
                    {d.value}
                    <span className="ml-1 text-xs font-normal text-muted-foreground">
                      {Math.round((d.value / total) * 100)}%
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
