"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogBody,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    AlertDialog, AlertDialogAction, AlertDialogCancel,
    AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
    AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus, Trash2, TrendingUp, Package, DollarSign, Wheat, Factory, XCircle, Save, AlertTriangle, ClipboardList, Scale } from "lucide-react";
import { toast } from "sonner";

interface Talhao {
    id: string;
    nome: string;
}

interface Romaneio {
    id: string;
    safra_id: string;
    talhao_id: string;
    numero_romaneio: string | null;
    data_colheita: string;
    turno: string | null;
    peso_bruto_kg: number;
    tara_kg: number | null;
    peso_liquido_padrao_kg: number | null;
    sacas_60kg: number | null;
    umidade_pct: number | null;
    impureza_pct: number | null;
    produtividade_sc_ha: number | null;
    preco_saca: number | null;
    receita_total: number | null;
    destino: string | null;
    observacoes: string | null;
}

interface KPIs {
    total_romaneios: number;
    total_sacas: number;
    receita_total: number;
    produtividade_sc_ha: number | null;
}

interface ColheitaPendente {
    tarefa_campo_id: string;
    safra_id: string | null;
    talhao_id: string | null;
    talhao_nome: string | null;
    concluida_em: string | null;
}

interface Props {
    safraId: string;
    talhoes: Talhao[];
    cultura?: string;
    anoSafra?: string;
}

const TURNOS = ["MANHA", "TARDE", "NOITE"];
const DESTINOS = ["ARMAZEM", "COOPERATIVA", "INDUSTRIA", "PROPRIO"];

function fmt(n: number | null | undefined, dec = 2) {
    if (n == null) return "—";
    return n.toLocaleString("pt-BR", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

const createColumns = (
    processar: any,
    setDeleteId: any,
    talhaoMap: any,
    solicitarPesagem: any,
): ColumnDef<Romaneio>[] => [
    {
        id: "data_colheita",
        header: "Data",
        accessorKey: "data_colheita",
        sortable: true,
        cell: (value: string) => (
            <span className="text-sm">
                {new Date(value + "T00:00:00").toLocaleDateString("pt-BR")}
            </span>
        ),
    },
    {
        id: "talhao",
        header: "Talhão",
        accessorKey: "talhao_id",
        sortable: true,
        cell: (value: string) => (
            <span className="text-sm font-medium">
                {talhaoMap[value] ?? value.slice(0, 8)}
            </span>
        ),
    },
    {
        id: "numero_romaneio",
        header: "Nº Romaneio",
        accessorKey: "numero_romaneio",
        sortable: true,
        cell: (value: string | null) => (
            <span className="text-sm text-muted-foreground">
                {value ?? "—"}
            </span>
        ),
    },
    {
        id: "peso_bruto_kg",
        header: "Peso Bruto",
        accessorKey: "peso_bruto_kg",
        sortable: true,
        cell: (value: number) => (
            <div className="text-right text-sm">
                {fmt(value, 0)} kg
            </div>
        ),
    },
    {
        id: "sacas_60kg",
        header: "Sacas",
        accessorKey: "sacas_60kg",
        sortable: true,
        cell: (value: number | null) => (
            <div className="text-right text-sm font-medium">
                {fmt(value)} sc
            </div>
        ),
    },
    {
        id: "umidade_pct",
        header: "Umidade",
        accessorKey: "umidade_pct",
        sortable: true,
        cell: (value: number | null) => (
            <div className="text-right text-sm">
                {value != null ? (
                    <Badge variant={value > 14 ? "destructive" : "secondary"} className="text-xs">
                        {fmt(value, 1)}%
                    </Badge>
                ) : "—"}
            </div>
        ),
    },
    {
        id: "produtividade_sc_ha",
        header: "Prod. sc/ha",
        accessorKey: "produtividade_sc_ha",
        sortable: true,
        cell: (value: number | null) => (
            <div className="text-right text-sm">
                {value ? `${fmt(value)} sc/ha` : "—"}
            </div>
        ),
    },
    {
        id: "receita_total",
        header: "Receita",
        accessorKey: "receita_total",
        sortable: true,
        cell: (value: number | null) => (
            <div className="text-right text-sm">
                {value ? `R$ ${fmt(value, 0)}` : "—"}
            </div>
        ),
    },
    {
        id: "destino",
        header: "Destino",
        accessorKey: "destino",
        sortable: true,
        cell: (value: string | null) => (
            <span className="text-sm text-muted-foreground">
                {value ?? "—"}
            </span>
        ),
    },
    {
        id: "acoes",
        header: "",
        accessorKey: "id",
        sortable: false,
        filterable: false,
        exportable: false,
        cell: (id: string, row: Romaneio) => (
            <div className="flex gap-0 items-center justify-end">
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-blue-600 border-none"
                    onClick={() => processar.mutate(id)}
                    disabled={processar.isPending}
                    title="Processar em beneficiamento"
                >
                    <Factory className="size-3.5" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-blue-600 border-none"
                    onClick={() => solicitarPesagem.mutate(id)}
                    disabled={solicitarPesagem.isPending}
                    title="Solicitar pesagem oficial na balança"
                >
                    <Scale className="size-3.5" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-destructive border-none"
                    onClick={() => setDeleteId(id)}
                >
                    <Trash2 className="size-3.5" />
                </Button>
            </div>
        ),
    },
];

export function RomaneiosColheita({ safraId, talhoes, cultura, anoSafra }: Props) {
    const qc = useQueryClient();
    const [open, setOpen] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null);

    const [form, setForm] = useState({
        talhao_id: "",
        data_colheita: new Date().toISOString().slice(0, 10),
        numero_romaneio: "",
        turno: "",
        peso_bruto_kg: "",
        tara_kg: "0",
        umidade_pct: "",
        impureza_pct: "",
        preco_saca: "",
        destino: "",
        observacoes: "",
    });
    const [tarefaCampoId, setTarefaCampoId] = useState<string | null>(null);

    const { data: pendentes = [] } = useQuery<ColheitaPendente[]>({
        queryKey: ["romaneios-pendentes", safraId],
        queryFn: () => apiFetch(`/romaneios/pendentes?safra_id=${safraId}`),
    });

    const { data: romaneios = [], isLoading } = useQuery<Romaneio[]>({
        queryKey: ["romaneios", safraId],
        queryFn: () => apiFetch(`/romaneios?safra_id=${safraId}`),
    });

    const { data: kpis } = useQuery<KPIs>({
        queryKey: ["romaneios-kpis", safraId],
        queryFn: () => apiFetch(`/romaneios/kpis?safra_id=${safraId}`),
    });

    const criar = useMutation({
        mutationFn: (body: object) =>
            apiFetch("/romaneios/", { method: "POST", body: JSON.stringify(body) }),
        onSuccess: () => {
            toast.success("Romaneio registrado.");
            qc.invalidateQueries({ queryKey: ["romaneios", safraId] });
            qc.invalidateQueries({ queryKey: ["romaneios-kpis", safraId] });
            qc.invalidateQueries({ queryKey: ["romaneios-pendentes", safraId] });
            setOpen(false);
        },
        onError: () => toast.error("Erro ao registrar romaneio."),
    });

    const excluir = useMutation({
        mutationFn: (id: string) =>
            apiFetch(`/romaneios/${id}`, { method: "DELETE" }),
        onSuccess: () => {
            toast.success("Romaneio excluído.");
            qc.invalidateQueries({ queryKey: ["romaneios", safraId] });
            qc.invalidateQueries({ queryKey: ["romaneios-kpis", safraId] });
            setDeleteId(null);
        },
        onError: () => toast.error("Erro ao excluir."),
    });

    const solicitarPesagem = useMutation({
        mutationFn: (romaneioId: string) =>
            apiFetch(`/romaneios/${romaneioId}/solicitar-pesagem-balanca`, { method: "POST" }),
        onSuccess: () => {
            toast.success("Pesagem solicitada à balança!");
            qc.invalidateQueries({ queryKey: ["romaneios", safraId] });
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao solicitar pesagem."),
    });

    const processar = useMutation({
        mutationFn: (romaneioId: string) =>
            apiFetch(`/beneficiamento/from-romaneio/${romaneioId}`, { method: "POST" }),
        onSuccess: (data: any) => {
            toast.success(`Lote ${data.numero_lote} criado! Redirecionando…`);
            setTimeout(() => {
                window.location.href = `/agricola/safras/${safraId}/beneficiamento`;
            }, 800);
        },
        onError: (e: any) => toast.error(e?.message ?? "Erro ao processar romaneio."),
    });

    const talhaoMap = Object.fromEntries(talhoes.map(t => [t.id, t.nome]));

    function handleSalvar() {
        if (!form.talhao_id || !form.peso_bruto_kg) {
            toast.error("Talhão e peso bruto são obrigatórios.");
            return;
        }
        const body: Record<string, unknown> = {
            safra_id: safraId,
            talhao_id: form.talhao_id,
            data_colheita: form.data_colheita,
            peso_bruto_kg: parseFloat(form.peso_bruto_kg),
            tara_kg: parseFloat(form.tara_kg || "0"),
        };
        if (form.numero_romaneio) body.numero_romaneio = form.numero_romaneio;
        if (form.turno) body.turno = form.turno;
        if (form.umidade_pct) body.umidade_pct = parseFloat(form.umidade_pct);
        if (form.impureza_pct) body.impureza_pct = parseFloat(form.impureza_pct);
        if (form.preco_saca) body.preco_saca = parseFloat(form.preco_saca);
        if (form.destino) body.destino = form.destino;
        if (form.observacoes) body.observacoes = form.observacoes;
        if (tarefaCampoId) body.tarefa_campo_id = tarefaCampoId;
        criar.mutate(body);
    }

    function resetForm(pendente?: ColheitaPendente) {
        setTarefaCampoId(pendente?.tarefa_campo_id ?? null);
        setForm({
            talhao_id: pendente?.talhao_id ?? talhoes[0]?.id ?? "",
            data_colheita: pendente?.concluida_em
                ? pendente.concluida_em.slice(0, 10)
                : new Date().toISOString().slice(0, 10),
            numero_romaneio: "",
            turno: "",
            peso_bruto_kg: "",
            tara_kg: "0",
            umidade_pct: "",
            impureza_pct: "",
            preco_saca: "",
            destino: "",
            observacoes: "",
        });
    }

    return (
        <div className="space-y-6">
            {/* KPIs */}
            {kpis && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <Card className="rounded-sm shadow-sm border-border/40">
                        <CardContent className="pt-4">
                            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                <Package className="size-3.5" /> Romaneios
                            </div>
                            <p className="text-2xl font-bold">{kpis.total_romaneios}</p>
                        </CardContent>
                    </Card>
                    <Card className="rounded-sm shadow-sm border-border/40">
                        <CardContent className="pt-4">
                            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                <Wheat className="size-3.5" /> Total Sacas
                            </div>
                            <p className="text-2xl font-bold">{fmt(kpis.total_sacas, 0)}</p>
                        </CardContent>
                    </Card>
                    <Card className="rounded-sm shadow-sm border-border/40">
                        <CardContent className="pt-4">
                            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                <TrendingUp className="size-3.5" /> Produtividade
                            </div>
                            <p className="text-2xl font-bold">
                                {kpis.produtividade_sc_ha ? `${fmt(kpis.produtividade_sc_ha)} sc/ha` : "—"}
                            </p>
                        </CardContent>
                    </Card>
                    <Card className="rounded-sm shadow-sm border-border/40">
                        <CardContent className="pt-4">
                            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-1">
                                <DollarSign className="size-3.5" /> Receita
                            </div>
                            <p className="text-2xl font-bold">
                                {kpis.receita_total > 0
                                    ? `R$ ${fmt(kpis.receita_total, 0)}`
                                    : "—"}
                            </p>
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Pendentes de romaneio */}
            {pendentes.length > 0 && (
                <div className="rounded-sm border border-amber-500/30 bg-amber-500/10 p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle className="size-4 text-amber-600 shrink-0" />
                        <p className="text-sm font-medium text-amber-800">
                            {pendentes.length} colheita(s) concluída(s) no campo sem romaneio lançado
                        </p>
                    </div>
                    <div className="space-y-2">
                        {pendentes.map((p) => (
                            <div
                                key={p.tarefa_campo_id}
                                className="flex items-center justify-between gap-3 rounded-sm bg-background/60 px-3 py-2"
                            >
                                <div className="flex items-center gap-2 text-sm min-w-0">
                                    <ClipboardList className="size-3.5 text-muted-foreground shrink-0" />
                                    <span className="truncate">
                                        {p.talhao_nome ?? (p.talhao_id ? `${p.talhao_id.slice(0, 8)}…` : "Talhão desconhecido")}
                                    </span>
                                    {p.concluida_em && (
                                        <span className="text-xs text-muted-foreground shrink-0">
                                            · concluída em {new Date(p.concluida_em).toLocaleDateString("pt-BR")}
                                        </span>
                                    )}
                                </div>
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="rounded-sm shrink-0"
                                    onClick={() => { resetForm(p); setOpen(true); }}
                                >
                                    Lançar romaneio
                                </Button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Header + New button */}
            <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm">Registros de Colheita</h3>
                <Button variant="outline" size="sm" className="rounded-sm" onClick={() => { resetForm(); setOpen(true); }}>
                    <Plus className="size-4 mr-1" /> Novo Romaneio
                </Button>
            </div>

            {/* Table */}
            {isLoading ? (
                <Skeleton className="h-32 w-full" />
            ) : romaneios.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                    Nenhum romaneio registrado para esta safra.
                </p>
            ) : (
                <div className="rounded-sm border border-border/40 bg-surface">
                    <DataTable
                        data={romaneios}
                        columns={createColumns(processar, setDeleteId, talhaoMap, solicitarPesagem)}
                        searchable={true}
                        searchPlaceholder="Buscar por romaneio..."
                        exportable={true}
                        exportFileName="romaneios-colheita"
                    />
                    <div className="flex flex-wrap items-center justify-end gap-x-6 gap-y-1 border-t border-border/40 bg-muted/30 px-4 py-2.5 text-sm">
                        <span className="text-muted-foreground">
                            Total Peso Bruto: <span className="font-semibold text-foreground">
                                {fmt(romaneios.reduce((s, r) => s + (r.peso_bruto_kg ?? 0), 0), 0)} kg
                            </span>
                        </span>
                        <span className="text-muted-foreground">
                            Total Sacas: <span className="font-semibold text-foreground">
                                {fmt(romaneios.reduce((s, r) => s + (r.sacas_60kg ?? 0), 0))} sc
                            </span>
                        </span>
                        <span className="text-muted-foreground">
                            Total Valor: <span className="font-semibold text-foreground">
                                R$ {fmt(romaneios.reduce((s, r) => s + (r.receita_total ?? 0), 0), 2)}
                            </span>
                        </span>
                    </div>
                </div>
            )}

            {/* Create Dialog */}
            <Dialog open={open} onOpenChange={setOpen}>
                <DialogContent className="max-w-xl p-0 rounded-sm shadow-sm border-border/40 overflow-hidden">
                    <DialogHeader>
                        <div className="flex items-center gap-2.5">
                            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center">
                                <Package className="size-4 text-primary" />
                            </div>
                            <DialogTitle>Novo Romaneio de Colheita</DialogTitle>
                        </div>
                    </DialogHeader>
                    <DialogBody className="space-y-8 pt-4">
                        
                        {/* Seção 1: Origem e Destino */}
                        <div className="space-y-4">
                            <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                                Origem e Informações Gerais
                            </h4>
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="col-span-2 sm:col-span-1 space-y-2">
                                    <Label className="text-sm font-medium">Talhão *</Label>
                                    <Select value={form.talhao_id || "none"} onValueChange={(value) => setForm(p => ({ ...p, talhao_id: value === "none" ? "" : value }))}>
                                        <SelectTrigger className="h-8 rounded-sm">
                                            <SelectValue placeholder="Selecione o talhão" />
                                        </SelectTrigger>
                                        <SelectContent className="rounded-sm">
                                            <SelectItem value="none">Selecione...</SelectItem>
                                            {talhoes.map((t) => (
                                                <SelectItem key={t.id} value={t.id}>
                                                    {t.nome}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Data Colheita *</Label>
                                    <Input type="date" className="h-8 rounded-sm"
                                        value={form.data_colheita}
                                        onChange={e => setForm(p => ({ ...p, data_colheita: e.target.value }))} />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Turno</Label>
                                    <Select value={form.turno || "none"} onValueChange={(value) => setForm(p => ({ ...p, turno: value === "none" ? "" : value }))}>
                                        <SelectTrigger className="h-8 rounded-sm">
                                            <SelectValue placeholder="Selecione o turno" />
                                        </SelectTrigger>
                                        <SelectContent className="rounded-sm">
                                            <SelectItem value="none">—</SelectItem>
                                            {TURNOS.map((turno) => (
                                                <SelectItem key={turno} value={turno}>
                                                    {turno}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Destino</Label>
                                    <Select value={form.destino || "none"} onValueChange={(value) => setForm(p => ({ ...p, destino: value === "none" ? "" : value }))}>
                                        <SelectTrigger className="h-8 rounded-sm">
                                            <SelectValue placeholder="Selecione o destino" />
                                        </SelectTrigger>
                                        <SelectContent className="rounded-sm">
                                            <SelectItem value="none">—</SelectItem>
                                            {DESTINOS.map((destino) => (
                                                <SelectItem key={destino} value={destino}>
                                                    {destino}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </div>

                        {/* Seção 2: Pesagem e Qualidade */}
                        <div className="space-y-4">
                            <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                                Pesagem e Qualidade
                            </h4>
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Nº Romaneio</Label>
                                    <Input className="h-8 rounded-sm" placeholder="Opcional"
                                        value={form.numero_romaneio}
                                        onChange={e => setForm(p => ({ ...p, numero_romaneio: e.target.value }))} />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Peso Bruto (kg) *</Label>
                                    <Input type="number" inputMode="decimal" className="h-8 rounded-sm" placeholder="0"
                                        value={form.peso_bruto_kg}
                                        onChange={e => setForm(p => ({ ...p, peso_bruto_kg: e.target.value }))} />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Tara (kg)</Label>
                                    <Input type="number" inputMode="decimal" className="h-8 rounded-sm"
                                        value={form.tara_kg}
                                        onChange={e => setForm(p => ({ ...p, tara_kg: e.target.value }))} />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Umidade (%)</Label>
                                    <Input type="number" step="0.1" inputMode="decimal" className="h-8 rounded-sm" placeholder="14,0"
                                        value={form.umidade_pct}
                                        onChange={e => setForm(p => ({ ...p, umidade_pct: e.target.value }))} />
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Impureza (%)</Label>
                                    <Input type="number" step="0.1" inputMode="decimal" className="h-8 rounded-sm" placeholder="1,0"
                                        value={form.impureza_pct}
                                        onChange={e => setForm(p => ({ ...p, impureza_pct: e.target.value }))} />
                                </div>
                            </div>
                        </div>

                        {/* Seção 3: Comercial e Obs */}
                        <div className="space-y-4">
                            <h4 className="text-sm font-semibold text-muted-foreground border-b border-border/50 pb-2">
                                Comercial (Opcional)
                            </h4>
                            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium">Preço/Saca (R$)</Label>
                                    <Input type="number" step="0.01" inputMode="decimal" className="h-8 rounded-sm" placeholder="Opcional (para previsão)"
                                        value={form.preco_saca}
                                        onChange={e => setForm(p => ({ ...p, preco_saca: e.target.value }))} />
                                </div>
                                <div className="space-y-2 col-span-2">
                                    <Label className="text-sm font-medium">Observações</Label>
                                    <Textarea
                                        className="min-h-16 rounded-sm resize-none text-sm"
                                        value={form.observacoes}
                                        onChange={e => setForm(p => ({ ...p, observacoes: e.target.value }))} />
                                </div>
                            </div>
                        </div>

                    </DialogBody>
                    <DialogFooter>
                        <Button variant="outline" size="sm" className="rounded-sm" onClick={() => setOpen(false)}>
                            <XCircle className="size-4 mr-1.5" />
                            Cancelar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="rounded-sm"
                            onClick={handleSalvar}
                            disabled={criar.isPending}
                        >
                            <Save className="size-4 mr-1.5" />
                            {criar.isPending ? "Salvando…" : "Registrar Romaneio"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirm */}
            <AlertDialog open={!!deleteId} onOpenChange={v => !v && setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Excluir romaneio?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Esta ação não pode ser desfeita. A receita financeira associada não será removida automaticamente.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancelar</AlertDialogCancel>
                        <AlertDialogAction
                            className="bg-destructive text-destructive-foreground"
                            onClick={() => deleteId && excluir.mutate(deleteId)}
                        >
                            Excluir
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
