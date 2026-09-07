"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import {
    BarChart3, Tractor, Package, TrendingDown, TrendingUp,
    Gauge, Wrench, Calendar, Filter,
} from "lucide-react";
import { PageHeader } from "@/components/shared";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
    Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CustoMaquinario {
    maquinario_id: string;
    nome: string;
    tipo: string;
    status: string;
    horimetro_atual: number;
    total_os_concluidas: number;
    custo_total_pecas: number;
    custo_total_mao_obra: number;
    custo_total: number;
    custo_por_hora: number;
}

interface ConsumoInsumo {
    safra_id: string;
    safra_nome: string;
    produto_id: string;
    produto_nome: string;
    unidade_medida: string;
    quantidade_total: number;
    custo_total: number;
    aplicacoes: number;
}

interface MovimentacaoPeriodo {
    produto_id: string;
    produto_nome: string;
    unidade_medida: string;
    tipo: string;
    qtd_movimentos: number;
    quantidade_total: number;
    custo_total: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (v: number) => `R$ ${v.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
const fmtN = (v: number, dec = 2) => v.toLocaleString("pt-BR", { minimumFractionDigits: dec, maximumFractionDigits: dec });

function tipoColor(tipo: string) {
    if (tipo === "ENTRADA") return "bg-green-100 text-green-700";
    if (tipo === "SAIDA") return "bg-red-100 text-red-700";
    if (tipo === "TRANSFERENCIA") return "bg-blue-100 text-blue-700";
    return "bg-gray-100 text-gray-700";
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function RelatoriosOperacionaisPage() {
    const { activeFazendaId } = useAppStore();
    const today = new Date().toISOString().split("T")[0];
    const thirtyDaysAgo = new Date(Date.now() - 30 * 86400000).toISOString().split("T")[0];

    const [dataInicio, setDataInicio] = useState(thirtyDaysAgo);
    const [dataFim, setDataFim] = useState(today);
    const [filtroApply, setFiltroApply] = useState({ inicio: thirtyDaysAgo, fim: today });

    const fazendaParam = activeFazendaId ? `&unidade_produtiva_id=${activeFazendaId}` : "";

    const { data: custos, isLoading: loadingCustos } = useQuery<CustoMaquinario[]>({
        queryKey: ["rel-custo-maquinario", activeFazendaId, filtroApply],
        queryFn: () => apiFetch(
            `/operacional/relatorios/custo-maquinario?data_inicio=${filtroApply.inicio}&data_fim=${filtroApply.fim}${fazendaParam}`
        ),
    });

    const { data: consumo, isLoading: loadingConsumo } = useQuery<ConsumoInsumo[]>({
        queryKey: ["rel-consumo-insumos", activeFazendaId],
        queryFn: () => apiFetch(`/operacional/relatorios/consumo-insumos${activeFazendaId ? `?unidade_produtiva_id=${activeFazendaId}` : ""}`),
    });

    const { data: movs, isLoading: loadingMovs, refetch: refetchMovs } = useQuery<MovimentacaoPeriodo[]>({
        queryKey: ["rel-movimentacoes", activeFazendaId, filtroApply],
        queryFn: () => apiFetch(
            `/operacional/relatorios/movimentacoes?data_inicio=${filtroApply.inicio}&data_fim=${filtroApply.fim}${fazendaParam}`
        ),
    });

    // KPIs rápidos
    const totalCustoFrota = custos?.reduce((a, c) => a + c.custo_total, 0) ?? 0;
    const maqMaisCaro = custos?.[0];
    const totalConsumoInsumos = consumo?.reduce((a, c) => a + c.custo_total, 0) ?? 0;
    const totalEntradas = movs?.filter(m => m.tipo === "ENTRADA").reduce((a, m) => a + m.custo_total, 0) ?? 0;
    const totalSaidas = movs?.filter(m => m.tipo === "SAIDA").reduce((a, m) => a + m.custo_total, 0) ?? 0;

    // Agrupa consumo por safra para exibição
    const consumoPorSafra = consumo?.reduce((acc, c) => {
        if (!acc[c.safra_nome]) acc[c.safra_nome] = [];
        acc[c.safra_nome].push(c);
        return acc;
    }, {} as Record<string, ConsumoInsumo[]>) ?? {};

    return (
        <div className="p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-7xl mx-auto w-full">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-3">
                        <BarChart3 className="text-primary" /> Relatórios Operacionais
                    </h1>
                    <p className="text-muted-foreground mt-1">
                        Custo por maquinário, consumo de insumos por safra e movimentações de estoque.
                    </p>
                </div>

                {/* Filtro de período */}
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Calendar size={14} />
                        <Input
                            type="date"
                            value={dataInicio}
                            onChange={e => setDataInicio(e.target.value)}
                            className="h-8 w-[140px] text-xs"
                        />
                        <span>até</span>
                        <Input
                            type="date"
                            value={dataFim}
                            onChange={e => setDataFim(e.target.value)}
                            className="h-8 w-[140px] text-xs"
                        />
                    </div>
                    <Button size="sm" className="gap-1 h-8" onClick={() => setFiltroApply({ inicio: dataInicio, fim: dataFim })}>
                        <Filter size={14} /> Filtrar
                    </Button>
                </div>
            </div>

            {/* KPI cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="border-l-4 border-l-amber-500">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase text-muted-foreground">Custo Total Frota</p>
                        <p className="text-2xl font-black mt-1">{fmt(totalCustoFrota)}</p>
                        {maqMaisCaro && (
                            <p className="text-xs text-muted-foreground mt-1 truncate">
                                Maior: {maqMaisCaro.nome}
                            </p>
                        )}
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-green-500">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase text-muted-foreground">Custo Insumos (Safras)</p>
                        <p className="text-2xl font-black mt-1">{fmt(totalConsumoInsumos)}</p>
                        <p className="text-xs text-muted-foreground mt-1">{consumo?.length ?? 0} combinações produto/safra</p>
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-blue-500">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase text-muted-foreground flex items-center gap-1">
                            <TrendingDown size={10} /> Entradas (Período)
                        </p>
                        <p className="text-2xl font-black mt-1 text-green-600">{fmt(totalEntradas)}</p>
                    </CardContent>
                </Card>
                <Card className="border-l-4 border-l-red-500">
                    <CardContent className="p-4">
                        <p className="text-[10px] font-black uppercase text-muted-foreground flex items-center gap-1">
                            <TrendingUp size={10} /> Saídas (Período)
                        </p>
                        <p className="text-2xl font-black mt-1 text-red-600">{fmt(totalSaidas)}</p>
                    </CardContent>
                </Card>
            </div>

            <Tabs defaultValue="maquinario" className="w-full">
                <TabsList className="grid w-full max-w-[560px] grid-cols-3">
                    <TabsTrigger value="maquinario" className="gap-1 text-xs">
                        <Tractor size={13} /> Custo/Maquinário
                    </TabsTrigger>
                    <TabsTrigger value="insumos" className="gap-1 text-xs">
                        <Package size={13} /> Insumos/Safra
                    </TabsTrigger>
                    <TabsTrigger value="movimentacoes" className="gap-1 text-xs">
                        <BarChart3 size={13} /> Movimentações
                    </TabsTrigger>
                </TabsList>

                {/* ── Tab Custo por Maquinário ── */}
                <TabsContent value="maquinario" className="mt-6">
                    <Card className="border-none shadow-sm">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Wrench size={18} className="text-amber-600" /> Custo de Manutenção por Ativo
                            </CardTitle>
                            <CardDescription>
                                OS concluídas no período · Peças + mão de obra · Custo por hora de operação
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Maquinário</TableHead>
                                        <TableHead>Tipo</TableHead>
                                        <TableHead className="text-center">OS Concluídas</TableHead>
                                        <TableHead className="text-right">Peças</TableHead>
                                        <TableHead className="text-right">Mão de Obra</TableHead>
                                        <TableHead className="text-right">Total</TableHead>
                                        <TableHead className="text-right">Custo/hora</TableHead>
                                        <TableHead>Status</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {loadingCustos ? (
                                        Array(3).fill(0).map((_, i) => (
                                            <TableRow key={i}><TableCell colSpan={8}><Skeleton className="h-8 w-full" /></TableCell></TableRow>
                                        ))
                                    ) : custos?.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={8} className="text-center py-12 text-muted-foreground italic">
                                                Nenhum maquinário encontrado ou sem OS concluídas no período.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        custos?.map(m => (
                                            <TableRow key={m.maquinario_id}>
                                                <TableCell>
                                                    <div className="flex items-center gap-2">
                                                        <Tractor size={16} className="text-muted-foreground" />
                                                        <span className="font-semibold">{m.nome}</span>
                                                    </div>
                                                </TableCell>
                                                <TableCell>
                                                    <Badge variant="secondary" className="text-[10px]">{m.tipo}</Badge>
                                                </TableCell>
                                                <TableCell className="text-center font-bold">{m.total_os_concluidas}</TableCell>
                                                <TableCell className="text-right text-sm">{fmt(m.custo_total_pecas)}</TableCell>
                                                <TableCell className="text-right text-sm">{fmt(m.custo_total_mao_obra)}</TableCell>
                                                <TableCell className="text-right font-bold">{fmt(m.custo_total)}</TableCell>
                                                <TableCell className="text-right text-sm text-muted-foreground">
                                                    {m.custo_por_hora > 0 ? `R$ ${fmtN(m.custo_por_hora)}/h` : "—"}
                                                </TableCell>
                                                <TableCell>
                                                    <Badge className={
                                                        m.status === "ATIVO"
                                                            ? "bg-green-100 text-green-700 border-none text-[10px]"
                                                            : "bg-amber-100 text-amber-700 border-none text-[10px]"
                                                    }>
                                                        {m.status}
                                                    </Badge>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ── Tab Consumo de Insumos ── */}
                <TabsContent value="insumos" className="mt-6 space-y-6">
                    {loadingConsumo ? (
                        <Skeleton className="h-40 w-full" />
                    ) : Object.keys(consumoPorSafra).length === 0 ? (
                        <Card className="border-none shadow-sm">
                            <CardContent className="py-16 text-center text-muted-foreground italic">
                                Nenhum insumo aplicado registrado nas operações agrícolas.
                            </CardContent>
                        </Card>
                    ) : (
                        Object.entries(consumoPorSafra).map(([safra, itens]) => {
                            const totalSafra = itens.reduce((a, i) => a + i.custo_total, 0);
                            return (
                                <Card key={safra} className="border-none shadow-sm">
                                    <CardHeader className="pb-3">
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="text-base flex items-center gap-2">
                                                <Package size={16} className="text-green-600" />
                                                Safra: {safra}
                                            </CardTitle>
                                            <span className="text-sm font-bold text-muted-foreground">
                                                Total: {fmt(totalSafra)}
                                            </span>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>Insumo</TableHead>
                                                    <TableHead className="text-right">Qtd Total</TableHead>
                                                    <TableHead>U.M.</TableHead>
                                                    <TableHead className="text-center">Aplicações</TableHead>
                                                    <TableHead className="text-right">Custo Total</TableHead>
                                                    <TableHead className="text-right">% do Total</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {itens.map(i => (
                                                    <TableRow key={i.produto_id}>
                                                        <TableCell className="font-semibold">{i.produto_nome}</TableCell>
                                                        <TableCell className="text-right">{fmtN(i.quantidade_total, 4)}</TableCell>
                                                        <TableCell className="text-xs text-muted-foreground">{i.unidade_medida}</TableCell>
                                                        <TableCell className="text-center">{i.aplicacoes}</TableCell>
                                                        <TableCell className="text-right font-bold">{fmt(i.custo_total)}</TableCell>
                                                        <TableCell className="text-right text-muted-foreground text-sm">
                                                            {totalSafra > 0 ? `${((i.custo_total / totalSafra) * 100).toFixed(1)}%` : "—"}
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </CardContent>
                                </Card>
                            );
                        })
                    )}
                </TabsContent>

                {/* ── Tab Movimentações ── */}
                <TabsContent value="movimentacoes" className="mt-6">
                    <Card className="border-none shadow-sm">
                        <CardHeader>
                            <CardTitle className="text-lg flex items-center gap-2">
                                <BarChart3 size={18} className="text-blue-600" /> Movimentações por Produto — Período
                            </CardTitle>
                            <CardDescription>
                                Agrupado por produto e tipo de movimentação no período selecionado
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Produto</TableHead>
                                        <TableHead>Tipo</TableHead>
                                        <TableHead className="text-center">Movimentos</TableHead>
                                        <TableHead className="text-right">Quantidade</TableHead>
                                        <TableHead>U.M.</TableHead>
                                        <TableHead className="text-right">Valor Total</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {loadingMovs ? (
                                        Array(4).fill(0).map((_, i) => (
                                            <TableRow key={i}><TableCell colSpan={6}><Skeleton className="h-8 w-full" /></TableCell></TableRow>
                                        ))
                                    ) : movs?.length === 0 ? (
                                        <TableRow>
                                            <TableCell colSpan={6} className="text-center py-12 text-muted-foreground italic">
                                                Nenhuma movimentação no período selecionado.
                                            </TableCell>
                                        </TableRow>
                                    ) : (
                                        movs?.map((m, idx) => (
                                            <TableRow key={idx}>
                                                <TableCell className="font-semibold">{m.produto_nome}</TableCell>
                                                <TableCell>
                                                    <Badge className={`${tipoColor(m.tipo)} border-none text-[10px]`}>
                                                        {m.tipo}
                                                    </Badge>
                                                </TableCell>
                                                <TableCell className="text-center">{m.qtd_movimentos}</TableCell>
                                                <TableCell className="text-right font-bold">{fmtN(m.quantidade_total, 2)}</TableCell>
                                                <TableCell className="text-xs text-muted-foreground">{m.unidade_medida}</TableCell>
                                                <TableCell className="text-right">
                                                    {m.custo_total > 0 ? fmt(m.custo_total) : "—"}
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    )}
                                </TableBody>
                            </Table>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
