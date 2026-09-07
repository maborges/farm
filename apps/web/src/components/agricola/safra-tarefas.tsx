"use client";

import { type ReactNode, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import {
    CheckCircle2, CheckSquare, XCircle, Play, Plus, ListTodo, Ban,
    Pencil, MapPin, AlertTriangle, CalendarDays, Flag,
    LayoutTemplate, Zap, Check, FilePlus2
} from "lucide-react";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useForm, Controller } from "react-hook-form";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { ApplyTemplateSheet } from "./templates/apply-template-sheet";

/* ------------------------------------------------------------------ */
/* CONSTANTS                                                            */
/* ------------------------------------------------------------------ */

const STATUS_LABEL: Record<string, string> = {
    PENDENTE_APROVACAO: "Pendente",
    APROVADA: "Aprovada",
    EM_EXECUCAO: "Em Execução",
    CONCLUIDA: "Concluída",
    CANCELADA: "Cancelada",
    INVALIDADA: "Invalidada",
};

const STATUS_COLOR: Record<string, string> = {
    PENDENTE_APROVACAO: "bg-amber-500/10 text-amber-700",
    APROVADA: "bg-slate-200 text-slate-700",
    EM_EXECUCAO: "bg-blue-500/10 text-blue-700",
    CONCLUIDA: "bg-emerald-500/10 text-emerald-700",
    CANCELADA: "bg-red-500/10 text-red-700",
    INVALIDADA: "bg-violet-500/10 text-violet-700",
};

const PRIORIDADE_COLOR: Record<string, string> = {
    BAIXA: "text-slate-500",
    MEDIA: "text-blue-500",
    ALTA: "text-orange-500",
    URGENTE: "text-rose-600",
};

const TIPO_LABEL: Record<string, string> = {
    MANUAL: "Manual",
    AUTOMATICA: "Automática",
    TEMPLATE: "Template de Fase",
};

const FASE_LABEL: Record<string, string> = {
    PLANEJADA: "Planejamento",
    PREPARO_SOLO: "Preparo do Solo",
    PLANTIO: "Plantio",
    DESENVOLVIMENTO: "Desenvolvimento",
    COLHEITA: "Colheita",
    POS_COLHEITA: "Pós-Colheita",
    ENCERRADA: "Encerrada",
};

const CRITICIDADE_LABEL: Record<string, string> = {
    NORMAL: "Normal",
    CRITICA: "Crítica",
    OPCIONAL: "Opcional",
};

const PRIORIDADE_LABEL: Record<string, string> = {
    BAIXA: "Baixa",
    MEDIA: "Média",
    ALTA: "Alta",
    URGENTE: "Urgente",
};

/* ------------------------------------------------------------------ */
/* TYPES                                                                */
/* ------------------------------------------------------------------ */

interface Tarefa {
    id: string;
    descricao: string;
    status: string;
    tipo: string;
    prioridade: string;
    criticidade?: string;
    fase?: string;
    talhao_id?: string;
    ordem?: number;
    data_prevista?: string;
    concluida_em?: string;
    obs?: string;
}

interface AreaRural {
    id: string;
    nome: string;
}

interface CultivoArea {
    area_id: string;
    area_ha: number;
}

interface Cultivo {
    id: string;
    areas: CultivoArea[];
}

/* ------------------------------------------------------------------ */
/* HELPERS                                                              */
/* ------------------------------------------------------------------ */

function fmtDate(d: string | null | undefined) {
    if (!d) return null;
    try { return format(new Date(d), "dd/MM/yy", { locale: ptBR }); }
    catch { return null; }
}

function isPlanoAssistido(obs: string | null | undefined) {
    return Boolean(obs && obs.includes("Origem operacional: PLANO_ASSISTIDO"));
}

function GrupoSection({
    label,
    dotColor,
    children,
}: {
    label: string;
    dotColor: string;
    children: ReactNode;
}) {
    return (
        <section className="space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                <span className={cn("size-1.5 rounded-full", dotColor)} />
                {label}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {children}
            </div>
        </section>
    );
}

/* ------------------------------------------------------------------ */
/* COMPONENT                                                            */
/* ------------------------------------------------------------------ */

export function SafraTarefas({
    safraId,
    isFullPage = false,
    fase = "",
    cultura = "",
}: {
    safraId: string;
    isFullPage?: boolean;
    fase?: string;
    cultura?: string;
}) {
    const queryClient = useQueryClient();
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [isTemplateOpen, setIsTemplateOpen] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [cancelingId, setCancelingId] = useState<string | null>(null);
    const [motivoCancelamento, setMotivoCancelamento] = useState("");
    const [invalidatingId, setInvalidatingId] = useState<string | null>(null);
    const [motivoInvalidacao, setMotivoInvalidacao] = useState("");
    const [gerandoOsId, setGerandoOsId] = useState<string | null>(null);
    const [dataPrevistaOs, setDataPrevistaOs] = useState("");
    const [iniciandoId, setIniciandoId] = useState<string | null>(null);
    const [filtroFase, setFiltroFase] = useState("ALL");
    const [filtroStatus, setFiltroStatus] = useState("ALL");
    const [filtroTalhao, setFiltroTalhao] = useState("ALL");

    const { register, handleSubmit, reset, control } = useForm({
        defaultValues: {
            tipo: "MANUAL",
            prioridade: "MEDIA",
            criticidade: "NORMAL",
            descricao: "",
            obs: "",
            fase: "",
            talhao_id: "",
        },
    });

    const { data: tarefas = [], isLoading } = useQuery<Tarefa[]>({
        queryKey: ["safras", safraId, "tarefas"],
        queryFn: () => apiFetch(`/safras/${safraId}/tarefas`),
        enabled: !!safraId,
    });

    const { data: todasAreas = [] } = useQuery<AreaRural[]>({
        queryKey: ["areas-rurais-talhoes"],
        queryFn: () => apiFetch("/cadastros/areas-rurais?tipo=TALHAO"),
    });

    const { data: cultivosDaSafra = [] } = useQuery<Cultivo[]>({
        queryKey: ["safras", safraId, "cultivos"],
        queryFn: () => apiFetch(`/safras/${safraId}/cultivos`),
        enabled: !!safraId,
    });

    const talhoesDaSafra = Array.from(
        new Set(cultivosDaSafra.flatMap((cultivo) => cultivo.areas.map((area) => area.area_id))),
    );

    const adicionarMut = useMutation({
        mutationFn: (d: Record<string, string>) => {
            const body = {
                ...d,
                talhao_id: d.talhao_id === "" ? null : d.talhao_id,
                fase: d.fase === "" ? null : d.fase,
            };
            return apiFetch(`/safras/${safraId}/tarefas`, { method: "POST", body: body as never });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            setIsAddOpen(false);
            reset();
            toast.success("Tarefa planejada!");
        },
        onError: (err: Error) => toast.error("Erro ao salvar tarefa: " + err.message),
    });

    const editarMut = useMutation({
        mutationFn: (d: Record<string, string>) => {
            const body = {
                ...d,
                talhao_id: d.talhao_id === "" ? null : d.talhao_id,
                fase: d.fase === "" ? null : d.fase,
            };
            return apiFetch(`/tarefas/${editingId}`, { method: "PATCH", body: body as never });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            setIsAddOpen(false);
            setEditingId(null);
            reset();
            toast.success("Tarefa atualizada!");
        },
        onError: (err: Error) => toast.error("Erro ao atualizar tarefa: " + err.message),
    });

    const cancelarMut = useMutation({
        mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
            apiFetch(`/tarefas/${id}/rejeitar`, { method: "DELETE", params: { motivo } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            setCancelingId(null);
            setMotivoCancelamento("");
            toast.success("Tarefa cancelada.");
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const invalidarMut = useMutation({
        mutationFn: ({ id, motivo }: { id: string; motivo: string }) =>
            apiFetch(`/tarefas/${id}/invalidar`, { method: "PATCH", params: { motivo } }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            setInvalidatingId(null);
            setMotivoInvalidacao("");
            toast.success("Tarefa invalidada com histórico preservado.");
        },
        onError: (err: Error) => toast.error(err.message),
    });

    const aprovarMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/tarefas/${id}/aprovar`, { method: "PATCH" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            toast.success("Tarefa aprovada!");
        },
        onError: (err: Error) => toast.error("Erro ao aprovar tarefa: " + err.message),
    });

    const iniciarMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/tarefas/${id}/iniciar`, { method: "PATCH" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            setIniciandoId(null);
            toast.success("Execução iniciada!");
        },
        onError: (err: Error) => toast.error("Erro ao iniciar tarefa: " + err.message),
    });

    const gerarOsMut = useMutation({
        mutationFn: ({ id, data_prevista }: { id: string; data_prevista: string }) =>
            apiFetch(`/tarefas/${id}/planejar-operacao`, {
                method: "POST",
                body: { data_prevista } as never,
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "operacoes"] });
            setGerandoOsId(null);
            setDataPrevistaOs("");
            toast.success("Ordem de serviço gerada! O campo já pode executar em Execução.");
        },
        onError: (err: Error) => toast.error("Erro ao gerar ordem de serviço: " + err.message),
    });

    const concluirMut = useMutation({
        mutationFn: (id: string) => apiFetch(`/tarefas/${id}/concluir`, { method: "PATCH" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["safras", safraId, "tarefas"] });
            toast.success("Tarefa concluída!");
        },
    });

    /* ---- LOADING ---- */
    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-[88px] w-full rounded-sm" />)}
            </div>
        );
    }

    /* ---- FILTERING ---- */
    const tarefasFiltradas = tarefas.filter(t => {
        if (filtroFase !== "ALL" && t.fase !== filtroFase) return false;
        if (filtroStatus !== "ALL" && t.status !== filtroStatus) return false;
        if (filtroTalhao !== "ALL" && t.talhao_id !== filtroTalhao) return false;
        return true;
    });

    /* ---- GROUPING ---- */
    const porOrdem = (a: Tarefa, b: Tarefa) => (a.ordem ?? 0) - (b.ordem ?? 0);
    const pendentes  = tarefasFiltradas.filter(t => t.status === "PENDENTE_APROVACAO" || t.status === "APROVADA").sort(porOrdem);
    const ativas     = tarefasFiltradas.filter(t => t.status === "EM_EXECUCAO").sort(porOrdem);
    const encerradas = tarefasFiltradas.filter(t => t.status === "CONCLUIDA" || t.status === "CANCELADA" || t.status === "INVALIDADA").sort(porOrdem);

    const ActionTooltip = ({ text, children }: { text: string; children: React.ReactNode }) => (
        <Tooltip>
            <TooltipTrigger asChild>{children}</TooltipTrigger>
            <TooltipContent className="max-w-[280px] text-center">{text}</TooltipContent>
        </Tooltip>
    );

    /* ---- ACTION BUTTONS (sem borda, sem texto, ícone semântico) ---- */
    const TarefaActions = ({ t }: { t: Tarefa }) => {
        const isPendenteAprovacao = t.status === "PENDENTE_APROVACAO";
        const isAprovada  = t.status === "APROVADA";
        const isPendente  = isPendenteAprovacao || isAprovada;
        const isExecucao  = t.status === "EM_EXECUCAO";
        const isConcluida = t.status === "CONCLUIDA";
        const isCancelada = t.status === "CANCELADA";
        const isInvalidada = t.status === "INVALIDADA";

        return (
            <TooltipProvider>
                <div className="flex gap-1">
                    {isPendenteAprovacao && (
                        <ActionTooltip text="Aprovar tarefa">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7 text-emerald-700 hover:text-emerald-800"
                                onClick={e => { e.stopPropagation(); aprovarMut.mutate(t.id); }}
                                disabled={aprovarMut.isPending}
                            >
                                <Check className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {isAprovada && (
                        <ActionTooltip text="Gerar ordem de serviço: cria uma operação PLANEJADA. Ao marcar a operação como realizada no campo, esta tarefa é concluída automaticamente.">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7"
                                disabled={gerarOsMut.isPending}
                                onClick={e => { e.stopPropagation(); setGerandoOsId(t.id); setDataPrevistaOs(t.data_prevista?.slice(0, 10) || ""); }}
                            >
                                <FilePlus2 className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {isAprovada && (
                        <ActionTooltip text="Iniciar execução direta: marca a tarefa como Em Execução sem gerar OS. Você precisará concluir esta tarefa manualmente depois.">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7"
                                onClick={e => { e.stopPropagation(); setIniciandoId(t.id); }}
                            >
                                <Play className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {isExecucao && (
                        <ActionTooltip text="Concluir tarefa">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7"
                                onClick={e => { e.stopPropagation(); concluirMut.mutate(t.id); }}
                                disabled={concluirMut.isPending}
                            >
                                <CheckCircle2 className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {isConcluida && (
                        <ActionTooltip text="Invalidar tarefa">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7 text-violet-700 hover:text-violet-800"
                                onClick={e => { e.stopPropagation(); setInvalidatingId(t.id); }}
                            >
                                <XCircle className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {(isPendente || isExecucao) && (
                        <ActionTooltip text="Cancelar tarefa">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7 text-destructive hover:text-destructive"
                                onClick={e => { e.stopPropagation(); setCancelingId(t.id); }}
                            >
                                <Ban className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                    {!isConcluida && !isCancelada && !isInvalidada && (
                        <ActionTooltip text="Editar tarefa">
                            <Button
                                size="icon" variant="ghost"
                                className="h-7 w-7"
                                onClick={e => {
                                    e.stopPropagation();
                                    reset({
                                        tipo: t.tipo,
                                        prioridade: t.prioridade,
                                        criticidade: t.criticidade || "NORMAL",
                                        descricao: t.descricao,
                                        obs: t.obs || "",
                                        fase: t.fase || "",
                                        talhao_id: t.talhao_id || "",
                                    });
                                    setEditingId(t.id);
                                    setIsAddOpen(true);
                                }}
                            >
                                <Pencil className="h-3.5 w-3.5" />
                            </Button>
                        </ActionTooltip>
                    )}
                </div>
            </TooltipProvider>
        );
    };

    /* ---- TAREFA CARD — mesmo padrão do CultivoCard ---- */
    const TarefaCard = ({ t }: { t: Tarefa }) => {
        const talhaoNome  = t.talhao_id ? todasAreas.find(a => a.id === t.talhao_id)?.nome : null;
        const dataPrevista = fmtDate(t.data_prevista);
        const statusColor  = STATUS_COLOR[t.status] ?? "bg-slate-100 text-slate-600";

        return (
            <Card className="overflow-hidden border-l-[3px] border-l-primary">
                {/* Header */}
                <div className="flex items-start justify-between px-4 pt-3 pb-2">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            {!!t.ordem && (
                                <span className="flex items-center justify-center size-5 rounded-full bg-muted text-[10px] font-semibold text-muted-foreground flex-shrink-0">
                                    {t.ordem}
                                </span>
                            )}
                            <span className="font-semibold text-sm">{t.descricao}</span>
                            <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", statusColor)}>
                                {STATUS_LABEL[t.status]}
                            </span>
                            {t.criticidade === "CRITICA" && (
                                <Badge variant="outline" className="text-xs py-0 border-rose-200 text-rose-700 bg-rose-50">
                                    Crítica
                                </Badge>
                            )}
                        </div>
                        {t.fase && (
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {FASE_LABEL[t.fase] ?? t.fase}
                            </p>
                        )}
                    </div>
                    <div className="flex gap-1 ml-2 flex-shrink-0">
                        <TarefaActions t={t} />
                    </div>
                </div>

                <CardContent className="px-4 pb-3 pt-0 space-y-2.5">
                    {/* Métricas em linha */}
                    <div className="flex items-center gap-3 flex-wrap text-xs text-muted-foreground">
                        {talhaoNome && (
                            <div className="flex items-center gap-1.5">
                                <MapPin className="size-3 flex-shrink-0" />
                                <span className="font-medium text-foreground">{talhaoNome}</span>
                            </div>
                        )}
                        {dataPrevista && (
                            <div className="flex items-center gap-1.5">
                                <CalendarDays className="size-3 flex-shrink-0" />
                                <span>{dataPrevista}</span>
                            </div>
                        )}
                        <div className="flex items-center gap-1.5">
                            <Flag className="size-3 flex-shrink-0" />
                            <span className={cn("font-medium", PRIORIDADE_COLOR[t.prioridade])}>
                                {PRIORIDADE_LABEL[t.prioridade] ?? t.prioridade}
                            </span>
                        </div>
                        {isPlanoAssistido(t.obs) && (
                            <Badge variant="outline" className="rounded-sm border-primary/20 bg-primary/5 text-primary">
                                Derivada de plano assistido
                            </Badge>
                        )}
                    </div>

                    {t.obs && (
                        <p className="text-xs text-muted-foreground italic line-clamp-2">{t.obs}</p>
                    )}
                </CardContent>
            </Card>
        );
    };

    /* ---------------------------------------------------------------- */
    /* RENDER                                                             */
    /* ---------------------------------------------------------------- */
    return (
        <>
            {/* Cabeçalho da seção */}
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                    <ListTodo className="size-4 text-muted-foreground" />
                    <h3 className="text-sm font-semibold">Tarefas Planejadas</h3>
                    <span className="text-xs text-muted-foreground">
                        — {tarefasFiltradas.length} de {tarefas.length}
                    </span>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    <Select value={filtroFase} onValueChange={setFiltroFase}>
                        <SelectTrigger className="h-8 w-[150px] text-xs">
                            <SelectValue placeholder="Fase" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">Todas as fases</SelectItem>
                            {Object.entries(FASE_LABEL).map(([k, v]) => (
                                <SelectItem key={k} value={k}>{v}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                        <SelectTrigger className="h-8 w-[150px] text-xs">
                            <SelectValue placeholder="Situação" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">Todas as situações</SelectItem>
                            {Object.entries(STATUS_LABEL).map(([k, v]) => (
                                <SelectItem key={k} value={k}>{v}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Select value={filtroTalhao} onValueChange={setFiltroTalhao}>
                        <SelectTrigger className="h-8 w-[150px] text-xs">
                            <SelectValue placeholder="Talhão" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="ALL">Todos os talhões</SelectItem>
                            {talhoesDaSafra.map((areaId) => {
                                const area = todasAreas.find(a => a.id === areaId);
                                if (!area) return null;
                                return (
                                    <SelectItem key={area.id} value={area.id}>{area.nome}</SelectItem>
                                );
                            })}
                        </SelectContent>
                    </Select>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setIsTemplateOpen(true)}
                        className="border-primary/50 text-primary hover:bg-primary/5"
                    >
                        <LayoutTemplate className="h-3.5 w-3.5 mr-1.5" />
                        Templates
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => { setEditingId(null); reset(); setIsAddOpen(true); }}
                    >
                        <Plus className="h-3.5 w-3.5 mr-1.5" />
                        Nova Tarefa
                    </Button>
                </div>
            </div>

            {tarefas.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center border border-dashed rounded-sm bg-muted/20">
                    <ListTodo className="size-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">Nenhuma tarefa planejada.</p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                        Use o botão acima para adicionar a primeira tarefa.
                    </p>
                </div>
            ) : tarefasFiltradas.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center border border-dashed rounded-sm bg-muted/20">
                    <ListTodo className="size-8 text-muted-foreground/40 mb-2" />
                    <p className="text-sm text-muted-foreground">Nenhuma tarefa encontrada para este filtro.</p>
                </div>
            ) : (
                <div className="space-y-6">
                    {pendentes.length > 0 && (
                        <GrupoSection
                            label="Planejadas"
                            dotColor="bg-slate-400"
                        >
                            {pendentes.map((t) => <TarefaCard key={t.id} t={t} />)}
                        </GrupoSection>
                    )}
                    {ativas.length > 0 && (
                        <GrupoSection
                            label="Em andamento"
                            dotColor="bg-blue-500"
                        >
                            {ativas.map((t) => <TarefaCard key={t.id} t={t} />)}
                        </GrupoSection>
                    )}
                    {encerradas.length > 0 && (
                        <GrupoSection
                            label="Encerradas"
                            dotColor="bg-emerald-500"
                        >
                            {encerradas.map((t) => <TarefaCard key={t.id} t={t} />)}
                        </GrupoSection>
                    )}
                </div>
            )}

            {/* Modal Nova / Editar Tarefa */}
            <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                <DialogContent className="sm:max-w-[520px] p-0 gap-0 overflow-hidden rounded-sm">
                    <form
                        onSubmit={handleSubmit(d => editingId ? editarMut.mutate(d as Record<string, string>) : adicionarMut.mutate(d as Record<string, string>))}
                        className="flex max-h-[85vh] min-h-0 flex-col"
                    >
                        <DialogHeader className="border-b px-6 py-5">
                            <div className="flex items-center gap-2.5">
                                <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                                    <CheckSquare className="size-4 text-primary" />
                                </div>
                                <div className="min-w-0">
                                    <DialogTitle className="text-base leading-tight">
                                        {editingId ? "Editar Tarefa" : "Nova Tarefa"}
                                    </DialogTitle>
                                    <DialogDescription className="text-xs">
                                        {editingId
                                            ? "Atualize os dados da tarefa planejada para esta safra."
                                            : "Cadastre uma tarefa para acompanhar a fase atual da safra."}
                                    </DialogDescription>
                                </div>
                            </div>
                        </DialogHeader>

                        <DialogBody className="px-6 py-5">
                            <div className="flex flex-col gap-5">
                                <section className="rounded-sm border bg-muted/30 p-4">
                                    <div className="mb-4">
                                        <h3 className="text-sm font-medium text-foreground">Identificação</h3>
                                        <p className="text-xs text-muted-foreground">
                                            Defina o nome da tarefa e o contexto operacional do planejamento.
                                        </p>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-muted-foreground">Descrição *</Label>
                                            <Input
                                                placeholder="Ex: Aplicar ureia em cobertura"
                                                {...register("descricao", { required: true, minLength: 3 })}
                                            />
                                        </div>

                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium text-muted-foreground">Talhão</Label>
                                                <Controller
                                                    control={control}
                                                    name="talhao_id"
                                                    render={({ field }) => (
                                                        <Select
                                                            value={field.value || "ALL"}
                                                            onValueChange={(val: string) => field.onChange(val === "ALL" ? "" : val)}
                                                        >
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={field.value === "" || field.value === "ALL" ? "Toda a safra" : todasAreas.find(a => a.id === field.value)?.nome || field.value} />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="ALL">Toda a safra</SelectItem>
                                                                {talhoesDaSafra.map((areaId) => {
                                                                    const area = todasAreas.find((a) => a.id === areaId);
                                                                    if (!area) return null;
                                                                    return (
                                                                        <SelectItem key={area.id} value={area.id}>
                                                                            {area.nome}
                                                                        </SelectItem>
                                                                    );
                                                                })}
                                                                {field.value && field.value !== "ALL" && !talhoesDaSafra.includes(field.value) && (
                                                                    <SelectItem value={field.value}>
                                                                        {todasAreas.find((a) => a.id === field.value)?.nome ?? field.value}
                                                                    </SelectItem>
                                                                )}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                            </div>

                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium text-muted-foreground">Fase</Label>
                                                <Controller
                                                    control={control}
                                                    name="fase"
                                                    render={({ field }) => (
                                                        <Select
                                                            value={field.value || "NONE"}
                                                            onValueChange={(val: string) => field.onChange(val === "NONE" ? "" : val)}
                                                        >
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={field.value === "" || field.value === "NONE" ? "Sem fase" : FASE_LABEL[field.value] || field.value} />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                <SelectItem value="NONE">Sem fase</SelectItem>
                                                                {Object.entries(FASE_LABEL).map(([k, v]) => (
                                                                    <SelectItem key={k} value={k}>{v}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </section>

                                <section className="rounded-sm border bg-muted/30 p-4">
                                    <div className="mb-4">
                                        <h3 className="text-sm font-medium text-foreground">Classificação</h3>
                                        <p className="text-xs text-muted-foreground">
                                            Ajuste prioridade, criticidade e observações complementares.
                                        </p>
                                    </div>

                                    <div className="space-y-4">
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium text-muted-foreground">Prioridade</Label>
                                                <Controller
                                                    control={control}
                                                    name="prioridade"
                                                    render={({ field }) => (
                                                        <Select value={field.value} onValueChange={field.onChange}>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={PRIORIDADE_LABEL[field.value] || field.value} />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {Object.entries(PRIORIDADE_LABEL).map(([k, v]) => (
                                                                    <SelectItem key={k} value={k}>{v}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                            </div>

                                            <div className="space-y-1.5">
                                                <Label className="text-xs font-medium text-muted-foreground">Criticidade</Label>
                                                <Controller
                                                    control={control}
                                                    name="criticidade"
                                                    render={({ field }) => (
                                                        <Select value={field.value} onValueChange={field.onChange}>
                                                            <SelectTrigger>
                                                                <SelectValue placeholder={CRITICIDADE_LABEL[field.value] || field.value} />
                                                            </SelectTrigger>
                                                            <SelectContent>
                                                                {Object.entries(CRITICIDADE_LABEL).map(([k, v]) => (
                                                                    <SelectItem key={k} value={k}>{v}</SelectItem>
                                                                ))}
                                                            </SelectContent>
                                                        </Select>
                                                    )}
                                                />
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <Label className="text-xs font-medium text-muted-foreground">Observações</Label>
                                            <Textarea
                                                placeholder="Detalhes adicionais..."
                                                {...register("obs")}
                                                rows={2}
                                                className="resize-none text-sm"
                                            />
                                        </div>
                                    </div>
                                </section>
                            </div>
                        </DialogBody>

                        <DialogFooter className="border-t px-6 py-4">
                            <Button
                                variant="outline" size="sm" type="button"
                                onClick={() => setIsAddOpen(false)}
                            >
                                <XCircle className="h-3.5 w-3.5 mr-1.5" />
                                Cancelar
                            </Button>
                            <Button
                                size="sm" type="submit"
                                disabled={adicionarMut.isPending || editarMut.isPending}
                            >
                                <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
                                {editingId ? "Confirmar" : "Salvar"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* Modal Cancelamento */}
            <Dialog open={!!cancelingId} onOpenChange={(open) => !open && setCancelingId(null)}>
                <DialogContent className="sm:max-w-[420px] p-0 gap-0 overflow-hidden rounded-sm">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="text-destructive flex items-center gap-2">
                            <AlertTriangle className="size-5" />
                            Cancelar Tarefa
                        </DialogTitle>
                        <DialogDescription className="text-xs mt-1.5">
                            Esta ação não pode ser desfeita.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="px-6 py-5 space-y-4">
                        <div className="space-y-1.5">
                            <Label className="text-sm font-medium text-foreground">Motivo do cancelamento *</Label>
                            <Textarea
                                placeholder="Justifique o cancelamento..."
                                value={motivoCancelamento}
                                onChange={e => setMotivoCancelamento(e.target.value)}
                                rows={3}
                                className="resize-none"
                            />
                        </div>
                    </div>
                    <DialogFooter className="border-t px-6 py-4 bg-muted/20">
                        <Button
                            variant="outline" size="sm"
                            onClick={() => setCancelingId(null)}
                        >
                            <XCircle className="h-3.5 w-3.5 mr-1.5" />
                            Voltar
                        </Button>
                        <Button
                            variant="destructive" size="sm"
                            disabled={!motivoCancelamento || cancelarMut.isPending}
                            onClick={() =>
                                cancelingId &&
                                cancelarMut.mutate({ id: cancelingId, motivo: motivoCancelamento })
                            }
                        >
                            <Ban className="h-3.5 w-3.5 mr-1.5" />
                            Confirmar Cancelamento
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Modal Invalidação */}
            <Dialog open={!!invalidatingId} onOpenChange={(open) => !open && setInvalidatingId(null)}>
                <DialogContent className="sm:max-w-[420px] p-0 gap-0 overflow-hidden rounded-sm">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="text-violet-700 flex items-center gap-2">
                            <AlertTriangle className="size-5" />
                            Invalidar Tarefa
                        </DialogTitle>
                        <DialogDescription className="text-xs mt-1.5">
                            Esta tarefa já integra o histórico operacional.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="px-6 py-5 space-y-4">
                        <div className="space-y-1.5">
                            <Label className="text-sm font-medium text-foreground">Motivo da invalidação *</Label>
                            <Textarea
                                placeholder="Justifique a invalidação..."
                                value={motivoInvalidacao}
                                onChange={e => setMotivoInvalidacao(e.target.value)}
                                rows={3}
                                className="resize-none"
                            />
                        </div>
                    </div>
                    <DialogFooter className="border-t px-6 py-4 bg-muted/20">
                        <Button
                            variant="outline" size="sm"
                            onClick={() => setInvalidatingId(null)}
                        >
                            <Ban className="h-3.5 w-3.5 mr-1.5" />
                            Voltar
                        </Button>
                        <Button
                            size="sm"
                            className="bg-violet-600 hover:bg-violet-700 text-white"
                            disabled={!motivoInvalidacao || invalidarMut.isPending}
                            onClick={() =>
                                invalidatingId &&
                                invalidarMut.mutate({ id: invalidatingId, motivo: motivoInvalidacao })
                            }
                        >
                            <XCircle className="h-3.5 w-3.5 mr-1.5" />
                            Confirmar Invalidação
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Modal Gerar Ordem de Serviço */}
            <Dialog open={!!gerandoOsId} onOpenChange={(open) => !open && setGerandoOsId(null)}>
                <DialogContent className="sm:max-w-[420px] p-0 gap-0 overflow-hidden rounded-sm">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="flex items-center gap-2">
                            <FilePlus2 className="size-5 text-primary" />
                            Gerar Ordem de Serviço
                        </DialogTitle>
                        <DialogDescription className="text-xs mt-1.5">
                            Cria uma operação agrícola planejada a partir desta tarefa, para o campo executar
                            em &quot;Execução&quot;. Ao ser registrada como realizada, esta tarefa é concluída automaticamente.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="px-6 py-5 space-y-4">
                        <div className="space-y-1.5">
                            <Label className="text-sm font-medium text-foreground">Data prevista *</Label>
                            <Input
                                type="date"
                                value={dataPrevistaOs}
                                onChange={e => setDataPrevistaOs(e.target.value)}
                            />
                        </div>
                    </div>
                    <DialogFooter className="border-t px-6 py-4 bg-muted/20">
                        <Button
                            variant="outline" size="sm"
                            onClick={() => setGerandoOsId(null)}
                        >
                            <XCircle className="h-3.5 w-3.5 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button
                            size="sm"
                            disabled={!dataPrevistaOs || gerarOsMut.isPending}
                            onClick={() =>
                                gerandoOsId &&
                                gerarOsMut.mutate({ id: gerandoOsId, data_prevista: dataPrevistaOs })
                            }
                        >
                            <FilePlus2 className="h-3.5 w-3.5 mr-1.5" />
                            Gerar Ordem de Serviço
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Confirmação Iniciar Execução (sem OS) */}
            <AlertDialog open={!!iniciandoId} onOpenChange={(open) => !open && setIniciandoId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Iniciar execução sem ordem de serviço?</AlertDialogTitle>
                        <AlertDialogDescription>
                            A tarefa passará para &quot;Em Execução&quot; imediatamente, sem criar uma operação
                            agrícola para o campo. Use esta opção apenas quando não há necessidade de rastreio
                            de custo ou execução em campo. Você precisará marcar esta tarefa como concluída
                            manualmente mais tarde — ela não será fechada automaticamente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            disabled={iniciarMut.isPending}
                            onClick={() => iniciandoId && iniciarMut.mutate(iniciandoId)}
                        >
                            Iniciar execução
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            <ApplyTemplateSheet
                open={isTemplateOpen}
                onOpenChange={setIsTemplateOpen}
                safraId={safraId}
                cultura={cultura}
                fase={fase}
                type="OPERATION"
            />
        </>
    );
}
