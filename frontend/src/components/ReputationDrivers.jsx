import React from "react";
import { AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// How much a story's tone counts toward reputation depends on where it ran:
// a front-page hit moves the needle far more than a buried mention.
const PROM_WEIGHT = {
  front_page: 2.2,
  prominent: 1.6,
  standard: 1.0,
  minor: 0.6,
};
const isProminent = (p) => p === "front_page" || p === "prominent";

// Decomposes the reputation index into the topics lifting it vs. dragging it
// down. Each topic's impact = Σ(article sentiment_score × prominence weight),
// so it answers "which narratives are actually moving the score, and by how
// much" — not just how often a topic appears.
export default function ReputationDrivers({ articles }) {
  const rows = articles || [];
  const map = {};

  rows.forEach((a) => {
    const score = typeof a.sentiment_score === "number" ? a.sentiment_score : 0;
    const w = PROM_WEIGHT[a.prominence] ?? 1;
    (a.topics || []).forEach((t) => {
      const e = (map[t] ||= {
        topic: t,
        impact: 0,
        count: 0,
        flagged: false, // negative coverage in a prominent slot
      });
      e.impact += score * w;
      e.count += 1;
      if (a.sentiment_label === "negative" && isProminent(a.prominence))
        e.flagged = true;
    });
  });

  const topics = Object.values(map)
    .filter((t) => t.count > 0)
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 7);
  if (topics.length === 0) return null;

  const maxAbs = Math.max(...topics.map((t) => Math.abs(t.impact)), 1);

  const lifts = topics.filter((t) => t.impact > 0);
  const drags = topics.filter((t) => t.impact < 0);
  const topLift = lifts[0] || topics.find((t) => t.impact > 0);
  const topDrag = [...drags].sort((a, b) => a.impact - b.impact)[0];

  return (
    <Card className="mt-[18px] break-inside-avoid">
      <CardHeader>
        <CardTitle>Reputation Drivers</CardTitle>
        <span className="text-[13px] text-muted-foreground">
          Net reputation impact by topic · prominence-weighted points
        </span>
      </CardHeader>
      <CardContent className="pt-2">
        {/* axis labels */}
        <div className="mb-2 flex items-center gap-3">
          <span className="w-28 shrink-0" />
          <div className="flex flex-1 items-center justify-between text-[11px] font-semibold uppercase tracking-[0.04em]">
            <span className="flex items-center gap-1 text-negative">
              <TrendingDown className="size-3.5" /> Drags
            </span>
            <span className="flex items-center gap-1 text-positive">
              Lifts <TrendingUp className="size-3.5" />
            </span>
          </div>
          <span className="w-16 shrink-0" />
        </div>

        <div className="flex flex-col gap-2.5">
          {topics.map((t) => {
            // Scale the raw weighted sum into readable "impact points".
            const points = Math.round(t.impact / 10);
            const zero = points === 0;
            const positive = t.impact >= 0;
            const pct = (Math.abs(t.impact) / maxAbs) * 50; // half-track max
            return (
              <div key={t.topic} className="flex items-center gap-3">
                <span
                  className="flex w-28 shrink-0 items-center justify-end gap-1 truncate text-right text-[13px] font-medium text-foreground"
                  title={t.topic}
                >
                  {t.flagged && (
                    <AlertTriangle
                      className="size-3.5 shrink-0 text-negative"
                      aria-label="Negative coverage in a prominent slot"
                    />
                  )}
                  <span className="truncate">{t.topic}</span>
                </span>

                {/* diverging track with a center spine */}
                <div className="relative h-7 flex-1 rounded-md bg-secondary/50">
                  <div className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-border-strong" />
                  {!zero && (
                    <div
                      className="absolute inset-y-1 rounded-[5px] transition-all"
                      style={{
                        width: `${Math.max(pct, 1.5)}%`,
                        [positive ? "left" : "right"]: "50%",
                        background: positive
                          ? "linear-gradient(90deg, color-mix(in srgb, var(--positive) 55%, transparent), var(--positive))"
                          : "linear-gradient(270deg, color-mix(in srgb, var(--negative) 55%, transparent), var(--negative))",
                        borderRadius: positive
                          ? "5px 6px 6px 5px"
                          : "6px 5px 5px 6px",
                      }}
                    />
                  )}
                </div>

                <span
                  className={
                    "w-16 shrink-0 text-right text-[13px] font-bold tabular-nums " +
                    (zero
                      ? "text-muted-foreground"
                      : positive
                        ? "text-positive"
                        : "text-negative")
                  }
                >
                  {zero ? "0" : `${positive ? "+" : "−"}${Math.abs(points)}`}
                  <span className="text-[11px] font-normal text-muted-foreground">
                    {" "}
                    pts
                  </span>
                </span>
              </div>
            );
          })}
        </div>

        {/* exec read-out */}
        <div className="mt-4 border-t border-border pt-3 text-[13px] text-ink2">
          {topLift && (
            <span>
              <b className="text-positive">{topLift.topic}</b> coverage is
              lifting your reputation the most
            </span>
          )}
          {topLift && topDrag && <span> · </span>}
          {topDrag && (
            <span>
              <b className="text-negative">{topDrag.topic}</b> is your biggest
              drag
              {topDrag.flagged && " — and it ran in a prominent slot"}
            </span>
          )}
          {!topDrag && topLift && (
            <span> · no topic is dragging the score down</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
