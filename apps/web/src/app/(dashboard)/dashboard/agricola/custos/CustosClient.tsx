"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Wallet, BarChart2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

export interface Safra { id: string; ano_safra: string; cultura: string; status?: string; }
export interface CustoBreakdown { categoria: string; valor_total: number; valor_por_ha: number; percentual: number; }
export interface ResumosCustos {
    safra_id: string; area_total_ha: number;
    custo_total_realizado: number; custo_realizado_por_ha: number;
    orcamento_previsto_total: number | null; desvio_orcamento_pct: number | null;
    breakdown: CustoBreakdown[];
}

function toBRL(v: number) { return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

export function CustosClient({ 
    initialSafras, initialCustos, initialActiveFazendaId 
}: { 
    initialSafras: Safra[], initialCustos: ResumosCustos | null, initialActiveFazendaId?: string 
}) {
    const { activeFazendaId } = useAppStore();
    const qs = activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : "";
    const [safraId, setSafraId] = useState<string>("");

    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["agricola", "safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras${qs}`),
        initialData: activeFazendaId === initialActiveFazendaId ? initialSafras : undefined,
    });
    
    // Auto select first safra if none selected
    if (safras.length > 0 && !safraId) {
        setSafraId(safras[0].id);
    }

    const { data: custos, isLoading } = useQuery<ResumosCustos>({
        queryKey: ["agricola", "custos", activeFazendaId, safraId],
        queryFn: () => apiFetch(`/custos/safra/${safraId}`),
        enabled: !!safraId,
        initialData: activeFazendaId === initialActiveFazendaId && (!safraId || (safras.length > 0 && safraId === safras[0].id)) ? (initialCustos ?? undefined) : undefined,
    });

    const desvio = custos?.desvio_orcamento_pct;

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Custos Agrícolas"
                description="Apuração de custos por safra e categoria"
                actions={
                    <div className="flex items-center gap-2">
                        <Label className="text-xs whitespace-nowrap">Safra</Label>
                        <Select onValueChange={setSafraId} value={safraId}>
                            <SelectTrigger className="h-8 text-xs w-48">
                                <SelectValue placeholder="Selecione uma safra..." />
                            </SelectTrigger>
                            <SelectContent>
                                {safras.map(s => <SelectItem key={s.id} value={s.id}>{s.ano_safra} — {s.cultura}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                }
            />

            {!safraId && (
                <div className="text-center py-16 text-sm text-muted-foreground">
                    <Wallet className="size-10 mx-auto mb-3 opacity-25" />
                    Selecione uma safra para visualizar os custos.
                </div>
            )}

            {safraId && isLoading && <Skeleton className="h-60 w-full" />}

            {custos && (
                <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                            { label: "Custo Total Realizado", value: toBRL(custos.custo_total_realizado) },
                            { label: "Custo por Hectare", value: toBRL(custos.custo_realizado_por_ha) },
                            { label: "Orçamento Previsto", value: custos.orcamento_previsto_total ? toBRL(custos.orcamento_previsto_total) : "—" },
                            {
                                label: "Desvio Orçamento", value: desvio != null ? `${desvio > 0 ? "+" : ""}${desvio.toFixed(1)}%` : "—",
                                warn: desvio != null && desvio > 10, ok: desvio != null && desvio <= 0
                            },
                        ].map(k => (
                            <Card key={k.label}>
                                <CardHeader className="pb-1"><CardTitle className="text-xs text-muted-foreground">{k.label}</CardTitle></CardHeader>
                                <CardContent>
                                    <p className={`text-xl font-bold ${(k as any).warn ? "text-red-600" : (k as any).ok ? "text-green-600" : ""}`}>{k.value}</p>
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    <Card>
                        <CardHeader><CardTitle className="text-sm flex items-center gap-1"><BarChart2 className="size-4" />Breakdown por Categoria</CardTitle></CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {custos.breakdown.map(b => (
                                    <div key={b.categoria}>
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="font-medium">{b.categoria}</span>
                                            <span className="text-muted-foreground">{toBRL(b.valor_total)} · {toBRL(b.valor_por_ha)}/ha · {b.percentual.toFixed(1)}%</span>
                                        </div>
                                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.min(b.percentual, 100)}%` }} />
                                        </div>
                                    </div>
                                ))}
                                {custos.breakdown.length === 0 && <p className="text-sm text-muted-foreground">Nenhum lançamento de custo para esta safra.</p>}
                            </div>
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
