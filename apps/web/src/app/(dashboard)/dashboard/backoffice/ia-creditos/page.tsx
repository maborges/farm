"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BrainCircuit, TrendingUp, DollarSign, Coins, PackageCheck, Download, BarChart3, Trophy } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { apiFetch } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { getApiBaseUrl } from "@/lib/runtime-config";

interface AuditoriaItem {
    solicitacao_id: string;
    tenant_id: string;
    quantidade_creditos: number | null;
    valor_total: number | null;
    custo_estimado: number | null;
    margem_estimada: number | null;
    margem_percentual: number | null;
    status_pagamento: string | null;
    status: string;
    created_at: string;
}

interface AuditoriaTotais {
    receita_total: number;
    custo_total: number;
    margem_total: number;
    total_vendas: number;
    total_creditos: number;
}

interface AuditoriaResponse {
    itens: AuditoriaItem[];
    totais: AuditoriaTotais;
}

interface TopTenantItem {
    tenant_id: string;
    tenant_nome: string;
    receita_total: number;
    creditos_comprados: number;
}

interface ResumoExecutivoResponse {
    receita_total: number;
    custo_total: number;
    margem_total: number;
    margem_percentual_media: number;
    creditos_vendidos: number;
    quantidade_vendas: number;
    ticket_medio: number;
    top_tenants: TopTenantItem[];
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
    PAGO: { label: "Pago", className: "border-emerald-500/30 text-emerald-700 bg-emerald-500/5 dark:bg-emerald-500/20 dark:text-emerald-100 dark:border-emerald-400/30" },
    PENDENTE: { label: "Pendente", className: "border-amber-500/30 text-amber-700 bg-amber-500/5 dark:bg-amber-500/20 dark:text-amber-100 dark:border-amber-400/30" },
    EXPIRADO: { label: "Expirado", className: "border-muted-foreground/30 text-muted-foreground bg-muted dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700" },
};

function formatBRL(v: number | null | undefined): string {
    if (v == null) return "—";
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function buildQueryString(statusPagamento: string, dataInicio: string, dataFim: string) {
    const params = new URLSearchParams();
    if (statusPagamento && statusPagamento !== "TODOS") params.set("status_pagamento", statusPagamento);
    if (dataInicio) params.set("data_inicio", dataInicio);
    if (dataFim) params.set("data_fim", dataFim);
    params.set("limit", "200");
    return params.toString();
}

function buildResumoQueryString(dataInicio: string, dataFim: string) {
    const params = new URLSearchParams();
    if (dataInicio) params.set("data_inicio", dataInicio);
    if (dataFim) params.set("data_fim", dataFim);
    params.set("top_n", "5");
    return params.toString();
}

export default function IACreditsAuditoriaPage() {
    const [statusFiltro, setStatusFiltro] = useState("TODOS");
    const [dataInicio, setDataInicio] = useState("");
    const [dataFim, setDataFim] = useState("");

    const qs = buildQueryString(statusFiltro, dataInicio, dataFim);
    const resumoQs = buildResumoQueryString(dataInicio, dataFim);

    function handleExportCSV() {
        const apiBase = getApiBaseUrl();
        const url = `${apiBase}/backoffice/ia/creditos/auditoria/export.csv?${qs}`;
        window.open(url, "_blank");
    }

    const { data, isLoading } = useQuery<AuditoriaResponse>({
        queryKey: ["ia-auditoria", qs],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/auditoria?${qs}`),
        staleTime: 30_000,
    });

    const { data: resumo, isLoading: resumoLoading } = useQuery<ResumoExecutivoResponse>({
        queryKey: ["ia-resumo-executivo", resumoQs],
        queryFn: () => apiFetch(`/backoffice/ia/creditos/resumo-executivo?${resumoQs}`),
        staleTime: 30_000,
    });

    const totais = data?.totais;
    const itens = data?.itens ?? [];

    return (
        <div className="space-y-6 max-w-5xl">
            {/* Header */}
            <div>
                <h1 className="text-lg font-bold text-foreground flex items-center gap-2">
                    <BrainCircuit className="size-5 text-primary" />
                    Auditoria — Créditos de IA
                </h1>
                <p className="text-sm text-muted-foreground mt-0.5">
                    Vendas, custos e margem dos pacotes de créditos de IA.
                </p>
            </div>

            <Separator />

            {/* Resumo Executivo */}
            <div className="space-y-3">
                <div className="flex items-center gap-2">
                    <BarChart3 className="size-4 text-primary" />
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">Resumo executivo</p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                        { label: "Receita total", value: formatBRL(resumo?.receita_total), icon: DollarSign, color: "text-green-600" },
                        { label: "Margem total", value: formatBRL(resumo?.margem_total), icon: TrendingUp, color: "text-primary" },
                        { label: "Margem média", value: resumo != null ? `${resumo.margem_percentual_media.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%` : "—", icon: PackageCheck, color: "text-primary" },
                        { label: "Ticket médio", value: formatBRL(resumo?.ticket_medio), icon: Coins, color: "text-amber-600" },
                    ].map(({ label, value, icon: Icon, color }) => (
                        <div key={label} className="rounded-sm border border-border bg-card p-4 space-y-2">
                            <div className="flex items-center gap-2">
                                <Icon className={`size-4 ${color}`} />
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
                            </div>
                            {resumoLoading ? (
                                <Skeleton className="h-6 w-24" />
                            ) : (
                                <p className="text-xl font-bold tabular-nums">{value}</p>
                            )}
                        </div>
                    ))}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
                    {/* Métricas de volume */}
                    <div className="rounded-sm border border-border bg-card p-4 space-y-2">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Volume de vendas</p>
                        {resumoLoading ? (
                            <Skeleton className="h-5 w-32" />
                        ) : (
                            <div className="flex items-baseline gap-3">
                                <span className="text-xl font-bold tabular-nums">{(resumo?.quantidade_vendas ?? 0).toLocaleString("pt-BR")}</span>
                                <span className="text-xs text-muted-foreground">vendas</span>
                                <span className="text-xl font-bold tabular-nums ml-2">{(resumo?.creditos_vendidos ?? 0).toLocaleString("pt-BR")}</span>
                                <span className="text-xs text-muted-foreground">créditos</span>
                            </div>
                        )}
                    </div>

                    {/* Top tenants */}
                    <div className="rounded-sm border border-border bg-card p-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <Trophy className="size-3.5 text-amber-500" />
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Top produtores por receita</p>
                        </div>
                        {resumoLoading ? (
                            <div className="space-y-1.5">
                                {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-3.5 w-full" />)}
                            </div>
                        ) : (resumo?.top_tenants ?? []).length === 0 ? (
                            <p className="text-xs text-muted-foreground">Nenhum dado disponível.</p>
                        ) : (
                            <div className="space-y-1">
                                {(resumo?.top_tenants ?? []).map((t, idx) => (
                                    <div key={t.tenant_id} className="flex items-center justify-between text-xs">
                                        <span className="text-muted-foreground font-mono">
                                            <span className="text-foreground font-semibold mr-1">{idx + 1}.</span>
                                            {t.tenant_nome}
                                        </span>
                                        <span className="tabular-nums font-medium text-green-700">{formatBRL(t.receita_total)}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <Separator />

            {/* Totais da auditoria */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                    { label: "Receita total", value: formatBRL(totais?.receita_total), icon: DollarSign, color: "text-green-600" },
                    { label: "Custo estimado", value: formatBRL(totais?.custo_total), icon: TrendingUp, color: "text-destructive" },
                    { label: "Margem estimada", value: formatBRL(totais?.margem_total), icon: PackageCheck, color: "text-primary" },
                    { label: "Créditos vendidos", value: (totais?.total_creditos ?? 0).toLocaleString("pt-BR"), icon: Coins, color: "text-amber-600" },
                ].map(({ label, value, icon: Icon, color }) => (
                    <div key={label} className="rounded-sm border border-border bg-card p-4 space-y-2">
                        <div className="flex items-center gap-2">
                            <Icon className={`size-4 ${color}`} />
                            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
                        </div>
                        {isLoading ? (
                            <Skeleton className="h-6 w-24" />
                        ) : (
                            <p className="text-xl font-bold tabular-nums">{value}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Filtros + Exportar */}
            <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-1">
                    <Label className="text-xs">Status pagamento</Label>
                    <Select value={statusFiltro} onValueChange={setStatusFiltro}>
                        <SelectTrigger className="h-8 text-xs w-36">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="TODOS">Todos</SelectItem>
                            <SelectItem value="PAGO">Pago</SelectItem>
                            <SelectItem value="PENDENTE">Pendente</SelectItem>
                            <SelectItem value="EXPIRADO">Expirado</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div className="space-y-1">
                    <Label className="text-xs">Data início</Label>
                    <Input
                        type="date"
                        value={dataInicio}
                        onChange={(e) => setDataInicio(e.target.value)}
                        className="h-8 text-xs w-36"
                    />
                </div>
                <div className="space-y-1">
                    <Label className="text-xs">Data fim</Label>
                    <Input
                        type="date"
                        value={dataFim}
                        onChange={(e) => setDataFim(e.target.value)}
                        className="h-8 text-xs w-36"
                    />
                </div>
                <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 h-8 text-xs ml-auto"
                    onClick={handleExportCSV}
                    disabled={isLoading}
                >
                    <Download className="size-3.5" />
                    Exportar CSV
                </Button>
            </div>

            {/* Tabela */}
            <div className="rounded-sm border border-border bg-card shadow-sm overflow-hidden">
                <div className="px-5 py-3 border-b border-border bg-muted/30">
                    <p className="text-[11px] font-black uppercase tracking-[0.18em] text-muted-foreground">
                        {isLoading ? "Carregando..." : `${itens.length} registro(s)`}
                    </p>
                </div>

                {isLoading ? (
                    <div className="divide-y divide-border">
                        {Array.from({ length: 5 }).map((_, i) => (
                            <div key={i} className="flex items-center gap-4 px-5 py-3">
                                <Skeleton className="h-3.5 w-32" />
                                <Skeleton className="h-3.5 w-24" />
                                <Skeleton className="h-3.5 w-20 ml-auto" />
                            </div>
                        ))}
                    </div>
                ) : itens.length === 0 ? (
                    <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                        Nenhum registro encontrado para os filtros aplicados.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead>
                                <tr className="border-b border-border bg-muted/20">
                                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Data</th>
                                    <th className="text-left px-4 py-2.5 font-semibold text-muted-foreground">Produtor</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Créditos</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Receita</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Custo</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Margem</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Margem %</th>
                                    <th className="text-right px-4 py-2.5 font-semibold text-muted-foreground">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {itens.map((item) => {
                                    const cfg = STATUS_CONFIG[item.status_pagamento ?? ""] ?? STATUS_CONFIG.PENDENTE;
                                    return (
                                        <tr key={item.solicitacao_id} className="hover:bg-muted/20 transition-colors">
                                            <td className="px-4 py-2.5 text-muted-foreground tabular-nums">
                                                {format(new Date(item.created_at), "dd/MM/yy HH:mm", { locale: ptBR })}
                                            </td>
                                            <td className="px-4 py-2.5 font-mono text-[10px] text-muted-foreground">
                                                {item.tenant_id.slice(0, 8)}…
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                                                {item.quantidade_creditos ?? "—"}
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums text-green-700">
                                                {formatBRL(item.valor_total)}
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums text-destructive">
                                                {formatBRL(item.custo_estimado)}
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums text-primary">
                                                {formatBRL(item.margem_estimada)}
                                            </td>
                                            <td className="px-4 py-2.5 text-right tabular-nums">
                                                {item.margem_percentual != null
                                                    ? `${item.margem_percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`
                                                    : "—"}
                                            </td>
                                            <td className="px-4 py-2.5 text-right">
                                                <Badge variant="outline" className={`text-[10px] ${cfg.className}`}>
                                                    {cfg.label}
                                                </Badge>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
