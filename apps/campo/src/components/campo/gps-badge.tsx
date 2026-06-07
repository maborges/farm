"use client";

import { CampoPill } from "./ui";

interface GpsBadgeProps {
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}

export function GpsBadge({ status }: GpsBadgeProps) {
  const map = {
    DISPONIVEL: { icon: "📍", label: "GPS disponível", cls: "border-green-200 bg-green-50 text-green-800 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-200" },
    AGUARDANDO: { icon: "⏳", label: "Obtendo GPS", cls: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200" },
    INDISPONIVEL: { icon: "📵", label: "Sem GPS", cls: "border-border bg-muted text-muted-foreground" },
  };
  const { icon, label, cls } = map[status];
  return (
    <CampoPill className={cls}>
      <span>{icon}</span>
      <span>{label}</span>
    </CampoPill>
  );
}
