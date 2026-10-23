import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Coverage topics as count-badged chips. Uniform sizing reads cleanly with a
// few topics or many; the most-covered topic gets a subtle primary emphasis.
export default function Topics({ topics }) {
  const rows = [...(topics || [])].sort((a, b) => (b.count || 0) - (a.count || 0));
  const max = Math.max(1, ...rows.map((t) => t.count || 0));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Coverage Topics</CardTitle>
      </CardHeader>
      <CardContent className="pt-2">
        {rows.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted-foreground">
            No topics yet
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {rows.map((t) => {
              const isTop = (t.count || 0) === max;
              return (
                <span
                  key={t.topic}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-medium",
                    isTop
                      ? "border-primary/20 bg-primary-soft text-primary-ink"
                      : "border-border bg-secondary text-foreground"
                  )}
                >
                  {t.topic}
                  <span
                    className={cn(
                      "rounded-full px-1.5 py-px text-[10px] font-bold tabular-nums",
                      isTop
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-card text-muted-foreground"
                    )}
                  >
                    {t.count}
                  </span>
                </span>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
