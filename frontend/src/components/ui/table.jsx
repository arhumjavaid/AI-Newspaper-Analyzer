import React from "react";
import { cn } from "@/lib/utils";

export function Table({ className, ...props }) {
  return (
    <div className="w-full overflow-x-auto">
      <table
        className={cn("w-full caption-bottom text-[13.5px]", className)}
        {...props}
      />
    </div>
  );
}

export function TableHeader({ className, ...props }) {
  return <thead className={cn(className)} {...props} />;
}

export function TableBody({ className, ...props }) {
  return <tbody className={cn(className)} {...props} />;
}

export function TableRow({ className, ...props }) {
  return (
    <tr
      className={cn(
        "border-b border-border transition-colors last:border-0 hover:bg-secondary",
        className
      )}
      {...props}
    />
  );
}

export function TableHead({ className, ...props }) {
  return (
    <th
      className={cn(
        "border-b border-border-strong px-3 py-2.5 text-left text-[11.5px] font-semibold uppercase tracking-[0.04em] text-muted-foreground whitespace-nowrap",
        className
      )}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }) {
  return (
    <td
      className={cn("px-3 py-2.5 align-middle text-ink2", className)}
      {...props}
    />
  );
}
