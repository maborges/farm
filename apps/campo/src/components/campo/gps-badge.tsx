"use client";

import { CampoPill } from "./ui";

interface GpsBadgeProps {
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}

export function GpsBadge({ status }: GpsBadgeProps) {
  const map = {
    DISPONIVEL: { icon: "📍", label: "GPS disponível", cls: "border-emerald-400/20 bg-emerald-400/12 text-emerald-100" },
    AGUARDANDO: { icon: "⏳", label: "Obtendo GPS", cls: "border-amber-400/20 bg-amber-400/12 text-amber-100" },
    INDISPONIVEL: { icon: "📵", label: "Sem GPS", cls: "border-white/10 bg-white/6 text-white/70" },
  };
  const { icon, label, cls } = map[status];
  return (
    <CampoPill className={cls}>
      <span>{icon}</span>
      <span>{label}</span>
    </CampoPill>
  );
}
