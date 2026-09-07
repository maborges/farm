"use client";

import { formatCurrency } from "@farm/utils";

interface CategoryProgressBarProps {
  categoria: string;
  percentual: number;
  custo_por_ha: number;
  custo_total: number;
}

const CATEGORIA_COLORS: Record<string, { bg: string; bar: string; text: string }> = {
  SEMENTE: { bg: "bg-emerald-50", bar: "bg-emerald-500", text: "text-emerald-700" },
  FERTILIZANTE: { bg: "bg-amber-50", bar: "bg-amber-500", text: "text-amber-700" },
  DEFENSIVO: { bg: "bg-orange-50", bar: "bg-orange-500", text: "text-orange-700" },
  COMBUSTIVEL: { bg: "bg-red-50", bar: "bg-red-500", text: "text-red-700" },
  MAO_DE_OBRA: { bg: "bg-blue-50", bar: "bg-blue-500", text: "text-blue-700" },
  SERVICO: { bg: "bg-purple-50", bar: "bg-purple-500", text: "text-purple-700" },
  SEGURO: { bg: "bg-slate-50", bar: "bg-slate-500", text: "text-slate-700" },
  OUTROS: { bg: "bg-gray-50", bar: "bg-gray-500", text: "text-gray-700" },
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
    <div className={`p-4 rounded-lg ${colors.bg} border border-gray-200`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className={`text-sm font-semibold ${colors.text}`}>{label}</h4>
        <span className="text-xs text-muted-foreground font-mono">{percentual.toFixed(1)}%</span>
      </div>

      {/* Barra de progresso */}
      <div className="h-2 bg-white rounded-full overflow-hidden mb-2">
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
