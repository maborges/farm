"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { DataTable, type ColumnDef } from "@/components/ui/data-table";
import {
    Bug, Plus, Search, Map as MapIcon, ClipboardCheck,
    AlertTriangle, Filter, Download, Camera, BrainCircuit,
    ArrowUpRight, ChevronRight, Microscope, Info
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
    Dialog, DialogContent, DialogDescription,
    DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface MonitoramentoRecord {
    id: string;
    talhao_id: string;
    talhao_nome?: string | null;
    data_avaliacao: string;
    tipo: string;
    nome_popular: string;
    nivel_infestacao: number;
    unidade_medida: string;
    atingiu_nde: boolean;
    fotos: string[];
}

const getStatusInfo = (record: MonitoramentoRecord) => {
    if (record.atingiu_nde) return { label: "Crítico", class: "bg-red-500/10 text-red-700 border-red-200", icon: <AlertTriangle className="size-3" /> };
    if (record.nivel_infestacao > 0) return { label: "Atenção", class: "bg-amber-500/10 text-amber-700 border-amber-200", icon: <Info className="size-3" /> };
    return { label: "Normal", class: "bg-green-500/10 text-green-700 border-green-200", icon: <ClipboardCheck className="size-3" /> };
};

const createMonitoramentoColumns = (getTalhaoNome: (id: string) => string): ColumnDef<MonitoramentoRecord>[] => [
    {
        id: "talhao",
        header: "Talhão / Área",
        accessorFn: (row) => row.talhao_nome ?? getTalhaoNome(row.talhao_id),
        sortable: true,
        cell: (value: string) => (
            <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-sm bg-primary/10 flex items-center justify-center text-primary font-black text-xs">T{value.substring(0, 2).toUpperCase()}</div>
                <div>
                    <p className="font-bold text-sm">{value}</p>
                    <p className="text-[10px] text-muted-foreground uppercase font-black">Talhão</p>
                </div>
            </div>
        ),
    },
    {
        id: "nome_popular",
        header: "Praga ou Doença",
        accessorKey: "nome_popular",
        sortable: true,
        filterable: true,
        cell: (value: string, row: MonitoramentoRecord) => (
            <div>
                <p className="font-bold text-sm text-foreground">{value}</p>
                <p className="text-[10px] text-primary font-bold italic opacity-70">Tipo: {row.tipo}</p>
            </div>
        ),
    },
    {
        id: "nivel_infestacao",
        header: "Infestação",
        accessorFn: (row) => `${row.nivel_infestacao}${row.unidade_medida}`,
        sortable: true,
        cell: (value: string) => <span className="text-lg font-black">{value}</span>,
    },
    {
        id: "data_avaliacao",
        header: "Data Avaliação",
        accessorKey: "data_avaliacao",
        sortable: true,
        cell: (value: string) => new Date(value).toLocaleDateString('pt-BR'),
    },
    {
        id: "status",
        header: "Status / NDE",
        accessorFn: (row) => row,
        sortable: false,
        cell: (value: MonitoramentoRecord) => {
            const status = getStatusInfo(value);
            return (
                <div className="flex justify-center">
                    <Badge className={`rounded-sm px-3 py-1 border-none shadow-sm flex items-center gap-1.5 font-black text-[10px] uppercase tracking-wider ${status.class}`}>
                        {status.icon}
                        {status.label}
                    </Badge>
                </div>
            );
        },
    },
];

export default function MonitoramentoPragasPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);

    // Form State
    const [formData, setFormData] = useState({
        talhao_id: "",
        safra_id: "",
        tipo: "PRAGA",
        nome_popular: "",
        nivel_infestacao: 0,
        unidade_medida: "%",
        data_avaliacao: new Date().toISOString().split('T')[0]
    });

    // IA Diagnosis Mutation
    const aiMutation = useMutation({
        mutationFn: async (file: File) => {
            const body = new FormData();
            body.append("foto", file);
            // In a real app, we might need an ID first or use a general endpoint
            return await apiFetch<any>("/monitoramentos/diagnosticar-avulso", {
                method: "POST",
                body // apiFetch handles FormData automatically if body is FormData instance
            });
        },
        onSuccess: (data) => {
            setFormData(prev => ({
                ...prev,
                nome_popular: data.praga_identificada,
                tipo: data.tipo || prev.tipo
            }));
            toast.success(`IA: ${data.praga_identificada} identificada com ${data.certeza_percentual}% de confiança.`);
            setIsAnalyzing(false);
        },
        onError: () => {
            toast.error("Falha na análise da IA. Preencha manualmente.");
            setIsAnalyzing(false);
        }
    });

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setPreviewUrl(URL.createObjectURL(file));

            // Trigger AI analysis automatically
            setIsAnalyzing(true);
            aiMutation.mutate(file);
        }
    };

    // Queries
    const { data: monitoramentos, isLoading } = useQuery<MonitoramentoRecord[]>({
        queryKey: ["agricola", "monitoramentos", activeFazendaId],
        queryFn: () => apiFetch(`/monitoramentos/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const { data: talhoes } = useQuery<any[]>({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    const getTalhaoNome = (id: string) => talhoes?.find((talhao) => talhao.id === id)?.nome ?? "Talhão não informado";
    const monitoramentoColumns = createMonitoramentoColumns(getTalhaoNome);

    const { data: safras } = useQuery<any[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId
    });

    // Mutations
    const mutation = useMutation({
        mutationFn: (data: any) => apiFetch("/monitoramentos/", {
            method: "POST",
            body: JSON.stringify(data)
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["agricola", "monitoramentos", activeFazendaId] });
            toast.success("Monitoramento registrado com sucesso!");
            setIsDialogOpen(false);
            resetForm();
        },
        onError: (err: any) => {
            toast.error(err.message || "Erro ao registrar monitoramento");
        }
    });

    const resetForm = () => {
        setFormData({
            talhao_id: "",
            safra_id: safras?.[0]?.id || "",
            tipo: "PRAGA",
            nome_popular: "",
            nivel_infestacao: 0,
            unidade_medida: "%",
            data_avaliacao: new Date().toISOString().split('T')[0]
        });
    };

    const handleSave = () => {
        if (!formData.talhao_id || !formData.safra_id || !formData.nome_popular) {
            toast.error("Preencha todos os campos obrigatórios.");
            return;
        }
        mutation.mutate(formData);
    };


    if (isLoading) {
        return (
            <div className="p-8 space-y-8 animate-in fade-in duration-500">
                <div className="flex justify-between items-center">
                    <Skeleton className="h-10 w-64" />
                    <Skeleton className="h-10 w-32" />
                </div>
                <div className="grid grid-cols-4 gap-6">
                    <Skeleton className="h-32 rounded-sm" />
                    <Skeleton className="h-32 rounded-sm" />
                    <Skeleton className="h-32 rounded-sm" />
                    <Skeleton className="h-32 rounded-sm" />
                </div>
                <Skeleton className="h-96 rounded-sm w-full" />
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="MIP — Manejo Integrado de Pragas"
                description="Levantamento de pragas, doenças e invasoras por talhão."
                icon={<Bug className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Monitoramento" }, { label: "MIP" }]}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" className="gap-2">
                            <Download size={14} /> Exportar Laudo
                        </Button>
                        <Button variant="outline" size="sm" className="gap-2" onClick={() => setIsDialogOpen(true)}>
                            <Plus size={14} /> Novo Levantamento
                        </Button>
                    </div>
                }
            />
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                        <DialogContent className="sm:max-w-[500px] rounded-sm p-0 overflow-hidden border-none shadow-2xl">
                            <div className="bg-primary p-8 text-primary-foreground relative">
                                <DialogHeader>
                                    <DialogTitle className="text-3xl font-black flex items-center gap-2 text-white">
                                        <Bug className="text-white lg:h-8 lg:w-8" /> Novo MIP
                                    </DialogTitle>
                                    <DialogDescription className="text-primary-foreground/80 font-medium">Caderno de campo digital: Georeferenciado.</DialogDescription>
                                </DialogHeader>
                            </div>

                            <div className="grid gap-6 p-8 bg-background">
                                <div className="grid gap-4">
                                    <div className="grid gap-2">
                                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1">Talhão</label>
                                        <Select value={formData.talhao_id} onValueChange={(v: string) => setFormData({ ...formData, talhao_id: v })}>
                                            <SelectTrigger className="rounded-sm h-11 border-none bg-muted/50 focus:ring-primary/20">
                                                <SelectValue placeholder="Selecione o talhão" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {talhoes?.map(t => (
                                                    <SelectItem key={t.id} value={t.id}>{t.nome}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="grid gap-2">
                                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1">Safra Ativa</label>
                                        <Select value={formData.safra_id} onValueChange={(v: string) => setFormData({ ...formData, safra_id: v })}>
                                            <SelectTrigger className="rounded-sm h-11 border-none bg-muted/50 focus:ring-primary/20">
                                                <SelectValue placeholder="Selecione a safra" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {safras?.map(s => (
                                                    <SelectItem key={s.id} value={s.id}>{s.nome}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="grid gap-2">
                                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1">Ocorrência (Praga/Doença)</label>
                                        <Input
                                            placeholder="Ex: Lagarta do Cartucho"
                                            className="rounded-sm h-11 border-none bg-muted/50 focus-visible:ring-primary/20"
                                            value={formData.nome_popular}
                                            onChange={(e) => setFormData({ ...formData, nome_popular: e.target.value })}
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="grid gap-2">
                                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1">Tipo</label>
                                            <Select value={formData.tipo} onValueChange={(v: string) => setFormData({ ...formData, tipo: v })}>
                                                <SelectTrigger className="rounded-sm h-11 border-none bg-muted/50 focus:ring-primary/20">
                                                    <SelectValue placeholder="Tipo" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="PRAGA">Praga</SelectItem>
                                                    <SelectItem value="DOENCA">Doença</SelectItem>
                                                    <SelectItem value="INVASORA">Invasora</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                        <div className="grid gap-2">
                                            <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1">Nível Infestação</label>
                                            <div className="relative">
                                                <Input
                                                    type="number"
                                                    placeholder="0.00"
                                                    className="rounded-sm h-11 border-none bg-muted/50 focus-visible:ring-primary/20 pr-10"
                                                    value={formData.nivel_infestacao}
                                                    onChange={(e) => setFormData({ ...formData, nivel_infestacao: Number(e.target.value) })}
                                                />
                                                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-muted-foreground">%</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <label className="text-[10px] font-black uppercase text-muted-foreground tracking-widest px-1 mb-2 block">Evidência e Análise IA</label>
                                        <label
                                            htmlFor="camera-input"
                                            className={`relative h-44 border-2 border-dashed rounded-sm flex flex-col items-center justify-center gap-3 overflow-hidden transition-all cursor-pointer group 
                                                ${previewUrl ? 'border-primary/40 bg-muted/20' : 'border-primary/20 bg-primary/5 hover:bg-primary/10'}`}
                                        >
                                            {previewUrl ? (
                                                <>
                                                    <img src={previewUrl} className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:opacity-40 transition-opacity" />
                                                    <div className="relative z-10 bg-background/80 backdrop-blur-md px-4 py-2 rounded-sm border border-border shadow-xl space-y-1">
                                                        <p className="text-[10px] font-black uppercase text-center text-primary">Imagem Capturada</p>
                                                        {isAnalyzing && (
                                                            <div className="flex items-center gap-2 text-foreground font-black text-xs animate-pulse">
                                                                <BrainCircuit size={14} className="text-blue-500" /> IA ANALISANDO...
                                                            </div>
                                                        )}
                                                    </div>
                                                </>
                                            ) : (
                                                <>
                                                    <div className="h-12 w-12 rounded-sm bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                                                        <Camera size={24} className="text-primary" />
                                                    </div>
                                                    <div className="text-center">
                                                        <span className="text-[10px] font-black text-primary uppercase tracking-widest block">Anexar Foto do Campo</span>
                                                        <span className="text-[8px] text-muted-foreground uppercase font-bold tracking-tight">Otimizado para Diagnóstico por IA</span>
                                                    </div>
                                                </>
                                            )}
                                            <input
                                                id="camera-input"
                                                type="file"
                                                accept="image/*"
                                                className="hidden"
                                                onChange={handleFileChange}
                                            />
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <div className="p-8 pt-0 bg-background">
                                <Button
                                    onClick={handleSave}
                                    className="w-full h-14 rounded-sm font-black text-lg shadow-xl shadow-primary/20 group overflow-hidden relative"
                                    disabled={mutation.isPending || isAnalyzing}
                                >
                                    <div className="relative z-10 flex items-center justify-center gap-2">
                                        {mutation.isPending ? "Processando..." : (
                                            <>
                                                <ClipboardCheck size={20} /> Confirmar Levantamento
                                            </>
                                        )}
                                    </div>
                                    {isAnalyzing && (
                                        <div className="absolute inset-x-0 bottom-0 h-1 bg-blue-500 animate-pulse" />
                                    )}
                                </Button>
                            </div>
                        </DialogContent>
                    </Dialog>

            {/* Quick Metrics Row */}
            <div className="grid gap-6 md:grid-cols-4">
                <Card className="bg-surface shadow-md overflow-hidden border-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-red-600 flex items-center gap-2">
                            <AlertTriangle size={12} className="animate-pulse" /> Nível de Alerta
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-4xl font-black text-red-600">CRÍTICO</div>
                        <p className="text-[10px] mt-1 text-muted-foreground">3 Talhões atingiram o NDE</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md overflow-hidden ring-1 ring-border border-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-muted-foreground">Total Safra</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black">{monitoramentos?.length || 0}</div>
                        <p className="text-[10px] mt-1 text-muted-foreground">Levantamentos realizados</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md overflow-hidden ring-1 ring-border border-none">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-[10px] font-black uppercase text-primary">Cobertura Area</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-primary">82.4%</div>
                        <p className="text-[10px] mt-1 text-muted-foreground">Visitada nos últimos 10 dias</p>
                    </CardContent>
                </Card>

                <Card className="bg-surface shadow-md overflow-hidden border-none">
                    <CardHeader className="pb-2 flex flex-row items-center justify-between">
                        <CardTitle className="text-[10px] font-black uppercase text-blue-600">IA Diagnóstico</CardTitle>
                        <BrainCircuit size={16} className="text-blue-600" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-black text-blue-600">96%</div>
                        <p className="text-[10px] mt-1 text-muted-foreground">Precisão média identificação</p>
                    </CardContent>
                </Card>
            </div>

            <Card className="bg-surface shadow-xl border-none ring-1 ring-border overflow-hidden rounded-sm">
                <CardContent className="p-6">
                    <DataTable
                        data={monitoramentos || []}
                        columns={monitoramentoColumns}
                        searchable={true}
                        searchPlaceholder="Buscar por praga ou talhão..."
                        exportable={true}
                        exportFileName="monitoramento-pragas"
                    />
                </CardContent>
            </Card>
        </div>
    );
}
