import React from "react";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

// Sentiment chips: soft tint + matching border, tabular numerics.
const badgeVariants = cva(
  "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-semibold tabular-nums",
  {
    variants: {
      variant: {
        default: "border-border bg-secondary text-muted-foreground",
        primary:
          "border-primary/20 bg-primary-soft text-primary-ink",
        outline: "border-border-strong bg-card text-muted-foreground",
        positive: "border-positive/25 bg-positive-soft text-positive",
        negative: "border-negative/25 bg-negative-soft text-negative",
        neutral: "border-border-strong bg-neutral-soft text-neutral",
        mixed: "border-mixed/30 bg-mixed-soft text-mixed",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export function Badge({ className, variant, ...props }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { badgeVariants };
