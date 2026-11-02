"use client";

import { type LucideIcon } from "lucide-react";

type QuickActionColor = "agro" | "pecuaria" | "neutral" | "blue";

interface PwaQuickActionProps {
  label: string;
  icon: LucideIcon;
  onClick: () => void;
  color?: QuickActionColor;
  badge?: string;
}

const ICON_TONE_CLASSES: Record<QuickActionColor, string> = {
  agro: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  pecuaria: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  blue: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  neutral: "bg-primary/10 text-primary",
};

export function PwaQuickAction({
  label,
  icon: Icon,
  onClick,
  color = "neutral",
  badge,
}: PwaQuickActionProps) {
  const iconTone = ICON_TONE_CLASSES[color];

  return (
    <button
      type="button"
      onClick={onClick}
      className="relative flex flex-col items-center justify-center gap-1.5 p-2.5 rounded-sm border border-border bg-card hover:border-primary/40 active:scale-95 transition-all shadow-xs text-center"
    >
      {badge && (
        <span className="absolute -right-1 -top-1 inline-flex min-w-[16px] items-center justify-center rounded-sm bg-rose-500 px-1 py-0.2 text-[9px] font-bold text-white shadow-2xs">
          {badge}
        </span>
      )}

      <div className={["p-2 rounded-sm", iconTone].join(" ")}>
        <Icon className="w-5 h-5" />
      </div>

      <span className="text-[11px] font-semibold text-foreground leading-tight">
        {label}
      </span>
    </button>
  );
}
