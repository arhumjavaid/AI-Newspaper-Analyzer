import React from "react";
import { AlertTriangle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function CrisisAlerts({ alerts }) {
  const rows = alerts || [];
  if (rows.length === 0) return null;
  return (
    <Card className="mt-[18px] border-negative/35 bg-gradient-to-b from-negative-soft to-card p-5">
      <h3 className="mb-1 flex items-center gap-2 text-[11.5px] font-semibold uppercase tracking-[0.08em] text-negative">
        <AlertTriangle className="size-4" /> Crisis Alerts · {rows.length} need
        response
      </h3>
      {rows.map((a, i) => (
        <div key={i} className="border-t border-border py-3.5 first:border-0">
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-semibold text-foreground">{a.headline}</span>
            <Badge variant="negative">{a.sentiment_score}</Badge>
          </div>
          {a.key_quote && (
            <div className="mt-1.5 text-[13px] italic text-ink2">
              “{a.key_quote}”
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>Page {a.page ?? "?"}</span>
            <span>{a.prominence?.replace("_", " ")}</span>
            {a.tone_tags?.length > 0 && <span>{a.tone_tags.join(", ")}</span>}
          </div>
          {a.suggested_response && (
            <div className="mt-2 text-[13px] text-ink2">
              <b className="text-primary-ink">Suggested response (drafted by Gemini):</b>{" "}
              {a.suggested_response}
            </div>
          )}
        </div>
      ))}
    </Card>
  );
}
