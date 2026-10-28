import React from "react";
import { AlertTriangle, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import ArticleNlp from "./ArticleNlp";

const RISK = {
  critical: { label: "Critical", variant: "negative", dot: "bg-negative" },
  negative: { label: "Negative", variant: "negative", dot: "bg-negative" },
  watch: { label: "Watch", variant: "mixed", dot: "bg-mixed" },
  positive: { label: "Positive", variant: "positive", dot: "bg-positive" },
};

export default function ArticleCard({ article }) {
  const a = article;
  const risk = RISK[a.risk_level];
  return (
    <div
      className={cn(
        "mb-3.5 rounded-md border border-border bg-card p-[18px] transition-shadow hover:border-border-strong hover:shadow-lift",
        a.risk_level === "critical" &&
          "border-negative/45 shadow-[0_0_0_1px_rgba(204,66,80,0.2)]"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-base font-semibold leading-snug text-foreground">
          {a.headline}
          {a.relevance === "implicit" && (
            <Badge
              variant="mixed"
              className="ml-2 align-middle text-[10px]"
              title="Client not named, but clearly about its electricity domain"
            >
              implied
            </Badge>
          )}
        </h4>
        <div className="flex shrink-0 gap-1.5">
          {a.needs_review && (
            <Badge
              variant="mixed"
              title={`LLM verdict needs a human check: ${a.review_reasons.join("; ")}`}
            >
              <AlertTriangle className="size-3" /> Review
            </Badge>
          )}
          {risk && (
            <Badge variant={risk.variant} title="PR risk level">
              <span className={cn("size-1.5 rounded-full", risk.dot)} />
              {risk.label}
            </Badge>
          )}
          <Badge variant={a.sentiment_label} title={a.llm ? "Sentiment from the NLP engine" : undefined}>
            {a.sentiment_label}{" "}
            {a.sentiment_score > 0 ? `+${a.sentiment_score}` : a.sentiment_score}
          </Badge>
        </div>
      </div>

      {a.summary && (
        <div className="my-2.5 text-sm text-ink2">{a.summary}</div>
      )}
      {a.key_quote && (
        <div className="my-2.5 border-l-[3px] border-primary pl-3 text-[13.5px] italic text-ink2">
          “{a.key_quote}”
        </div>
      )}

      {(a.tone_tags?.length > 0 || a.topics?.length > 0) && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {a.tone_tags?.map((t) => (
            <Badge key={t} variant="outline" className="font-medium">
              {t}
            </Badge>
          ))}
          {a.topics?.map((t) => (
            <Badge key={t} variant="primary" className="font-medium">
              #{t}
            </Badge>
          ))}
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-border pt-3 text-xs text-muted-foreground">
        <span>Page {a.page ?? "?"}</span>
        <span className="capitalize">{a.prominence?.replace("_", " ")}</span>
        {a.locations?.length > 0 && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="size-3" /> {a.locations.join(", ")}
          </span>
        )}
        {a.entities?.length > 0 && <span>Mentions: {a.entities.join(", ")}</span>}
        <span>{a.llm ? "NLP confidence" : "Confidence"} {Math.round((a.confidence ?? 0) * 100)}%</span>
      </div>

      {a.needs_review && (
        <div className="mt-3 rounded-md border border-mixed/40 bg-mixed/10 px-3 py-2 text-xs text-ink2">
          <span className="font-semibold">Needs human review:</span>{" "}
          {a.review_reasons.join(" · ")}
        </div>
      )}

      <ArticleNlp nlp={a.nlp} llmLabel={a.llm ? a.llm.sentiment_label : a.sentiment_label} />
    </div>
  );
}
