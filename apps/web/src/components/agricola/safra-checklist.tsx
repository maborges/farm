"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
    CheckCircle2, Circle, Plus, AlertTriangle, 
    CheckSquare, XCircle, Ban, LayoutTemplate 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { ApplyTemplateSheet } from "./templates/apply-template-sheet";

type TipoResultado = "TAREFA_CAMPO" | "SOLICITACAO_ESTOQUE" | "MANUAL";
type StatusVerificacao = "PENDENTE" | "OK" | "OK_PARCIAL" | "BLOQUEANTE";

interface ChecklistItem {
    id: string;
    titulo: string;
    descricao: string | null;
    obrigatorio: boolean;
    concluido: boolean;
    concluido_em: string | null;
    cancelado: boolean;
    cancelado_em: string | null;
    tipo_resultado: TipoResultado;
    operacao_agricola_id: string | null;
    reserva_estoque_id: string | null;
    requisicao_material_id: string | null;
    responsavel_id: string | null;
    prazo_resposta: string | null;
    status_verificacao: StatusVerificacao;
    justificativa_ok_parcial: string | null;
}

interface ChecklistFaseStatus {
    fase: string;
    total: number;
    concluidos: number;
    obrigatorios_pendentes: number;
    pode_avancar: boolean;
    veredito: "OK" | "OK_PARCIAL" | "BLOQUEANTE";
    itens: ChecklistItem[];
}

const TIPO_RESULTADO_LABEL: Record<TipoResultado, string> = {
    TAREFA_CAMPO: "Gera OS",
    SOLICITACAO_ESTOQUE: "Verifica estoque",
    MANUAL: "Manual",
};

interface SafraChecklistProps {
    safraId: string;
    cultura: string | null;
    fase: string;
}

interface ChecklistCreateForm {
    titulo: string;
    descricao: string;
    obrigatorio: boolean;
}


const FASE_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo do Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
    ENCERRADA: "Encerrada",
    SÉM_SAFRA: "Sem Safra",
};

export function SafraChecklist({ safraId, cultura, fase }: SafraChecklistProps) {
    const queryClient = useQueryClient();
    const queryKey = ["checklist", safraId, fase];
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [isTemplateOpen, setIsTemplateOpen] = useState(false);

    const { data, isLoading, error } = useQuery<ChecklistFaseStatus>({
        queryKey,
        queryFn: async () => {
            // Gera itens se não existirem, depois busca status
            await apiFetch(`/safras/${safraId}/checklist/${fase}/gerar?cultura=${encodeURIComponent(cultura ?? "")}`, {
                method: "POST",
            });
            return apiFetch(`/safras/${safraId}/checklist/${fase}`);
        },
        staleTime: 30_000,
        retry: 1,
    });

    const toggleMutation = useMutation({
        mutationFn: ({ itemId, concluido, cancelado }: { itemId: string; concluido?: boolean; cancelado?: boolean }) =>
            apiFetch(`/safras/${safraId}/checklist/itens/${itemId}`, {
                method: "PATCH",
                body: JSON.stringify({ concluido, cancelado }),
            }),
        onSuccess: () => queryClient.invalidateQueries({ queryKey }),
        onError: () => toast.error("Erro ao atualizar item"),
    });

    const assumirMutation = useMutation({
        mutationFn: (itemId: string) =>
            apiFetch(`/safras/${safraId}/checklist/itens/${itemId}/assumir`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success("Item assumido!");
        },
        onError: (e: Error) => toast.error(e?.message || "Erro ao assumir item"),
    });

    const [overrideItem, setOverrideItem] = useState<ChecklistItem | null>(null);
    const [overrideJustificativa, setOverrideJustificativa] = useState("");
    const overrideMutation = useMutation({
        mutationFn: ({ itemId, justificativa }: { itemId: string; justificativa: string }) =>
            apiFetch(`/safras/${safraId}/checklist/itens/${itemId}/override`, {
                method: "PATCH",
                body: JSON.stringify({ status_verificacao: "OK_PARCIAL", justificativa }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success("Override registrado — item marcado como OK parcial.");
            setOverrideItem(null);
            setOverrideJustificativa("");
        },
        onError: (e: Error) => toast.error(e?.message || "Erro ao aplicar override"),
    });

    const [gerarOsItem, setGerarOsItem] = useState<ChecklistItem | null>(null);
    const [talhaoSelecionado, setTalhaoSelecionado] = useState<string>("");

    const { data: talhoesDaSafra = [] } = useQuery<{ area_id: string; nome: string | null }[]>({
        queryKey: ["safra-talhoes", safraId],
        queryFn: () => apiFetch(`/safras/${safraId}/talhoes`),
        enabled: !!gerarOsItem,
        staleTime: 60_000,
    });

    const gerarOsMutation = useMutation({
        mutationFn: ({ itemId, talhaoId }: { itemId: string; talhaoId: string }) =>
            apiFetch(`/safras/${safraId}/checklist/itens/${itemId}/gerar-operacao`, {
                method: "POST",
                body: JSON.stringify({ talhao_id: talhaoId }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success("OS gerada e vinculada ao item!");
            setGerarOsItem(null);
            setTalhaoSelecionado("");
        },
        onError: (e: Error) => toast.error(e?.message || "Erro ao gerar OS"),
    });

    const adicionarMutation = useMutation({
        mutationFn: (dados: ChecklistCreateForm) =>
            apiFetch(`/safras/${safraId}/checklist/${fase}/itens`, {
                method: "POST",
                body: JSON.stringify(dados),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey });
            toast.success("Item adicionado!");
            setIsAddOpen(false);
            reset();
        },
    });

    const { register, handleSubmit, reset, control } = useForm<ChecklistCreateForm>({
        defaultValues: {
            titulo: "",
            descricao: "",
            obrigatorio: false,
        },
    });

    if (isLoading) {
        return <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>;
    }

    if (error) {
        return (
            <div className="text-center py-6 text-muted-foreground">
                <AlertTriangle className="size-5 mx-auto mb-2 text-amber-600" />
                <p className="text-sm">Erro ao carregar checklist</p>
                <p className="text-xs mt-1">{(error as Error)?.message || "Tente novamente"}</p>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="text-center py-6 text-muted-foreground">
                <p className="text-sm">Nenhuma atividade encontrada para esta fase</p>
            </div>
        );
    }

    const { itens, concluidos, total, obrigatorios_pendentes, veredito } = data;
    const VEREDITO_BADGE: Record<ChecklistFaseStatus["veredito"], { label: string; className: string }> = {
        OK: { label: "OK para avançar", className: "text-emerald-700 border-emerald-200 bg-emerald-50" },
        OK_PARCIAL: { label: "OK parcial — com pendências justificadas", className: "text-amber-700 border-amber-200 bg-amber-50" },
        BLOQUEANTE: { label: "Bloqueado para avançar", className: "text-destructive border-destructive/30 bg-destructive/5" },
    };

    return (
        <>
            {/* Cabeçalho da seção */}
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex min-w-0 items-start gap-2">
                    <CheckSquare className="size-4 text-muted-foreground" />
                    <div className="min-w-0">
                        <h3 className="text-sm font-semibold">Checklist — {FASE_LABEL[fase] ?? fase}</h3>
                        <span className="text-xs text-muted-foreground">Obrigatórios para avanço de fase</span>
                    </div>
                </div>
                <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setIsTemplateOpen(true)}
                        aria-label="Templates"
                        title="Templates"
                        className="border-primary/50 text-primary hover:bg-primary/5"
                    >
                        <LayoutTemplate className="size-3.5 mr-1.5" />
                        Templates
                    </Button>
                    <Button
                        size="icon-sm"
                        variant="outline"
                        onClick={() => setIsAddOpen(true)}
                        aria-label="Adicionar atividade"
                        title="Adicionar atividade"
                    >
                        <Plus />
                    </Button>
                </div>
            </div>

            {/* Progresso */}
            <div className="mb-4 flex flex-col gap-3 rounded-sm border border-border/50 bg-muted/30 p-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex flex-col">
                        <span className="text-sm font-bold">{concluidos}/{total} concluídos</span>
                        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Progresso da Fase</span>
                    </div>
                    {obrigatorios_pendentes > 0 && (
                        <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50/50 gap-1 text-[10px] font-bold">
                            <AlertTriangle className="size-3" />
                            {obrigatorios_pendentes} PENDENTE{obrigatorios_pendentes > 1 ? "S" : ""}
                        </Badge>
                    )}
                    <Badge variant="outline" className={cn("gap-1 text-[10px] font-bold", VEREDITO_BADGE[veredito].className)}>
                        {VEREDITO_BADGE[veredito].label}
                    </Badge>
                </div>
                <div className="flex items-center gap-3 self-end sm:self-auto">
                    <div className="h-1.5 w-32 overflow-hidden rounded-full border border-border/50 bg-muted">
                        <div
                            className="h-full bg-emerald-500 rounded-full transition-all"
                            style={{ width: total > 0 ? `${(concluidos / total) * 100}%` : "0%" }}
                        />
                    </div>
                    <span className="text-xs font-bold tabular-nums">
                        {total > 0 ? Math.round((concluidos / total) * 100) : 0}%
                    </span>
                </div>
            </div>

            {/* Itens */}
            {itens.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">Nenhuma atividade para esta fase.</p>
            ) : (
                <ul className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                    {itens.map(item => {
                        const isManual = item.tipo_resultado === "MANUAL";
                        const podeAssumir = item.tipo_resultado !== "TAREFA_CAMPO" && !item.responsavel_id && !item.concluido && !item.cancelado;
                        const podeJustificar = item.tipo_resultado === "SOLICITACAO_ESTOQUE" && item.status_verificacao === "BLOQUEANTE";
                        const podeGerarOs = item.tipo_resultado === "TAREFA_CAMPO" && !item.operacao_agricola_id && !item.cancelado;
                        return (
                        <li
                            key={item.id}
                            className={cn(
                                "group relative flex flex-col rounded-sm border border-border/50 bg-muted/30 p-2.5 transition-colors",
                                isManual && "cursor-pointer hover:bg-muted/40",
                                item.concluido && "border-emerald-200/60 bg-emerald-50/20",
                                item.cancelado && "opacity-60 grayscale",
                                !item.concluido && !item.cancelado && item.obrigatorio && "border-amber-200",
                                item.status_verificacao === "BLOQUEANTE" && "border-destructive/40",
                            )}
                            onClick={() => isManual && !item.cancelado && toggleMutation.mutate({ itemId: item.id, concluido: !item.concluido })}
                        >
                            <div className="flex items-start gap-2">
                                <div className="mt-0.5 shrink-0">
                                    {item.cancelado
                                        ? <Ban className="size-4 text-slate-400" />
                                        : item.concluido
                                            ? <CheckCircle2 className="size-4 text-emerald-500" />
                                            : <Circle className="size-4 text-muted-foreground" />}
                                </div>
                                <div className="flex-1 min-w-0 pr-6">
                                    <p className={cn(
                                        "text-sm font-semibold leading-tight",
                                        (item.concluido || item.cancelado) && "line-through text-muted-foreground",
                                        !item.concluido && !item.cancelado && item.obrigatorio && "text-amber-900",
                                    )}>
                                        {item.titulo}
                                    </p>
                                    {item.descricao && (
                                        <p className="text-[11px] text-muted-foreground leading-relaxed mt-1 line-clamp-2">
                                            {item.descricao}
                                        </p>
                                    )}
                                </div>

                                {!item.concluido && (
                                    <Button
                                        size="icon-sm"
                                        variant="outline"
                                        className={cn(
                                            "absolute top-1.5 right-1.5",
                                            item.cancelado
                                                ? "text-emerald-600 hover:text-emerald-700"
                                                : "text-muted-foreground hover:text-destructive"
                                        )}
                                        onClick={e => {
                                            e.stopPropagation();
                                            toggleMutation.mutate({ itemId: item.id, cancelado: !item.cancelado });
                                        }}
                                        title={item.cancelado ? "Reativar" : "Cancelar"}
                                        aria-label={item.cancelado ? "Reativar" : "Cancelar"}
                                    >
                                        {item.cancelado ? <CheckCircle2 /> : <XCircle />}
                                    </Button>
                                )}
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5 mt-2">
                                {item.obrigatorio && !item.concluido && !item.cancelado && (
                                    <span className="text-[10px] font-bold px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full">
                                        OBRIGATÓRIO
                                    </span>
                                )}
                                {!isManual && (
                                    <span className="text-[10px] px-1.5 py-0.5 bg-sky-100 text-sky-700 rounded-full">
                                        {TIPO_RESULTADO_LABEL[item.tipo_resultado]}
                                    </span>
                                )}
                                {item.status_verificacao === "BLOQUEANTE" && (
                                    <span className="text-[10px] font-bold px-1.5 py-0.5 bg-destructive/10 text-destructive rounded-full">
                                        BLOQUEANTE
                                    </span>
                                )}
                                {item.status_verificacao === "OK_PARCIAL" && (
                                    <span className="text-[10px] font-bold px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded-full" title={item.justificativa_ok_parcial ?? undefined}>
                                        OK PARCIAL
                                    </span>
                                )}
                                {item.concluido && (
                                    <span className="text-[10px] text-emerald-600 font-bold">Concluído ✓</span>
                                )}
                                {item.cancelado && (
                                    <span className="text-[10px] text-muted-foreground">Cancelado</span>
                                )}
                            </div>

                            {item.tipo_resultado === "TAREFA_CAMPO" && item.operacao_agricola_id && (
                                <p className="text-[10px] text-muted-foreground mt-2 pt-2 border-t border-border/40">
                                    OS vinculada — status acompanhado pela operação agrícola.
                                </p>
                            )}

                            {(podeAssumir || podeJustificar || podeGerarOs || item.responsavel_id) && (
                                <div className="flex flex-wrap items-center gap-1.5 mt-2 pt-2 border-t border-border/40">
                                    {item.responsavel_id && (
                                        <span className="text-[10px] text-muted-foreground">
                                            Responsável atribuído{item.prazo_resposta ? ` · prazo ${new Date(item.prazo_resposta + "T00:00:00").toLocaleDateString("pt-BR")}` : ""}
                                        </span>
                                    )}
                                    {podeGerarOs && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="min-h-8 h-auto px-2 py-1 text-[10px]"
                                            onClick={(e) => { e.stopPropagation(); setGerarOsItem(item); }}
                                        >
                                            Gerar OS
                                        </Button>
                                    )}
                                    {podeAssumir && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="min-h-8 h-auto px-2 py-1 text-[10px]"
                                            onClick={(e) => { e.stopPropagation(); assumirMutation.mutate(item.id); }}
                                            disabled={assumirMutation.isPending}
                                        >
                                            Assumir
                                        </Button>
                                    )}
                                    {podeJustificar && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="min-h-8 h-auto border-amber-300 px-2 py-1 text-[10px] text-amber-700"
                                            onClick={(e) => { e.stopPropagation(); setOverrideItem(item); }}
                                        >
                                            Justificar OK parcial
                                        </Button>
                                    )}
                                </div>
                            )}
                        </li>
                        );
                    })}
                </ul>
            )}

            <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                <DialogContent className="sm:max-w-[400px]">
                    <form onSubmit={handleSubmit(d => adicionarMutation.mutate(d))}>
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <CheckSquare className="size-4 text-primary" />
                            </div>
                            <div className="space-y-0.5">
                                <DialogTitle>Nova Atividade</DialogTitle>
                                <DialogDescription className="text-xs">
                                    Registre uma atividade para acompanhar a fase atual da safra.
                                </DialogDescription>
                            </div>
                        </div>
                    </DialogHeader>
                    <DialogBody className="space-y-4">
                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium text-muted-foreground">Título</Label>
                            <Input 
                                className="rounded-sm"
                                placeholder="Ex: Aplicar herbicida pré-emergente" 
                                {...register("titulo", { required: true })} 
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label className="text-xs font-medium text-muted-foreground">Descrição (opcional)</Label>
                            <Input 
                                className="rounded-sm"
                                placeholder="Detalhes..." 
                                {...register("descricao")} 
                            />
                        </div>
                        <div className="flex items-center gap-2">
                            <Controller
                                control={control}
                                name="obrigatorio"
                                render={({ field }) => (
                                    <Checkbox
                                        id="obrigatorio"
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                )}
                            />
                            <Label htmlFor="obrigatorio" className="text-xs font-medium cursor-pointer">
                                Obrigatória para avançar fase
                            </Label>
                        </div>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" type="button" onClick={() => setIsAddOpen(false)}>
                            <XCircle />
                            Cancelar
                        </Button>
                        <Button size="sm" type="submit" disabled={adicionarMutation.isPending}>
                            <Plus />
                            Adicionar
                        </Button>
                    </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            <ApplyTemplateSheet
                open={isTemplateOpen}
                onOpenChange={setIsTemplateOpen}
                safraId={safraId}
                cultura={cultura ?? ""}
                fase={fase}
                type="PHASE"
            />

            <Dialog open={!!overrideItem} onOpenChange={(open) => !open && setOverrideItem(null)}>
                <DialogContent className="sm:max-w-[420px]">
                    <DialogHeader>
                        <DialogTitle>Justificar OK parcial</DialogTitle>
                        <DialogDescription className="text-xs">
                            O saldo de estoque ainda não atende "{overrideItem?.titulo}". Se a compra já foi providenciada, justifique para liberar o avanço com pendência.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody className="space-y-1.5">
                        <Label className="text-xs font-medium text-muted-foreground">Justificativa</Label>
                        <Input
                            className="rounded-sm"
                            placeholder="Ex: Pedido de compra PC-000123 já emitido, aguardando entrega."
                            value={overrideJustificativa}
                            onChange={(e) => setOverrideJustificativa(e.target.value)}
                        />
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setOverrideItem(null)}>
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            disabled={overrideJustificativa.trim().length < 3 || overrideMutation.isPending}
                            onClick={() => overrideItem && overrideMutation.mutate({ itemId: overrideItem.id, justificativa: overrideJustificativa })}
                        >
                            Confirmar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <Dialog open={!!gerarOsItem} onOpenChange={(open) => !open && setGerarOsItem(null)}>
                <DialogContent className="sm:max-w-[420px]">
                    <DialogHeader>
                        <DialogTitle>Gerar OS</DialogTitle>
                        <DialogDescription className="text-xs">
                            Escolha o talhão onde "{gerarOsItem?.titulo}" será executado. A safra pode ter mais de um talhão — não há como escolher automaticamente.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogBody className="space-y-1.5">
                        <Label className="text-xs font-medium text-muted-foreground">Talhão</Label>
                        <Select value={talhaoSelecionado} onValueChange={setTalhaoSelecionado}>
                            <SelectTrigger className="rounded-sm">
                                <SelectValue placeholder="Selecione um talhão" />
                            </SelectTrigger>
                            <SelectContent>
                                {talhoesDaSafra.map((t) => (
                                    <SelectItem key={t.area_id} value={t.area_id}>
                                        {t.nome ?? `${t.area_id.slice(0, 8)}…`}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" onClick={() => setGerarOsItem(null)}>
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            disabled={!talhaoSelecionado || gerarOsMutation.isPending}
                            onClick={() => gerarOsItem && gerarOsMutation.mutate({ itemId: gerarOsItem.id, talhaoId: talhaoSelecionado })}
                        >
                            Gerar OS
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
