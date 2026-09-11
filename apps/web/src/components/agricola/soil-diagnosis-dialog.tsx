"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import Link from "next/link";
import { 
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { 
    BrainCircuit, Loader2, Droplets, ArrowRight,
    TrendingUp, AlertCircle, CheckCircle2, XCircle, Lock
} from "lucide-react";
import { useRecomendacoes, useSafrasAtivas, useAnaliseSolo, type RecomendacaoSoloItem } from "@/hooks/use-agricola";
import { useHasTier } from "@/hooks/use-has-tier";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { 
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue 
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { trackMonetizationEvent, useMonetizationPromptTracking } from "@/lib/monetization";

interface Props {
    analiseId: string | null;
    onClose: () => void;
}

export function SoilDiagnosisDialog({ analiseId, onClose }: Props) {
    const qc = useQueryClient();
    const hasProfessionalTier = useHasTier("PROFISSIONAL");
    const { data: recomendacoes, isLoading } = useRecomendacoes(analiseId || undefined);
    const { data: analise } = useAnaliseSolo(analiseId || undefined);
    const { data: safras = [] } = useSafrasAtivas();
    const [selectedSafraId, setSelectedSafraId] = useState<string>("");

    useMonetizationPromptTracking(!hasProfessionalTier, {
        feature: "agricola.soil_diagnosis",
        surface: "agricola.soil_diagnosis.dialog",
        requiredTier: "PROFISSIONAL",
        ctaLabel: "Ver planos",
    });

    const mutation = useMutation({
        mutationFn: async () => {
            if (!hasProfessionalTier) {
                trackMonetizationEvent("monetization_blocked", {
                    feature: "agricola.soil_diagnosis.generate_tasks",
                    surface: "agricola.soil_diagnosis.dialog",
                    requiredTier: "PROFISSIONAL",
                    ctaLabel: "Gerar tarefas",
                    reason: "mutation_guard",
                });
                throw new Error("Recurso disponível no plano PROFISSIONAL.");
            }
            if (!analiseId || !selectedSafraId) return;
            return apiFetch(`/agricola/analises-solo/${analiseId}/gerar-tarefas`, {
                method: "POST",
                params: { safra_id: selectedSafraId }
            });
        },
        onSuccess: (data: { tarefas_geradas?: unknown[]; tarefas_existentes?: unknown[] } | undefined) => {
            const geradas = data?.tarefas_geradas?.length || 0;
            const existentes = data?.tarefas_existentes?.length || 0;
            if (geradas > 0 && existentes > 0) {
                toast.success(`${geradas} tarefa(s) nova(s) gerada(s). ${existentes} já existia(m) para esta análise e safra.`);
            } else if (geradas > 0) {
                toast.success(`${geradas} tarefa(s) de correção gerada(s) com sucesso!`);
            } else if (existentes > 0) {
                toast.info(`Nenhuma tarefa nova: ${existentes} tarefa(s) já existia(m) para esta análise e safra.`);
            } else {
                toast.info("Nenhuma recomendação aplicável para gerar tarefas.");
            }
            qc.invalidateQueries({ queryKey: ["safras", selectedSafraId, "tarefas"] });
            onClose();
        },
        onError: (err: Error) => {
            toast.error(err.message || "Erro ao gerar tarefas");
        }
    });

    const hasRecommendations = hasProfessionalTier && recomendacoes && Object.keys(recomendacoes).length > 0;

    return (
        <Dialog open={!!analiseId} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-2xl p-0 gap-0 overflow-hidden rounded-sm">
                <DialogHeader>
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-sm bg-primary/10 flex items-center justify-center">
                            <BrainCircuit className="size-5 text-primary" />
                        </div>
                        <div>
                            <DialogTitle className="text-xl">Laudo Inteligente</DialogTitle>
                            <DialogDescription className="text-xs">
                                Diagnóstico agronômico baseado no motor de regras do DeepFarms.
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <DialogBody className="max-h-[70vh] overflow-y-auto">
                    {!hasProfessionalTier ? (
                        <Alert className="rounded-sm">
                            <Lock className="size-4" />
                            <AlertTitle>Inteligência de solo disponível no PROFISSIONAL</AlertTitle>
                            <AlertDescription className="space-y-3">
                                <p>
                                    O plano atual mantém o acesso operacional às análises. Recomendações automáticas e geração de planejamento exigem tier PROFISSIONAL.
                                </p>
                                <Button
                                    asChild
                                    size="sm"
                                    onClick={() => trackMonetizationEvent("monetization_cta_clicked", {
                                        feature: "agricola.soil_diagnosis",
                                        surface: "agricola.soil_diagnosis.dialog",
                                        requiredTier: "PROFISSIONAL",
                                        ctaLabel: "Ver planos",
                                    })}
                                >
                                    <Link href="/dashboard/settings/billing">Ver planos</Link>
                                </Button>
                            </AlertDescription>
                        </Alert>
                    ) : isLoading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-3">
                            <Loader2 className="size-8 animate-spin text-primary" />
                            <p className="text-sm text-muted-foreground">Interpretando resultados laboratoriais...</p>
                        </div>
                    ) : !hasRecommendations ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-3 text-center">
                            <AlertCircle className="size-10 text-muted-foreground" />
                            <p className="text-sm font-medium">Nenhuma recomendação gerada.</p>
                            <p className="text-xs text-muted-foreground max-w-xs">
                                Verifique se há Regras Agronômicas cadastradas para a cultura e tipo de solo desta análise.
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Resumo Químico/Físico — dados reais da análise de solo */}
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <Card className="border-0 bg-muted/30 rounded-sm shadow-none">
                                    <CardContent className="p-3 text-center">
                                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">pH Água</p>
                                        <p className="text-lg font-bold">{analise?.ph_agua != null ? analise.ph_agua : "—"}</p>
                                    </CardContent>
                                </Card>
                                <Card className="border-0 bg-muted/30 rounded-sm shadow-none">
                                    <CardContent className="p-3 text-center">
                                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">V %</p>
                                        <p className="text-lg font-bold">{analise?.v_pct != null ? `${analise.v_pct}%` : "—"}</p>
                                    </CardContent>
                                </Card>
                                <Card className="border-0 bg-muted/30 rounded-sm shadow-none">
                                    <CardContent className="p-3 text-center">
                                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Argila</p>
                                        <p className="text-lg font-bold">{analise?.argila_pct != null ? `${analise.argila_pct}%` : "—"}</p>
                                    </CardContent>
                                </Card>
                                <Card className="border-0 bg-muted/30 rounded-sm shadow-none">
                                    <CardContent className="p-3 text-center">
                                        <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Área Total</p>
                                        <p className="text-lg font-bold">{recomendacoes?.area_ha || 0} ha</p>
                                    </CardContent>
                                </Card>
                            </div>

                            <Card className="border border-primary/20 bg-primary/5 rounded-sm overflow-hidden shadow-none">
                                <CardContent className="p-4 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="size-10 rounded-sm bg-primary/20 flex items-center justify-center">
                                            <TrendingUp className="size-5 text-primary" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Investimento Estimado</p>
                                            <p className="text-xl font-bold text-primary">
                                                {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(recomendacoes?.investimento_estimado_total || 0)}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-[10px] text-muted-foreground">Previsão baseada em</p>
                                        <p className="text-[10px] font-bold text-primary italic">Preços de Mercado</p>
                                    </div>
                                </CardContent>
                            </Card>

                            <Separator />

                            {/* Recomendações Detalhadas */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-bold flex items-center gap-2">
                                    <Droplets className="size-4 text-blue-500" />
                                    Intervenções Necessárias
                                </h3>

                                {(['calagem', 'fosforo', 'potassio', 'nitrogenio'] as const).map((key) => {
                                    const rec = recomendacoes[key];
                                    if (!rec) return null;
                                    const recomendacao = rec as RecomendacaoSoloItem;

                                    const isNecessary = recomendacao.necessaria || (recomendacao.quantidade && recomendacao.quantidade > 0) || (recomendacao.dose_t_ha && recomendacao.dose_t_ha > 0) || (recomendacao.rec_p2o5_kg_ha && recomendacao.rec_p2o5_kg_ha > 0) || (recomendacao.rec_k2o_kg_ha && recomendacao.rec_k2o_kg_ha > 0) || (recomendacao.rec_n_kg_ha && recomendacao.rec_n_kg_ha > 0);
                                    
                                    const quantity = recomendacao.dose_t_ha || recomendacao.rec_p2o5_kg_ha || recomendacao.rec_k2o_kg_ha || recomendacao.rec_n_kg_ha || 0;
                                    const unit = key === 'calagem' ? 't/ha' : 'kg/ha';
                                    const element = key === 'calagem' ? 'Calcário' : (key === 'fosforo' ? 'P₂O₅' : (key === 'potassio' ? 'K₂O' : 'N'));

                                    return (
                                        <Card key={key} className="hover:border-primary/30 transition-colors">
                                            <div className="flex items-start gap-3 p-4">
                                            <div className="mt-1">
                                        {isNecessary ? (
                                            <TrendingUp className="text-orange-500" />
                                        ) : (
                                            <CheckCircle2 className="text-green-500" />
                                        )}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex justify-between items-center mb-1">
                                                    <h4 className="text-sm font-bold capitalize">{key}</h4>
                                                    {isNecessary && (
                                                        <Badge variant="secondary" className="bg-orange-100 text-orange-700 hover:bg-orange-100 rounded-sm border-0">
                                                            Ação Requerida
                                                        </Badge>
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground leading-relaxed">
                                                    {recomendacao.observacao || "Nenhuma recomendação específica para este parâmetro."}
                                                </p>
                                                {isNecessary && (
                                                    <div className="mt-2 flex items-center justify-between">
                                                        <Badge variant="outline" className="text-[10px] font-bold text-primary border-primary/20 bg-primary/5 rounded-sm">
                                                            {quantity} {unit} de {element}
                                                        </Badge>
                                                        
                                                        <p className="text-[11px] font-bold text-muted-foreground">
                                                            {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(recomendacao.custo_estimado || 0)} Est.
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                            </div>
                                        </Card>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </DialogBody>

                <DialogFooter>
                    <div className="flex items-center gap-2 w-full sm:w-auto">
                        <Select value={selectedSafraId} onValueChange={setSelectedSafraId} disabled={!hasProfessionalTier}>
                            <SelectTrigger className="w-full sm:w-48 text-xs">
                                <SelectValue placeholder="Vincular à Safra..." />
                            </SelectTrigger>
                            <SelectContent>
                                {safras.map(s => (
                                    <SelectItem key={s.id} value={s.id}>
                                        {s.nome}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="flex items-center gap-2 mt-4 sm:mt-0">
                        <Button variant="outline" size="sm" onClick={onClose} disabled={mutation.isPending}>
                            <XCircle className="size-4" />
                            Fechar
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => mutation.mutate()}
                            disabled={!hasProfessionalTier || !selectedSafraId || !hasRecommendations || mutation.isPending}
                        >
                            {mutation.isPending ? (
                                <Loader2 className="size-4 animate-spin" />
                            ) : (
                                <ArrowRight className="size-4" />
                            )}
                            Gerar Planejamento
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
