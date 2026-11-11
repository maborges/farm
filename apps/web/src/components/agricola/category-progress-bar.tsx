"use client";

import { formatCurrency } from "@farm/utils";

interface CategoryProgressBarProps {
  categoria: string;
  percentual: number;
  custo_por_ha: number;
  custo_total: number;
}

const CATEGORIA_COLORS: Record<string, { bg: string; border: string; bar: string; text: string }> = {
  SEMENTE: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", bar: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-400" },
  FERTILIZANTE: { bg: "bg-amber-500/10", border: "border-amber-500/20", bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" },
  DEFENSIVO: { bg: "bg-orange-500/10", border: "border-orange-500/20", bar: "bg-orange-500", text: "text-orange-700 dark:text-orange-400" },
  COMBUSTIVEL: { bg: "bg-red-500/10", border: "border-red-500/20", bar: "bg-red-500", text: "text-red-700 dark:text-red-400" },
  MAO_DE_OBRA: { bg: "bg-blue-500/10", border: "border-blue-500/20", bar: "bg-blue-500", text: "text-blue-700 dark:text-blue-400" },
  SERVICO: { bg: "bg-purple-500/10", border: "border-purple-500/20", bar: "bg-purple-500", text: "text-purple-700 dark:text-purple-400" },
  SEGURO: { bg: "bg-slate-500/10", border: "border-slate-500/20", bar: "bg-slate-500", text: "text-slate-700 dark:text-slate-400" },
  OUTROS: { bg: "bg-muted/50", border: "border-border", bar: "bg-muted-foreground", text: "text-muted-foreground" },
};

const CATEGORIA_LABELS: Record<string, string> = {
  SEMENTE: "Semente",
  FERTILIZANTE: "Fertilizante",
  DEFENSIVO: "Defensivo",
  COMBUSTIVEL: "Combustível",
  MAO_DE_OBRA: "Mão de Obra",
  SERVICO: "Serviço",
  SEGURO: "Seguro",
  OUTROS: "Outros",
};

function categoriaLabel(categoria: string) {
  return CATEGORIA_LABELS[categoria] ?? categoria;
}

export function CategoryProgressBar({
  categoria,
  percentual,
  custo_por_ha,
  custo_total,
}: CategoryProgressBarProps) {
  const colors = CATEGORIA_COLORS[categoria] || CATEGORIA_COLORS.OUTROS;
  const label = categoriaLabel(categoria);

  return (
    <div className={`p-4 rounded-sm ${colors.bg} border ${colors.border}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className={`text-sm font-semibold ${colors.text}`}>{label}</h4>
        <span className="text-xs text-muted-foreground font-mono">{percentual.toFixed(1)}%</span>
      </div>

      {/* Barra de progresso */}
      <div className="h-2 bg-muted rounded-full overflow-hidden mb-2">
        <div
          className={`h-full ${colors.bar} transition-all duration-300`}
          style={{ width: `${Math.min(percentual, 100)}%` }}
        />
      </div>

      {/* Info */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-mono">{formatCurrency(custo_por_ha)}/ha</span>
        <span className="font-mono font-medium text-foreground">{formatCurrency(custo_total)}</span>
      </div>
    </div>
  );
}
