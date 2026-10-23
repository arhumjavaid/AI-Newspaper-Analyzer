import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Ranked horizontal-bar list. Sizes to its content (no fixed chart height),
// so it reads cleanly whether there are one or many outlets.
export default function ShareOfVoice({ data }) {
  const rows = [...(data || [])].sort(
    (a, b) => (b.mentions || 0) - (a.mentions || 0)
  );
  const max = Math.max(1, ...rows.map((r) => r.mentions || 0));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Share of Voice</CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        {rows.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted-foreground">
            No data yet
          </div>
        ) : (
          <div className="flex flex-col gap-3.5">
            {rows.map((r, i) => {
              const pct = Math.round(((r.mentions || 0) / max) * 100);
              return (
                <div key={i} className="flex items-center gap-3">
                  <span
                    className={cn(
                      "w-28 shrink-0 truncate text-[13px]",
                      r.is_client
                        ? "font-semibold text-foreground"
                        : "text-muted-foreground"
                    )}
                    title={r.name}
                  >
                    {r.name}
                  </span>
                  <div className="h-7 flex-1 overflow-hidden rounded-md bg-secondary">
                    <div
                      className="h-full rounded-md transition-all duration-700"
                      style={{
                        width: `${Math.max(pct, 4)}%`,
                        background: r.is_client
                          ? "var(--primary)"
                          : "var(--chart-primary-muted)",
                      }}
                    />
                  </div>
                  <span className="w-6 shrink-0 text-right text-[13px] font-semibold tabular-nums text-foreground">
                    {r.mentions}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
