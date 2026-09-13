"use client";

import { useState, useMemo } from "react";
import Map, { NavigationControl, Source, Layer } from "react-map-gl/maplibre";
import { FeatureCollection } from "geojson";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    FileUp, Layers, Activity, Pipette,
    Maximize2, Calendar, ArrowRight, Wand2
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue
} from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogDescription,
    DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useHasTier } from "@/hooks/use-has-tier";
import { Lock } from "lucide-react";
import Link from "next/link";

const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

interface Talhao {
    id: string;
    nome: string;
}

interface Safra {
    id: string;
    nome?: string;
    ano_safra?: string;
}

interface Prescricao {
    id: string;
    nome: string;
    tipo_operacao: string;
    status: string;
    insumo: string;
    data_prescricao: string;
    quantidade_total_estimada?: number;
    area_total_ha?: number;
}

interface PrescricaoForm {
    nome: string;
    tipo_operacao: string;
    insumo: string;
    safra_id: string;
    observacoes: string;
    area_total_ha: string;
    quantidade_total_estimada: string;
}

interface TipoOperacao {
    id: string;
    tipo_operacao: string;
    fases_permitidas: string[];
    descricao?: string | null;
}

export default function PrescricoesVRAPage() {
    const { activeFazendaId } = useAppStore();
    const queryClient = useQueryClient();
    const hasEnterpriseTier = useHasTier("ENTERPRISE");
    const [selectedTalhaoId, setSelectedTalhaoId] = useState<string>("");
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [activePrescricaoId, setActivePrescricaoId] = useState<string | null>(null);

    // Form State
    const [formData, setFormData] = useState<PrescricaoForm>({
        nome: "",
        tipo_operacao: "ADUBAÇÃO",
        insumo: "",
        safra_id: "",
        observacoes: "",
        area_total_ha: "",
        quantidade_total_estimada: ""
    });

    // Queries
    const { data: talhoes = [] } = useQuery<Talhao[]>({
        queryKey: ["talhoes", activeFazendaId],
        queryFn: () => apiFetch<Talhao[]>(`/cadastros/areas-rurais/?tipo=TALHAO&unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && hasEnterpriseTier
    });

    const { data: safras = [] } = useQuery<Safra[]>({
        queryKey: ["safras", activeFazendaId],
        queryFn: () => apiFetch<Safra[]>(`/safras/?unidade_produtiva_id=${activeFazendaId}`),
        enabled: !!activeFazendaId && hasEnterpriseTier
    });

    const { data: prescricoes = [] } = useQuery<Prescricao[]>({
        queryKey: ["prescricoes_vra", selectedTalhaoId],
        queryFn: () => apiFetch<Prescricao[]>(`/prescricoes/?talhao_id=${selectedTalhaoId}`),
        enabled: !!selectedTalhaoId && hasEnterpriseTier
    });

    const { data: tiposOperacao = [] } = useQuery<TipoOperacao[]>({
        queryKey: ["operacoes-tipos"],
        queryFn: () => apiFetch("/operacoes/tipos"),
        staleTime: 5 * 60 * 1000,
        enabled: hasEnterpriseTier,
    });

    const getTipoLabel = (tipo: string) =>
        tiposOperacao.find((item) => item.tipo_operacao === tipo)?.descricao || tipo;

    const createMutation = useMutation({
        mutationFn: (data: Omit<PrescricaoForm, "area_total_ha" | "quantidade_total_estimada"> & { talhao_id: string; area_total_ha: number; quantidade_total_estimada: number; data_prescricao: string }) => {
            if (!hasEnterpriseTier) {
                throw new Error("Prescrições VRA disponíveis no plano ENTERPRISE.");
            }
            return apiFetch("/prescricoes/", { method: "POST", body: JSON.stringify(data) });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["prescricoes_vra"] });
            toast.success("Mapa de prescrição gerado com sucesso!");
            setIsCreateDialogOpen(false);
        }
    });

    // TODO: motor de geração de zonas VRA ainda não existe no backend (prescricoes_vra
    // só persiste caminho_geojson, sem lógica de cálculo). Placeholder visual — não
    // representar como dado real do talhão selecionado até o backend gerar as zonas.
    const prescriptionGeoJSON = useMemo<FeatureCollection | null>(() => {
        if (!selectedTalhaoId) return null;

        return {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    properties: { rate: 180, zone: "Alta" },
                    geometry: {
                        type: "Polygon",
                        coordinates: [[
                            [-51.930, -23.420], [-51.925, -23.420],
                            [-51.925, -23.425], [-51.930, -23.425], [-51.930, -23.420]
                        ]]
                    }
                },
                {
                    type: "Feature",
                    properties: { rate: 120, zone: "Média" },
                    geometry: {
                        type: "Polygon",
                        coordinates: [[
                            [-51.925, -23.420], [-51.920, -23.420],
                            [-51.920, -23.425], [-51.925, -23.425], [-51.925, -23.420]
                        ]]
                    }
                }
            ]
        };
    }, [selectedTalhaoId]);

    const activePrescricao = prescricoes.find((p) => p.id === activePrescricaoId) || prescricoes[0];

    if (!hasEnterpriseTier) {
        return (
            <div className="p-6 space-y-6">
                <PageHeader
                    title="Mapas de Prescrição VRA"
                    description="Arquitetura de dados para Taxa Variável e Manejo de Alta Precisão."
                    icon={<Layers className="text-primary" size={22} />}
                    breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Prescrições VRA" }]}
                />
                <Alert className="rounded-sm">
                    <Lock className="size-4" />
                    <AlertTitle>Prescrições VRA disponíveis no ENTERPRISE</AlertTitle>
                    <AlertDescription className="space-y-3">
                        <p>Mapas de taxa variável, ingestão de sensores e exportações de prescrição exigem tier ENTERPRISE.</p>
                        <Button asChild size="sm" className="rounded-sm">
                            <Link href="/dashboard/settings/billing">Ver planos</Link>
                        </Button>
                    </AlertDescription>
                </Alert>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6 flex flex-col h-[calc(100vh-90px)] animate-in fade-in duration-700">
            <PageHeader
                title="Mapas de Prescrição VRA"
                description="Arquitetura de dados para Taxa Variável e Manejo de Alta Precisão."
                icon={<Layers className="text-primary" size={22} />}
                breadcrumbs={[{ label: "Agrícola", href: "/agricola" }, { label: "Prescrições VRA" }]}
                actions={
                    <div className="flex items-center gap-3 bg-muted/30 p-1 rounded-sm border border-border/40">
                        <Select value={selectedTalhaoId} onValueChange={setSelectedTalhaoId}>
                            <SelectTrigger className="w-[200px] h-8 bg-background border-none rounded-sm font-bold shadow-sm text-xs">
                                <SelectValue placeholder="Selecione o Talhão" />
                            </SelectTrigger>
                            <SelectContent className="rounded-sm border-border/40">
                                {talhoes.map((t) => (
                                    <SelectItem key={t.id} value={t.id} className="font-bold text-xs">{t.nome}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <Separator orientation="vertical" className="h-4" />
                        <Button
                            size="sm"
                            variant="outline"
                            className="rounded-sm gap-2 font-black shadow-lg shadow-primary/5 h-8 text-xs"
                            onClick={() => setIsCreateDialogOpen(true)}
                        >
                            <Wand2 size={14} /> Gerar VRA
                        </Button>
                    </div>
                }
            />

            <div className="relative flex-1 rounded-sm overflow-hidden border border-border/40 shadow-2xl flex flex-col md:flex-row bg-background">
                {/* Sidebar: Prescricao Catalog */}
                <div className="w-full md:w-96 border-b md:border-b-0 md:border-r border-border/20 flex flex-col z-10 bg-background/85">
                    <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground flex items-center gap-2">
                                <Activity size={12} className="text-primary" /> Histórico de Prescrições
                            </h3>

                            <div className="space-y-3">
                                {prescricoes.length === 0 ? (
                                    <div className="py-12 border-2 border-dashed rounded-sm text-center opacity-40 flex flex-col items-center gap-3">
                                        <FileUp size={32} />
                                        <p className="text-xs font-black uppercase">Nenhum mapa importado</p>
                                    </div>
                                ) : (
                                    prescricoes.map((p) => (
                                        <button
                                            type="button"
                                            key={p.id}
                                            onClick={() => setActivePrescricaoId(p.id)}
                                            aria-pressed={activePrescricaoId === p.id}
                                            className={`p-4 rounded-sm border-2 transition-all cursor-pointer group relative overflow-hidden
                                                w-full text-left ${activePrescricaoId === p.id ? 'border-primary bg-primary/5 shadow-md' : 'border-transparent bg-muted/30 hover:bg-muted/50'}`}
                                        >
                                            <div className="flex justify-between items-start mb-2 relative z-10">
                                                <div className="space-y-1">
                                                    <span className="text-sm font-black uppercase block">{p.nome}</span>
                                                    <Badge variant="outline" className="text-[9px] font-black border-none bg-primary/20 px-1.5 h-4">{getTipoLabel(p.tipo_operacao)}</Badge>
                                                </div>
                                                <Badge className={`border-none text-[9px] font-black ${p.status === 'PENDENTE' ? 'bg-amber-500/20 text-amber-600' : 'bg-green-500/20 text-green-600'}`}>
                                                    {p.status}
                                                </Badge>
                                            </div>
                                            <div className="flex items-center gap-4 text-[10px] font-bold text-muted-foreground relative z-10">
                                                <p className="flex items-center gap-1.5"><Pipette size={12} className="text-primary" /> {p.insumo}</p>
                                                <p className="flex items-center gap-1.5"><Calendar size={12} /> {new Date(p.data_prescricao).toLocaleDateString()}</p>
                                            </div>
                                            {activePrescricaoId === p.id && (
                                                <div className="absolute right-0 top-0 bottom-0 w-1 bg-primary" />
                                            )}
                                        </button>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Quick Specs Panel */}
                    {activePrescricao && (
                        <div className="p-6 bg-muted/20 border-t border-border/20">
                            <Card className="border-none bg-background/50 rounded-sm shadow-sm">
                                <CardContent className="p-4 space-y-4">
                                    <div className="flex justify-between items-center">
                                        <p className="text-[10px] font-black uppercase text-muted-foreground">Configuração da Calda</p>
                                        <ArrowRight size={14} className="text-primary" />
                                    </div>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-0.5">
                                            <p className="text-[9px] font-bold text-muted-foreground uppercase">Volume Total</p>
                                            <p className="text-lg font-black">{activePrescricao.quantidade_total_estimada || 0} <span className="text-[10px]">kg</span></p>
                                        </div>
                                        <div className="space-y-0.5 border-l border-border/20 pl-4">
                                            <p className="text-[9px] font-bold text-muted-foreground uppercase">Área Alvo</p>
                                            <p className="text-lg font-black">{activePrescricao.area_total_ha || 0} <span className="text-[10px]">ha</span></p>
                                        </div>
                                    </div>
                                    <Button className="w-full rounded-sm h-10 font-bold gap-2 text-xs" variant="outline">
                                        <FileUp size={14} /> Exportar para Monitor (USB)
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    )}
                </div>

                {/* Main Map Viewer */}
                <div className="flex-1 relative bg-muted/10">
                    <Map
                        mapLib={maplibregl}
                        initialViewState={{
                            longitude: -51.9253,
                            latitude: -23.4205,
                            zoom: 14
                        }}
                        mapStyle={MAP_STYLE}
                        style={{ width: "100%", height: "100%" }}
                    >
                        <NavigationControl position="top-right" />

                        {/* Rendering Prescriptions if available */}
                        {prescriptionGeoJSON && (
                            <Source id="vra-zones" type="geojson" data={prescriptionGeoJSON}>
                                <Layer
                                    id="vra-fills"
                                    type="fill"
                                    paint={{
                                        "fill-color": [
                                            "interpolate", ["linear"], ["get", "rate"],
                                            0, "#ff4d4d",
                                            100, "#ffa352",
                                            200, "#2fb344"
                                        ],
                                        "fill-opacity": 0.4
                                    }}
                                />
                                <Layer
                                    id="vra-borders"
                                    type="line"
                                    paint={{
                                        "line-color": "#ffffff",
                                        "line-width": 1,
                                        "line-opacity": 0.3
                                    }}
                                />
                            </Source>
                        )}

                        {prescriptionGeoJSON && (
                            <div className="absolute top-6 right-6 z-10">
                                <Badge variant="outline" className="bg-background/90 backdrop-blur-md text-[9px] font-black uppercase tracking-wider border-amber-400 text-amber-600 px-2 py-1">
                                    Zonas ilustrativas — motor de cálculo VRA em desenvolvimento
                                </Badge>
                            </div>
                        )}

                        {/* Legend Overlay */}
                        <div className="absolute top-6 left-6 p-5 bg-background/80 backdrop-blur-md rounded-sm shadow-2xl border border-border/20 min-w-[200px]">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-[10px] font-black uppercase tracking-[0.1em] text-primary">Mapa de Taxas</h4>
                                    <Badge className="h-4 px-1 text-[8px] bg-primary/10 text-primary border-none">kg/ha</Badge>
                                </div>
                                <div className="space-y-2.5">
                                    <div className="flex items-center justify-between text-[11px] font-bold">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-red-500 shadow-sm" />
                                            <span>Baixa</span>
                                        </div>
                                        <span className="text-muted-foregrounder">0 - 50</span>
                                    </div>
                                    <div className="flex items-center justify-between text-[11px] font-bold">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-orange-400 shadow-sm" />
                                            <span>Média</span>
                                        </div>
                                        <span className="text-muted-foregrounder">50 - 150</span>
                                    </div>
                                    <div className="flex items-center justify-between text-[11px] font-bold">
                                        <div className="flex items-center gap-2">
                                            <div className="w-3 h-3 rounded-full bg-green-500 shadow-sm" />
                                            <span>Alta</span>
                                        </div>
                                        <span className="text-muted-foregrounder">150+</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Activity floating control */}
                        <div className="absolute bottom-8 right-8 flex flex-col gap-3">
                            <Button size="icon" variant="secondary" className="rounded-sm shadow-xl h-12 w-12 bg-background border-none hover:scale-105 active:scale-95 transition-all">
                                <Maximize2 className="size-5" />
                            </Button>
                        </div>
                    </Map>
                </div>
            </div>

            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                <DialogContent className="sm:max-w-[600px] rounded-sm p-0 overflow-hidden border-none shadow-2xl">
                    <div className="bg-gradient-to-br from-primary to-green-600 p-8 text-white">
                        <DialogHeader>
                            <DialogTitle className="text-3xl font-black">Gerar Prescrição Inteligente</DialogTitle>
                            <DialogDescription className="text-primary-foreground/80 font-bold uppercase text-[10px] tracking-widest mt-1">
                                Algoritmo VRA baseado em NDVI e Sensores.
                            </DialogDescription>
                        </DialogHeader>
                    </div>

                    <div className="p-8 bg-background space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Nome do Mapa</label>
                                <Input
                                    className="rounded-sm bg-muted/50 border-none h-12 font-bold"
                                    placeholder="Ex: Reforço N-P-K"
                                    value={formData.nome}
                                    onChange={e => setFormData({ ...formData, nome: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Safra</label>
                                <Select value={formData.safra_id} onValueChange={(v: string) => setFormData({ ...formData, safra_id: v })}>
                                    <SelectTrigger className="rounded-sm bg-muted/50 border-none h-12 font-bold">
                                        <SelectValue placeholder="Selecione..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {safras.map((s) => <SelectItem key={s.id} value={s.id}>{s.nome || s.ano_safra}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Insumo Base</label>
                                <Input
                                    className="rounded-sm bg-muted/50 border-none h-12 font-bold"
                                    placeholder="Ex: Ureia Coberta"
                                    value={formData.insumo}
                                    onChange={e => setFormData({ ...formData, insumo: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Fonte de Dados</label>
                                <Select defaultValue="ndvi">
                                    <SelectTrigger className="rounded-sm bg-muted/50 border-none h-12 font-bold">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="ndvi">Sentinel-2 (NDVI)</SelectItem>
                                        <SelectItem value="solo">Grade Amostragem Solo</SelectItem>
                                        <SelectItem value="manual">Desenho Livre</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Área Total (ha)</label>
                                <Input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    className="rounded-sm bg-muted/50 border-none h-12 font-bold"
                                    placeholder="Ex: 15,50"
                                    value={formData.area_total_ha}
                                    onChange={e => setFormData({ ...formData, area_total_ha: e.target.value })}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Quantidade Total Estimada</label>
                                <Input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    className="rounded-sm bg-muted/50 border-none h-12 font-bold"
                                    placeholder="Ex: 2500"
                                    value={formData.quantidade_total_estimada}
                                    onChange={e => setFormData({ ...formData, quantidade_total_estimada: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-[10px] font-black uppercase text-muted-foreground px-1">Observações Técnicas</label>
                            <Textarea
                                className="rounded-sm bg-muted/50 border-none min-h-[100px] font-medium"
                                placeholder="Notas para o operador do trator..."
                                value={formData.observacoes}
                                onChange={e => setFormData({ ...formData, observacoes: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="p-8 pt-0 flex gap-3">
                        <Button variant="outline" className="h-14 rounded-sm flex-1 font-black uppercase text-xs" onClick={() => setIsCreateDialogOpen(false)}>
                            Cancelar
                        </Button>
                        <Button
                            className="h-14 rounded-sm flex-[2] font-black text-lg shadow-xl shadow-primary/20"
                            disabled={createMutation.isPending}
                            onClick={() => {
                                if (!selectedTalhaoId || !formData.safra_id) {
                                    toast.error("Talhão e Safra são obrigatórios!");
                                    return;
                                }
                                const areaTotalHa = Number(formData.area_total_ha.replace(",", "."));
                                const quantidadeTotalEstimada = Number(formData.quantidade_total_estimada.replace(",", "."));
                                if (!formData.area_total_ha || !Number.isFinite(areaTotalHa) || areaTotalHa <= 0) {
                                    toast.error("Informe a área total (ha) da prescrição.");
                                    return;
                                }
                                if (!formData.quantidade_total_estimada || !Number.isFinite(quantidadeTotalEstimada) || quantidadeTotalEstimada <= 0) {
                                    toast.error("Informe a quantidade total estimada.");
                                    return;
                                }
                                const { area_total_ha, quantidade_total_estimada, ...rest } = formData;
                                createMutation.mutate({
                                    ...rest,
                                    talhao_id: selectedTalhaoId,
                                    area_total_ha: areaTotalHa,
                                    quantidade_total_estimada: quantidadeTotalEstimada,
                                    data_prescricao: new Date().toISOString().split('T')[0]
                                });
                            }}
                        >
                            {createMutation.isPending ? "Processando..." : "Gerar Mapa VRA"}
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
