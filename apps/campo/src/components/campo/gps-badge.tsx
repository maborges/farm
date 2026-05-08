"use client";

interface GpsBadgeProps {
  status: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
}

export function GpsBadge({ status }: GpsBadgeProps) {
  const map = {
    DISPONIVEL: { icon: "📍", label: "GPS OK", cls: "text-green-400 bg-green-950" },
    AGUARDANDO: { icon: "⏳", label: "GPS...", cls: "text-amber-400 bg-amber-950" },
    INDISPONIVEL: { icon: "📵", label: "Sem GPS", cls: "text-neutral-500 bg-neutral-800" },
  };
  const { icon, label, cls } = map[status];
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {icon} {label}
    </span>
  );
}
