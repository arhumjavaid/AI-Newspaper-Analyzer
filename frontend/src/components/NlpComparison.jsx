import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Local NLP (VADER lexicon) vs the LLM's sentiment labels for the same articles.
const LLM_LABELS = ["positive", "neutral", "negative", "mixed"];
const VADER_LABELS = ["positive", "neutral", "negative"];

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-border bg-secondary/40 p-4">
      <div className="text-[12px] text-muted-foreground">{label}</div>
      <div className="mt-1 text-[22px] font-bold tabular-nums text-foreground">{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

export default function NlpComparison({ comparison }) {
  if (!comparison) return null;
  const c = comparison;
  const max = Math.max(
    1,
    ...LLM_LABELS.flatMap((l) => VADER_LABELS.map((v) => c.confusion_matrix[l]?.[v] || 0))
  );

  return (
    <Card className="mt-[18px]">
      <CardHeader className="flex-col gap-0">
        <CardTitle>NLP vs LLM Sentiment</CardTitle>
        <CardDescription>
          VADER lexicon (rule-based NLP) compared with Gemini on {c.articles} article
          {c.articles === 1 ? "" : "s"}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-[18px] pt-3 lg:grid-cols-[1fr_1.3fr]">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 lg:grid-cols-1">
          <Stat
            label="Label agreement"
            value={`${Math.round(c.agreement * 100)}%`}
            hint="same positive / neutral / negative label"
          />
          <Stat
            label="Score correlation"
            value={c.score_correlation ?? "–"}
            hint="Pearson r, −100…+100 scores"
          />
          <Stat
            label="Mean score difference"
            value={c.mean_abs_score_diff}
            hint="average |Gemini − VADER| points"
          />
        </div>

        <div className="overflow-x-auto">
          <div className="mb-2 text-[12px] font-semibold text-muted-foreground">
            Confusion matrix
          </div>
          <table className="w-full border-separate border-spacing-1 text-[13px]">
            <thead>
              <tr>
                <th className="text-left text-[11px] font-medium text-muted-foreground">
                  Gemini ↓ / VADER →
                </th>
                {VADER_LABELS.map((v) => (
                  <th key={v} className="text-center text-[11px] font-medium capitalize text-muted-foreground">
                    {v}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {LLM_LABELS.map((l) => (
                <tr key={l}>
                  <td className="pr-2 font-medium capitalize text-foreground">{l}</td>
                  {VADER_LABELS.map((v) => {
                    const n = c.confusion_matrix[l]?.[v] || 0;
                    return (
                      <td
                        key={v}
                        className={cn(
                          "rounded-md py-2 text-center font-semibold tabular-nums",
                          n === 0 ? "text-muted-foreground" : "text-foreground",
                          l === v ? "bg-positive-soft" : n > 0 ? "bg-negative-soft" : "bg-secondary/60"
                        )}
                        style={n > 0 ? { opacity: 0.55 + 0.45 * (n / max) } : undefined}
                      >
                        {n}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-muted-foreground">
            Green diagonal = agreement. VADER has no “mixed” class, so mixed articles always count as disagreement.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
