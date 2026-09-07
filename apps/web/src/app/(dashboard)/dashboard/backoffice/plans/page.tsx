"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Plus, Check, X, Package, Edit, Users, Tractor, Globe, Briefcase, Sparkles, Star } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Card, CardHeader, CardContent, CardTitle, CardDescription } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
    DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useState, useEffect } from "react";
import { formatCurrency } from "@/lib/utils";
import { getPacotes, type PacoteId } from "@/lib/constants/pacotes";
import { StatusBadge } from "@/components/ui/status-badge";

interface PlanResponse {
    id: string;
    nome: string;
    descricao: string | null;
    modulos_inclusos: string[];
    limite_usuarios_minimo: number;
    limite_usuarios_maximo: number | null;
    limite_hectares: number | null;
    max_categorias_plano: number;
    preco_mensal: number;
    preco_anual: number;
    ativo: boolean;
    is_default: boolean;
    disponivel_site: boolean;
    disponivel_crm: boolean;
    created_at: string;
}

interface PlanFormData {
    nome: string;
    descricao: string;
    modulos_inclusos: string[];
    limite_usuarios_minimo: number;
    limite_usuarios_maximo: number | null;
    limite_hectares: string;
    max_categorias_plano: number;
    preco_mensal: string;
    preco_anual: string;
    is_default: boolean;
    disponivel_site: boolean;
    disponivel_crm: boolean;
}

const AVAILABLE_MODULES = [
    { id: "CORE",                  label: "Núcleo AgroSaaS",          group: "Base" },
    { id: "A1_PLANEJAMENTO",       label: "Planejamento de Safra",    group: "Agrícola" },
    { id: "A2_CAMPO",              label: "Caderno de Campo",         group: "Agrícola" },
    { id: "A3_DEFENSIVOS",         label: "Defensivos e Receituário", group: "Agrícola" },
    { id: "A4_PRECISAO",           label: "Agricultura de Precisão",  group: "Agrícola" },
    { id: "A5_COLHEITA",           label: "Colheita e Romaneio",      group: "Agrícola" },
    { id: "P1_REBANHO",            label: "Controle de Rebanho",      group: "Pecuária" },
    { id: "P2_GENETICA",           label: "Genética Reprodutiva",     group: "Pecuária" },
    { id: "P3_CONFINAMENTO",       label: "Confinamento",             group: "Pecuária" },
    { id: "P4_LEITE",              label: "Pecuária Leiteira",        group: "Pecuária" },
    { id: "F1_TESOURARIA",         label: "Tesouraria",               group: "Financeiro" },
    { id: "F2_CUSTOS_ABC",         label: "Custos ABC",               group: "Financeiro" },
    { id: "F3_FISCAL",             label: "Fiscal e Compliance",      group: "Financeiro" },
    { id: "F4_HEDGING",            label: "Hedging e Futuros",        group: "Financeiro" },
    { id: "O1_FROTA",              label: "Controle de Frota",        group: "Operacional" },
    { id: "O2_ESTOQUE",            label: "Estoque Multi-armazéns",   group: "Operacional" },
    { id: "O3_COMPRAS",            label: "Suprimentos e Compras",    group: "Operacional" },
    { id: "O4_BALANCA",            label: "Balança de Pesagem",       group: "Operacional" },
    { id: "IMOVEIS_CADASTRO",      label: "Cadastro de Imóveis",      group: "Imóveis" },
    { id: "IMOVEIS_ARRENDAMENTOS", label: "Arrendamentos",            group: "Imóveis" },
    { id: "IMOVEIS_AVALIACAO",     label: "Avaliação Patrimonial",    group: "Imóveis" },
    { id: "RH1_REMUNERACAO",       label: "Remuneração Rural",        group: "RH" },
    { id: "RH2_SEGURANCA",         label: "Segurança do Trabalho",    group: "RH" },
    { id: "AM1_COMPLIANCE",        label: "Compliance Ambiental",     group: "Ambiental" },
    { id: "AM2_CARBONO",           label: "Gestão de Carbono",        group: "Ambiental" },
    { id: "EXT_IA",                label: "IA Copilot Agrônoma",      group: "Extensões" },
    { id: "EXT_IOT",               label: "Integração IoT",           group: "Extensões" },
    { id: "EXT_ERP",               label: "Integração ERP Corporativo", group: "Extensões" },
];

const MODULE_GROUPS = ["Base", "Agrícola", "Pecuária", "Financeiro", "Operacional", "Imóveis", "RH", "Ambiental", "Extensões"];

const EMPTY_FORM: PlanFormData = {
    nome: "",
    descricao: "",
    modulos_inclusos: ["CORE"],
    limite_usuarios_minimo: 1,
    limite_usuarios_maximo: null,
    limite_hectares: "",
    max_categorias_plano: 10,
    preco_mensal: "",
    preco_anual: "",
    is_default: false,
    disponivel_site: false,
    disponivel_crm: true,
};

function maskBRL(value: string): string {
    const digits = value.replace(/\D/g, "");
    if (!digits) return "";
    const num = parseInt(digits, 10);
    return (num / 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function parseBRL(value: string): number {
    return parseFloat(value.replace(/\./g, "").replace(",", ".")) || 0;
}

function numToBRL(value: number): string {
    if (!value) return "";
    return value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function ModuleSelector({ selected, onChange }: { selected: string[]; onChange: (v: string[]) => void }) {
    const toggle = (id: string) =>
        onChange(selected.includes(id) ? selected.filter(m => m !== id) : [...selected, id]);

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODULE_GROUPS.map(group => {
                const mods = AVAILABLE_MODULES.filter(m => m.group === group);
                return (
                    <div key={group} className="space-y-2">
                        <p className="text-xs font-semibold uppercase text-muted-foreground">{group}</p>
                        <div className="space-y-1">
                            {mods.map(mod => (
                                <label key={mod.id} className="flex items-center gap-2 cursor-pointer text-sm select-none">
                                    <Checkbox
                                        checked={selected.includes(mod.id)}
                                        onCheckedChange={() => toggle(mod.id)}
                                        disabled={mod.id === "CORE"}
                                    />
                                    {mod.label}
                                </label>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function PlanFormDialog({
    open,
    onOpenChange,
    initial,
    planId,
}: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    initial?: PlanResponse;
    planId?: string;
}) {
    const queryClient = useQueryClient();
    const isEdit = !!planId;
    const pacotes = getPacotes();

    const mandatory = ["CORE"];
    const withMandatory = (mods: string[]) =>
        Array.from(new Set([...mandatory, ...mods]));

    // Etapa: 0 = seleção de pacote, 1 = formulário
    const [step, setStep] = useState<"select" | "form">(initial ? "form" : "select");
    const [selectedPacote, setSelectedPacote] = useState<PacoteId | null>(null);

    const [form, setForm] = useState<PlanFormData>(() =>
        initial
            ? {
                nome: initial.nome,
                descricao: initial.descricao ?? "",
                modulos_inclusos: withMandatory(initial.modulos_inclusos),
                limite_usuarios_minimo: initial.limite_usuarios_minimo,
                limite_usuarios_maximo: initial.limite_usuarios_maximo,
                limite_hectares: initial.limite_hectares?.toString() ?? "",
                max_categorias_plano: initial.max_categorias_plano ?? 10,
                preco_mensal: numToBRL(initial.preco_mensal),
                preco_anual: numToBRL(initial.preco_anual),
                is_default: initial.is_default ?? false,
                disponivel_site: initial.disponivel_site ?? false,
                disponivel_crm: initial.disponivel_crm ?? true,
            }
            : EMPTY_FORM
    );

    useEffect(() => {
        if (initial) {
            setForm({
                nome: initial.nome,
                descricao: initial.descricao ?? "",
                modulos_inclusos: withMandatory(initial.modulos_inclusos),
                limite_usuarios_minimo: initial.limite_usuarios_minimo,
                limite_usuarios_maximo: initial.limite_usuarios_maximo,
                limite_hectares: initial.limite_hectares?.toString() ?? "",
                max_categorias_plano: initial.max_categorias_plano ?? 10,
                preco_mensal: numToBRL(initial.preco_mensal),
                preco_anual: numToBRL(initial.preco_anual),
                is_default: initial.is_default ?? false,
                disponivel_site: initial.disponivel_site ?? false,
                disponivel_crm: initial.disponivel_crm ?? true,
            });
            setStep("form");
        }
    }, [initial]);

    // Aplicar template de pacote ao selecionar
    const applyPacoteTemplate = (pacoteId: PacoteId) => {
        const pacote = pacotes.find(p => p.id === pacoteId);
        if (!pacote) return;

        setSelectedPacote(pacoteId);
        setForm({
            nome: pacote.nome,
            descricao: pacote.descricao,
            modulos_inclusos: withMandatory(pacote.modulos),
            limite_usuarios_minimo: 1,
            limite_usuarios_maximo: pacote.limiteUsuarios,
            limite_hectares: pacote.limiteHectares?.toString() ?? "",
            max_categorias_plano: 10,
            preco_mensal: numToBRL(pacote.precoMensal),
            preco_anual: numToBRL(pacote.precoAnual),
            is_default: false,
            disponivel_site: true,
            disponivel_crm: true,
        });
        setStep("form");
    };

    const set = (field: keyof PlanFormData, value: unknown) =>
        setForm(prev => ({ ...prev, [field]: value }));

    const mutation = useMutation({
        mutationFn: (data: object) =>
            apiFetch(isEdit ? `/backoffice/plans/${planId}` : "/backoffice/plans", {
                method: isEdit ? "PATCH" : "POST",
                body: JSON.stringify(data),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "plans"] });
            toast.success(isEdit ? "Plano atualizado!" : "Plano criado!");
            onOpenChange(false);
        },
        onError: () => toast.error("Erro ao salvar plano."),
    });

    const onSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.nome.trim()) { toast.error("Nome é obrigatório."); return; }
        mutation.mutate({
            ...form,
            limite_hectares: form.limite_hectares ? parseFloat(form.limite_hectares) : null,
            max_categorias_plano: form.max_categorias_plano,
            preco_mensal: parseBRL(form.preco_mensal),
            preco_anual: parseBRL(form.preco_anual),
            limite_usuarios_minimo: form.limite_usuarios_minimo,
            limite_usuarios_maximo: form.limite_usuarios_maximo || null,
        });
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="w-[calc(100vw-1rem)] sm:max-w-5xl max-h-[90vh] overflow-hidden p-0 flex flex-col">
                <DialogHeader className="border-b px-6 py-5">
                    <DialogTitle className="flex items-center gap-2">
                        <Package className="h-5 w-5 text-primary" />
                        {isEdit ? "Editar Plano" : "Novo Plano"}
                    </DialogTitle>
                    {!isEdit && step === "select" && (
                        <DialogDescription className="text-sm">
                            Escolha um pacote como ponto de partida ou comece do zero.
                        </DialogDescription>
                    )}
                </DialogHeader>

                <div className="flex-1 overflow-y-auto px-6 py-5">
                    {/* ── Etapa 1: Seleção de Pacote Template ────────────────── */}
                    {!isEdit && step === "select" && (
                    <div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                            {pacotes.map(pacote => (
                                <button
                                    key={pacote.id}
                                    type="button"
                                    onClick={() => applyPacoteTemplate(pacote.id)}
                                    className="group flex flex-col items-start text-left border-2 border-border rounded-lg p-5 hover:border-primary hover:shadow-md transition-all cursor-pointer bg-card"
                                >
                                    {/* Badge de destaque */}
                                    {pacote.destaque && (
                                        <Badge className="mb-3 text-[10px] bg-primary/10 text-primary border-primary/20 hover:bg-primary/15">
                                            <Sparkles className="size-3 mr-1" />
                                            {pacote.destaque}
                                        </Badge>
                                    )}
                                    {!pacote.destaque && <div className="mb-3" />}

                                    <h3 className="text-lg font-bold text-foreground">{pacote.nome}</h3>
                                    <p className="text-xs text-muted-foreground mt-1 mb-3 line-clamp-2 leading-relaxed">
                                        {pacote.descricao}
                                    </p>

                                    <div className="mt-auto pt-3 border-t w-full space-y-2">
                                        <div className="flex items-baseline gap-1">
                                            <span className="text-lg font-bold text-foreground">
                                                {formatCurrency(pacote.precoMensal)}
                                            </span>
                                            <span className="text-xs text-muted-foreground">/mês</span>
                                        </div>

                                        <div className="space-y-1 text-xs text-muted-foreground">
                                            <div className="flex items-center gap-1.5">
                                                <Users className="size-3" />
                                                {pacote.limiteUsuarios === 999
                                                    ? "Usuários ilimitados"
                                                    : `${pacote.limiteUsuarios} usuários`
                                                }
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <Tractor className="size-3" />
                                                {pacote.limiteHectares === null
                                                    ? "Hectares ilimitados"
                                                    : `${pacote.limiteHectares.toLocaleString("pt-BR")} ha`
                                                }
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <Package className="size-3" />
                                                {pacote.modulos.length} módulos
                                            </div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>

                        {/* Botão começar do zero */}
                        <div className="text-center">
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => setStep("form")}
                                className="text-muted-foreground hover:text-foreground"
                            >
                                Começar do zero
                            </Button>
                        </div>
                        </div>
                    )}

                    {/* ── Etapa 2: Formulário de Plano ──────────────────────── */}
                    {(isEdit || step === "form") && (
                        <div>
                            {/* Botão voltar para seleção (apenas criação) */}
                            {!isEdit && (
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setStep("select")}
                                    className="mb-2 -ml-2 text-muted-foreground hover:text-foreground"
                                >
                                    ← Voltar para pacotes
                                </Button>
                            )}
                            <form id="plan-form" onSubmit={onSubmit} className="space-y-4">
                        {/* Dados básicos */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="nome">Nome do plano *</Label>
                                <Input id="nome" value={form.nome} onChange={e => set("nome", e.target.value)} placeholder="Ex: Profissional" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="limite_usuarios_maximo">Limite máximo de usuários</Label>
                                <Input id="limite_usuarios_maximo" type="number" min="1" value={form.limite_usuarios_maximo ?? ""} onChange={e => set("limite_usuarios_maximo", e.target.value ? Number(e.target.value) : null)} placeholder="Vazio = ilimitado" />
                            </div>
                        </div>

                        {/* Descrição */}
                        <div className="space-y-2">
                            <Label htmlFor="descricao">Descrição</Label>
                            <Textarea
                                id="descricao"
                                value={form.descricao}
                                onChange={e => set("descricao", e.target.value)}
                                placeholder="Descreva o plano para os clientes"
                                rows={2}
                                className="resize-none"
                            />
                        </div>

                        {/* Preços e limites */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="preco_mensal">Preço mensal</Label>
                                <div className="relative">
                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground">R$</span>
                                    <Input
                                        id="preco_mensal"
                                        type="text"
                                        inputMode="numeric"
                                        className="pl-9"
                                        value={form.preco_mensal}
                                        onChange={e => set("preco_mensal", maskBRL(e.target.value))}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="preco_anual">Preço anual</Label>
                                <div className="relative">
                                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground">R$</span>
                                    <Input
                                        id="preco_anual"
                                        type="text"
                                        inputMode="numeric"
                                        className="pl-9"
                                        value={form.preco_anual}
                                        onChange={e => set("preco_anual", maskBRL(e.target.value))}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="limite_hectares">Limite hectares</Label>
                                <Input id="limite_hectares" type="number" step="0.1" min="0" value={form.limite_hectares} onChange={e => set("limite_hectares", e.target.value)} placeholder="Ilimitado" />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="max_categorias_plano">Limite categorias do plano</Label>
                                <Input
                                    id="max_categorias_plano"
                                    type="number"
                                    min="1"
                                    value={form.max_categorias_plano}
                                    onChange={e => set("max_categorias_plano", Number(e.target.value) || 0)}
                                    placeholder="Ex: 10"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Módulos Selecionados</Label>
                                <div className="flex items-center h-7 px-3 py-1 text-xs border rounded-sm bg-muted/50 font-medium">
                                    {form.modulos_inclusos.length} módulo(s)
                                </div>
                            </div>
                        </div>

                        {/* Plano Padrão */}
                        <div className="p-3 border rounded-sm bg-amber-50/30 border-amber-200 dark:bg-amber-950/10 dark:border-amber-800/30">
                            <div className="flex items-center justify-between gap-4">
                                <div className="space-y-0.5">
                                    <div className="flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-400">
                                        <Star className="size-4" />
                                        Plano Padrão
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Plano atribuído automaticamente no onboarding de novos tenants
                                    </p>
                                </div>
                                <Switch
                                    size="sm"
                                    checked={form.is_default}
                                    onCheckedChange={(v: boolean) => set("is_default", v)}
                                />
                            </div>
                        </div>

                        {/* Canais de comercialização */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-3 border rounded-sm bg-muted/30">
                            <div className="flex items-center justify-between gap-4">
                                <div className="space-y-0.5">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <Globe className="size-4 text-muted-foreground" />
                                        Disponível no Site
                                    </div>
                                    <p className="text-xs text-muted-foreground">Aparece no checkout e landing page público</p>
                                </div>
                                <Switch
                                    size="sm"
                                    checked={form.disponivel_site}
                                    onCheckedChange={(v: boolean) => set("disponivel_site", v)}
                                />
                            </div>
                            <div className="flex items-center justify-between gap-4">
                                <div className="space-y-0.5">
                                    <div className="flex items-center gap-2 text-sm font-medium">
                                        <Briefcase className="size-4 text-muted-foreground" />
                                        Disponível no CRM
                                    </div>
                                    <p className="text-xs text-muted-foreground">Aparece nas opções de conversão de leads</p>
                                </div>
                                <Switch
                                    size="sm"
                                    checked={form.disponivel_crm}
                                    onCheckedChange={(v: boolean) => set("disponivel_crm", v)}
                                />
                            </div>
                        </div>

                        {/* Módulos */}
                        <div className="space-y-2">
                            <Label>Módulos inclusos</Label>
                            <div className="border rounded-sm p-3">
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {MODULE_GROUPS.map(group => {
                                        const mods = AVAILABLE_MODULES.filter(m => m.group === group);
                                        return (
                                            <div key={group} className="space-y-1.5">
                                                <p className="text-xs font-semibold uppercase text-muted-foreground">{group}</p>
                                                <div className="space-y-1">
                                                    {mods.map(mod => (
                                                        <label key={mod.id} className="flex items-center gap-2 cursor-pointer text-sm select-none">
                                                            <Checkbox
                                                                checked={form.modulos_inclusos.includes(mod.id)}
                                                                onCheckedChange={() => {
                                                                    const selected = form.modulos_inclusos.includes(mod.id)
                                                                        ? form.modulos_inclusos.filter(m => m !== mod.id)
                                                                        : [...form.modulos_inclusos, mod.id];
                                                                    set("modulos_inclusos", selected);
                                                                }}
                                                                disabled={mod.id === "CORE"}
                                                            />
                                                            {mod.label}
                                                        </label>
                                                    ))}
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </form>
                        </div>
                    )}
                </div>

                {(isEdit || step === "form") && (
                    <DialogFooter className="border-t px-6 py-5">
                        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
                        <Button type="submit" form="plan-form" disabled={mutation.isPending}>
                            {mutation.isPending ? "Salvando..." : isEdit ? "Salvar alterações" : "Criar plano"}
                        </Button>
                    </DialogFooter>
                )}
            </DialogContent>
        </Dialog>
    );
}

export default function PlansBackofficePage() {
    const queryClient = useQueryClient();
    const [createOpen, setCreateOpen] = useState(false);
    const [editPlan, setEditPlan] = useState<PlanResponse | null>(null);

    const { data: plans, isLoading } = useQuery<PlanResponse[]>({
        queryKey: ["backoffice", "plans"],
        queryFn: () => apiFetch("/backoffice/plans"),
    });

    const toggleStatusMutation = useMutation({
        mutationFn: (planId: string) => apiFetch(`/backoffice/plans/${planId}/toggle-status`, { method: "POST" }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["backoffice", "plans"] });
            toast.success("Status do plano atualizado!");
        },
        onError: () => toast.error("Falha ao atualizar status."),
    });

    if (isLoading) {
        return (
            <div className="flex-1 space-y-8 p-8 max-w-7xl mx-auto w-full">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-10 w-48" />
                    <Skeleton className="h-10 w-32" />
                </div>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {[1, 2, 3].map(i => <Skeleton key={i} className="h-80 w-full rounded-sm" />)}
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 w-full max-w-full">
            <PageHeader
                title="Catálogo de Planos"
                description="Configure os pacotes comerciais e módulos disponíveis."
                icon={<Package className="text-primary" size={22} />}
                actions={
                    <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-2">
                        <Plus className="size-4" />
                        Novo Plano
                    </Button>
                }
            />

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {plans?.map((plan) => (
                    <Card
                        key={plan.id}
                        className={`flex flex-col relative overflow-hidden transition-all duration-300 border-l-[3px] ${plan.ativo ? "border-l-primary" : "border-l-muted/50 opacity-70 grayscale"}`}
                    >
                        <CardHeader>
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                    {plan.is_default && (
                                        <Badge variant="default" className="gap-1 text-[10px]">
                                            <Star className="size-2.5" /> Padrão
                                        </Badge>
                                    )}
                                    <StatusBadge status={plan.ativo ? "ativo" : "inativo"} />
                                    {plan.disponivel_site && (
                                        <Badge variant="secondary" className="gap-1 text-[10px]">
                                            <Globe className="size-2.5" /> Site
                                        </Badge>
                                    )}
                                    {plan.disponivel_crm && (
                                        <Badge variant="secondary" className="gap-1 text-[10px]">
                                            <Briefcase className="size-2.5" /> CRM
                                        </Badge>
                                    )}
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-8 w-8 text-muted-foreground hover:text-primary"
                                    onClick={() => setEditPlan(plan)}
                                >
                                    <Edit className="size-4" />
                                </Button>
                            </div>
                            <CardTitle className="text-xl font-bold">{plan.nome}</CardTitle>
                            <CardDescription className="line-clamp-2 min-h-[40px]">
                                {plan.descricao || "Sem descrição disponível."}
                            </CardDescription>
                        </CardHeader>

                        <CardContent className="flex-1 space-y-4">
                            <div className="space-y-1">
                                <div className="text-3xl font-bold">
                                    {formatCurrency(plan.preco_mensal)}
                                    <span className="text-sm font-normal text-muted-foreground">/mês</span>
                                </div>
                                <div className="text-sm text-muted-foreground">
                                    ou {formatCurrency(plan.preco_anual)}/ano
                                </div>
                            </div>

                            <div className="space-y-2 pt-4 border-t">
                                <div className="flex items-center gap-2 text-sm">
                                    <Users className="size-4 text-primary" />
                                    {plan.limite_usuarios_maximo ?? "∞"} usuários
                                </div>
                                {plan.limite_hectares && (
                                    <div className="flex items-center gap-2 text-sm">
                                        <Tractor className="size-4 text-primary" />
                                        Até {plan.limite_hectares} ha
                                    </div>
                                )}
                                <div className="flex items-center gap-2 text-sm">
                                    <Package className="size-4 text-primary" />
                                    {plan.max_categorias_plano === -1 ? "Categorias ilimitadas" : `${plan.max_categorias_plano} categorias`}
                                </div>
                            </div>

                            <div className="space-y-2 pt-2">
                                <div className="text-xs uppercase font-bold text-muted-foreground">
                                    Módulos ({plan.modulos_inclusos.length}):
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {plan.modulos_inclusos.map(mod => {
                                        const meta = AVAILABLE_MODULES.find(m => m.id === mod);
                                        return (
                                            <span
                                                key={mod}
                                                className="inline-flex items-center px-2 py-0.5 rounded-full bg-primary/5 text-[10px] font-medium text-primary border border-primary/10"
                                            >
                                                {meta?.label ?? mod}
                                            </span>
                                        );
                                    })}
                                </div>
                            </div>
                        </CardContent>

                        <div className="p-6 bg-muted/30 border-t mt-auto">
                            <Button
                                variant={plan.ativo ? "outline" : "default"}
                                size="sm"
                                className="w-full gap-2"
                                onClick={() => toggleStatusMutation.mutate(plan.id)}
                                disabled={toggleStatusMutation.isPending}
                            >
                                {plan.ativo ? (
                                    <><X className="h-3.5 w-3.5" /> Pausar Vendas</>
                                ) : (
                                    <><Check className="h-3.5 w-3.5" /> Reativar Plano</>
                                )}
                            </Button>
                        </div>
                    </Card>
                ))}
            </div>

            {plans?.length === 0 && (
                <div className="flex flex-col items-center justify-center p-12 text-center border-2 border-dashed rounded-sm space-y-4">
                    <Package className="h-12 w-12 text-muted-foreground" />
                    <div className="space-y-1">
                        <h3 className="font-semibold text-lg">Nenhum plano disponível</h3>
                        <p className="text-muted-foreground">Comece criando o primeiro pacote comercial da plataforma.</p>
                    </div>
                    <Button onClick={() => setCreateOpen(true)} className="gap-2">
                        <Plus className="size-4" /> Criar primeiro plano
                    </Button>
                </div>
            )}

            {/* Dialog de criação */}
            <PlanFormDialog
                open={createOpen}
                onOpenChange={v => { setCreateOpen(v); }}
                key={createOpen ? "create" : "create-closed"}
            />

            {/* Dialog de edição */}
            {editPlan && (
                <PlanFormDialog
                    open={!!editPlan}
                    onOpenChange={v => { if (!v) setEditPlan(null); }}
                    initial={editPlan}
                    planId={editPlan.id}
                    key={editPlan.id}
                />
            )}
        </div>
    );
}
