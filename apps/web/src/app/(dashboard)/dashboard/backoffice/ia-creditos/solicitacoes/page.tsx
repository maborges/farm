"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    BrainCircuit, RefreshCw, MessageSquare, UserCircle, X, History,
    ArrowRightLeft, User, FileText, Inbox, Loader2, CheckCircle2,
    XCircle, TrendingUp, DollarSign, CalendarClock, ArrowUpDown, Send, CheckCheck
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription,
    AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose,
} from "@/components/ui/dialog";
import Link from "next/link";

interface SolicitacaoItem {
    id: string;
    tenant_id: string;
    tenant_nome: string;
    usuario_id: string | null;
    tipo: string;
    quantidade_creditos: number | null;
    valor_estimado: number | null;
    status: string;
    status_pagamento: string | null;
    observacao_comercial: string | null;
    responsavel_usuario_id: string | null;
    responsavel_nome: string | null;
    proximo_followup_em: string | null;
    followup_observacao: string | null;
    created_at: string;
    prioridade: number;
    crm_sync_status: string;
}

function PrioridadeBadge({ score }: { score: number }) {
    if (score >= 80) return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-700 border border-red-500/30 dark:bg-red-500/20 dark:text-red-100 dark:border-red-400/30">
            {score}
        </span>
    );
    if (score >= 50) return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-700 border border-amber-500/30 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30">
            {score}
        </span>
    );
    return (
        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-700 border border-emerald-500/30 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30">
            {score}
        </span>
    );
}

interface AdminUser { id: string; nome: string; email: string; }

interface HistoricoItem {
    id: string;
    tipo_evento: string;
    valor_anterior: string | null;
    valor_novo: string | null;
    observacao: string | null;
    created_at: string;
}

interface ResumoPorResponsavel {
    responsavel_usuario_id: string | null;
    responsavel_nome: string;
    total: number;
    valor_estimado: number;
}

interface ResumoSolicitacoes {
    total_abertas: number;
    total_em_analise: number;
    total_concluidas: number;
    total_canceladas: number;
    valor_pendente: number;
    valor_concluido: number;
    taxa_conversao: number;
    por_responsavel: ResumoPorResponsavel[];
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
    ABERTA: { label: "Aberta", className: "border-blue-500/30 text-blue-700 bg-blue-500/5 dark:bg-blue-500/20 dark:text-blue-100 dark:border-blue-400/30" },
    EM_ANALISE: { label: "Em análise", className: "border-amber-500/30 text-amber-700 bg-amber-500/5 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
    CONCLUIDA: { label: "Concluída", className: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    CANCELADA: { label: "Cancelada", className: "border-muted-foreground/30 text-muted-foreground bg-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" },
};

const PGTO_CONFIG: Record<string, { label: string; className: string }> = {
    PAGO: { label: "Pago", className: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    PENDENTE: { label: "Pendente", className: "border-amber-500/30 text-amber-700 bg-amber-500/5 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
    EXPIRADO: { label: "Expirado", className: "border-muted-foreground/30 text-muted-foreground bg-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" },
};

const STATUS_OPTIONS = [
    { value: "ABERTA", label: "Aberta" },
    { value: "EM_ANALISE", label: "Em análise" },
    { value: "CONCLUIDA", label: "Concluída" },
    { value: "CANCELADA", label: "Cancelada" },
];

const EVENTO_CONFIG: Record<string, { label: string; Icon: React.ElementType; color: string }> = {
    STATUS_ALTERADO: { label: "Status alterado", Icon: ArrowRightLeft, color: "text-blue-600" },
    RESPONSAVEL_ALTERADO: { label: "Responsável alterado", Icon: User, color: "text-amber-600" },
    OBSERVACAO_ALTERADA: { label: "Observação alterada", Icon: FileText, color: "text-primary" },
    FOLLOWUP_ALTERADO: { label: "Follow-up alterado", Icon: CalendarClock, color: "text-purple-600" },
};

function formatBRL(v: number | null | undefined) {
    if (v == null) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function EventoLabel({ tipo }: { tipo: string }) {
    const cfg = EVENTO_CONFIG[tipo] ?? { label: tipo, Icon: History, color: "text-muted-foreground" };
    return (
        <span className={`flex items-center gap-1.5 font-semibold text-xs ${cfg.color}`}>
            <cfg.Icon className="size-3.5" />
            {cfg.label}
        </span>
    );
}

export default function SolicitacoesPage() {
    const queryClient = useQueryClient();

    const [statusFiltro, setStatusFiltro] = useState("TODOS");
    const [pgtoFiltro, setPgtoFiltro] = useState("TODOS");
    const [dataInicio, setDataInicio] = useState("");
    const [dataFim, setDataFim] = useState("");
    const [ordenarPrioridade, setOrdenarPrioridade] = useState(false);

    const [pendingChange, setPendingChange] = useState<{ id: string; novoStatus: string } | null>(null);
    const [obsDialog, setObsDialog] = useState<{ id: string } | null>(null);
    const [obsText, setObsText] = useState("");
    const [respDialog, setRespDialog] = useState<{ item: SolicitacaoItem } | null>(null);
    const [respSelecionado, setRespSelecionado] = useState<string>("NENHUM");
    const [histDialog, setHistDialog] = useState<{ id: string; tenantNome: string } | null>(null);
    const [followupDialog, setFollowupDialog] = useState<{ item: SolicitacaoItem } | null>(null);
    const [followupDataStr, setFollowupDataStr] = useState("");
    const [followupObsStr, setFollowupObsStr] = useState("");

    const periodoQs = (() => {
        const p = new URLSearchParams();
        if (dataInicio) p.set("data_inicio", dataInicio);
        if (dataFim) p.set("data_fim", dataFim);
        return p.toString();
    })();

    const qs = (() => {
        const p = new URLSearchParams(periodoQs);
        if (statusFiltro !== "TODOS") p.set("status", statusFiltro);
        if (pgtoFiltro !== "TODOS") p.set("status_pagamento", pgtoFiltro);
        if (ordenarPrioridade) p.set("ordenar_por", "prioridade");
        p.set("limit", "200");
        return p.toString();
    })();

    const { data: itens = [], isLoading } = useQuery<SolicitacaoItem[]>({
        queryKey: ["ia-solicitacoes", qs],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/solicitacoes?${qs}`),
        staleTime: 20_000,
    });

    const { data: resumo, isLoading: resumoLoading } = useQuery<ResumoSolicitacoes>({
        queryKey: ["ia-solicitacoes-resumo", periodoQs],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/solicitacoes/resumo?${periodoQs}`),
        staleTime: 20_000,
    });

    const { data: adminUsers = [] } = useQuery<AdminUser[]>({
        queryKey: ["admin-users-lista"],
        queryFn: () => apiFetch("/backoffice/admin/usuarios?limit=100"),
        staleTime: 60_000,
    });

    const { data: historico = [], isLoading: histLoading } = useQuery<HistoricoItem[]>({
        queryKey: ["ia-solicitacao-historico", histDialog?.id],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/solicitacoes/${histDialog!.id}/historico`),
        enabled: !!histDialog?.id,
        staleTime: 10_000,
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, status, observacao_comercial }: { id: string; status: string; observacao_comercial?: string }) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/status`, {
                method: "PATCH",
                body: JSON.stringify({ status, observacao_comercial }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes-resumo"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacao-historico"] });
            setPendingChange(null);
            setObsDialog(null);
        },
    });

    const respMutation = useMutation({
        mutationFn: ({ id, responsavel_usuario_id }: { id: string; responsavel_usuario_id: string | null }) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/responsavel`, {
                method: "PATCH",
                body: JSON.stringify({ responsavel_usuario_id }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes-resumo"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacao-historico"] });
            setRespDialog(null);
        },
    });

    const followupMutation = useMutation({
        mutationFn: ({ id, proximo_followup_em, followup_observacao }: { id: string; proximo_followup_em: string | null; followup_observacao: string | null }) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/followup`, {
                method: "PATCH",
                body: JSON.stringify({ proximo_followup_em, followup_observacao }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes-kanban"] });
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacao-historico"] });
            setFollowupDialog(null);
        },
    });

    const crmMutation = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/backoffice/ia/creditos/solicitacoes/${id}/enviar-crm`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["ia-solicitacoes"] });
            queryClient.invalidateQueries({ queryKey: ["ia-fila-prioritaria"] });
        },
    });

    function handleStatusChange(id: string, novoStatus: string) { setPendingChange({ id, novoStatus }); }
    function confirmChange() {
        if (pendingChange) updateMutation.mutate({ id: pendingChange.id, status: pendingChange.novoStatus });
    }
    function openObsDialog(item: SolicitacaoItem) { setObsText(item.observacao_comercial ?? ""); setObsDialog({ id: item.id }); }
    function saveObs() {
        if (!obsDialog) return;
        const item = itens.find((i) => i.id === obsDialog.id);
        if (!item) return;
        updateMutation.mutate({ id: obsDialog.id, status: item.status, observacao_comercial: obsText });
    }
    function openRespDialog(item: SolicitacaoItem) { setRespSelecionado(item.responsavel_usuario_id ?? "NENHUM"); setRespDialog({ item }); }
    function saveResp() {
        if (!respDialog) return;
        respMutation.mutate({ id: respDialog.item.id, responsavel_usuario_id: respSelecionado === "NENHUM" ? null : respSelecionado });
    }
    function openFollowupDialog(item: SolicitacaoItem) {
        setFollowupDataStr(item.proximo_followup_em ? item.proximo_followup_em.slice(0, 16) : "");
        setFollowupObsStr(item.followup_observacao ?? "");
        setFollowupDialog({ item });
    }
    function saveFollowup() {
        if (!followupDialog) return;
        const dt = followupDataStr ? new Date(followupDataStr).toISOString() : null;
        followupMutation.mutate({ id: followupDialog.item.id, proximo_followup_em: dt, followup_observacao: followupObsStr || null });
    }

    return (
        <div className="space-y-6 max-w-6xl">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-lg font-bold text-foreground flex items-center gap-2">
                        <BrainCircuit className="size-5 text-primary" />
                        Solicitações — Créditos de IA
                    </h1>
                    <p className="text-sm text-muted-foreground mt-0.5">
                        Funil comercial e operação das solicitações de créditos de IA.
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/backoffice/ia-creditos/solicitacoes/fila">
                            <ArrowUpDown className="size-3.5 mr-1.5" />
                            Fila prioritária
                        </Link>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/backoffice/ia-creditos/solicitacoes/kanban">
                            Ver Kanban
                        </Link>
                    </Button>
                </div>
            </div>

            <Separator />

            {/* KPI cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                    { label: "Abertas", value: resumo?.total_abertas ?? 0, icon: Inbox, color: "text-blue-600" },
                    { label: "Em análise", value: resumo?.total_em_analise ?? 0, icon: Loader2, color: "text-amber-600" },
                    { label: "Concluídas", value: resumo?.total_concluidas ?? 0, icon: CheckCircle2, color: "text-green-600" },
                    { label: "Valor pendente", value: formatBRL(resumo?.valor_pendente), icon: DollarSign, color: "text-amber-600" },
                    { label: "Taxa conversão", value: resumo != null ? `${resumo.taxa_conversao.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%` : "—", icon: TrendingUp, color: "text-primary" },
                ].map(({ label, value, icon: Icon, color }) => (
                    <div key={label} className="rounded-sm border border-border bg-card p-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <Icon className={`size-4 ${color}`} />
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
                        </div>
                        {resumoLoading ? (
                            <Skeleton className="h-6 w-16" />
                        ) : (
                            <p className="text-xl font-bold tabular-nums">{value}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Por responsável */}
            {(resumo?.por_responsavel?.length ?? 0) > 0 && (
                <div className="rounded-sm border border-border bg-card p-4 space-y-3">
                    <div className="flex items-center gap-2">
                        <UserCircle className="size-4 text-primary" />
                        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">Por responsável</p>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        {(resumo?.por_responsavel ?? []).map((r) => (
                            <div key={r.responsavel_nome} className="rounded-sm border border-border bg-muted/20 px-3 py-2 space-y-0.5">
                                <p className={`text-xs font-semibold truncate ${r.responsavel_usuario_id ? "text-foreground" : "text-muted-foreground italic"}`}>
                                    {r.responsavel_nome}
                                </p>
                                <div className="flex items-center justify-between">
                                    <span className="text-[11px] text-muted-foreground">{r.total} solicitação(ões)</span>
                                    <span className="text-[11px] font-medium text-green-700 tabular-nums">{formatBRL(r.valor_estimado)}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <Separator />

            {/* Filtros */}
            <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-1">
                    <Label className="text-xs">Status</Label>
                    <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                        <SelectTrigger className="h-8 text-xs w-36"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="TODOS">Todos</SelectItem>
                            {STATUS_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-xs">Pagamento</Label>
                    <Select value={pgtoFiltro} onValueChange={setPgtoFiltro}>
                        <SelectTrigger className="h-8 text-xs w-36"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="TODOS">Todos</SelectItem>
                            <SelectItem value="PENDENTE">Pendente</SelectItem>
                            <SelectItem value="PAGO">Pago</SelectItem>
                            <SelectItem value="EXPIRADO">Expirado</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-xs">Data início</Label>
                    <Input type="date" value={dataInicio} onChange={(e) => setDataInicio(e.target.value)} className="h-8 text-xs w-36" />
                </div>
                <div className="space-y-1">
                    <Label className="text-xs">Data fim</Label>
                    <Input type="date" value={dataFim} onChange={(e) => setDataFim(e.target.value)} className="h-8 text-xs w-36" />
                </div>
                <div className="space-y-1 ml-auto">
                    <Label className="text-xs opacity-0">x</Label>
                    <Button
                        variant={ordenarPrioridade ? "default" : "outline"}
                        size="sm"
                        className="h-8 text-xs gap-1.5"
                        onClick={() => setOrdenarPrioridade((v) => !v)}
                    >
                        <ArrowUpDown className="size-3.5" />
                        {ordenarPrioridade ? "Ordenando por prioridade" : "Ordenar por prioridade"}
                    </Button>
                </div>
            </div>

            {/* Tabela */}
            <div className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-border bg-muted/30">
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        {isLoading ? "Carregando..." : `${itens.length} solicitação(ões)`}
                    </p>
                </div>

                {isLoading ? (
                    <div className="divide-y divide-border">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="flex items-center gap-4 px-5 py-3">
                                <Skeleton className="h-3.5 w-32" /><Skeleton className="h-3.5 w-24" /><Skeleton className="h-3.5 w-20 ml-auto" />
                            </div>
                        ))}
                    </div>
                ) : itens.length === 0 ? (
                    <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                        Nenhuma solicitação encontrada para os filtros aplicados.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b border-border bg-muted/20">
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Prioridade</th>
                                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Data</th>
                                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Tenant</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Créditos</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Valor</th>
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Pagamento</th>
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Status</th>
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Alterar status</th>
                                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Responsável</th>
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Follow-up</th>
                                    <th className="text-center px-4 py-2.5 font-semibold text-muted-foreground">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {itens.map((item) => {
                                    const sCfg = STATUS_CONFIG[item.status] ?? STATUS_CONFIG.ABERTA;
                                    const pCfg = PGTO_CONFIG[item.status_pagamento ?? ""] ?? PGTO_CONFIG.PENDENTE;
                                    return (
                                        <tr key={item.id} className={`hover:bg-muted/20 transition-colors ${item.prioridade >= 80 ? "bg-red-500/5" : ""}`}>
                                            <td className="px-4 py-2.5 text-center">
                                                <PrioridadeBadge score={item.prioridade} />
                                            </td>
                                            <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                                                {format(new Date(item.created_at), "dd/MM/yy HH:mm", { locale: ptBR })}
                                            </td>
                                            <td className="px-4 py-2.5">
                                                <span className="font-medium text-foreground">{item.tenant_nome}</span>
                                                <span className="ml-1.5 font-mono text-[10px] text-muted-foreground">{item.tenant_id.slice(0, 8)}…</span>
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums font-medium">{item.quantidade_creditos ?? "—"}</td>
                                            <td className="px-4 py-2.5 text-right tabular-nums text-green-700">{formatBRL(item.valor_estimado)}</td>
                                            <td className="px-4 py-2.5 text-center">
                                                <Badge variant="outline" className={`text-[10px] ${pCfg.className}`}>{pCfg.label}</Badge>
                                            </td>
                                            <td className="px-4 py-2.5 text-center">
                                                <Badge variant="outline" className={`text-[10px] ${sCfg.className}`}>{sCfg.label}</Badge>
                                            </td>
                                            <td className="px-4 py-2.5 text-center">
                                                <Select value={item.status} onValueChange={(v) => handleStatusChange(item.id, v)} disabled={updateMutation.isPending}>
                                                    <SelectTrigger className="h-7 text-[11px] w-32 mx-auto"><SelectValue /></SelectTrigger>
                                                    <SelectContent>
                                                        {STATUS_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                                                    </SelectContent>
                                                </Select>
                                            </td>
                                            <td className="px-4 py-2.5">
                                                <button onClick={() => openRespDialog(item)} className="flex items-center gap-1.5 text-left group">
                                                    <UserCircle className={`size-3.5 shrink-0 ${item.responsavel_nome ? "text-primary" : "text-muted-foreground"}`} />
                                                    <span className={`truncate max-w-[100px] group-hover:underline ${item.responsavel_nome ? "text-foreground font-medium" : "text-muted-foreground italic"}`}>
                                                        {item.responsavel_nome ?? "Sem responsável"}
                                                    </span>
                                                </button>
                                            </td>
                                            <td className="px-4 py-2.5 text-center">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    className={`h-7 px-2 text-[10px] ${item.proximo_followup_em ? "text-purple-600 bg-purple-500/10 hover:bg-purple-500/20" : "text-muted-foreground"}`}
                                                    onClick={() => openFollowupDialog(item)}
                                                >
                                                    <CalendarClock className="size-3.5 mr-1" />
                                                    {item.proximo_followup_em ? format(parseISO(item.proximo_followup_em), "dd/MM HH:mm") : "Agendar"}
                                                </Button>
                                            </td>
                                            <td className="px-4 py-2.5">
                                                <div className="flex items-center justify-center gap-0.5">
                                                    {item.crm_sync_status === "ENVIADO" ? (
                                                        <span className="flex items-center gap-1 text-[10px] text-green-700 font-medium px-1.5">
                                                            <CheckCheck className="size-3" /> CRM
                                                        </span>
                                                    ) : (
                                                        <Button size="icon" variant="ghost"
                                                            className={`size-7 ${item.crm_sync_status === "ERRO" ? "text-destructive" : "text-muted-foreground"} hover:text-primary`}
                                                            aria-label="Enviar para CRM"
                                                            title="Enviar para CRM"
                                                            disabled={crmMutation.isPending}
                                                            onClick={() => crmMutation.mutate(item.id)}>
                                                            <Send className="size-3.5" />
                                                        </Button>
                                                    )}
                                                    <Button size="icon" variant="ghost"
                                                        className={`size-7 ${item.observacao_comercial ? "text-primary" : "text-muted-foreground"} hover:text-primary`}
                                                        aria-label="Anotação" onClick={() => openObsDialog(item)}>
                                                        <MessageSquare className="size-3.5" />
                                                    </Button>
                                                    <Button size="icon" variant="ghost"
                                                        className="size-7 text-muted-foreground hover:text-primary"
                                                        aria-label="Histórico"
                                                        onClick={() => setHistDialog({ id: item.id, tenantNome: item.tenant_nome })}>
                                                        <History className="size-3.5" />
                                                    </Button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Confirmação de troca de status */}
            <AlertDialog open={!!pendingChange} onOpenChange={(open) => { if (!open) setPendingChange(null); }}>
                <AlertDialogContent className="w-[calc(100vw-1rem)] sm:max-w-md">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Confirmar alteração de status</AlertDialogTitle>
                        <AlertDialogDescription>
                            Deseja alterar o status para{" "}
                            <strong>{STATUS_CONFIG[pendingChange?.novoStatus ?? ""]?.label ?? pendingChange?.novoStatus}</strong>?
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction onClick={confirmChange} disabled={updateMutation.isPending}>
                            {updateMutation.isPending && <RefreshCw className="size-3.5 animate-spin mr-1.5" />}
                            Confirmar
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/* Dialog de observação */}
            <Dialog open={!!obsDialog} onOpenChange={(open) => { if (!open) setObsDialog(null); }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <MessageSquare className="size-4 text-primary" />
                            Anotação comercial
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-2 py-2">
                        <Label className="text-xs text-muted-foreground">Observação interna sobre esta solicitação</Label>
                        <Textarea value={obsText} onChange={(e) => setObsText(e.target.value)}
                            placeholder="Ex: Cliente pediu contato na próxima semana."
                            className="min-h-[100px] text-sm resize-none" maxLength={1000} />
                        <p className="text-[10px] text-muted-foreground text-right">{obsText.length}/1.000</p>
                    </div>
                    <DialogFooter>
                        <DialogClose asChild><Button variant="outline" size="sm">Cancelar</Button></DialogClose>
                        <Button size="sm" onClick={saveObs} disabled={updateMutation.isPending}>
                            {updateMutation.isPending && <RefreshCw className="size-3.5 animate-spin mr-1.5" />}
                            Salvar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog de responsável */}
            <Dialog open={!!respDialog} onOpenChange={(open) => { if (!open) setRespDialog(null); }}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <UserCircle className="size-4 text-primary" />
                            Responsável comercial
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-2 py-2">
                        <Label className="text-xs text-muted-foreground">Selecione o responsável por esta solicitação</Label>
                        <Select value={respSelecionado} onValueChange={setRespSelecionado}>
                            <SelectTrigger className="text-sm"><SelectValue placeholder="Selecionar..." /></SelectTrigger>
                            <SelectContent>
                                <SelectItem value="NENHUM">
                                    <span className="flex items-center gap-2 text-muted-foreground italic">
                                        <X className="size-3.5" /> Sem responsável
                                    </span>
                                </SelectItem>
                                {adminUsers.map((u) => <SelectItem key={u.id} value={u.id}>{u.nome}</SelectItem>)}
                            </SelectContent>
                        </Select>
                    </div>
                    <DialogFooter>
                        <DialogClose asChild><Button variant="outline" size="sm">Cancelar</Button></DialogClose>
                        <Button size="sm" onClick={saveResp} disabled={respMutation.isPending}>
                            {respMutation.isPending && <RefreshCw className="size-3.5 animate-spin mr-1.5" />}
                            Salvar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog de follow-up */}
            <Dialog open={!!followupDialog} onOpenChange={(open) => { if (!open) setFollowupDialog(null); }}>
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <CalendarClock className="size-4 text-purple-600" />
                            Agendar Follow-up
                        </DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 py-2">
                        <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">Data e Hora do Contato</Label>
                            <Input
                                type="datetime-local"
                                value={followupDataStr}
                                onChange={(e) => setFollowupDataStr(e.target.value)}
                                className="text-sm"
                            />
                        </div>
                        <div className="space-y-1">
                            <Label className="text-xs text-muted-foreground">Observação para o follow-up</Label>
                            <Textarea
                                value={followupObsStr}
                                onChange={(e) => setFollowupObsStr(e.target.value)}
                                placeholder="Ex: Ligar para verificar se aprovou proposta..."
                                className="min-h-[80px] text-sm resize-none"
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button
                            variant="ghost"
                            size="sm"
                            className="mr-auto text-destructive hover:text-destructive"
                            onClick={() => {
                                setFollowupDataStr("");
                                setFollowupObsStr("");
                            }}
                        >
                            Limpar
                        </Button>
                        <DialogClose asChild><Button variant="outline" size="sm">Cancelar</Button></DialogClose>
                        <Button size="sm" onClick={saveFollowup} disabled={followupMutation.isPending}>
                            {followupMutation.isPending && <RefreshCw className="size-3.5 animate-spin mr-1.5" />}
                            Salvar
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Dialog de histórico */}
            <Dialog open={!!histDialog} onOpenChange={(open) => { if (!open) setHistDialog(null); }}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            <History className="size-4 text-primary" />
                            Histórico — {histDialog?.tenantNome}
                        </DialogTitle>
                    </DialogHeader>
                    <div className="py-2 max-h-[400px] overflow-y-auto">
                        {histLoading ? (
                            <div className="space-y-3">
                                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
                            </div>
                        ) : historico.length === 0 ? (
                            <p className="text-sm text-muted-foreground text-center py-6">Nenhum evento registrado.</p>
                        ) : (
                            <ol className="relative border-l border-border ml-3 space-y-5">
                                {historico.map((h) => (
                                    <li key={h.id} className="ml-4">
                                        <span className="absolute -left-1.5 mt-1 size-3 rounded-full border border-border bg-muted" />
                                        <div className="space-y-0.5">
                                            <EventoLabel tipo={h.tipo_evento} />
                                            <p className="text-[10px] text-muted-foreground">
                                                {format(new Date(h.created_at), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                                            </p>
                                            {(h.valor_anterior !== null || h.valor_novo !== null) && (
                                                <p className="text-xs text-muted-foreground">
                                                    {h.valor_anterior
                                                        ? <><span className="line-through opacity-60">{h.valor_anterior}</span>{" → "}</>
                                                        : null}
                                                    <span className="font-medium text-foreground">{h.valor_novo ?? "—"}</span>
                                                </p>
                                            )}
                                            {h.observacao && <p className="text-xs text-muted-foreground italic">{h.observacao}</p>}
                                        </div>
                                    </li>
                                ))}
                            </ol>
                        )}
                    </div>
                    <DialogFooter>
                        <DialogClose asChild><Button variant="outline" size="sm">Fechar</Button></DialogClose>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
