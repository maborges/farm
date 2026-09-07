"use client";

import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { BarChart3, Leaf, TreePine, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";

interface RegistroCAR {
    id: string;
    unidade_produtiva_id?: string | null;
    imovel_rural_id?: string | null;
    fazenda_nome: string;
    codigo_car: string;
    uf: string;
    municipio?: string;
    status: string;
    area_total_ha?: number;
    area_app_ha?: number;
    area_rl_ha?: number;
    area_vegetacao_nativa_ha?: number;
    area_uso_consolidado_ha?: number;
    unidade_nome?: string;
    origem_cadastro?: boolean;
}

function pct(v?: number, total?: number) {
    if (!v || !total || total === 0) return 0;
    return Math.min(100, Math.round((v / total) * 100));
}

export default function AreasCarPage() {
    const unidadesAutorizadas = useAppStore((state) => state.unidadesProdutivasAutorizadas);
    const { data: cars = [] } = useQuery<RegistroCAR[]>({
        queryKey: ["ambiental", "car", "todos"],
        queryFn: () => apiFetch("/ambiental/car"),
    });
    const { data: contextosFundiarios = [], isLoading: carregandoContextos, error: erroContexto } = useQuery<Array<{
        unidade_produtiva_id: string;
        unidade_nome: string;
        imovel_rural_id: string;
        nome: string;
        car_numero?: string | null;
        uf?: string | null;
        municipio?: string | null;
        area_total_ha?: number | null;
        area_app_ha?: number | null;
        area_rl_ha?: number | null;
    }>>({
        queryKey: ["ambiental", "contexto-fundiario-consolidado"],
        queryFn: () => apiFetch("/ambiental/contexto-fundiario"),
    });
    const carsDoCadastro = contextosFundiarios
        .filter((imovel) => (imovel.car_numero || imovel.area_total_ha != null) && !cars.some((car) => car.imovel_rural_id === imovel.imovel_rural_id || (!!imovel.car_numero && car.codigo_car === imovel.car_numero)))
        .map((imovel): RegistroCAR => ({
            id: `cadastro-${imovel.imovel_rural_id}`,
            fazenda_nome: imovel.nome,
            codigo_car: imovel.car_numero ?? "CAR não informado",
            uf: imovel.uf ?? "",
            municipio: imovel.municipio ?? undefined,
            status: "PENDENTE",
            area_total_ha: imovel.area_total_ha ?? undefined,
            area_app_ha: imovel.area_app_ha ?? undefined,
            area_rl_ha: imovel.area_rl_ha ?? undefined,
            unidade_nome: imovel.unidade_nome,
            origem_cadastro: true,
        }));
    const unidadesComAreaSemImovel = unidadesAutorizadas
        .filter((unidade) => unidade.area_total_ha != null && !contextosFundiarios.some((imovel) => imovel.unidade_produtiva_id === unidade.id && imovel.area_total_ha != null) && !cars.some((car) => car.unidade_produtiva_id === unidade.id && car.area_total_ha != null))
        .map((unidade): RegistroCAR => ({
            id: `unidade-${unidade.id}`,
            fazenda_nome: unidade.nome,
            codigo_car: "CAR não informado",
            uf: unidade.uf ?? "",
            status: "PENDENTE",
            area_total_ha: unidade.area_total_ha ?? undefined,
            area_app_ha: unidade.area_app_ha ?? undefined,
            area_rl_ha: unidade.area_rl_ha ?? undefined,
            unidade_nome: unidade.nome,
            origem_cadastro: true,
        }));
    const carsConsolidados = [...cars, ...carsDoCadastro, ...unidadesComAreaSemImovel];

    const ativos = carsConsolidados.filter(c => c.status === "ATIVO" || c.status === "PENDENTE");
    const totalHa = ativos.reduce((s, c) => s + (c.area_total_ha ?? 0), 0);
    const totalApp = ativos.reduce((s, c) => s + (c.area_app_ha ?? 0), 0);
    const totalRL = ativos.reduce((s, c) => s + (c.area_rl_ha ?? 0), 0);
    const totalVeg = ativos.reduce((s, c) => s + (c.area_vegetacao_nativa_ha ?? 0), 0);
    const totalUso = ativos.reduce((s, c) => s + (c.area_uso_consolidado_ha ?? 0), 0);

    const fmt = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });

    return (
        <div className="w-full p-6 flex flex-col gap-6">
            <PageHeader
                title="Dashboard de Áreas"
                description="Consolidado de uso do solo por todos os CARs ativos."
                breadcrumbs={[
                    { label: "Dashboard", href: "/dashboard" },
                    { label: "Ambiental", href: "/dashboard/ambiental" },
                    { label: "CAR" },
                    { label: "Áreas" },
                ]}
                icon={<BarChart3 />}
                actions={(
                    <Button variant="outline" size="sm" asChild>
                        <Link href="/dashboard/ambiental/car/lista">
                            <Leaf data-icon="inline-start" />
                            Ver CARs
                        </Link>
                    </Button>
                )}
            />

            <div role="status" className="rounded-sm border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-800 dark:text-violet-200">
                <strong>Visão consolidada:</strong> os indicadores reúnem áreas dos CARs de todas as unidades produtivas autorizadas. A unidade de origem é identificada na lista de propriedades.
            </div>

            {carregandoContextos && carsConsolidados.length === 0 && unidadesAutorizadas.length === 0 ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[1,2,3,4].map(i => <Skeleton key={i} className="h-24 rounded-lg" />)}
                </div>
            ) : erroContexto && carsConsolidados.length === 0 ? (
                <Card><CardContent className="py-8 text-center text-sm text-destructive">
                    Não foi possível carregar os dados fundiários das unidades. Tente atualizar a página.
                </CardContent></Card>
            ) : (
                <>
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                        {[
                            { label: "Área Total", value: fmt(totalHa), unit: "ha", icon: <BarChart3 />, color: "text-foreground" },
                            { label: "APP", value: fmt(totalApp), unit: "ha", icon: <Waves />, color: "text-blue-600" },
                            { label: "Reserva Legal", value: fmt(totalRL), unit: "ha", icon: <TreePine />, color: "text-emerald-600" },
                            { label: "Veg. Nativa", value: fmt(totalVeg), unit: "ha", icon: <Leaf />, color: "text-green-600" },
                        ].map(kpi => (
                            <Card key={kpi.label}>
                                <CardContent className="flex items-center gap-3 py-4">
                                    {kpi.icon}
                                    <div>
                                        <p className="text-xs text-muted-foreground">{kpi.label}</p>
                                        <p className={`text-xl font-bold tabular-nums ${kpi.color}`}>{kpi.value}</p>
                                        <p className="text-xs text-muted-foreground">{kpi.unit}</p>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>

                    {totalHa > 0 && (
                        <Card>
                            <CardHeader className="pb-3"><CardTitle className="text-sm">Distribuição de Uso do Solo</CardTitle></CardHeader>
                            <CardContent className="flex flex-col gap-4">
                                {[
                                    { label: "APP", value: totalApp, color: "bg-blue-500" },
                                    { label: "Reserva Legal", value: totalRL, color: "bg-emerald-500" },
                                    { label: "Vegetação Nativa", value: totalVeg, color: "bg-green-500" },
                                    { label: "Uso Consolidado", value: totalUso, color: "bg-amber-500" },
                                ].map(item => {
                                    const p = pct(item.value, totalHa);
                                    return (
                                        <div key={item.label} className="space-y-1">
                                            <div className="flex justify-between text-xs">
                                                <span>{item.label}</span>
                                                <span className="tabular-nums text-muted-foreground">{fmt(item.value)} ha ({p}%)</span>
                                            </div>
                                            <Progress value={p} className="h-2" />
                                        </div>
                                    );
                                })}
                            </CardContent>
                        </Card>
                    )}

                    <Card>
                        <CardHeader className="pb-3"><CardTitle className="text-sm">Por Propriedade</CardTitle></CardHeader>
                        <CardContent className="flex flex-col gap-3">
                            {ativos.length === 0 ? (
                                <p className="text-sm text-muted-foreground text-center py-4">Nenhum CAR ativo com dados de área.</p>
                            ) : ativos.filter(c => c.area_total_ha).map(c => (
                                <div key={c.id} className="flex flex-col gap-1">
                                    <div className="flex justify-between text-xs">
                                        <span className="font-medium">{c.fazenda_nome}{c.unidade_nome ? ` — ${c.unidade_nome}` : ""}</span>
                                        <span className="tabular-nums text-muted-foreground">{fmt(c.area_total_ha ?? 0)} ha</span>
                                    </div>
                                    <div className="flex gap-1 h-2">
                                        <div className="bg-blue-500 rounded-l" style={{ width: `${pct(c.area_app_ha, c.area_total_ha)}%` }} title={`APP: ${c.area_app_ha} ha`} />
                                        <div className="bg-emerald-500" style={{ width: `${pct(c.area_rl_ha, c.area_total_ha)}%` }} title={`RL: ${c.area_rl_ha} ha`} />
                                        <div className="bg-green-400 rounded-r flex-1" title="Demais áreas" />
                                    </div>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                </>
            )}
        </div>
    );
}
