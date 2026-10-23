import React, { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const RISK = {
  critical: { label: "Critical", variant: "negative", dot: "bg-negative", rank: 3 },
  negative: { label: "Negative", variant: "negative", dot: "bg-negative", rank: 2 },
  watch: { label: "Watch", variant: "mixed", dot: "bg-mixed", rank: 1 },
  positive: { label: "Positive", variant: "positive", dot: "bg-positive", rank: 0 },
};
const PROMINENCE_RANK = { front_page: 3, prominent: 2, standard: 1, minor: 0 };

const COLUMNS = [
  { key: "headline", label: "Headline", align: "left" },
  { key: "risk_level", label: "Risk", align: "left" },
  { key: "sentiment_score", label: "Sentiment", align: "right" },
  { key: "prominence", label: "Prominence", align: "left" },
  { key: "page", label: "Page", align: "right" },
  { key: "confidence", label: "Confidence", align: "right" },
];

function sortValue(a, key) {
  if (key === "risk_level") return RISK[a.risk_level]?.rank ?? -1;
  if (key === "prominence") return PROMINENCE_RANK[a.prominence] ?? -1;
  if (key === "headline") return (a.headline || "").toLowerCase();
  return a[key] ?? 0;
}

export default function ArticleTable({ articles }) {
  const [sort, setSort] = useState({ key: "risk_level", dir: "desc" });

  function toggle(key) {
    setSort((s) =>
      s.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "headline" ? "asc" : "desc" }
    );
  }

  const rows = [...articles].sort((x, y) => {
    const vx = sortValue(x, sort.key);
    const vy = sortValue(y, sort.key);
    if (vx < vy) return sort.dir === "asc" ? -1 : 1;
    if (vx > vy) return sort.dir === "asc" ? 1 : -1;
    return 0;
  });

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {COLUMNS.map((c) => (
            <TableHead
              key={c.key}
              onClick={() => toggle(c.key)}
              className={cn(
                "cursor-pointer select-none hover:text-primary-ink",
                c.align === "right" && "text-right"
              )}
            >
              <span
                className={cn(
                  "inline-flex items-center gap-1",
                  c.align === "right" && "flex-row-reverse"
                )}
              >
                {c.label}
                {sort.key === c.key &&
                  (sort.dir === "asc" ? (
                    <ChevronUp className="size-3.5 text-primary-ink" />
                  ) : (
                    <ChevronDown className="size-3.5 text-primary-ink" />
                  ))}
              </span>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((a, i) => {
          const risk = RISK[a.risk_level];
          return (
            <TableRow key={i}>
              <TableCell className="max-w-[420px] font-medium text-foreground">
                {a.headline}
                {a.relevance === "implicit" && (
                  <Badge variant="mixed" className="ml-1.5 text-[10px]">
                    implied
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                {risk && (
                  <Badge variant={risk.variant}>
                    <span className={cn("size-1.5 rounded-full", risk.dot)} />
                    {risk.label}
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right">
                <Badge variant={a.sentiment_label}>
                  {a.sentiment_score > 0
                    ? `+${a.sentiment_score}`
                    : a.sentiment_score}
                </Badge>
              </TableCell>
              <TableCell className="capitalize">
                {a.prominence?.replace("_", " ")}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {a.page ?? "?"}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {Math.round((a.confidence ?? 0) * 100)}%
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
