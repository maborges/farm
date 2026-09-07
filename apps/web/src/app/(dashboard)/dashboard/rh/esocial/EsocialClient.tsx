"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { FileText, Plus, CheckCircle, XCircle, Clock, AlertCircle, RefreshCw, FileCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export interface EsocialEvento {
    id: string;
    colaborador_id?: string;
    colaborador_nome?: string;
    tipo_evento: string;
    status: string;
    numero_recibo?: string;
    codigo_erro?: string;
    descricao_erro?: string;
    periodo_apuracao?: string;
    enviado_em?: string;
    created_at: string;
}

const TIPOS_EVENTO = [
    { value: "S-2200", label: "S-2200 — Admissão / Cadastro Vínculo" },
    { value: "S-2300", label: "S-2300 — Trabalhador Sem Vínculo" },
    { value: "S-2299", label: "S-2299 — Desligamento" },
    { value: "S-1200", label: "S-1200 — Remuneração Mensal" },
    { value: "S-2400", label: "S-2400 — Cadastro de Beneficiário" },
];

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    PENDENTE:    { label: "Pendente",    color: "bg-yellow-100 text-yellow-700 border-yellow-200", icon: <Clock size={12} /> },
    ENVIADO:     { label: "Enviado",     color: "bg-green-100 text-green-700 border-green-200",   icon: <CheckCircle size={12} /> },
    ERRO:        { label: "Erro",        color: "bg-red-100 text-red-700 border-red-200",         icon: <XCircle size={12} /> },
    PROCESSANDO: { label: "Processando", color: "bg-blue-100 text-blue-700 border-blue-200",      icon: <RefreshCw size={12} /> },
};

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground border-border", icon: null };
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${cfg.color}`}>
            {cfg.icon} {cfg.label}
        </span>
    );
}

export function EsocialClient({ initialData }: { initialData: EsocialEvento[] }) {
    const qc = useQueryClient();
    const [filtroTipo, setFiltroTipo] = useState<string>("todos");
    const [filtroStatus, setFiltroStatus] = useState<string>("todos");
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState({ colaborador_nome: "", tipo_evento: "", periodo_apuracao: "" });

    const qs = [
        filtroTipo !== "todos" ? `tipo_evento=${filtroTipo}` : "",
        filtroStatus !== "todos" ? `status=${filtroStatus}` : "",
    ].filter(Boolean).join("&");

    const { data: eventos = [], isLoading } = useQuery<EsocialEvento[]>({
        queryKey: ["rh", "esocial", filtroTipo, filtroStatus],
        queryFn: () => apiFetch(`/rh/esocial/eventos${qs ? `?${qs}` : ""}`),
        initialData: filtroTipo === "todos" && filtroStatus === "todos" ? initialData : undefined,
    });

    const criarMut = useMutation({
        mutationFn: (d: typeof form) => apiFetch("/rh/esocial/eventos", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["rh", "esocial"] });
            setShowForm(false);
            setForm({ colaborador_nome: "", tipo_evento: "", periodo_apuracao: "" });
            toast.success("Evento registrado.");
        },
        onError: (e: any) => toast.error(e.message || "Erro ao registrar."),
    });

    const totais = {
        total: eventos.length,
        pendentes: eventos.filter(e => e.status === "PENDENTE").length,
        enviados: eventos.filter(e => e.status === "ENVIADO").length,
        erros: eventos.filter(e => e.status === "ERRO").length,
    };

    function formatDate(iso?: string) {
        if (!iso) return "—";
        return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
    }

    return (
        <div className="flex flex-col gap-6 p-6">
            <PageHeader
                title="eSocial"
                description="Histórico e controle de envio de eventos trabalhistas."
                icon={<FileCheck className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Pessoas & RH", href: "/dashboard/rh" },
                    { label: "eSocial" }
                ]}
                actions={
                    <Button
                        size="sm"
                        onClick={() => setShowForm(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                        variant="outline"
                    >
                        <Plus className="size-4 mr-1.5" /> Registrar Evento
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                    { label: "Total", value: totais.total, color: "text-foreground", icon: <FileText className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                    { label: "Pendentes", value: totais.pendentes, color: "text-yellow-600", icon: <Clock className="size-4 text-yellow-500 opacity-50" />, border: "border-l-yellow-500/60" },
                    { label: "Enviados", value: totais.enviados, color: "text-green-600", icon: <CheckCircle className="size-4 text-green-500 opacity-50" />, border: "border-l-green-500/60" },
                    { label: "Erros", value: totais.erros, color: "text-red-600", icon: <XCircle className="size-4 text-red-500 opacity-50" />, border: "border-l-red-500/60" },
                ].map(kpi => (
                    <Card key={kpi.label} className={`rounded-sm border-l-[3px] ${kpi.border} shadow-sm transition-all hover:shadow-md`}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{kpi.label}</CardTitle>
                            {kpi.icon}
                        </CardHeader>
                        <CardContent>
                            <p className={`text-2xl font-black tabular-nums ${kpi.color}`}>{kpi.value}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Filtros */}
            <div className="flex gap-3 flex-wrap">
                <Select value={filtroTipo} onValueChange={setFiltroTipo}>
                    <SelectTrigger className="w-[220px] h-8 text-sm">
                        <SelectValue placeholder="Tipo de evento" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="todos">Todos os tipos</SelectItem>
                        {TIPOS_EVENTO.map(t => (
                            <SelectItem key={t.value} value={t.value}>{t.value}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
                <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                    <SelectTrigger className="w-[160px] h-8 text-sm">
                        <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="todos">Todos os status</SelectItem>
                        {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                            <SelectItem key={k} value={k}>{v.label}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Tabela */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Eventos</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="p-4 space-y-2">
                            {[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}
                        </div>
                    ) : eventos.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10">
                            <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                <FileCheck className="size-6 text-primary" />
                            </div>
                            <h3 className="text-lg font-semibold mb-1">Nenhum evento encontrado</h3>
                            <p className="text-sm text-muted-foreground max-w-sm mb-5">
                                Não há eventos eSocial registrados.
                            </p>
                            <Button size="sm" variant="outline" onClick={() => setShowForm(true)} className="rounded-sm">
                                <Plus className="size-4 mr-1.5" /> Registrar evento
                            </Button>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Evento</TableHead>
                                    <TableHead>Colaborador</TableHead>
                                    <TableHead>Período</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Recibo</TableHead>
                                    <TableHead>Enviado em</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {eventos.map(ev => (
                                    <TableRow key={ev.id}>
                                        <TableCell>
                                            <span className="font-mono text-xs font-semibold">{ev.tipo_evento}</span>
                                        </TableCell>
                                        <TableCell className="text-sm">{ev.colaborador_nome ?? "—"}</TableCell>
                                        <TableCell className="text-sm tabular-nums">{ev.periodo_apuracao ?? "—"}</TableCell>
                                        <TableCell>
                                            <StatusBadge status={ev.status} />
                                            {ev.status === "ERRO" && ev.descricao_erro && (
                                                <p className="text-xs text-red-600 mt-0.5 max-w-[200px] truncate">{ev.descricao_erro}</p>
                                            )}
                                        </TableCell>
                                        <TableCell className="font-mono text-xs">{ev.numero_recibo ?? "—"}</TableCell>
                                        <TableCell className="text-xs text-muted-foreground">{formatDate(ev.enviado_em)}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Dialog registrar */}
            <Dialog open={showForm} onOpenChange={o => { if (!o) { setShowForm(false); setForm({ colaborador_nome: "", tipo_evento: "", periodo_apuracao: "" }); } }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Registrar Evento eSocial</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Tipo de Evento <span className="text-destructive">*</span></Label>
                            <Select value={form.tipo_evento} onValueChange={v => setForm(f => ({ ...f, tipo_evento: v }))}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Selecione o evento" />
                                </SelectTrigger>
                                <SelectContent>
                                    {TIPOS_EVENTO.map(t => (
                                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-2">
                            <Label>Colaborador</Label>
                            <Input
                                placeholder="Nome do colaborador"
                                value={form.colaborador_nome}
                                onChange={e => setForm(f => ({ ...f, colaborador_nome: e.target.value }))}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Período de Apuração</Label>
                            <Input
                                placeholder="YYYY-MM (ex: 2026-04)"
                                value={form.periodo_apuracao}
                                onChange={e => setForm(f => ({ ...f, periodo_apuracao: e.target.value }))}
                                maxLength={7}
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
                        <Button
                            onClick={() => {
                                if (!form.tipo_evento) { toast.error("Selecione o tipo de evento."); return; }
                                criarMut.mutate(form);
                            }}
                            disabled={criarMut.isPending}
                        >
                            {criarMut.isPending ? "Registrando..." : "Registrar Evento"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
