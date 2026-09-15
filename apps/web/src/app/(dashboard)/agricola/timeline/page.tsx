"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    Clock,
    CalendarDays,
    Tractor,
    Leaf,
    Activity,
    CalendarDays as CalendarIcon
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { OperacaoAgricolaResponse } from "@farm/zod-schemas";
import { cn } from "@/lib/utils";

interface Safra { id: string; ano_safra: string; cultura: string; status: string; }

export default function TimelinePage() {
    const [selectedSafraId, setSelectedSafraId] = useState<string>("all");

    // Fetch safras
    const { data: safras = [], isLoading: isLoadingSafras } = useQuery<Safra[]>({
        queryKey: ["safras"],
        queryFn: () => apiFetch("/safras/"),
    });

    const activeSafras = safras.filter(s => !["ENCERRADA", "CANCELADA"].includes(s.status));
    const safraSelecionadaParam = selectedSafraId === "all" ? undefined : selectedSafraId;

    // Fetch operações
    const url = safraSelecionadaParam ? `/operacoes?safra_id=${safraSelecionadaParam}` : `/operacoes`;
    const { data: operacoes = [], isLoading: isLoadingOperacoes } = useQuery<OperacaoAgricolaResponse[]>({
        queryKey: ["operacoes", safraSelecionadaParam],
        queryFn: () => apiFetch(url),
    });

    // Grouping logic (by month-year)
    const agrupado = useMemo(() => {
        if (!operacoes || operacoes.length === 0) return {};
        
        // Sort explicitly by data_realizada (descending - newest first)
        const sorted = [...operacoes].sort((a, b) => new Date(b.data_realizada).getTime() - new Date(a.data_realizada).getTime());

        const groups: Record<string, OperacaoAgricolaResponse[]> = {};
        for (const op of sorted) {
            const dt = parseISO(op.data_realizada);
            // Format as "Novembro 2024"
            const monthYear = format(dt, "MMMM yyyy", { locale: ptBR });
            const key = monthYear.charAt(0).toUpperCase() + monthYear.slice(1);
            if (!groups[key]) groups[key] = [];
            groups[key].push(op);
        }
        return groups;
    }, [operacoes]);

    if (isLoadingSafras || isLoadingOperacoes) {
        return (
            <div className="space-y-6 p-6">
                <Skeleton className="h-10 w-64 rounded-sm" />
                <Skeleton className="h-12 w-full rounded-sm" />
                <Skeleton className="h-96 w-full rounded-sm" />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            <PageHeader
                title="Timeline Operacional"
                description="Visualização cronológica e status de execução das operações na safra."
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Timeline" }]}
                icon={<Activity className="text-primary" size={22} />}
            />

            <Card className="shadow-sm rounded-sm">
                <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <CalendarDays className="size-4" />
                            <span className="font-medium">Filtrar por safra:</span>
                        </div>
                        <Select value={selectedSafraId} onValueChange={setSelectedSafraId}>
                            <SelectTrigger className="w-full max-w-sm">
                                <SelectValue placeholder="Todas as Safras" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Todas as Safras</SelectItem>
                                {safras.map(s => (
                                    <SelectItem key={s.id} value={s.id}>{s.cultura} — {s.ano_safra}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </CardContent>
            </Card>

            {Object.keys(agrupado).length === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-center text-muted-foreground border-2 border-dashed rounded-sm">
                    <CalendarDays className="size-8 opacity-20 mb-2" aria-hidden="true" />
                    <p className="mb-4 text-pretty">Nenhuma operação registrada no período selecionado.</p>
                    <Button variant="outline" asChild>
                        <a href="/agricola/operacoes" className="rounded-sm">Registrar Nova Operação</a>
                    </Button>
                </div>
            ) : (
                <div className="relative border-l-2 border-muted pl-6 md:pl-8 space-y-10 py-4">
                    {Object.entries(agrupado).map(([mesAno, ops]) => (
                        <div key={mesAno} className="relative">
                            {/* Marcador de mês */}
                            <div className="absolute -left-[35px] md:-left-[43px] bg-background w-6 h-6 rounded-full flex items-center justify-center border-2 border-muted">
                                <Clock className="size-3 text-muted-foreground" aria-hidden="true" />
                            </div>
                            <h3 className="text-lg font-semibold text-foreground mb-4 bg-background py-1 sticky top-0 z-10">{mesAno}</h3>

                            <div className="space-y-4">
                                {ops.map(op => (
                                    <Card key={op.id} className="shadow-sm hover:shadow-md transition-shadow rounded-sm">
                                        <CardContent className="p-4 flex flex-col sm:flex-row gap-4">
                                            <div className="flex flex-col min-w-[120px] text-sm">
                                                <span className="font-semibold font-mono tabular-nums">{format(parseISO(op.data_realizada), "dd/MM/yyyy")}</span>
                                                <span className="text-muted-foreground">{format(parseISO(op.data_realizada), "EEEE", { locale: ptBR })}</span>
                                                <Badge className="w-fit mt-1 rounded-sm" variant={op.status === "REALIZADA" ? "default" : "secondary"}>
                                                    {op.status}
                                                </Badge>
                                            </div>
                                            <div className="flex-1 space-y-1.5">
                                                <div className="flex items-center gap-2">
                                                    <Tractor className="size-4 text-primary" aria-hidden="true" />
                                                    <span className="font-semibold text-lg">{op.descricao}</span>
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-muted-foreground flex-wrap">
                                                    <span className="bg-muted px-2 py-0.5 rounded-sm text-foreground font-medium">{op.tipo}</span>
                                                    {op.area_aplicada_ha && (
                                                        <span>Área: {op.area_aplicada_ha} ha</span>
                                                    )}
                                                    {op.fase_safra && (
                                                        <span className="flex items-center"><Leaf className="size-3 mr-1" aria-hidden="true"/> Fase: {op.fase_safra}</span>
                                                    )}
                                                </div>

                                                {op.insumos && op.insumos.length > 0 && (
                                                    <div className="mt-3 pt-3 border-t">
                                                        <p className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground mb-1">Insumos Aplicados:</p>
                                                        <div className="flex flex-wrap gap-1">
                                                            {op.insumos.map((ins, idx) => (
                                                                <Badge key={idx} variant="outline" className="text-[10px] bg-slate-50 rounded-sm">
                                                                    ID:{ins.produto_id.substring(0,6)} • {ins.dose_por_ha}{ins.unidade}/ha
                                                                </Badge>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Price/Cost column (Optional) */}
                                            <div className="flex flex-col gap-1 items-end min-w-[100px] border-t sm:border-t-0 sm:border-l pt-3 sm:pt-0 sm:pl-4">
                                                {op.custo_total > 0 ? (
                                                    <>
                                                        <span className="text-xs text-muted-foreground">Custo:</span>
                                                        <span className="font-mono tabular-nums text-primary font-semibold text-sm">R$ {op.custo_total.toFixed(2)}</span>
                                                    </>
                                                ) : (
                                                    <span className="text-xs text-muted-foreground italic">S/ Custo</span>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
        </div>
    );
}
