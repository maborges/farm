"use client";

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    BookOpen,
    Sprout,
    Scale,
    ArrowRightLeft,
    Search,
    Plus,
    Edit,
    Trash2,
    Power,
    ShieldAlert,
    AlertTriangle,
    Download,
    FileSpreadsheet,
    FileText,
    CheckCircle2,
    X,
    Filter,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from "@/components/ui/dialog";

// Tipos estritos sem "any"
interface CommodityItem {
    id: string;
    nome: string;
    codigo: string;
    tipo: string;
    unidade_padrao: string;
    peso_unidade: number | null;
    umidade_padrao_pct: number | null;
    impureza_padrao_pct: number | null;
    possui_cotacao: boolean;
    bolsa_referencia: string | null;
    codigo_bolsa: string | null;
    ativo: boolean;
    sistema: boolean;
    descricao: string | null;
}

interface CommodityListResponse {
    itens: CommodityItem[];
    total: number;
    pagina: number;
    tamanho_pagina: number;
}

interface CulturaItem {
    id: string;
    nome: string;
    nome_cientifico: string | null;
    grupo: string | null;
    ciclo_dias_min: number | null;
    ciclo_dias_max: number | null;
    espacamento_cm: number | null;
    populacao_plantas_ha: number | null;
    produtividade_media_sc_ha: number | null;
    v_meta_pct_padrao: number | null;
    ativa: boolean;
    sistema: boolean;
}

interface CulturaListResponse {
    itens: CulturaItem[];
    total: number;
    pagina: number;
    tamanho_pagina: number;
}

interface UomItem {
    id: string;
    codigo: string;
    nome: string;
    dimensao: string;
    codigo_referencia: string;
    fator_referencia: number;
    casas_decimais: number;
    eh_unidade_base: boolean;
    ativo: boolean;
    sistema: boolean;
}

interface UomListResponse {
    itens: UomItem[];
    total: number;
    pagina: number;
    tamanho_pagina: number;
}

interface UomConversaoItem {
    id: string;
    unidade_origem_id: string;
    unidade_destino_id: string;
    fator: number;
    cultura: string | null;
    commodity_id: string | null;
    observacoes: string | null;
}

interface UomConversaoListResponse {
    itens: UomConversaoItem[];
    total: number;
    pagina: number;
    tamanho_pagina: number;
}

export default function BibliotecasGlobaisPage() {
    const queryClient = useQueryClient();
    const canEdit = usePermission("backoffice:agro:config:edit");

    // Estados de filtros
    const [tabAtiva, setTabAtiva] = useState("commodities");
    const [termoBusca, setTermoBusca] = useState("");
    const [pagina, setPagina] = useState(1);

    // Modal de Cadastro/Edição de Commodity
    const [modalCommodityAberto, setModalCommodityAberto] = useState(false);
    const [commodityEmEdicao, setCommodityEmEdicao] = useState<Partial<CommodityItem> | null>(null);

    // Modal de confirmação de exclusão
    const [modalExclusaoAberto, setModalExclusaoAberto] = useState(false);
    const [itemParaExcluir, setItemParaExcluir] = useState<{ tipo: string; id: string; nome: string } | null>(null);

    // Queries
    const { data: commoditiesData, isLoading: loadingCommodities } = useQuery<CommodityListResponse>({
        queryKey: ["agro-commodities", termoBusca, pagina],
        queryFn: () =>
            apiFetch(
                `/api/v1/backoffice/agro/catalogo/commodities?q=${encodeURIComponent(termoBusca)}&pagina=${pagina}&tamanho_pagina=20`
            ),
        enabled: tabAtiva === "commodities",
    });

    const { data: culturasData, isLoading: loadingCulturas } = useQuery<CulturaListResponse>({
        queryKey: ["agro-culturas", termoBusca, pagina],
        queryFn: () =>
            apiFetch(
                `/api/v1/backoffice/agro/catalogo/culturas?q=${encodeURIComponent(termoBusca)}&pagina=${pagina}&tamanho_pagina=20`
            ),
        enabled: tabAtiva === "culturas",
    });

    const { data: uomData, isLoading: loadingUom } = useQuery<UomListResponse>({
        queryKey: ["agro-uom", termoBusca, pagina],
        queryFn: () =>
            apiFetch(
                `/api/v1/backoffice/agro/catalogo/unidades?q=${encodeURIComponent(termoBusca)}&pagina=${pagina}&tamanho_pagina=50`
            ),
        enabled: tabAtiva === "unidades",
    });

    const { data: conversoesData, isLoading: loadingConversoes } = useQuery<UomConversaoListResponse>({
        queryKey: ["agro-conversoes", pagina],
        queryFn: () =>
            apiFetch(`/api/v1/backoffice/agro/catalogo/conversoes?pagina=${pagina}&tamanho_pagina=50`),
        enabled: tabAtiva === "conversoes",
    });

    // Mutations
    const salvarCommodityMutation = useMutation({
        mutationFn: async (dados: Partial<CommodityItem>) => {
            if (dados.id) {
                return apiFetch(`/api/v1/backoffice/agro/catalogo/commodities/${dados.id}`, {
                    method: "PUT",
                    body: JSON.stringify(dados),
                });
            } else {
                return apiFetch(`/api/v1/backoffice/agro/catalogo/commodities`, {
                    method: "POST",
                    body: JSON.stringify(dados),
                });
            }
        },
        onSuccess: () => {
            toast.success("Commodity global salva com sucesso!");
            setModalCommodityAberto(false);
            setCommodityEmEdicao(null);
            queryClient.invalidateQueries({ queryKey: ["agro-commodities"] });
        },
        onError: (err: Error) => {
            toast.error(`Falha ao salvar commodity: ${err.message}`);
        },
    });

    const excluirItemMutation = useMutation({
        mutationFn: async ({ tipo, id }: { tipo: string; id: string }) => {
            return apiFetch(`/api/v1/backoffice/agro/catalogo/${tipo}/${id}`, {
                method: "DELETE",
            });
        },
        onSuccess: () => {
            toast.success("Item removido com sucesso!");
            setModalExclusaoAberto(false);
            setItemParaExcluir(null);
            queryClient.invalidateQueries({ queryKey: ["agro-commodities"] });
            queryClient.invalidateQueries({ queryKey: ["agro-culturas"] });
            queryClient.invalidateQueries({ queryKey: ["agro-uom"] });
            queryClient.invalidateQueries({ queryKey: ["agro-conversoes"] });
        },
        onError: (err: Error) => {
            toast.error(`Não foi possível excluir: ${err.message}`);
        },
    });

    // Função de exportação para CSV
    const exportarCSV = (dados: Array<Record<string, unknown>>, nomeArquivo: string) => {
        if (!dados || dados.length === 0) {
            toast.error("Nenhum registro para exportar.");
            return;
        }
        const colunas = Object.keys(dados[0]);
        const linhas = dados.map((row) =>
            colunas.map((col) => JSON.stringify(row[col] ?? "")).join(",")
        );
        const conteudo = [colunas.join(","), ...linhas].join("\n");
        const blob = new Blob([conteudo], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${nomeArquivo}-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success("Exportação concluída com sucesso.");
    };

    return (
        <div className="p-8 space-y-6 w-full max-w-full">
            <PageHeader
                title="Bibliotecas Globais & Catálogos"
                description="Governança de commodities padronizadas, culturas agrícolas e unidades de medida compartilhadas no ecossistema DeepFarms Agro."
            />

            {/* Banner de Isolamento Multi-Tenant */}
            <Alert className="border-emerald-600/30 bg-emerald-500/10 text-emerald-950 dark:text-emerald-200 rounded-sm">
                <ShieldAlert className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <AlertTitle className="text-xs font-bold uppercase tracking-wider">
                    Governança Canônica Compartilhada (Multi-Tenant Segregado)
                </AlertTitle>
                <AlertDescription className="text-xs mt-1 leading-relaxed">
                    Os registros desta biblioteca possuem escopo global (<code className="font-mono text-[11px]">tenant_id = NULL</code>, <code className="font-mono text-[11px]">sistema = True</code>) e servem como referência pública para o aplicativo gratuito e cadastros do SaaS. Alterações preservam estritamente o isolamento de dados privados dos clientes comerciais.
                </AlertDescription>
            </Alert>

            {/* Controle de Tabs */}
            <Tabs
                defaultValue="commodities"
                value={tabAtiva}
                onValueChange={(val) => {
                    setTabAtiva(val);
                    setPagina(1);
                    setTermoBusca("");
                }}
                className="w-full"
            >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2">
                    <TabsList className="bg-muted/80 rounded-sm p-1 border gap-1">
                        <TabsTrigger value="commodities" className="rounded-sm text-xs gap-1.5 font-semibold">
                            <BookOpen size={13} />
                            Commodities Globais
                        </TabsTrigger>
                        <TabsTrigger value="culturas" className="rounded-sm text-xs gap-1.5 font-semibold">
                            <Sprout size={13} />
                            Culturas Agrícolas
                        </TabsTrigger>
                        <TabsTrigger value="unidades" className="rounded-sm text-xs gap-1.5 font-semibold">
                            <Scale size={13} />
                            Unidades de Medida
                        </TabsTrigger>
                        <TabsTrigger value="conversoes" className="rounded-sm text-xs gap-1.5 font-semibold">
                            <ArrowRightLeft size={13} />
                            Regras de Conversão
                        </TabsTrigger>
                    </TabsList>

                    {/* Barra de Ações / Pesquisa */}
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                            <Input
                                placeholder="Pesquisar por nome ou código..."
                                value={termoBusca}
                                onChange={(e) => {
                                    setTermoBusca(e.target.value);
                                    setPagina(1);
                                }}
                                className="h-8 pl-8 text-xs w-56 rounded-sm"
                            />
                        </div>

                        {tabAtiva === "commodities" && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                    exportarCSV(
                                        (commoditiesData?.itens ?? []) as unknown as Array<Record<string, unknown>>,
                                        "commodities-globais"
                                    )
                                }
                                className="rounded-sm h-8 text-xs gap-1.5"
                                title="Exportar tabela para CSV"
                            >
                                <Download size={13} />
                                CSV
                            </Button>
                        )}

                        {canEdit && tabAtiva === "commodities" && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    setCommodityEmEdicao({
                                        tipo: "AGRICOLA",
                                        unidade_padrao: "SACA_60KG",
                                        peso_unidade: 60.0,
                                        ativo: true,
                                        possui_cotacao: false,
                                    });
                                    setModalCommodityAberto(true);
                                }}
                                className="rounded-sm h-8 text-xs gap-1.5 border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300"
                            >
                                <Plus size={14} />
                                Nova Commodity
                            </Button>
                        )}
                    </div>
                </div>

                {/* ABA 1: COMMODITIES */}
                <TabsContent value="commodities" className="mt-2">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Catálogo Oficial de Commodities</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Padrões de mercado para comercialização, precificação e cálculo de romaneio.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Total: {commoditiesData?.total ?? 0}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingCommodities ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">Código</th>
                                                <th className="py-2.5 px-4 font-semibold">Nome</th>
                                                <th className="py-2.5 px-4 font-semibold">Tipo</th>
                                                <th className="py-2.5 px-4 font-semibold">Unidade Padrão</th>
                                                <th className="py-2.5 px-4 font-semibold">Cotação</th>
                                                <th className="py-2.5 px-4 font-semibold">Status</th>
                                                <th className="py-2.5 px-4 text-right"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {commoditiesData?.itens.length === 0 ? (
                                                <tr>
                                                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                                                        Nenhuma commodity global encontrada.
                                                    </td>
                                                </tr>
                                            ) : (
                                                commoditiesData?.itens.map((item) => (
                                                    <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                                                        <td className="py-2 px-4 font-mono font-bold text-foreground">
                                                            {item.codigo}
                                                        </td>
                                                        <td className="py-2 px-4 font-semibold">{item.nome}</td>
                                                        <td className="py-2 px-4">
                                                            <Badge variant="outline" className="text-[10px] rounded-sm uppercase">
                                                                {item.tipo}
                                                            </Badge>
                                                        </td>
                                                        <td className="py-2 px-4 font-mono text-muted-foreground">
                                                            {item.unidade_padrao} {item.peso_unidade ? `(${item.peso_unidade}kg)` : ""}
                                                        </td>
                                                        <td className="py-2 px-4">
                                                            {item.possui_cotacao ? (
                                                                <Badge className="text-[10px] rounded-sm bg-emerald-600 text-white">
                                                                    {item.bolsa_referencia ?? "Sim"}
                                                                </Badge>
                                                            ) : (
                                                                <span className="text-muted-foreground text-[11px]">—</span>
                                                            )}
                                                        </td>
                                                        <td className="py-2 px-4">
                                                            {item.ativo ? (
                                                                <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-[11px]">
                                                                    <CheckCircle2 size={12} /> Ativo
                                                                </span>
                                                            ) : (
                                                                <span className="text-muted-foreground text-[11px]">Inativo</span>
                                                            )}
                                                        </td>
                                                        <td className="py-2 px-4 text-right">
                                                            <div className="flex items-center justify-end gap-0">
                                                                {canEdit && (
                                                                    <>
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            onClick={() => {
                                                                                setCommodityEmEdicao(item);
                                                                                setModalCommodityAberto(true);
                                                                            }}
                                                                            className="h-7 w-7 p-0 rounded-sm text-muted-foreground hover:text-foreground"
                                                                            title="Editar commodity"
                                                                        >
                                                                            <Edit size={13} />
                                                                        </Button>
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="sm"
                                                                            onClick={() => {
                                                                                setItemParaExcluir({
                                                                                    tipo: "commodities",
                                                                                    id: item.id,
                                                                                    nome: item.nome,
                                                                                });
                                                                                setModalExclusaoAberto(true);
                                                                            }}
                                                                            className="h-7 w-7 p-0 rounded-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                                                                            title="Excluir commodity"
                                                                        >
                                                                            <Trash2 size={13} />
                                                                        </Button>
                                                                    </>
                                                                )}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 2: CULTURAS AGRÍCOLAS */}
                <TabsContent value="culturas" className="mt-2">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Culturas Agrícolas Canônicas</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Espécies botânicas, ciclos agronômicos e parâmetros padrão de solo.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Total: {culturasData?.total ?? 0}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingCulturas ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">Nome Comum</th>
                                                <th className="py-2.5 px-4 font-semibold">Nome Científico</th>
                                                <th className="py-2.5 px-4 font-semibold">Grupo</th>
                                                <th className="py-2.5 px-4 font-semibold">Ciclo (dias)</th>
                                                <th className="py-2.5 px-4 font-semibold">V% Meta</th>
                                                <th className="py-2.5 px-4 font-semibold">Status</th>
                                                <th className="py-2.5 px-4 text-right"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {culturasData?.itens.map((item) => (
                                                <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                                                    <td className="py-2 px-4 font-bold text-foreground">{item.nome}</td>
                                                    <td className="py-2 px-4 italic text-muted-foreground">
                                                        {item.nome_cientifico ?? "—"}
                                                    </td>
                                                    <td className="py-2 px-4">
                                                        <Badge variant="outline" className="text-[10px] rounded-sm">
                                                            {item.grupo ?? "GERAL"}
                                                        </Badge>
                                                    </td>
                                                    <td className="py-2 px-4 font-mono">
                                                        {item.ciclo_dias_min && item.ciclo_dias_max
                                                            ? `${item.ciclo_dias_min} - ${item.ciclo_dias_max}`
                                                            : "—"}
                                                    </td>
                                                    <td className="py-2 px-4 font-mono">
                                                        {item.v_meta_pct_padrao ? `${item.v_meta_pct_padrao}%` : "—"}
                                                    </td>
                                                    <td className="py-2 px-4">
                                                        {item.ativa ? (
                                                            <span className="text-emerald-600 font-semibold text-[11px]">
                                                                Ativa
                                                            </span>
                                                        ) : (
                                                            <span className="text-muted-foreground text-[11px]">Inativa</span>
                                                        )}
                                                    </td>
                                                    <td className="py-2 px-4 text-right">
                                                        {canEdit && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setItemParaExcluir({
                                                                        tipo: "culturas",
                                                                        id: item.id,
                                                                        nome: item.nome,
                                                                    });
                                                                    setModalExclusaoAberto(true);
                                                                }}
                                                                className="h-7 w-7 p-0 rounded-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                                                                title="Excluir cultura"
                                                            >
                                                                <Trash2 size={13} />
                                                            </Button>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 3: UNIDADES DE MEDIDA */}
                <TabsContent value="unidades" className="mt-2">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Unidades de Medida Canônicas</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Padrões SI e agronômicos (Massa, Volume, Área, Contagem).
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Total: {uomData?.total ?? 0}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingUom ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">Código</th>
                                                <th className="py-2.5 px-4 font-semibold">Nome</th>
                                                <th className="py-2.5 px-4 font-semibold">Dimensão</th>
                                                <th className="py-2.5 px-4 font-semibold">Referência</th>
                                                <th className="py-2.5 px-4 font-semibold">Fator Base</th>
                                                <th className="py-2.5 px-4 font-semibold">Decimais</th>
                                                <th className="py-2.5 px-4 font-semibold">Status</th>
                                                <th className="py-2.5 px-4 text-right"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {uomData?.itens.map((item) => (
                                                <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                                                    <td className="py-2 px-4 font-mono font-bold">{item.codigo}</td>
                                                    <td className="py-2 px-4 font-semibold">{item.nome}</td>
                                                    <td className="py-2 px-4">
                                                        <Badge variant="outline" className="text-[10px] rounded-sm">
                                                            {item.dimensao}
                                                        </Badge>
                                                    </td>
                                                    <td className="py-2 px-4 font-mono text-muted-foreground">
                                                        {item.codigo_referencia}
                                                    </td>
                                                    <td className="py-2 px-4 font-mono">{item.fator_referencia}</td>
                                                    <td className="py-2 px-4 font-mono">{item.casas_decimais}</td>
                                                    <td className="py-2 px-4">
                                                        {item.ativo ? (
                                                            <span className="text-emerald-600 font-semibold text-[11px]">
                                                                Ativo
                                                            </span>
                                                        ) : (
                                                            <span className="text-muted-foreground text-[11px]">Inativo</span>
                                                        )}
                                                    </td>
                                                    <td className="py-2 px-4 text-right">
                                                        {canEdit && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setItemParaExcluir({
                                                                        tipo: "unidades",
                                                                        id: item.id,
                                                                        nome: item.codigo,
                                                                    });
                                                                    setModalExclusaoAberto(true);
                                                                }}
                                                                className="h-7 w-7 p-0 rounded-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                                                                title="Excluir unidade"
                                                            >
                                                                <Trash2 size={13} />
                                                            </Button>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 4: REGRAS DE CONVERSÃO */}
                <TabsContent value="conversoes" className="mt-2">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="py-3 px-4 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Fatores de Conversão Padronizados</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Matriz de equivalência para romaneios, fretes e cotações.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Total: {conversoesData?.total ?? 0}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-0">
                            {loadingConversoes ? (
                                <div className="p-6 space-y-2">
                                    <Skeleton className="h-6 w-full" />
                                    <Skeleton className="h-6 w-full" />
                                </div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-xs text-left border-collapse">
                                        <thead className="bg-muted/50 border-b text-muted-foreground uppercase text-[10px] tracking-wider">
                                            <tr>
                                                <th className="py-2.5 px-4 font-semibold">Origem ID</th>
                                                <th className="py-2.5 px-4 font-semibold">Destino ID</th>
                                                <th className="py-2.5 px-4 font-semibold">Fator Multiplicador</th>
                                                <th className="py-2.5 px-4 font-semibold">Cultura Específica</th>
                                                <th className="py-2.5 px-4 font-semibold">Observações</th>
                                                <th className="py-2.5 px-4 text-right"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y">
                                            {conversoesData?.itens.map((item) => (
                                                <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                                                    <td className="py-2 px-4 font-mono">{item.unidade_origem_id.slice(0, 8)}...</td>
                                                    <td className="py-2 px-4 font-mono">{item.unidade_destino_id.slice(0, 8)}...</td>
                                                    <td className="py-2 px-4 font-mono font-bold text-foreground">
                                                        {item.fator}
                                                    </td>
                                                    <td className="py-2 px-4">{item.cultura ?? "Todas"}</td>
                                                    <td className="py-2 px-4 text-muted-foreground">{item.observacoes ?? "—"}</td>
                                                    <td className="py-2 px-4 text-right">
                                                        {canEdit && (
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => {
                                                                    setItemParaExcluir({
                                                                        tipo: "conversoes",
                                                                        id: item.id,
                                                                        nome: `Fator ${item.fator}`,
                                                                    });
                                                                    setModalExclusaoAberto(true);
                                                                }}
                                                                className="h-7 w-7 p-0 rounded-sm text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
                                                                title="Excluir conversão"
                                                            >
                                                                <Trash2 size={13} />
                                                            </Button>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>

            {/* MODAL DE CADASTRO / EDIÇÃO DE COMMODITY */}
            <Dialog open={modalCommodityAberto} onOpenChange={setModalCommodityAberto}>
                <DialogContent className="max-w-md rounded-sm">
                    <DialogHeader>
                        <DialogTitle className="text-sm font-bold">
                            {commodityEmEdicao?.id ? "Editar Commodity Global" : "Cadastrar Nova Commodity Global"}
                        </DialogTitle>
                        <DialogDescription className="text-xs">
                            Defina os metadados oficiais e parâmetros comerciais da commodity.
                        </DialogDescription>
                    </DialogHeader>

                    <form
                        onSubmit={(e) => {
                            e.preventDefault();
                            if (commodityEmEdicao) {
                                salvarCommodityMutation.mutate(commodityEmEdicao);
                            }
                        }}
                        className="space-y-3 pt-2"
                    >
                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <Label htmlFor="cod" className="text-xs font-semibold">
                                    Código Canônico
                                </Label>
                                <Input
                                    id="cod"
                                    value={commodityEmEdicao?.codigo ?? ""}
                                    onChange={(e) =>
                                        setCommodityEmEdicao((prev) => (prev ? { ...prev, codigo: e.target.value.toUpperCase() } : null))
                                    }
                                    placeholder="SOJA_GRAO"
                                    disabled={Boolean(commodityEmEdicao?.id)}
                                    className="h-8 text-xs font-mono rounded-sm"
                                    required
                                />
                            </div>

                            <div className="space-y-1">
                                <Label htmlFor="tipo" className="text-xs font-semibold">
                                    Tipo
                                </Label>
                                <select
                                    id="tipo"
                                    value={commodityEmEdicao?.tipo ?? "AGRICOLA"}
                                    onChange={(e) =>
                                        setCommodityEmEdicao((prev) => (prev ? { ...prev, tipo: e.target.value } : null))
                                    }
                                    className="w-full h-8 px-2 text-xs border rounded-sm bg-background"
                                >
                                    <option value="AGRICOLA">AGRICOLA</option>
                                    <option value="PECUARIA">PECUARIA</option>
                                    <option value="FLORESTAL">FLORESTAL</option>
                                </select>
                            </div>
                        </div>

                        <div className="space-y-1">
                            <Label htmlFor="nome" className="text-xs font-semibold">
                                Nome da Commodity
                            </Label>
                            <Input
                                id="nome"
                                value={commodityEmEdicao?.nome ?? ""}
                                onChange={(e) =>
                                    setCommodityEmEdicao((prev) => (prev ? { ...prev, nome: e.target.value } : null))
                                }
                                placeholder="Soja em Grão"
                                className="h-8 text-xs rounded-sm"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div className="space-y-1">
                                <Label htmlFor="uom" className="text-xs font-semibold">
                                    Unidade Padrão
                                </Label>
                                <Input
                                    id="uom"
                                    value={commodityEmEdicao?.unidade_padrao ?? "SACA_60KG"}
                                    onChange={(e) =>
                                        setCommodityEmEdicao((prev) => (prev ? { ...prev, unidade_padrao: e.target.value } : null))
                                    }
                                    className="h-8 text-xs font-mono rounded-sm"
                                    required
                                />
                            </div>

                            <div className="space-y-1">
                                <Label htmlFor="peso" className="text-xs font-semibold">
                                    Peso (kg)
                                </Label>
                                <Input
                                    id="peso"
                                    type="number"
                                    step="0.1"
                                    value={commodityEmEdicao?.peso_unidade ?? ""}
                                    onChange={(e) =>
                                        setCommodityEmEdicao((prev) =>
                                            prev ? { ...prev, peso_unidade: parseFloat(e.target.value) || null } : null
                                        )
                                    }
                                    placeholder="60.0"
                                    className="h-8 text-xs font-mono rounded-sm"
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <Label htmlFor="desc" className="text-xs font-semibold">
                                Descrição / Normas Técnicas
                            </Label>
                            <Input
                                id="desc"
                                value={commodityEmEdicao?.descricao ?? ""}
                                onChange={(e) =>
                                    setCommodityEmEdicao((prev) => (prev ? { ...prev, descricao: e.target.value } : null))
                                }
                                placeholder="Padrão exportação MAPA / DERAL"
                                className="h-8 text-xs rounded-sm"
                            />
                        </div>

                        <DialogFooter className="pt-3">
                            <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setModalCommodityAberto(false)}
                                className="rounded-sm h-8 text-xs"
                            >
                                Cancelar
                            </Button>
                            <Button
                                type="submit"
                                variant="outline"
                                size="sm"
                                disabled={salvarCommodityMutation.isPending}
                                className="rounded-sm h-8 text-xs font-semibold border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300"
                            >
                                {salvarCommodityMutation.isPending ? "Salvando..." : "Salvar Commodity"}
                            </Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* MODAL DE CONFIRMAÇÃO DE EXCLUSÃO COM INTEGRIDADE REFERENCIAL */}
            <Dialog open={modalExclusaoAberto} onOpenChange={setModalExclusaoAberto}>
                <DialogContent className="max-w-sm rounded-sm">
                    <DialogHeader>
                        <DialogTitle className="text-sm font-bold flex items-center gap-2 text-red-600">
                            <AlertTriangle size={16} />
                            Confirmar Exclusão
                        </DialogTitle>
                        <DialogDescription className="text-xs leading-relaxed pt-2">
                            Você está prestes a excluir <strong className="text-foreground">{itemParaExcluir?.nome}</strong> da biblioteca global.
                            <br />
                            <br />
                            <span className="text-red-700 dark:text-red-400 font-semibold">
                                Atenção: Se este registro possuir referências operacionais em conversões de unidades ou safras, a exclusão física será rejeitada pelo servidor para proteger a integridade referencial.
                            </span>
                        </DialogDescription>
                    </DialogHeader>

                    <DialogFooter className="pt-3">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => setModalExclusaoAberto(false)}
                            className="rounded-sm h-8 text-xs"
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => {
                                if (itemParaExcluir) {
                                    excluirItemMutation.mutate(itemParaExcluir);
                                }
                            }}
                            disabled={excluirItemMutation.isPending}
                            className="rounded-sm h-8 text-xs font-semibold border-red-600 text-red-700 hover:bg-red-50 dark:border-red-500 dark:text-red-300"
                        >
                            {excluirItemMutation.isPending ? "Excluindo..." : "Confirmar Exclusão"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
