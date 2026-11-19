import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  tone?: "default" | "warning" | "danger";
}

export function KpiCard({
  title,
  value,
  description,
  icon: Icon,
  tone = "default",
}: KpiCardProps) {
  return (
    <Card
      className={cn(
        "rounded-sm shadow-sm",
        tone === "warning" && "border-alert-warning-border",
        tone === "danger" && "border-alert-destructive-border"
      )}
    >
      <CardContent className="flex items-start gap-4 p-5">
        <div
          className={cn(
            "flex size-10 items-center justify-center rounded-sm",
            tone === "default" && "bg-primary/10 text-primary",
            tone === "warning" && "bg-alert-warning-bg text-alert-warning-icon border border-alert-warning-border",
            tone === "danger" && "bg-alert-destructive-bg text-alert-destructive-icon border border-alert-destructive-border"
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</p>
          <div className="mt-0.5 text-2xl font-black tracking-tight">{value}</div>
          <p className="mt-1 text-xs text-muted-foreground">{description}</p>
        </div>
      </CardContent>
    </Card>
  );
}
