"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { SimulacaoExposicaoRequest, SimulacaoExposicaoResponse } from "../types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calculator, AlertTriangle, ArrowRight, TrendingUp, TrendingDown, RefreshCcw } from "lucide-react";
import { RiscoBadge } from "./ExposicaoDashboardClient";
import { useToast } from "@/hooks/use-toast";

function fmt(val: number): string {
    return val.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
}

type ApiError = Error;

type ComparisonMetricProps = {
    label: string;
    atual: number;
    simulado: number;
    unit: string;
    inverseGood?: boolean;
};

export function SimulacaoPainel({
    safraId,
    commodityId,
}: {
    safraId?: string | null;
    commodityId?: string | null;
}) {
    const { toast } = useToast();
    
    const [deltas, setDeltas] = useState({
        variacao_producao_sc: "",
        variacao_estoque_sc: "",
        variacao_venda_sc: "",
        variacao_hedge_sc: "",
    });

    const mutation = useMutation<SimulacaoExposicaoResponse, Error, SimulacaoExposicaoRequest>({
        mutationFn: (req) => {
            return apiFetch("/financeiro/hedge/exposicao/simular", {
                method: "POST",
                body: JSON.stringify(req),
            });
        },
        onError: (err: ApiError) => {
            const msg = err.message || "Erro desconhecido ao simular.";
            toast({
                title: "Erro na simulação",
                description: msg,
                variant: "destructive",
            });
        }
    });

    const handleSimulate = (e: React.FormEvent) => {
        e.preventDefault();
        
        const req: SimulacaoExposicaoRequest = {
            safra_id: safraId,
            commodity: commodityId, // No contexto real, commodityId deveria ser resolvido ou endpoint adaptado. Assumimos uuid.
            variacao_producao_sc: Number(deltas.variacao_producao_sc) || 0,
            variacao_estoque_sc: Number(deltas.variacao_estoque_sc) || 0,
            variacao_venda_sc: Number(deltas.variacao_venda_sc) || 0,
            variacao_hedge_sc: Number(deltas.variacao_hedge_sc) || 0,
        };

        mutation.mutate(req);
    };

    const handleReset = () => {
        setDeltas({
            variacao_producao_sc: "",
            variacao_estoque_sc: "",
            variacao_venda_sc: "",
            variacao_hedge_sc: "",
        });
        mutation.reset();
    };

    const { data, isPending } = mutation;

    return (
        <Card className="rounded-sm border-0 shadow-sm bg-muted/10">
            <CardHeader className="pb-4 border-b">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Calculator className="h-4 w-4 text-primary" />
                    Simulador de Cenários (Stateless)
                </CardTitle>
                <CardDescription className="text-xs">
                    Adicione ou reduza volumes para projetar o impacto na sua exposição financeira sem afetar dados reais.
                </CardDescription>
            </CardHeader>
            <CardContent className="pt-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Form de Inputs */}
                    <div className="lg:col-span-5 space-y-4">
                        <form onSubmit={handleSimulate} className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-xs">Delta Produção (sc)</Label>
                                    <Input
                                        type="number"
                                        className="h-8 rounded-sm text-sm"
                                        placeholder="Ex: 1000 ou -500"
                                        value={deltas.variacao_producao_sc}
                                        onChange={(e) => setDeltas(p => ({ ...p, variacao_producao_sc: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs">Delta Venda Física (sc)</Label>
                                    <Input
                                        type="number"
                                        className="h-8 rounded-sm text-sm"
                                        placeholder="Ex: 2000"
                                        value={deltas.variacao_venda_sc}
                                        onChange={(e) => setDeltas(p => ({ ...p, variacao_venda_sc: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs">Delta Estoque Físico (sc)</Label>
                                    <Input
                                        type="number"
                                        className="h-8 rounded-sm text-sm"
                                        placeholder="Ex: 500"
                                        value={deltas.variacao_estoque_sc}
                                        onChange={(e) => setDeltas(p => ({ ...p, variacao_estoque_sc: e.target.value }))}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs">Delta Hedge B3/CBOT (sc)</Label>
                                    <Input
                                        type="number"
                                        className="h-8 rounded-sm text-sm"
                                        placeholder="Ex: 3000"
                                        value={deltas.variacao_hedge_sc}
                                        onChange={(e) => setDeltas(p => ({ ...p, variacao_hedge_sc: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div className="flex gap-2 pt-2">
                                <Button type="submit" size="sm" className="w-full rounded-sm bg-primary/90" disabled={isPending}>
                                    {isPending ? "Calculando..." : "Simular Cenário"}
                                </Button>
                                {data && (
                                    <Button type="button" variant="outline" size="sm" onClick={handleReset} className="rounded-sm">
                                        <RefreshCcw className="h-4 w-4" />
                                    </Button>
                                )}
                            </div>
                        </form>
                    </div>

                    {/* Resultados Comparativos */}
                    <div className="lg:col-span-7 border-l pl-8">
                        {!data ? (
                            <div className="h-full flex flex-col items-center justify-center text-muted-foreground space-y-3 opacity-60 min-h-[200px]">
                                <Calculator className="h-10 w-10" />
                                <p className="text-sm">Preencha os deltas e clique em simular.</p>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {data.alertas.length > 0 && (
                                    <div className="bg-amber-500/10 text-amber-600 border border-amber-500/20 p-3 rounded-sm text-xs flex gap-2 items-start">
                                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                                        <div>
                                            {data.alertas.map((a, i) => <p key={i}>{a}</p>)}
                                        </div>
                                    </div>
                                )}
                                
                                <div className="grid grid-cols-2 gap-6">
                                    <ComparisonMetric 
                                        label="Exposição Aberta"
                                        atual={data.cenario_atual.exposicao_aberta_sc}
                                        simulado={data.cenario_simulado.exposicao_aberta_sc}
                                        unit="sc"
                                        inverseGood
                                    />
                                    <ComparisonMetric 
                                        label="Hedge Ratio"
                                        atual={data.cenario_atual.percentual_cobertura}
                                        simulado={data.cenario_simulado.percentual_cobertura}
                                        unit="%"
                                    />
                                    <ComparisonMetric 
                                        label="Exposição Líquida"
                                        atual={data.cenario_atual.exposicao_liquida_sc}
                                        simulado={data.cenario_simulado.exposicao_liquida_sc}
                                        unit="sc"
                                    />
                                    <div className="space-y-1">
                                        <p className="text-xs text-muted-foreground uppercase tracking-wider">Risco Global</p>
                                        <div className="flex items-center gap-3">
                                            <RiscoBadge classificacao={data.cenario_atual.classificacao_risco} />
                                            <ArrowRight className="h-3 w-3 text-muted-foreground" />
                                            <RiscoBadge classificacao={data.cenario_simulado.classificacao_risco} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

function ComparisonMetric({ label, atual, simulado, unit, inverseGood = false }: ComparisonMetricProps) {
    const diff = simulado - atual;
    const isZero = diff === 0;
    const isUp = diff > 0;
    
    let isGood = isUp;
    if (inverseGood) isGood = !isUp;
    
    return (
        <div className="space-y-1">
            <p className="text-xs text-muted-foreground uppercase tracking-wider">{label}</p>
            <div className="flex items-end gap-3">
                <span className="text-xl font-semibold">
                    {fmt(simulado)}{unit}
                </span>
                {!isZero && (
                    <span className={`flex items-center text-xs font-medium pb-1 ${isGood ? "text-emerald-500" : "text-red-500"}`}>
                        {isUp ? <TrendingUp className="h-3 w-3 mr-1" /> : <TrendingDown className="h-3 w-3 mr-1" />}
                        {fmt(Math.abs(diff))}{unit}
                    </span>
                )}
                {isZero && (
                    <span className="text-xs text-muted-foreground pb-1 font-medium">--</span>
                )}
            </div>
            <p className="text-xs text-muted-foreground">Atual: {fmt(atual)}{unit}</p>
        </div>
    );
}
