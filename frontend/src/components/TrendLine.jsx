import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CHART, tooltipStyle, tooltipLabelStyle, axisTick } from "../chartTheme";

export default function TrendLine({ trends }) {
  const parsed = (trends || []).map((t) => ({
    date: new Date(t.date),
    reputation: t.reputation_index,
    articles: t.article_count,
  }));

  // When several analyses fall on one day, label by time so points don't all
  // read as the same date. Each point keeps a distinct x position (index).
  const sameDay =
    parsed.length > 1 &&
    new Set(parsed.map((p) => p.date.toDateString())).size <= 1;

  const data = parsed.map((p, i) => ({
    i,
    label: Number.isNaN(p.date.getTime())
      ? `#${i + 1}`
      : sameDay
        ? p.date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        : p.date.toLocaleDateString([], { month: "short", day: "numeric" }),
    reputation: p.reputation,
  }));

  const labelFor = (i) => data[i]?.label ?? "";
  const latest = data.length ? data[data.length - 1].reputation : null;
  const showChart = data.length >= 2;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reputation Trend</CardTitle>
        {latest != null && (
          <span className="text-[13px] font-semibold tabular-nums text-foreground">
            Now {latest}
            <span className="ml-1 text-[11px] font-normal text-muted-foreground">
              / 100
            </span>
          </span>
        )}
      </CardHeader>
      <CardContent className="pt-2">
        {showChart ? (
          <ResponsiveContainer width="100%" height={232}>
            <AreaChart
              data={data}
              margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="repFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={CHART.primary} stopOpacity={0.22} />
                  <stop offset="95%" stopColor={CHART.primary} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={CHART.grid} strokeWidth={1} vertical={false} />
              <XAxis
                dataKey="i"
                type="number"
                domain={["dataMin", "dataMax"]}
                ticks={data.map((d) => d.i)}
                tickFormatter={labelFor}
                tick={axisTick}
                tickLine={false}
                axisLine={false}
                tickMargin={10}
              />
              <YAxis
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                tick={axisTick}
                tickLine={false}
                axisLine={false}
                width={36}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                labelStyle={tooltipLabelStyle}
                labelFormatter={labelFor}
                cursor={{ stroke: CHART.primaryMuted, strokeWidth: 1.5 }}
              />
              <Area
                type="monotone"
                dataKey="reputation"
                name="Reputation"
                stroke={CHART.primary}
                strokeWidth={2.5}
                fill="url(#repFill)"
                dot={
                  data.length <= 8
                    ? { r: 4, fill: CHART.primary, stroke: "#fff", strokeWidth: 2 }
                    : false
                }
                activeDot={{ r: 5, fill: CHART.primary, stroke: "#fff", strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 text-center">
            {latest != null ? (
              <>
                <span className="text-[44px] font-bold leading-none tracking-tight tabular-nums text-foreground">
                  {latest}
                </span>
                <span className="text-[13px] text-muted-foreground">
                  Reputation from your first analysis
                </span>
                <span className="mt-1 max-w-[24ch] text-xs text-muted-foreground">
                  Analyze more issues to plot the trend over time.
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">
                Analyze newspapers over time to see the reputation trend.
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
