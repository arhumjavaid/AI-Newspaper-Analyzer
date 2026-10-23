import React from "react";
import { Users, MapPin, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const GROUPS = [
  { key: "people", label: "People Quoted", Icon: Users },
  { key: "locations", label: "Areas Affected", Icon: MapPin },
  { key: "organisations", label: "Organisations", Icon: Building2 },
];

function initials(name) {
  return (name || "")
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

function Group({ label, Icon, items, kind }) {
  return (
    <div className="rounded-xl border border-border bg-secondary/40 p-4">
      <div className="mb-3 flex items-center gap-2">
        <div className="grid size-8 place-items-center rounded-lg bg-primary-soft text-primary-ink">
          <Icon className="size-4" />
        </div>
        <span className="text-[13px] font-semibold text-foreground">{label}</span>
        <span className="ml-auto rounded-full border border-border bg-card px-2 py-0.5 text-[11px] font-semibold tabular-nums text-muted-foreground">
          {items.length}
        </span>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border px-3 py-2.5 text-center text-[13px] text-muted-foreground">
          None named
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((e) => (
            <span
              key={e.name}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-card py-1.5 pl-1.5 pr-3 text-[13px] font-medium text-foreground shadow-card transition-colors hover:border-border-strong"
            >
              {kind === "people" ? (
                <span className="grid size-6 place-items-center rounded-full bg-primary-soft text-[10px] font-bold text-primary-ink">
                  {initials(e.name)}
                </span>
              ) : (
                <span className="grid size-6 place-items-center rounded-full bg-secondary text-muted-foreground">
                  <Icon className="size-3.5" />
                </span>
              )}
              {e.name}
              {e.count > 1 && (
                <span className="rounded-full bg-primary-soft px-1.5 py-px text-[10px] font-bold tabular-nums text-primary-ink">
                  ×{e.count}
                </span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EntityInsights({ insights }) {
  if (!insights) return null;
  const total = GROUPS.reduce((n, g) => n + (insights[g.key]?.length || 0), 0);
  if (total === 0) return null;

  return (
    <Card className="mt-[18px]">
      <CardHeader>
        <CardTitle>Entity Insight</CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 pt-2 md:grid-cols-3">
        {GROUPS.map((g) => (
          <Group
            key={g.key}
            label={g.label}
            Icon={g.Icon}
            kind={g.key}
            items={insights[g.key] || []}
          />
        ))}
      </CardContent>
    </Card>
  );
}
