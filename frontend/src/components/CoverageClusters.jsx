import React from "react";
import { X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Clickable coverage-cluster chips that filter the article feed.
// Degrades to nothing when the backend supplies no clusters.
export default function CoverageClusters({ clusters, active, onSelect }) {
  const rows = clusters || [];
  if (rows.length === 0) return null;

  const nameOf = (c) => c.name ?? c.label ?? c.cluster ?? c;

  return (
    <Card className="mt-[18px]">
      <CardHeader>
        <CardTitle>Coverage Clusters</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2 pt-0">
        {rows.map((c) => {
          const name = nameOf(c);
          const isActive = active === name;
          return (
            <button
              key={name}
              onClick={() => onSelect(isActive ? null : name)}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[13px] font-medium transition-colors",
                isActive
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border-strong bg-card text-ink2 hover:border-primary hover:text-primary-ink"
              )}
            >
              {name}
              {c.count != null && (
                <span
                  className={cn(
                    "rounded-full px-2 py-px text-[11px] font-bold tabular-nums",
                    isActive
                      ? "bg-white/25 text-white"
                      : "bg-secondary text-primary-ink"
                  )}
                >
                  {c.count}
                </span>
              )}
            </button>
          );
        })}
        {active && (
          <button
            onClick={() => onSelect(null)}
            className="inline-flex items-center gap-1 px-1.5 py-1 text-[12.5px] text-muted-foreground transition-colors hover:text-negative"
          >
            <X className="size-3.5" /> Clear
          </button>
        )}
      </CardContent>
    </Card>
  );
}
