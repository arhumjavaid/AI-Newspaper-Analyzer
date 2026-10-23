import React from "react";
import { Sparkles } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Plain-English "read it to the client" overview of the day's coverage.
export default function ExecutiveSummary({ summary, reputation }) {
  if (!summary) return null;
  const verdict =
    reputation >= 66 ? "Favourable" : reputation >= 40 ? "Mixed" : "At Risk";
  const variant =
    reputation >= 66 ? "positive" : reputation >= 40 ? "mixed" : "negative";

  return (
    <Card className="mt-[18px] border-primary/20 bg-gradient-to-br from-primary-soft/60 to-card p-5">
      <div className="mb-2.5 flex items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-primary-ink">
          <Sparkles className="size-4" /> AI Executive Summary
        </h3>
        <Badge variant={variant}>{verdict}</Badge>
      </div>
      <p className="max-w-[90ch] text-base leading-relaxed text-foreground">
        {summary}
      </p>
      <div className="mt-3 text-[11.5px] text-muted-foreground">
        Generated from today’s coverage · AI-assisted
      </div>
    </Card>
  );
}
