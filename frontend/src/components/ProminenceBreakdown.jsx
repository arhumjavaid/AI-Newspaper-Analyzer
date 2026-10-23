import React from "react";
import { AlertTriangle, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Ordinal single-hue scale (darkest = most prominent). Not sentiment colour —
// this is "how visible was the coverage", independent of tone.
const LEVELS = [
  { key: "front_page", label: "Front page", shade: "var(--primary)" },
  {
    key: "prominent",
    label: "Prominent",
    shade: "color-mix(in oklch, var(--primary) 60%, var(--card))",
  },
  { key: "standard", label: "Standard", shade: "var(--chart-primary-muted)" },
  {
    key: "minor",
    label: "Minor",
    shade: "color-mix(in oklch, var(--chart-primary-muted) 45%, var(--card))",
  },
];

const isProminent = (a) =>
  a.prominence === "front_page" || a.prominence === "prominent";

export default function ProminenceBreakdown({ articles }) {
  const rows = articles || [];
  if (rows.length === 0) return null;

  const total = rows.length;
  const counts = LEVELS.map((l) => ({
    ...l,
    count: rows.filter((a) => a.prominence === l.key).length,
  }));

  // Prominence × sentiment — the stories that actually need attention.
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
        <CardTitle>Coverage Prominence</CardTitle>
        <span className="text-[13px] text-muted-foreground">
          How visible the client was across the issue
        </span>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="flex h-9 w-full gap-0.5 overflow-hidden rounded-lg">
          {counts
            .filter((c) => c.count > 0)
            .map((c) => (
              <div
                key={c.key}
                className="h-full first:rounded-l-lg last:rounded-r-lg"
                style={{
                  width: `${(c.count / total) * 100}%`,
                  background: c.shade,
                }}
                title={`${c.label}: ${c.count}`}
              />
            ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2.5">
          {counts.map((c) => (
            <div key={c.key} className="flex items-center gap-2 text-[13px]">
              <span
                className="size-2.5 rounded-full"
                style={{ background: c.shade }}
              />
              <span className="text-muted-foreground">{c.label}</span>
              <span className="font-semibold tabular-nums text-foreground">
                {c.count}
              </span>
            </div>
          ))}
        </div>

        {/* High-impact = prominent position × strong sentiment */}
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
