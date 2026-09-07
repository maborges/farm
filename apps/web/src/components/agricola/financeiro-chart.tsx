"use client";

function moeda(v: number) {
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface FinanceiroChartProps {
    financeiro: {
        despesa_total: number;
        receita_total: number;
    };
}

export function FinanceiroChart({ financeiro }: FinanceiroChartProps) {
    const max = Math.max(financeiro.despesa_total, financeiro.receita_total);
    const despesa_pct = max > 0 ? (financeiro.despesa_total / max) * 100 : 0;
    const receita_pct = max > 0 ? (financeiro.receita_total / max) * 100 : 0;

    return (
        <div className="space-y-6">
            {/* Barra de Despesa */}
            <div className="space-y-2">
                <div className="flex justify-between items-center">
                    <p className="text-sm font-medium">Despesa</p>
                    <p className="text-sm font-bold text-amber-600">{moeda(financeiro.despesa_total)}</p>
                </div>
                <div className="w-full h-8 bg-muted rounded-lg overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-amber-400 to-amber-500 rounded-lg transition-all"
                        style={{ width: `${despesa_pct}%` }}
                    />
                </div>
            </div>

            {/* Barra de Receita */}
            <div className="space-y-2">
                <div className="flex justify-between items-center">
                    <p className="text-sm font-medium">Receita</p>
                    <p className="text-sm font-bold text-emerald-600">{moeda(financeiro.receita_total)}</p>
                </div>
                <div className="w-full h-8 bg-muted rounded-lg overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-lg transition-all"
                        style={{ width: `${receita_pct}%` }}
                    />
                </div>
            </div>

            {/* Resumo */}
            <div className="pt-4 grid gap-4 sm:grid-cols-3 border-t">
                <div className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">Despesa</p>
                    <p className="font-bold text-sm">{moeda(financeiro.despesa_total)}</p>
                </div>
                <div className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">Receita</p>
                    <p className="font-bold text-sm">{moeda(financeiro.receita_total)}</p>
                </div>
                <div className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">Margem</p>
                    <p className={`font-bold text-sm ${financeiro.receita_total - financeiro.despesa_total >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {moeda(financeiro.receita_total - financeiro.despesa_total)}
                    </p>
                </div>
            </div>
        </div>
    );
}
