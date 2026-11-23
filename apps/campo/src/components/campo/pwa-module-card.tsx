"use client";

import type { CSSProperties } from "react";
import { ArrowRight, type LucideIcon } from "lucide-react";
import { formatInt } from "@/lib/format";

type ModuleColor = "agro" | "pecuaria";

interface PwaModuleCardProps {
  label: string;
  sublabel: string;
  icon: LucideIcon;
  taskCount: number;
  urgentCount: number;
  color: ModuleColor;
  onClick: () => void;
  disabled?: boolean;
  animDelay?: string;
}

const COLOR_MAP: Record<ModuleColor, { iconBox: string }> = {
  agro: {
    iconBox: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  },
  pecuaria: {
    iconBox: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  },
};

export function PwaModuleCard({
  label,
  sublabel,
  icon: Icon,
  taskCount,
  urgentCount,
  color,
  onClick,
  disabled = false,
  animDelay = "0ms",
}: PwaModuleCardProps) {
  const c = COLOR_MAP[color];

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{ "--campo-pwa-delay": animDelay } as CSSProperties}
      className="group campo-pwa-card-stagger flex h-full w-full flex-col justify-between rounded-xl md:rounded-sm border border-border bg-card text-card-foreground text-left shadow-2xs transition-all hover:border-primary/50 hover:shadow-xs active:scale-[0.99] disabled:pointer-events-none disabled:opacity-40"
    >
      {/* Topo no mesmo padrão visual do CardHeader do Agro */}
      <div className="flex w-full flex-row items-start justify-between p-3.5 pb-2 sm:p-5 sm:pb-2">
        <div className={["p-2.5 rounded-lg md:rounded-sm", c.iconBox].join(" ")}>
          <Icon className="w-5 h-5" />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="inline-flex items-center rounded-md md:rounded-sm border border-border px-2 py-0.5 text-[11px] md:text-[10px] font-semibold text-foreground">
            {formatInt(taskCount)} tarefa{taskCount !== 1 ? "s" : ""}
          </span>

          {urgentCount > 0 && (
            <span className="inline-flex items-center rounded-md md:rounded-sm border border-rose-500/30 bg-rose-500/15 px-2 py-0.5 text-[11px] md:text-[10px] font-semibold text-rose-700 dark:text-rose-400">
              {formatInt(urgentCount)} urgente{urgentCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Conteúdo no mesmo padrão visual do CardContent do Agro */}
      <div className="flex w-full flex-col gap-1 p-3.5 pt-0 sm:p-5 sm:pt-0">
        <div className="flex items-center justify-between text-base font-semibold leading-none tracking-tight text-foreground">
          <span>{label}</span>
          <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">{sublabel}</p>
      </div>
    </button>
  );
}
