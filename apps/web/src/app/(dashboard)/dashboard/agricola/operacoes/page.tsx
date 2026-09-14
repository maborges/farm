"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Tractor, Plus, ClipboardList,
    TrendingUp, DollarSign, Calendar, MapPin,
    Download,
    Droplets, Sprout, Hammer, Wheat, X
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription,
    DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import { getApiBaseUrl } from "@/lib/runtime-config";

interface InsumoRecord {
    id: string;
    insumo_id: string;
    dose_por_ha: number;
    unidade: string;
    quantidade_total: number;
}

interface OperacaoRecord {
    id: string;
    talhao_id: string;
    talhao_nome?: string | null;
    safra_id: string;
    tipo: string;
    subtipo: string | null;
    descricao: string;
    data_realizada: string;
    area_aplicada_ha: number;
    custo_total: number;
    status: string;
    insumos: InsumoRecord[];
}

interface TipoOperacao {
    id: string;
    tipo_operacao: string;
    fases_permitidas: string[];
    descricao?: string | null;
}

export default function OperacoesAgricolasPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [selectedSafraId, setSelectedSafraId] = useState<string>("");

    // Insumo add selectors
    const [selectedProdId, setSelectedProdId] = useState("");
    const [dose, setDose] = useState(0);

    // Form State
    const [formData, setFormData] = useState({
        safra_id: "",
        talhao_id: "",
        tipo: "PULVERIZAÇÃO",
        subtipo: "",
        descricao: "Aplicação de rotina técnica",
        data_realizada: new Date().toISOString().split('T')[0],
        area_aplicada_ha: 0,
        maquina_id: null as string | null,
        implemento: "",
        insumos: [] as any[]
    });

    // Queries
    const { data: operacoes, isLoading } = useQuery<OperacaoRecord[]>({
        queryKey: ["agricola", "operacoes", activeFazendaId],
        queryFn: () => apiFetch(`/operacoes/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: safras } = useQuery<any[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: talhoes } = useQuery<any[]>({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch(`/cadastros/areas-rurais?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: produtos = [] } = useQuery<any[]>({
        queryKey: ["estoque", "produtos"],
        queryFn: () => apiFetch("/cadastros/produtos?ativo=true"),
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes-tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        staleTime: 5 * 60 * 1000,
    });

    const { data: maquinas = [] } = useQuery<any[]>({
        queryKey: ["frota", "maquinarios", activeFazendaId],
        queryFn: () => apiFetch(`/frota/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: resumenCustos } = useQuery<any>({
        queryKey: ["agricola", "custos", selectedSafraId],
        queryFn: () => apiFetch(`/custos/safra/${selectedSafraId}`),
        enabled: !!selectedSafraId
    });

    const resumoCusto = resumenCustos;

    // Auto-select first safra
    useEffect(() => {
        if (safras && safras.length > 0 && !selectedSafraId) {
            setSelectedSafraId(safras[0].id);
        }
    }, [safras, selectedSafraId]);

    useEffect(() => {
        if (tiposOperacao.length === 0) return;
        const tipoAtualExiste = tiposOperacao.some((item) => item.tipo_operacao === formData.tipo);
        if (!tipoAtualExiste) {
            setFormData((current) => ({ ...current, tipo: tiposOperacao[0].tipo_operacao }));
        }
    }, [tiposOperacao, formData.tipo]);

    const mutation = useMutation({
        mutationFn: (data: any) => apiFetch("/operacoes/", { method: "POST", body: JSON.stringify(data) }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agricola", "operacoes"] });
            toast.success("Operação registrada e estoque atualizado!");
            setIsDialogOpen(false);
            // Reset form
            setFormData({
                safra_id: "",
                talhao_id: "",
                tipo: tiposOperacao[0]?.tipo_operacao || "PULVERIZAÇÃO",
                subtipo: "",
                descricao: "Aplicação de rotina técnica",
                data_realizada: new Date().toISOString().split('T')[0],
                area_aplicada_ha: 0,
                maquina_id: null as string | null,
                implemento: "",
                insumos: []
            });
        },
        onError: (err: any) => {
            toast.error(`Erro: ${err.message || "Falha ao registrar"}`);
        }
    });

    const handleSave = () => {
        if (!formData.safra_id || !formData.talhao_id) {
            toast.error("Selecione a safra e o talhão!");
            return;
        }
        mutation.mutate(formData);
    };

    const addInsumo = () => {
        if (!selectedProdId || dose <= 0) return toast.error("Selecione um produto e a dose.");

        const produto = produtos.find(p => p.id === selectedProdId);
        if (!produto) return;

        const newInsumo = {
            insumo_id: produto.id,
            nome_display: produto.nome,
            dose_por_ha: dose,
            unidade: produto.unidade_medida,
            lote_insumo: "AUTO"
        };

        setFormData({ ...formData, insumos: [...formData.insumos, newInsumo] });
        setSelectedProdId("");
        setDose(0);
    };

    const removeInsumo = (idx: number) => {
        const newInsumos = [...formData.insumos];
        newInsumos.splice(idx, 1);
        setFormData({ ...formData, insumos: newInsumos });
    };

    const totalCusto = operacoes?.reduce((acc, op) => acc + Number(op.custo_total || 0), 0) || 0;
    const totalArea = operacoes?.reduce((acc, op) => acc + Number(op.area_aplicada_ha || 0), 0) || 0;
    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao || tipo;

    const getTipoIcon = (tipo: string) => {
        switch (tipo) {
            case "PLANTIO": return <Sprout className="size-4" />;
            case "PULVERIZAÇÃO":
            case "IRRIGAÇÃO":
            case "APLICACAO":
                return <Droplets className="size-4" />;
            case "COLHEITA": return <Wheat className="size-4" />;
            case "ADUBAÇÃO":
            case "ADUBACAO":
            default: return <Hammer className="size-4" />;
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "CONCLUIDA": return <Badge className="bg-green-500/10 text-green-700 border-none">Concluída</Badge>;
            case "EM_ANDAMENTO": return <Badge className="bg-blue-500/10 text-blue-700 border-none">Em Andamento</Badge>;
            case "CANCELADA": return <Badge className="bg-red-500/10 text-red-700 border-none">Cancelada</Badge>;
            default: return <Badge className="bg-amber-500/10 text-amber-700 border-none">Planejada</Badge>;
        }
    };

    const getTalhaoNome = (id: string) => talhoes?.find((talhao) => talhao.id === id)?.nome ?? "Talhão não informado";

    const columns: ColumnDef<OperacaoRecord>[] = [
        {
            id: "data",
            header: "Data / Status",
            accessorKey: "data_realizada",
            cell: (value, row) => (
                <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-sm font-bold">
                        <Calendar size={14} className="text-muted-foreground" />
                        {new Date(value).toLocaleDateString('pt-BR')}
                    </div>
                    {getStatusBadge(row.status)}
                </div>
            ),
            sortable: true,
            exportFormat: (value, row) => `${new Date(value).toLocaleDateString('pt-BR')} - ${row.status}`,
        },
        {
            id: "tipo",
            header: "Operação",
            accessorKey: "tipo",
            cell: (value, row) => (
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-sm bg-primary/10 flex items-center justify-center text-primary">
                        {getTipoIcon(value)}
                    </div>
                    <div>
                        <p className="font-black text-sm uppercase">{getTipoLabel(value)}</p>
                        <p className="text-[10px] text-muted-foreground font-bold italic">{row.subtipo || "Mecanizada"}</p>
                    </div>
                </div>
            ),
            sortable: true,
            filterable: true,
            filterPlaceholder: "Filtrar tipo...",
            exportFormat: (value, row) => `${getTipoLabel(value)} - ${row.subtipo || "Mecanizada"}`,
        },
        {
            id: "talhao",
            header: "Talhão / Área",
            accessorFn: (row) => row.talhao_nome ?? getTalhaoNome(row.talhao_id),
            cell: (value, row) => (
                <div className="space-y-1">
                    <div className="flex items-center gap-2 font-bold text-sm">
                        <MapPin size={12} className="text-primary" />
                        {value}
                    </div>
                    <p className="text-xs text-muted-foreground">{row.area_aplicada_ha} hectares</p>
                </div>
            ),
            sortable: true,
            exportFormat: (value, row) => `${value} - ${row.area_aplicada_ha}ha`,
        },
        {
            id: "custo",
            header: "Custo",
            accessorKey: "custo_total",
            cell: (value) => (
                <div className="space-y-0.5">
                    <p className="font-black text-sm">R$ {Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</p>
                    <p className="text-[10px] text-muted-foreground font-black uppercase opacity-60">Direto</p>
                </div>
            ),
            sortable: true,
            exportFormat: (value) => `R$ ${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        },
        {
            id: "insumos",
            header: "Insumos",
            accessorFn: (row) => row.insumos?.map(i => `${i.dose_por_ha}${i.unidade}`).join(', ') || '-',
            cell: (_, row) => (
                <div className="flex gap-2">
                    {row.insumos?.slice(0, 2).map((ins, i) => (
                        <Badge key={i} variant="ghost" className="bg-muted/30 border-border/40 text-[10px] font-bold">
                            {ins.dose_por_ha}{ins.unidade}
                        </Badge>
                    ))}
                    {row.insumos?.length > 2 && (
                        <Badge variant="ghost" className="bg-muted/30 border-border/40 text-[10px] font-bold">
                            +{row.insumos.length - 2}
                        </Badge>
                    )}
                </div>
            ),
            exportFormat: (_, row) => row.insumos?.map(i => `${i.dose_por_ha}${i.unidade}`).join(', ') || '-',
        },
    ];

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Caderno de Campo"
                description="Registro de operações agrícolas por safra."
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Operações" }]}
                icon={<Tractor className="text-primary" size={22} />}
                actions={
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={async () => {
                                try {
                                    const response = await fetch(`${getApiBaseUrl()}/operacoes/export/pdf`, {
                                        headers: {
                                            'x-tenant-id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
                                            'x-fazenda-id': activeFazendaId || ''
                                        }
                                    });
                                    const blob = await response.blob();
                                    const url = window.URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = `Caderno_Campo_${new Date().toISOString().split('T')[0]}.pdf`;
                                    document.body.appendChild(a);
                                    a.click();
                                    a.remove();
                                    toast.success("Relatório gerado com sucesso!");
                                } catch (error) {
                                    console.error("Erro ao baixar PDF:", error);
                                    toast.error("Erro ao gerar relatório.");
                                }
                            }}
                        >
                            <Download className="mr-2 size-4" /> Relatório Mensal
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => setIsDialogOpen(true)}>
                            <Plus className="mr-2 size-4" /> Nova Operação
                        </Button>
                    </div>
                }
            />

            {/* Metrics Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <Card className="border-none shadow-sm ring-1 ring-border/60 bg-background overflow-hidden relative group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                        <Sprout size={48} className="text-primary" />
                    </div>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Área Monitorada</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">
                            {(resumoCusto?.area_total_ha || totalArea).toLocaleString()} ha
                        </div>
                        <p className="text-[10px] mt-1 text-muted-foreground flex items-center gap-1 font-bold">
                            Total aplicado na safra
                        </p>
                    </CardContent>
                </Card>

                <Card className="border-none shadow-sm ring-1 ring-border/60 overflow-hidden relative group bg-surface">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Investimento Realizado</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-foreground">R$ {(resumoCusto?.custo_total_realizado || totalCusto).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</div>
                        <p className="text-[10px] mt-1 text-muted-foreground flex items-center gap-1 font-bold">
                            R$ {(resumoCusto?.custo_realizado_por_ha || (totalCusto / (totalArea || 1))).toFixed(2)}/ha
                        </p>
                    </CardContent>
                    <div className="absolute top-0 right-0 p-4 opacity-5">
                        <DollarSign size={48} />
                    </div>
                </Card>

                <Card className="border-none shadow-sm ring-1 ring-border/60 overflow-hidden bg-surface">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Saldo do Orçamento</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black">
                            {resumoCusto?.orcamento_previsto_total
                                ? `R$ ${(resumoCusto.orcamento_previsto_total - resumoCusto.custo_total_realizado).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
                                : "N/D"}
                        </div>
                        <div className="flex gap-1 mt-2">
                            <div className="h-1.5 w-full bg-primary/20 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${resumoCusto?.desvio_orcamento_pct > 0 ? 'bg-red-500' : 'bg-primary'}`}
                                    style={{ width: `${Math.min(100, ((resumoCusto?.custo_total_realizado / resumoCusto?.orcamento_previsto_total) * 100) || 0)}%` }}
                                ></div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className={`border-none shadow-sm ring-1 ring-border/60 overflow-hidden text-primary-foreground shadow-primary/20 ${resumoCusto?.desvio_orcamento_pct > 0 ? 'bg-red-600' : 'bg-primary'}`}>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-primary-foreground/60 tracking-widest">Saúde Financeira</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black">
                            {resumoCusto?.desvio_orcamento_pct != null
                                ? `${resumoCusto.desvio_orcamento_pct > 0 ? '+' : ''}${resumoCusto.desvio_orcamento_pct}%`
                                : "100.0%"}
                        </div>
                        <p className="text-[10px] mt-1 opacity-80 uppercase font-black er">
                            {resumoCusto?.desvio_orcamento_pct > 0 ? "Orçamento Excedido" : "Dentro do Planejado"}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* DataTable */}
            <DataTable
                data={operacoes || []}
                columns={columns}
                searchable
                searchPlaceholder="Buscar operação ou talhão..."
                exportable
                exportFileName="operacoes-agricolas"
                emptyMessage="Nenhuma operação registrada nesta safra"
            />

            {/* New Operation Dialog Tool */}
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                <DialogContent className="sm:max-w-[900px] rounded-[40px] p-0 overflow-hidden border-none shadow-2xl bg-surface text-foreground">
                    <div className="bg-[#1e2227] p-10 text-white relative">
                        <div className="absolute top-0 right-0 p-10 opacity-10">
                            <Tractor size={120} />
                        </div>
                        <DialogHeader>
                            <DialogTitle className="text-4xl font-black flex items-center gap-3">
                                <Tractor className="h-10 w-10 text-primary" />
                                Registrar Operação
                            </DialogTitle>
                            <DialogDescription className="text-gray-400 text-lg font-medium">Caderno de Campo • Baixa Automática de Estoque.</DialogDescription>
                        </DialogHeader>
                    </div>

                    <div className="p-10 grid grid-cols-2 gap-10">
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[11px] font-black uppercase text-muted-foreground tracking-widest px-1">Geral / Planejamento</label>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                        <p className="text-[10px] opacity-50 uppercase font-black ml-1">Tipo</p>
                                        <Select value={formData.tipo} onValueChange={(v: string) => setFormData({ ...formData, tipo: v })}>
                                            <SelectTrigger className="h-12 rounded-sm border-none bg-muted/50 focus:ring-primary/20 text-sm font-bold text-left overflow-hidden">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="bg-surface border-border">
                                                {tiposOperacao.map((tipo) => (
                                                    <SelectItem key={tipo.id} value={tipo.tipo_operacao}>
                                                        {tipo.descricao || tipo.tipo_operacao}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] opacity-50 uppercase font-black ml-1">Ciclo/Safra</p>
                                        <Select value={formData.safra_id} onValueChange={(v: string) => setFormData({ ...formData, safra_id: v })}>
                                            <SelectTrigger className="h-12 rounded-sm border-none bg-muted/50 focus:ring-primary/20 text-sm font-bold text-left overflow-hidden">
                                                <SelectValue placeholder="Safra" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-surface border-border">
                                                {safras?.map(s => <SelectItem key={s.id} value={s.id}>{s.ano_safra} - {s.cultura}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-50 uppercase font-black ml-1">Talhão de Operação</p>
                                    <Select value={formData.talhao_id} onValueChange={(v: string) => setFormData({ ...formData, talhao_id: v })}>
                                        <SelectTrigger className="h-12 rounded-sm border-none bg-muted/50 focus:ring-primary/20 font-bold overflow-hidden">
                                            <SelectValue placeholder="Selecione" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-surface border-border">
                                            {talhoes?.map(t => <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>)}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[10px] opacity-50 uppercase font-black ml-1">Área Efetiva (ha)</p>
                                    <Input
                                        type="number"
                                        placeholder="0.00"
                                        className="h-12 rounded-sm border-none bg-muted/50 focus-visible:ring-primary/20 font-black text-lg"
                                        value={formData.area_aplicada_ha}
                                        onChange={(e) => setFormData({ ...formData, area_aplicada_ha: Number(e.target.value) })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-1">
                                <p className="text-[10px] opacity-50 uppercase font-black ml-1">Descrição</p>
                                <Input
                                    className="h-12 rounded-sm border-none bg-muted/50 focus-visible:ring-primary/20 font-bold text-sm"
                                    value={formData.descricao}
                                    onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2 pt-2">
                                <label className="text-[11px] font-black uppercase text-muted-foreground tracking-widest px-1">Logística de Operação</label>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1">
                                        <p className="text-[10px] opacity-50 uppercase font-black ml-1">Máquina / Trator</p>
                                        <Select value={formData.maquina_id || ""} onValueChange={(v: string) => setFormData({ ...formData, maquina_id: v })}>
                                            <SelectTrigger className="h-12 rounded-sm border-none bg-muted/50 focus:ring-primary/20 text-sm font-bold text-left overflow-hidden">
                                                <SelectValue placeholder="Selecione" />
                                            </SelectTrigger>
                                            <SelectContent className="bg-surface border-border">
                                                {maquinas.map((m: any) => <SelectItem key={m.id} value={m.id}>{m.nome}</SelectItem>)}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] opacity-50 uppercase font-black ml-1">Implemento</p>
                                        <Input
                                            className="h-12 rounded-sm border-none bg-muted/50 focus-visible:ring-primary/20 font-bold text-sm"
                                            value={formData.implemento}
                                            onChange={(e) => setFormData({ ...formData, implemento: e.target.value })}
                                            placeholder="Ex.: Plantadeira 12 L"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="bg-muted/30 rounded-sm p-6 border border-border/40 space-y-4">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-[11px] font-black uppercase tracking-widest text-primary">Insumos (Fórmula)</h4>
                                </div>

                                <div className="grid grid-cols-5 gap-2">
                                    <div className="col-span-3">
                                        <Select value={selectedProdId} onValueChange={setSelectedProdId}>
                                            <SelectTrigger className="h-10 rounded-sm bg-background border-border text-xs font-bold">
                                                <SelectValue placeholder="Escolher Insumo..." />
                                            </SelectTrigger>
                                            <SelectContent className="bg-surface border-border">
                                                {produtos.map((p: any) => (
                                                    <SelectItem key={p.id} value={p.id}>{p.nome} ({p.unidade_medida})</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <Input
                                        type="number"
                                        placeholder="Dose"
                                        className="h-10 rounded-sm bg-background border-border text-xs font-black"
                                        value={dose}
                                        onChange={e => setDose(Number(e.target.value))}
                                    />
                                    <Button size="sm" className="h-10 rounded-sm bg-primary text-white" onClick={addInsumo}><Plus size={16} /></Button>
                                </div>

                                <Separator className="bg-border/40" />

                                <div className="space-y-2 max-h-[160px] overflow-y-auto pr-2 custom-scrollbar">
                                    {formData.insumos.length === 0 ? (
                                        <div className="h-20 flex flex-col items-center justify-center opacity-30 italic">
                                            <p className="text-[10px] font-bold">Nenhum insumo adicionado</p>
                                        </div>
                                    ) : (
                                        formData.insumos.map((ins: any, idx: number) => (
                                            <div key={idx} className="flex items-center justify-between bg-surface border border-border/40 p-3 rounded-sm shadow-sm animate-in fade-in duration-200">
                                                <div className="flex items-center gap-3">
                                                    <div className="h-8 w-8 rounded-sm bg-primary/10 flex items-center justify-center text-primary"><Droplets size={14} /></div>
                                                    <div>
                                                        <p className="text-[11px] font-black uppercase leading-tight">{ins.nome_display}</p>
                                                        <p className="text-[10px] text-muted-foreground font-bold">{ins.dose_por_ha} {ins.unidade}/ha</p>
                                                    </div>
                                                </div>
                                                <Button size="icon" variant="ghost" className="h-7 w-7 text-muted-foreground hover:text-red-500 rounded-full" onClick={() => removeInsumo(idx)}>
                                                    <X size={14} />
                                                </Button>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            <div className="p-4 bg-primary/5 rounded-[24px] border border-primary/10 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-600"><TrendingUp size={16} /></div>
                                    <div>
                                        <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest opacity-60">Baixa Digital</p>
                                        <p className="text-xs font-bold">Saldo atualizado em tempo real</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="p-10 pt-4 flex gap-4">
                        <Button variant="ghost" className="h-14 flex-1 rounded-sm font-black text-xs uppercase tracking-widest border-border/60 hover:bg-muted transition-colors" onClick={() => setIsDialogOpen(false)} disabled={mutation.isPending}>
                            Cancelar
                        </Button>
                        <Button
                            className="h-14 flex-[2] rounded-sm font-black text-lg shadow-2xl bg-primary text-white shadow-primary/20 uppercase tracking-widest"
                            onClick={handleSave}
                            disabled={mutation.isPending}
                        >
                            {mutation.isPending ? "Validando Estoque..." : "Concluir Registro"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
