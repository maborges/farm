"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { ModuleCard } from "@/components/shared/module-card";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import {
    Layers, Sprout, Beef, Receipt, Wrench, MapPin, Users, Trees, Puzzle,
    Package, DollarSign, TrendingUp, Info,
} from "lucide-react";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

// ─── Types ───────────────────────────────────────────────────────────────────

interface ModuloCatalogo {
    id: string;
    nome: string;
    descricao: string;
    categoria: string;
    obrigatorio: boolean;
    preco_base_mensal: number;
    dependencias: string[];
}

// ─── Configuração de Categorias ──────────────────────────────────────────────

const CATEGORIA_LABELS: Record<string, string> = {
    CORE: "Base",
    AGRICOLA: "Agrícola",
    PECUARIA: "Pecuária",
    FINANCEIRO: "Financeiro",
    OPERACIONAL: "Operacional",
    IMOVEIS: "Imóveis",
    RH: "RH",
    AMBIENTAL: "Ambiental",
    EXTENSAO: "Extensões",
};

const CATEGORIA_ORDER = [
    "CORE", "AGRICOLA", "PECUARIA", "FINANCEIRO",
    "OPERACIONAL", "IMOVEIS", "RH", "AMBIENTAL", "EXTENSAO",
];

const CATEGORIA_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
    CORE: Package,
    AGRICOLA: Sprout,
    PECUARIA: Beef,
    FINANCEIRO: Receipt,
    OPERACIONAL: Wrench,
    IMOVEIS: MapPin,
    RH: Users,
    AMBIENTAL: Trees,
    EXTENSAO: Puzzle,
};

const CATEGORIA_MODULE_VARIANT: Record<string, "agro" | "pecuaria" | "financeiro" | "operacional" | "backoffice" | "neutral"> = {
    CORE: "backoffice",
    AGRICOLA: "agro",
    PECUARIA: "pecuaria",
    FINANCEIRO: "financeiro",
    OPERACIONAL: "operacional",
    IMOVEIS: "neutral",
    RH: "neutral",
    AMBIENTAL: "neutral",
    EXTENSAO: "neutral",
};

const CATEGORIA_DESCRIPTIONS: Record<string, string> = {
    CORE: "Módulos essenciais disponíveis para todos os assinantes",
    AGRICOLA: "Planejamento, operações de campo, monitoramento e análise de safras",
    PECUARIA: "Gestão de rebanho, saúde animal, nutrição e produtividade",
    FINANCEIRO: "Tesouraria, custos, fiscal e controle financeiro da propriedade",
    OPERACIONAL: "Compras, estoque, frota e manutenção dos ativos",
    IMOVEIS: "Cadastro, arrendamentos e avaliação patrimonial de imóveis rurais",
    RH: "Remuneração, segurança do trabalho e gestão de equipe",
    AMBIENTAL: "Compliance ambiental, CAR, monitoramento e gestão de carbono",
    EXTENSAO: "IA Copilot, integração IoT e conexão com ERPs corporativos",
};

// ─── Componente Principal ────────────────────────────────────────────────────

export default function ModulesPage() {
    const { data: modules, isLoading } = useQuery<ModuloCatalogo[]>({
        queryKey: ["backoffice", "modules"],
        queryFn: () => apiFetch("/backoffice/modules"),
    });

    // Loading skeleton
    if (isLoading) {
        return (
            <div className="flex flex-col gap-6 p-4 md:p-8">
                <Skeleton className="h-10 w-64" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[1, 2, 3, 4].map(i => (
                        <Skeleton key={i} className="h-24 rounded-lg" />
                    ))}
                </div>
                {[1, 2, 3].map(i => (
                    <div key={i} className="space-y-3">
                        <Skeleton className="h-6 w-32" />
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {[1, 2, 3, 4].map(j => (
                                <Skeleton key={j} className="h-48 rounded-lg" />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    // Empty state
    if (!modules || modules.length === 0) {
        return (
            <div className="p-4 md:p-8">
                <PageHeader
                    title="Catálogo de Módulos"
                    description="Configure os módulos disponíveis para assinatura."
                    icon={<Layers className="text-primary" size={22} />}
                    breadcrumbs={[
                        { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                        { label: "Catálogo de Módulos" },
                    ]}
                />
                <div className="mt-8">
                    <EmptyState
                        icon={<Layers className="size-7" />}
                        title="Nenhum módulo cadastrado"
                        description="Adicione módulos ao catálogo para que estejam disponíveis nos planos de assinatura."
                    />
                </div>
            </div>
        );
    }

    // Agrupamento por categoria
    const grouped = CATEGORIA_ORDER.reduce<Record<string, ModuloCatalogo[]>>((acc, cat) => {
        const items = modules.filter(m => m.categoria === cat);
        if (items.length) acc[cat] = items;
        return acc;
    }, {});

    // Métricas resumidas
    const totalModules = modules.length;
    const totalRevPotential = modules.reduce((s, m) => s + m.preco_base_mensal, 0);
    const totalObrigatorios = modules.filter(m => m.obrigatorio).length;
    const totalCategoriasAtivas = Object.keys(grouped).length;

    return (
        <div className="flex flex-col gap-6 p-4 md:p-8">
            {/* ── Header com breadcrumb ─────────────────────────────────── */}
            <PageHeader
                title="Catálogo de Módulos"
                description={`${totalModules} módulos · ${totalCategoriasAtivas} categorias · Receita potencial: ${formatCurrency(totalRevPotential)}/mês`}
                icon={<Layers className="text-primary" size={22} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Catálogo de Módulos" },
                ]}
            />

            {/* ── Stat Cards resumidos ──────────────────────────────────── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    icon={Layers}
                    label="Total de Módulos"
                    value={totalModules}
                    color="backoffice"
                />
                <StatCard
                    icon={Package}
                    label="Categorias Ativas"
                    value={totalCategoriasAtivas}
                    color="muted"
                />
                <StatCard
                    icon={TrendingUp}
                    label="Receita Potencial"
                    value={formatCurrency(totalRevPotential)}
                    subtitle="por tenant / mês"
                    color="financeiro"
                />
                <StatCard
                    icon={Info}
                    label="Módulos Obrigatórios"
                    value={totalObrigatorios}
                    color="warning"
                />
            </div>

            {/* ── Seções por categoria ──────────────────────────────────── */}
            {CATEGORIA_ORDER.filter(cat => grouped[cat]).map(cat => {
                const Icon = CATEGORIA_ICONS[cat] ?? Layers;
                const moduleVariant = CATEGORIA_MODULE_VARIANT[cat] ?? "neutral";
                const descricao = CATEGORIA_DESCRIPTIONS[cat];

                return (
                    <div key={cat} className="space-y-4">
                        {/* Cabeçalho da seção */}
                        <div className="flex items-center gap-3">
                            <div className="size-9 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
                                <Icon className="size-4" />
                            </div>
                            <div className="min-w-0">
                                <h2 className="text-base font-semibold text-foreground leading-tight">
                                    {CATEGORIA_LABELS[cat] ?? cat}
                                </h2>
                                {descricao && (
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        {descricao}
                                    </p>
                                )}
                            </div>
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger>
                                        <Badge variant="secondary" className="text-xs ml-auto shrink-0">
                                            {grouped[cat].length} {grouped[cat].length === 1 ? "módulo" : "módulos"}
                                        </Badge>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p className="text-xs">{grouped[cat].length} módulo{grouped[cat].length !== 1 && "s"} nesta categoria</p>
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </div>

                        {/* Grid de cards de módulos */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {grouped[cat].map(mod => (
                                <ModuleCard
                                    key={mod.id}
                                    module={moduleVariant}
                                    title={mod.nome}
                                    description={mod.descricao}
                                >
                                    {/* Preço */}
                                    <div className="flex items-center justify-between pt-2 mt-2 border-t">
                                        <span className="text-xs text-muted-foreground">Base/mês</span>
                                        <span className="text-sm font-bold">
                                            {mod.preco_base_mensal === 0
                                                ? (
                                                    <TooltipProvider>
                                                        <Tooltip>
                                                            <TooltipTrigger>
                                                                <span className="text-green-600 dark:text-green-400 cursor-help">
                                                                    Incluído
                                                                </span>
                                                            </TooltipTrigger>
                                                            <TooltipContent>
                                                                <p className="text-xs">Módulo incluído no plano sem custo adicional</p>
                                                            </TooltipContent>
                                                        </Tooltip>
                                                    </TooltipProvider>
                                                )
                                                : formatCurrency(mod.preco_base_mensal)
                                            }
                                        </span>
                                    </div>

                                    {/* Badge obrigatório */}
                                    {mod.obrigatorio && (
                                        <div className="flex items-center gap-1 pt-1">
                                            <Badge variant="default" className="text-[10px] px-1.5 py-0">
                                                Obrigatório
                                            </Badge>
                                        </div>
                                    )}

                                    {/* Dependências */}
                                    {mod.dependencias.length > 0 && (
                                        <div className="space-y-1 pt-1">
                                            <p className="text-[10px] uppercase font-semibold text-muted-foreground">
                                                Requer
                                            </p>
                                            <div className="flex flex-wrap gap-1">
                                                {mod.dependencias.map(dep => (
                                                    <code
                                                        key={dep}
                                                        className="inline-flex items-center px-1.5 py-0.5 rounded bg-muted text-[10px] font-mono text-muted-foreground"
                                                    >
                                                        {dep}
                                                    </code>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </ModuleCard>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
