"use client";

import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, XCircle, ChevronRight, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardAction, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

const FASES = [
    { key: "PLANEJADA", label: "Planejamento", descricao: "Definição de cultura, área e metas" },
    { key: "PREPARO_SOLO", label: "Preparo do Solo", descricao: "Calagem, gradagem e correções" },
    { key: "PLANTIO", label: "Plantio", descricao: "Semeadura e aplicações iniciais" },
    { key: "DESENVOLVIMENTO", label: "Desenvolvimento", descricao: "Tratos culturais e monitoramento" },
    { key: "COLHEITA", label: "Colheita", descricao: "Operação de colheita e romaneios" },
    { key: "POS_COLHEITA", label: "Pós-Colheita", descricao: "Secagem, armazenamento e venda" },
    { key: "ENCERRADA", label: "Encerrada", descricao: "Safra finalizada" },
];

const TRANSICOES: Record<string, string[]> = {
    PLANEJADA: ["PREPARO_SOLO", "CANCELADA"],
    PREPARO_SOLO: ["PLANTIO", "CANCELADA"],
    PLANTIO: ["DESENVOLVIMENTO", "CANCELADA"],
    DESENVOLVIMENTO: ["COLHEITA", "CANCELADA"],
    COLHEITA: ["POS_COLHEITA", "CANCELADA"],
    POS_COLHEITA: ["ENCERRADA"],
    ENCERRADA: [],
    CANCELADA: [],
};

interface SafraTimelineProps {
    safraId: string;
    statusAtual: string;
    queryKey: unknown[];
}

export function SafraTimeline({ safraId, statusAtual, queryKey }: SafraTimelineProps) {
    const queryClient = useQueryClient();
    const [confirmFase, setConfirmFase] = useState<string | null>(null);
    const [observacao, setObservacao] = useState("");
    const [errorBloqueio, setErrorBloqueio] = useState<string | null>(null);
    const [forcarAvanco, setForcarAvanco] = useState(false);
    const [justificativaBypass, setJustificativaBypass] = useState("");

    const proximasFases = TRANSICOES[statusAtual] ?? [];
    const proximaFasePrincipal = proximasFases.find(f => f !== "CANCELADA");

    const mutation = useMutation({
        mutationFn: (novaFase: string) =>
            apiFetch(`/safras/${safraId}/avancar-fase/${novaFase}`, {
                method: "POST",
                body: JSON.stringify({
                    observacao: observacao || null,
                    forcar_avanco: forcarAvanco,
                    justificativa_forcar_avanco: justificativaBypass || null
                }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            queryClient.invalidateQueries({ queryKey: ["safra-historico", safraId] });
            toast.success("Fase avançada com sucesso!");
            setConfirmFase(null);
            setObservacao("");
            setErrorBloqueio(null);
            setForcarAvanco(false);
            setJustificativaBypass("");
        },
        onError: (err: any) => {
            if (err?.message?.includes("Bloqueio de fase")) {
                setErrorBloqueio(err.message);
                toast.error("O avanço foi bloqueado devido a pendências na fase atual.");
            } else {
                toast.error(err?.message ?? "Erro ao avançar fase");
            }
        },
    });

    const cancelarMutation = useMutation({
        mutationFn: () =>
            apiFetch(`/safras/${safraId}/avancar-fase/CANCELADA`, {
                method: "POST",
                body: JSON.stringify({ observacao: observacao || null }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.warning("Safra cancelada.");
            setConfirmFase(null);
            setObservacao("");
        },
    });

    const faseAtualIdx = FASES.findIndex(f => f.key === statusAtual);
    const cancelada = statusAtual === "CANCELADA";

    return (
        <>
            <Card className="rounded-sm border shadow-sm">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-primary animate-pulse" />
                        <CardTitle>Linha do Tempo da Safra</CardTitle>
                    </div>
                    <CardDescription>
                        Fase Atual: <strong className="text-foreground">{FASES.find(f => f.key === statusAtual)?.label}</strong>
                    </CardDescription>
                    {!cancelada && statusAtual !== "ENCERRADA" && (
                        <CardAction className="flex items-center gap-2">
                            {proximasFases.includes("CANCELADA") && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setConfirmFase("CANCELADA")}
                                >
                                    <XCircle />
                                    Cancelar
                                </Button>
                            )}

                            {proximaFasePrincipal && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => setConfirmFase(proximaFasePrincipal)}
                                    disabled={mutation.isPending}
                                >
                                    <span>Próxima Fase</span>
                                    <ChevronRight />
                                </Button>
                            )}
                        </CardAction>
                    )}
                </CardHeader>
                <CardContent className="pt-6 pb-6 overflow-x-auto scrollbar-none">
                    <div className="flex items-start w-full min-w-[700px]">
                        {FASES.map((fase, idx) => {
                            const concluida = !cancelada && idx < faseAtualIdx;
                            const ativa = !cancelada && idx === faseAtualIdx;
                            const futura = !ativa && !concluida;

                            return (
                                <div key={fase.key} className="flex-1 flex flex-col items-center gap-3 group/item">
                                    <div className="relative flex items-center justify-center w-full">
                                        {/* Conector Esquerdo */}
                                        <div className={cn(
                                            "absolute left-0 right-1/2 top-4 h-0.5 -translate-y-1/2 z-0 transition-colors duration-500",
                                            idx === 0 ? "hidden" : (concluida || ativa ? "bg-emerald-500/40" : "bg-border")
                                        )} />

                                        {/* Conector Direito */}
                                        <div className={cn(
                                            "absolute left-1/2 right-0 top-4 h-0.5 -translate-y-1/2 z-0 transition-colors duration-500",
                                            idx === FASES.length - 1 ? "hidden" : (concluida ? "bg-emerald-500/40" : "bg-border")
                                        )} />

                                        <div className={cn(
                                            "relative z-10 size-8 rounded-full flex items-center justify-center transition-all duration-300",
                                            concluida && "bg-emerald-500 text-white shadow-sm shadow-emerald-200",
                                            ativa && "bg-primary text-primary-foreground ring-4 ring-primary/20 scale-110 shadow-md",
                                            futura && "bg-muted text-muted-foreground border-2 border-border/50",
                                        )}>
                                            {concluida
                                                ? <CheckCircle2 className="size-5" />
                                                : <Circle className={cn("size-4", ativa && "fill-primary-foreground/20")} />
                                            }
                                        </div>
                                    </div>

                                    <span className={cn(
                                        "text-[10px] uppercase tracking-wider font-bold text-center leading-tight px-2 transition-colors",
                                        ativa && "text-primary",
                                        concluida && "text-emerald-700",
                                        futura && "text-muted-foreground/70",
                                    )}>
                                        {fase.label}
                                    </span>
                                </div>
                            );
                        })}

                        {cancelada && (
                            <div className="flex-1 flex flex-col items-center gap-3 relative">
                                <div className="absolute left-0 right-1/2 top-4 h-0.5 -translate-y-1/2 bg-destructive/20 z-0" />
                                <div className="relative z-10 size-8 rounded-full flex items-center justify-center bg-destructive text-destructive-foreground ring-4 ring-destructive/10 shadow-md">
                                    <XCircle className="size-5" />
                                </div>
                                <span className="text-[10px] uppercase tracking-wider font-bold text-destructive text-center">Cancelada</span>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Modal de confirmação */}
            <Dialog open={!!confirmFase} onOpenChange={(open) => {
                if (!open) {
                    setConfirmFase(null);
                    setErrorBloqueio(null);
                    setForcarAvanco(false);
                    setJustificativaBypass("");
                }
            }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2.5">
                            <div className={cn(
                                "size-8 rounded-sm flex items-center justify-center shrink-0",
                                confirmFase === "CANCELADA"
                                    ? "bg-destructive/10 text-destructive"
                                    : "bg-primary/10 text-primary"
                            )}>
                                {confirmFase === "CANCELADA" ? (
                                    <AlertTriangle />
                                ) : (
                                    <ChevronRight />
                                )}
                            </div>
                            {confirmFase === "CANCELADA"
                                ? "Cancelar Safra"
                                : `Avançar para ${FASES.find(f => f.key === confirmFase)?.label}`}
                        </DialogTitle>
                        <DialogDescription className="text-xs">
                            Confirme a transição de fase e registre observações se necessário.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <div className={cn(
                            "rounded-sm border px-3 py-2.5",
                            confirmFase === "CANCELADA"
                                ? "border-destructive/15 bg-destructive/5"
                                : "border-primary/15 bg-primary/5"
                        )}>
                            <p className="text-sm text-muted-foreground">
                                {confirmFase === "CANCELADA"
                                    ? "Esta ação irá cancelar a safra. Adicione uma observação se necessário."
                                    : `${FASES.find(f => f.key === confirmFase)?.descricao}. Adicione uma observação opcional.`}
                            </p>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="obs" className="text-xs font-medium">Observação</Label>
                            <Textarea
                                id="obs"
                                placeholder="Ex: Solo corrigido, plantio iniciado no talhão norte..."
                                value={observacao}
                                onChange={e => setObservacao(e.target.value)}
                                rows={3}
                                className="resize-none rounded-sm text-sm"
                            />
                        </div>
                        {errorBloqueio && confirmFase !== "CANCELADA" && (
                            <div className="rounded-sm border border-destructive/20 bg-destructive/5 p-4 space-y-4">
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className="size-5 text-destructive mt-0.5 shrink-0" />
                                    <div className="space-y-1">
                                        <p className="text-sm font-medium text-destructive">Avanço Bloqueado</p>
                                        <p className="text-sm text-destructive/80">{errorBloqueio}</p>
                                    </div>
                                </div>
                                <div className="space-y-3 pt-1">
                                    <div className="flex items-center space-x-2">
                                        <Checkbox
                                            id="forcar"
                                            checked={forcarAvanco}
                                            onCheckedChange={(c) => setForcarAvanco(c === true)}
                                        />
                                        <Label htmlFor="forcar" className="text-sm font-medium cursor-pointer">
                                            Forçar avanço
                                        </Label>
                                    </div>
                                    {forcarAvanco && (
                                        <div className="space-y-2 pl-6">
                                            <Label htmlFor="justificativa" className="text-xs text-destructive font-medium">
                                                Justificativa obrigatória para auditoria
                                            </Label>
                                            <Textarea
                                                id="justificativa"
                                                placeholder="Informe o motivo de pular o checklist/tarefas..."
                                                value={justificativaBypass}
                                                onChange={e => setJustificativaBypass(e.target.value)}
                                                rows={2}
                                                className="resize-none rounded-sm border-destructive/30 focus-visible:ring-destructive/20 text-sm"
                                            />
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setConfirmFase(null)}>
                            <XCircle />
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            variant={confirmFase === "CANCELADA" ? "destructive" : "default"}
                            disabled={mutation.isPending || cancelarMutation.isPending}
                            onClick={() => {
                                if (confirmFase === "CANCELADA") cancelarMutation.mutate();
                                else if (confirmFase) mutation.mutate(confirmFase);
                            }}
                        >
                            {mutation.isPending || cancelarMutation.isPending ? (
                                <>
                                    <Loader2 className="animate-spin" />
                                    {confirmFase === "CANCELADA" ? "Cancelando…" : "Avançando…"}
                                </>
                            ) : (
                                <>
                                    <CheckCircle2 />
                                    {confirmFase === "CANCELADA" ? "Cancelar Safra" : `Avançar para ${FASES.find(f => f.key === confirmFase)?.label}`}
                                </>
                            )}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
