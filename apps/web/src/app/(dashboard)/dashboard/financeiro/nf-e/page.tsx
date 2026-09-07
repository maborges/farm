"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { FileText, Plus, CheckCircle, XCircle, Clock, AlertCircle, Edit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface NotaFiscal {
    id: string;
    tipo: string;
    numero?: number;
    serie: string;
    emitente_nome: string;
    destinatario_nome: string;
    destinatario_uf?: string;
    valor_total: number;
    valor_icms: number;
    status_sefaz: string;
    chave_acesso?: string;
    numero_protocolo?: string;
    descricao_produto?: string;
    data_emissao: string;
    data_autorizacao?: string;
}

interface Dashboard {
    total: number;
    autorizadas: number;
    canceladas: number;
    em_digitacao: number;
    valor_total_autorizado: number;
}

const TIPOS = ["NFP-e", "NF-e", "NFC-e"];

const STATUS_CFG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    em_digitacao: { label: "Em Digitação", color: "bg-slate-100 text-slate-700 border-slate-200",   icon: <Edit2 size={11} /> },
    assinada:     { label: "Assinada",     color: "bg-blue-100 text-blue-700 border-blue-200",      icon: <FileText size={11} /> },
    transmitida:  { label: "Transmitida",  color: "bg-yellow-100 text-yellow-700 border-yellow-200", icon: <Clock size={11} /> },
    autorizada:   { label: "Autorizada",   color: "bg-green-100 text-green-700 border-green-200",   icon: <CheckCircle size={11} /> },
    cancelada:    { label: "Cancelada",    color: "bg-red-100 text-red-700 border-red-200",         icon: <XCircle size={11} /> },
    denegada:     { label: "Denegada",     color: "bg-orange-100 text-orange-700 border-orange-200", icon: <XCircle size={11} /> },
    inutilizada:  { label: "Inutilizada",  color: "bg-muted text-muted-foreground border-border",   icon: null },
};

function StatusBadge({ status }: { status: string }) {
    const cfg = STATUS_CFG[status] ?? { label: status, color: "bg-muted text-muted-foreground border-border", icon: null };
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${cfg.color}`}>
            {cfg.icon} {cfg.label}
        </span>
    );
}

const EMPTY_FORM = {
    tipo: "NFP-e", numero: "", serie: "1",
    emitente_nome: "", emitente_cpf_cnpj: "",
    destinatario_nome: "", destinatario_documento: "", destinatario_uf: "",
    valor_produtos: "", valor_icms: "", valor_total: "",
    descricao_produto: "", ncm: "", quantidade: "", unidade: "SC",
};

export default function NfePage() {
    const qc = useQueryClient();
    const [filtroTipo, setFiltroTipo] = useState("todos");
    const [filtroStatus, setFiltroStatus] = useState("todos");
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState(EMPTY_FORM);

    const qs = [
        filtroTipo !== "todos" ? `tipo=${encodeURIComponent(filtroTipo)}` : "",
        filtroStatus !== "todos" ? `status_sefaz=${filtroStatus}` : "",
    ].filter(Boolean).join("&");

    const { data: dashboard } = useQuery<Dashboard>({
        queryKey: ["fin", "nfe", "dashboard"],
        queryFn: () => apiFetch("/financeiro/notas-fiscais/dashboard"),
    });

    const { data: notas = [], isLoading } = useQuery<NotaFiscal[]>({
        queryKey: ["fin", "nfe", filtroTipo, filtroStatus],
        queryFn: async () => {
            const res = await apiFetch<{ items: NotaFiscal[], total: number }>(`/financeiro/notas-fiscais${qs ? `?${qs}` : ""}`);
            return res.items || [];
        },
    });

    const criarMut = useMutation({
        mutationFn: (d: Record<string, any>) => apiFetch("/financeiro/notas-fiscais", { method: "POST", body: JSON.stringify(d) }),
        onSuccess: () => {
            qc.invalidateQueries({ queryKey: ["fin", "nfe"] });
            setShowForm(false);
            setForm(EMPTY_FORM);
            toast.success("Nota fiscal registrada.");
        },
        onError: (e: any) => toast.error(e.message || "Erro ao registrar."),
    });

    function salvar() {
        if (!form.emitente_nome || !form.destinatario_nome || !form.valor_total) {
            toast.error("Preencha emitente, destinatário e valor total."); return;
        }
        const payload: Record<string, any> = {
            tipo: form.tipo, serie: form.serie,
            emitente_nome: form.emitente_nome,
            destinatario_nome: form.destinatario_nome,
            valor_total: parseFloat(form.valor_total) || 0,
            valor_produtos: parseFloat(form.valor_produtos) || 0,
            valor_icms: parseFloat(form.valor_icms) || 0,
        };
        if (form.numero) payload.numero = parseInt(form.numero);
        if (form.emitente_cpf_cnpj) payload.emitente_cpf_cnpj = form.emitente_cpf_cnpj;
        if (form.destinatario_documento) payload.destinatario_documento = form.destinatario_documento;
        if (form.destinatario_uf) payload.destinatario_uf = form.destinatario_uf;
        if (form.descricao_produto) payload.descricao_produto = form.descricao_produto;
        if (form.ncm) payload.ncm = form.ncm;
        if (form.quantidade) payload.quantidade = parseFloat(form.quantidade);
        if (form.unidade) payload.unidade = form.unidade;
        criarMut.mutate(payload);
    }

    function fmt(v: number) {
        return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
    }
    function fmtDate(iso?: string) {
        if (!iso) return "—";
        return new Date(iso).toLocaleDateString("pt-BR");
    }

    return (
        <div className="flex flex-col gap-6 p-6">
            <PageHeader
                title="NF-e / NFP-e"
                description="Gestão de notas fiscais eletrônicas e de produtor rural."
                icon={<FileText className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Financeiro", href: "/dashboard/financeiro" },
                    { label: "Fiscal e Contábil" },
                    { label: "Notas Fiscais" }
                ]}
                actions={
                    <Button
                        size="sm"
                        onClick={() => setShowForm(true)}
                        className="rounded-sm border-primary text-primary hover:bg-primary/5 font-bold"
                        variant="outline"
                    >
                        <Plus className="size-4 mr-1.5" /> Nova Nota
                    </Button>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                    { label: "Total", value: dashboard?.total ?? 0, sub: null, icon: <FileText className="size-4 text-muted-foreground opacity-50" />, border: "border-l-primary/60" },
                    { label: "Autorizadas", value: dashboard?.autorizadas ?? 0, sub: dashboard ? fmt(dashboard.valor_total_autorizado) : null, icon: <CheckCircle className="size-4 text-green-500 opacity-50" />, border: "border-l-green-500/60" },
                    { label: "Em Digitação", value: dashboard?.em_digitacao ?? 0, sub: null, icon: <Clock className="size-4 text-yellow-500 opacity-50" />, border: "border-l-yellow-500/60" },
                    { label: "Canceladas", value: dashboard?.canceladas ?? 0, sub: null, icon: <XCircle className="size-4 text-red-500 opacity-50" />, border: "border-l-red-500/60" },
                ].map(kpi => (
                    <Card key={kpi.label} className={`rounded-sm border-l-[3px] ${kpi.border} shadow-sm transition-all hover:shadow-md`}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-[10px] text-muted-foreground uppercase tracking-wider font-bold">{kpi.label}</CardTitle>
                            {kpi.icon}
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-black tabular-nums">{kpi.value}</div>
                            {kpi.sub && <p className="text-xs text-muted-foreground mt-1 font-medium">{kpi.sub}</p>}
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Filtros */}
            <div className="flex gap-3 flex-wrap">
                <Select value={filtroTipo} onValueChange={setFiltroTipo}>
                    <SelectTrigger className="w-[140px] h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="todos">Todos os tipos</SelectItem>
                        {TIPOS.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                    </SelectContent>
                </Select>
                <Select value={filtroStatus} onValueChange={setFiltroStatus}>
                    <SelectTrigger className="w-[160px] h-8 text-sm">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="todos">Todos os status</SelectItem>
                        {Object.entries(STATUS_CFG).map(([k, v]) => (
                            <SelectItem key={k} value={k}>{v.label}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Tabela */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">Notas Fiscais</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="p-4 space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
                    ) : notas.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-muted/10">
                            <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                <FileText className="size-6 text-primary" />
                            </div>
                            <h3 className="text-lg font-semibold mb-1">Nenhuma nota fiscal encontrada</h3>
                            <p className="text-sm text-muted-foreground max-w-sm mb-5">
                                Não há notas fiscais registradas ou os filtros atuais não retornaram resultados.
                            </p>
                            <Button size="sm" variant="outline" onClick={() => setShowForm(true)} className="rounded-sm">
                                <Plus className="size-4 mr-1.5" /> Registrar nota
                            </Button>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Nº / Tipo</TableHead>
                                    <TableHead>Emitente</TableHead>
                                    <TableHead>Destinatário</TableHead>
                                    <TableHead>Produto</TableHead>
                                    <TableHead className="text-right">Valor Total</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Emissão</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {notas.map(n => (
                                    <TableRow key={n.id}>
                                        <TableCell>
                                            <div className="font-mono text-xs font-semibold">{n.tipo}</div>
                                            {n.numero && <div className="text-xs text-muted-foreground">Nº {n.numero} / Série {n.serie}</div>}
                                        </TableCell>
                                        <TableCell className="text-sm max-w-[140px] truncate">{n.emitente_nome}</TableCell>
                                        <TableCell className="text-sm max-w-[140px] truncate">
                                            {n.destinatario_nome}
                                            {n.destinatario_uf && <span className="text-muted-foreground ml-1">({n.destinatario_uf})</span>}
                                        </TableCell>
                                        <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">{n.descricao_produto ?? "—"}</TableCell>
                                        <TableCell className="text-right font-semibold tabular-nums text-sm">{fmt(n.valor_total)}</TableCell>
                                        <TableCell><StatusBadge status={n.status_sefaz} /></TableCell>
                                        <TableCell className="text-xs text-muted-foreground">{fmtDate(n.data_emissao)}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {/* Dialog nova nota */}
            <Dialog open={showForm} onOpenChange={o => { if (!o) { setShowForm(false); setForm(EMPTY_FORM); } }}>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Registrar Nota Fiscal</DialogTitle>
                    </DialogHeader>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Tipo <span className="text-destructive">*</span></Label>
                            <Select value={form.tipo} onValueChange={v => setForm(f => ({ ...f, tipo: v }))}>
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>{TIPOS.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                            </Select>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <div className="space-y-2">
                                <Label>Número</Label>
                                <Input type="number" placeholder="001" value={form.numero} onChange={e => setForm(f => ({ ...f, numero: e.target.value }))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Série</Label>
                                <Input placeholder="1" value={form.serie} onChange={e => setForm(f => ({ ...f, serie: e.target.value }))} />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Emitente <span className="text-destructive">*</span></Label>
                            <Input placeholder="Nome do emitente" value={form.emitente_nome} onChange={e => setForm(f => ({ ...f, emitente_nome: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>CPF/CNPJ Emitente</Label>
                            <Input placeholder="000.000.000-00" value={form.emitente_cpf_cnpj} onChange={e => setForm(f => ({ ...f, emitente_cpf_cnpj: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Destinatário <span className="text-destructive">*</span></Label>
                            <Input placeholder="Nome do destinatário" value={form.destinatario_nome} onChange={e => setForm(f => ({ ...f, destinatario_nome: e.target.value }))} />
                        </div>
                        <div className="grid grid-cols-3 gap-2">
                            <div className="col-span-2 space-y-2">
                                <Label>CPF/CNPJ Dest.</Label>
                                <Input placeholder="00.000.000/0000-00" value={form.destinatario_documento} onChange={e => setForm(f => ({ ...f, destinatario_documento: e.target.value }))} />
                            </div>
                            <div className="space-y-2">
                                <Label>UF</Label>
                                <Input placeholder="SP" maxLength={2} value={form.destinatario_uf} onChange={e => setForm(f => ({ ...f, destinatario_uf: e.target.value.toUpperCase() }))} />
                            </div>
                        </div>
                        <div className="col-span-2 space-y-2">
                            <Label>Produto / Descrição</Label>
                            <Input placeholder="ex: Soja em grão" value={form.descricao_produto} onChange={e => setForm(f => ({ ...f, descricao_produto: e.target.value }))} />
                        </div>
                        <div className="grid grid-cols-3 gap-2 col-span-2">
                            <div className="space-y-2">
                                <Label>NCM</Label>
                                <Input placeholder="12010090" maxLength={8} value={form.ncm} onChange={e => setForm(f => ({ ...f, ncm: e.target.value }))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Qtd</Label>
                                <Input type="number" placeholder="0.00" value={form.quantidade} onChange={e => setForm(f => ({ ...f, quantidade: e.target.value }))} />
                            </div>
                            <div className="space-y-2">
                                <Label>Unidade</Label>
                                <Input placeholder="SC" maxLength={6} value={form.unidade} onChange={e => setForm(f => ({ ...f, unidade: e.target.value }))} />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Valor Produtos (R$)</Label>
                            <Input type="number" placeholder="0,00" value={form.valor_produtos} onChange={e => setForm(f => ({ ...f, valor_produtos: e.target.value }))} />
                        </div>
                        <div className="space-y-2">
                            <Label>Valor ICMS (R$)</Label>
                            <Input type="number" placeholder="0,00" value={form.valor_icms} onChange={e => setForm(f => ({ ...f, valor_icms: e.target.value }))} />
                        </div>
                        <div className="col-span-2 space-y-2">
                            <Label>Valor Total (R$) <span className="text-destructive">*</span></Label>
                            <Input type="number" placeholder="0,00" value={form.valor_total} onChange={e => setForm(f => ({ ...f, valor_total: e.target.value }))} />
                        </div>
                    </div>
                    <DialogFooter className="mt-2">
                        <Button variant="outline" onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}>Cancelar</Button>
                        <Button onClick={salvar} disabled={criarMut.isPending}>
                            {criarMut.isPending ? "Salvando..." : "Registrar Nota"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
