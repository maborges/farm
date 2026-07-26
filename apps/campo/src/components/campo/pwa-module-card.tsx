"use client";

import { type LucideIcon } from "lucide-react";
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

const COLOR_MAP: Record<
  ModuleColor,
  {
    border: string;
    bg: string;
    iconBg: string;
    iconColor: string;
    badgeBg: string;
    badgeText: string;
    urgentBg: string;
    urgentText: string;
    pulse: string;
  }
> = {
  agro: {
    border: "border-[var(--campo-pwa-agro-light)] dark:border-[var(--campo-pwa-agro-mid)]",
    bg: "bg-[var(--campo-pwa-agro-bg)] dark:bg-[var(--campo-pwa-agro-bg)]",
    iconBg: "bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-light)]",
    iconColor: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    badgeBg: "bg-[var(--campo-pwa-agro-light)] dark:bg-[var(--campo-pwa-agro-light)]",
    badgeText: "text-[var(--campo-pwa-agro-dark-text)] dark:text-[var(--campo-pwa-agro)]",
    urgentBg: "bg-rose-100 dark:bg-rose-950/40",
    urgentText: "text-rose-700 dark:text-rose-300",
    pulse: "bg-[var(--campo-pwa-agro)]",
  },
  pecuaria: {
    border: "border-[var(--campo-pwa-pecuaria-light)] dark:border-[var(--campo-pwa-pecuaria-mid)]",
    bg: "bg-[var(--campo-pwa-pecuaria-bg)] dark:bg-[var(--campo-pwa-pecuaria-bg)]",
    iconBg: "bg-[var(--campo-pwa-pecuaria-light)] dark:bg-[var(--campo-pwa-pecuaria-light)]",
    iconColor: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    badgeBg: "bg-[var(--campo-pwa-pecuaria-light)] dark:bg-[var(--campo-pwa-pecuaria-light)]",
    badgeText: "text-[var(--campo-pwa-pecuaria-dark-text)] dark:text-[var(--campo-pwa-pecuaria)]",
    urgentBg: "bg-rose-100 dark:bg-rose-950/40",
    urgentText: "text-rose-700 dark:text-rose-300",
    pulse: "bg-[var(--campo-pwa-pecuaria)]",
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
      style={{ "--campo-pwa-delay": animDelay } as React.CSSProperties}
      className={[
        "campo-pwa-card-stagger",
        "relative flex w-full flex-col rounded-2xl border p-5 text-left shadow-sm",
        "transition-all duration-200 ease-out",
        "active:scale-[0.96] active:shadow-none",
        "hover:shadow-md",
        "disabled:pointer-events-none disabled:opacity-40",
        c.border,
        c.bg,
      ].join(" ")}
    >
      {/* Dot de status ativo */}
      <span
        className={[
          "campo-pwa-pulse-dot absolute right-4 top-4 size-2 rounded-full",
          taskCount > 0 ? c.pulse : "bg-muted-foreground/30",
        ].join(" ")}
      />

      {/* Ícone */}
      <span
        className={[
          "flex size-14 items-center justify-center rounded-2xl",
          c.iconBg,
          c.iconColor,
        ].join(" ")}
      >
        <Icon className="size-7" strokeWidth={1.75} />
      </span>

      {/* Título e subtítulo */}
      <p className="mt-4 text-base font-bold tracking-tight text-foreground">{label}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{sublabel}</p>

      {/* Badges de contagem */}
      <div className="mt-4 flex flex-wrap gap-2">
        <span
          className={[
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold",
            c.badgeBg,
            c.badgeText,
          ].join(" ")}
        >
          {formatInt(taskCount)} tarefa{taskCount !== 1 ? "s" : ""}
        </span>

        {urgentCount > 0 && (
          <span
            className={[
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold",
              c.urgentBg,
              c.urgentText,
            ].join(" ")}
          >
            {formatInt(urgentCount)} urgente{urgentCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Seta de acesso */}
      <div className="mt-4 flex items-center justify-end">
        <span className={["text-xs font-semibold", c.badgeText].join(" ")}>
          Acessar →
        </span>
      </div>
    </button>
  );
}
