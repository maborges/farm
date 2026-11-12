"use client";

import * as React from "react";
import Link from "next/link";
import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface QuickActionItem {
  id?: string;
  title: string;
  description: string;
  icon: LucideIcon | React.ComponentType<{ className?: string }>;
  href?: string;
  onClick?: () => void;
  badge?: string | number | null;
  badgeVariant?: "default" | "secondary" | "destructive" | "outline";
}

export interface QuickActionGridProps {
  actions: QuickActionItem[];
  label?: string;
  columnsClassName?: string;
  className?: string;
  layout?: "grid" | "centered";
}

export function QuickActionGrid({
  actions,
  label = "Comandos Rápidos",
  columnsClassName = "grid-cols-2 sm:grid-cols-4 lg:grid-cols-8",
  className,
  layout = "grid",
}: QuickActionGridProps) {
  const isCentered = layout === "centered";

  return (
    <div className={cn("space-y-2", className)}>
      {isCentered && (
        <style>{`
          .quick-action-item {
            width: calc((100% - 10px) / 2);
            max-width: calc((100% - 10px) / 2);
            flex: 0 0 calc((100% - 10px) / 2);
            height: 96px;
            min-height: 96px;
            max-height: 96px;
            box-sizing: border-box;
          }
          .quick-action-item > * {
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
          }
          @media (min-width: 640px) {
            .quick-action-item {
              width: calc((100% - 20px) / 3);
              max-width: calc((100% - 20px) / 3);
              flex: 0 0 calc((100% - 20px) / 3);
            }
          }
          @media (min-width: 1024px) {
            .quick-action-item {
              width: calc((100% - 50px) / 6);
              max-width: calc((100% - 50px) / 6);
              flex: 0 0 calc((100% - 50px) / 6);
            }
          }
        `}</style>
      )}

      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <span className="text-[11px] text-muted-foreground">
          {actions.length} atalhos diretos
        </span>
      </div>

      <div
        className={
          isCentered
            ? "flex flex-wrap justify-center gap-2.5"
            : cn("grid gap-2", columnsClassName)
        }
      >
        {actions.map((action, idx) => {
          const Icon = action.icon;
          const key = action.id ?? `${action.title}-${action.href ?? idx}`;

          const innerContent = (
            <div className="w-full h-full flex flex-col items-center justify-center gap-1.5">
              <div className="relative flex items-center justify-center">
                <div className="size-10 rounded-sm bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-200 shadow-2xs flex items-center justify-center p-0 overflow-hidden">
                  <Icon className="size-5 shrink-0" />
                </div>
                {action.badge ? (
                  <Badge
                    variant={action.badgeVariant ?? "secondary"}
                    className="absolute -top-1 -right-2 text-[9px] px-1 py-0 h-3.5 rounded-sm font-semibold truncate max-w-[65px]"
                  >
                    {action.badge}
                  </Badge>
                ) : null}
              </div>
              <div className="font-semibold text-xs leading-tight text-foreground group-hover:text-primary transition-colors text-center line-clamp-2 px-1">
                {action.title}
              </div>
            </div>
          );

          const buttonClassName =
            "w-full h-full p-2 flex flex-col items-center justify-center text-center rounded-sm border-border/70 hover:border-primary/60 hover:bg-primary/[0.03] transition-colors group relative overflow-hidden";

          return (
            <div
              key={key}
              className={isCentered ? "quick-action-item" : undefined}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  {action.href ? (
                    action.href.startsWith("#") ? (
                      <Button
                        asChild
                        variant="outline"
                        size="sm"
                        className={buttonClassName}
                        style={{ width: "100%", height: "100%" }}
                      >
                        <a href={action.href} style={{ width: "100%", height: "100%" }}>
                          {innerContent}
                        </a>
                      </Button>
                    ) : (
                      <Button
                        asChild
                        variant="outline"
                        size="sm"
                        className={buttonClassName}
                        style={{ width: "100%", height: "100%" }}
                      >
                        <Link href={action.href} style={{ width: "100%", height: "100%" }}>
                          {innerContent}
                        </Link>
                      </Button>
                    )
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={action.onClick}
                      className={buttonClassName}
                      style={{ width: "100%", height: "100%" }}
                    >
                      {innerContent}
                    </Button>
                  )}
                </TooltipTrigger>
                <TooltipContent
                  side="top"
                  className="max-w-[220px] text-center text-xs p-2.5 rounded-sm border border-border/80 bg-popover text-popover-foreground shadow-lg dark:bg-card dark:text-foreground"
                >
                  <p className="text-xs leading-relaxed font-normal">{action.description}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          );
        })}
      </div>
    </div>
  );
}

