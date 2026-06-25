"use client";

import { CampoPill } from "./ui";
import { formatTaskDomainLabel, type TaskDomain } from "@/lib/task-domain";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function TaskDomainBadge({
  domain,
  className,
}: {
  domain: TaskDomain;
  className?: string;
}) {
  return (
    <CampoPill
      className={cn(
        "px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]",
        domain === "PECUARIA"
          ? "border-purple-200 bg-purple-50 text-purple-800 dark:border-purple-900/60 dark:bg-purple-950/30 dark:text-purple-200"
          : "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200",
        className
      )}
    >
      [{formatTaskDomainLabel(domain).toUpperCase()}]
    </CampoPill>
  );
}

