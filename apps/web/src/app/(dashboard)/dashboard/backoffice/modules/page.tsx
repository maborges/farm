"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { ModuleCard } from "@/components/shared/module-card";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { ModuloMetadata, normalizeModuleId } from "@/lib/constants/modulos";
import {
    Layers, Sprout, Beef, Receipt, Wrench, MapPin, Users, Trees, Puzzle,
    Package, DollarSign, TrendingUp, Info, Edit,
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
    ativo: boolean;
}

type ModuloEditavel = Pick<ModuloCatalogo, "id" | "nome" | "descricao" | "categoria" | "obrigatorio" | "preco_base_mensal" | "dependencias">;

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
    const queryClient = useQueryClient();
    const [editing, setEditing] = useState<ModuloEditavel | null>(null);
    const updateModule = useMutation({
        mutationFn: (modulo: ModuloEditavel) => apiFetch(`/backoffice/modules/${encodeURIComponent(modulo.id)}`, {
            method: "PUT",
            body: JSON.stringify({ nome: modulo.nome, descricao: modulo.descricao, categoria: modulo.categoria, obrigatorio: modulo.obrigatorio, preco_base_mensal: Number(modulo.preco_base_mensal), dependencias: modulo.dependencias }),
        }),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["backoffice", "modules"] });
            toast.success("Módulo atualizado.");
            setEditing(null);
        },
        onError: () => toast.error("Não foi possível salvar o módulo."),
    });
    const toggleModuleStatus = useMutation({
        mutationFn: (moduloId: string) =>
            apiFetch<{ id: string; ativo: boolean }>(`/backoffice/modules/${encodeURIComponent(moduloId)}/toggle-status`, {
                method: "POST",
            }),
        onSuccess: async (resultado) => {
            await queryClient.invalidateQueries({ queryKey: ["backoffice", "modules"] });
            toast.success(
                resultado.ativo
                    ? "Módulo ativado. Ele volta a aparecer nos pacotes."
                    : "Módulo desativado. Ele não aparece mais nos pacotes nem pode ser contratado."
            );
        },
        onError: () => toast.error("Não foi possível alterar o status do módulo."),
    });
    const { data: modules, isLoading } = useQuery<ModuloCatalogo[]>({
        queryKey: ["backoffice", "modules"],
        queryFn: () => apiFetch("/backoffice/modules"),
    });

    // Loading skeleton
    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
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
            <div className="p-6 space-y-6">
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
    const moduleDescriptionById = new Map(modules.map(modulo => [modulo.id, modulo.descricao]));

    // Métricas resumidas
    const totalModules = modules.length;
    const totalRevPotential = modules.reduce((s, m) => s + m.preco_base_mensal, 0);
    const totalObrigatorios = modules.filter(m => m.obrigatorio).length;
    const totalCategoriasAtivas = Object.keys(grouped).length;

    return (
        <div className="p-6 space-y-6">
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
                                    headerAction={
                                        <div className="flex items-center gap-1">
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger className="inline-flex items-center">
                                                        <Switch
                                                            size="sm"
                                                            checked={mod.ativo !== false}
                                                            disabled={mod.id === "CORE" || toggleModuleStatus.isPending}
                                                            onCheckedChange={() => toggleModuleStatus.mutate(mod.id)}
                                                            aria-label={`${mod.ativo !== false ? "Desativar" : "Ativar"} ${mod.nome}`}
                                                        />
                                                    </TooltipTrigger>
                                                    <TooltipContent>
                                                        <p className="text-xs">
                                                            {mod.id === "CORE"
                                                                ? "O Núcleo é obrigatório e não pode ser desativado"
                                                                : mod.ativo !== false
                                                                    ? "Ativo: aparece nos pacotes / pode ser contratado"
                                                                    : "Inativo: oculto dos pacotes / não pode ser contratado"}
                                                        </p>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-muted-foreground hover:text-primary"
                                                aria-label={`Editar ${mod.nome}`}
                                                onClick={() => setEditing({ id: mod.id, nome: mod.nome, descricao: mod.descricao, categoria: mod.categoria, obrigatorio: mod.obrigatorio, preco_base_mensal: mod.preco_base_mensal, dependencias: mod.dependencias })}
                                            >
                                                <Edit className="size-4" />
                                            </Button>
                                        </div>
                                    }
                                >
                                    {mod.ativo === false && (
                                        <div className="pt-1">
                                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-destructive/40 text-destructive">
                                                Inativo — oculto dos pacotes
                                            </Badge>
                                        </div>
                                    )}
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
                                                {mod.dependencias.map(dep => {
                                                    const dependencyDescription =
                                                        moduleDescriptionById.get(dep) ??
                                                        ModuloMetadata[normalizeModuleId(dep)]?.descricao ??
                                                        dep;

                                                    return (
                                                        <span
                                                            key={dep}
                                                            className="inline-flex max-w-full items-center rounded-sm bg-muted px-1.5 py-0.5 text-[10px] leading-4 text-muted-foreground"
                                                        >
                                                            {dependencyDescription}
                                                        </span>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </ModuleCard>
                            ))}
                        </div>
                    </div>
                );
            })}
            <Dialog open={editing !== null} onOpenChange={open => { if (!open && !updateModule.isPending) setEditing(null); }}>
                <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-5xl max-h-[90vh] overflow-hidden p-0 flex flex-col">
                    <DialogHeader className="border-b px-6 py-5">
                        <DialogTitle className="flex items-center gap-2">
                            <Layers className="h-5 w-5 text-primary" />
                            Editar Módulo
                        </DialogTitle>
                        <DialogDescription>Altere as informações exibidas no catálogo.</DialogDescription>
                    </DialogHeader>
                    {editing && <form
                        id="module-form"
                        className="flex min-h-0 flex-1 flex-col"
                        onSubmit={event => { event.preventDefault(); updateModule.mutate(editing); }}
                    >
                        <div className="flex-1 overflow-y-auto px-6 py-5">
                            <div className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="module-name">Nome *</Label>
                                        <Input id="module-name" value={editing.nome} onChange={event => setEditing({ ...editing, nome: event.target.value })} required />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="module-category">Categoria</Label>
                                        <Input id="module-category" value={editing.categoria} onChange={event => setEditing({ ...editing, categoria: event.target.value.toUpperCase() })} />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="module-description">Descrição</Label>
                                    <Textarea id="module-description" rows={2} className="resize-none" value={editing.descricao} onChange={event => setEditing({ ...editing, descricao: event.target.value })} />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="module-price">Preço base mensal</Label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground">R$</span>
                                            <Input id="module-price" type="number" min="0" step="0.01" className="pl-9" value={editing.preco_base_mensal} onChange={event => setEditing({ ...editing, preco_base_mensal: Number(event.target.value) })} />
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between gap-4 p-3 border rounded-sm bg-muted/30">
                                        <div className="space-y-0.5">
                                            <Label htmlFor="module-required" className="text-sm font-medium">Módulo obrigatório</Label>
                                            <p className="text-xs text-muted-foreground">Disponível automaticamente nos planos</p>
                                        </div>
                                        <Switch id="module-required" size="sm" checked={editing.obrigatorio} onCheckedChange={obrigatorio => setEditing({ ...editing, obrigatorio })} />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label>Módulos requeridos</Label>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-3 border rounded-sm bg-muted/30">
                                        {modules.filter(option => option.id !== editing.id).map(option => (
                                            <label key={option.id} className="flex items-center gap-2 cursor-pointer text-sm">
                                                <Checkbox
                                                    checked={editing.dependencias.includes(option.id)}
                                                    onCheckedChange={checked => setEditing(current => {
                                                        if (!current) return current;
                                                        const dependencias = new Set(current.dependencias);
                                                        if (checked) dependencias.add(option.id);
                                                        else dependencias.delete(option.id);
                                                        return { ...current, dependencias: Array.from(dependencias) };
                                                    })}
                                                />
                                                <span>{option.nome}</span>
                                            </label>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <DialogFooter className="border-t px-6 py-5">
                            <Button type="button" variant="outline" onClick={() => setEditing(null)} disabled={updateModule.isPending}>Cancelar</Button>
                            <Button type="submit" disabled={!editing.nome.trim() || updateModule.isPending}>{updateModule.isPending ? "Salvando..." : "Salvar alterações"}</Button>
                        </DialogFooter>
                    </form>}
                </DialogContent>
            </Dialog>
        </div>
    );
}
