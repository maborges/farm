"use client";

import React, { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
    Settings,
    RotateCcw,
    RefreshCw,
    Save,
    Shield,
    ShieldAlert,
    CheckCircle2,
    CloudSun,
    TrendingUp,
    MessageSquare,
    Flag,
    Info,
    AlertTriangle,
    Clock,
    Lock,
    SlidersHorizontal,
    FileText,
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
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface ConfigMetadata {
    revision: number;
    updated_at: string;
    updated_by: string;
    version: string;
}

interface ConfigItem<T> {
    chave: string;
    valor: T;
    meta: ConfigMetadata;
    descricao?: string;
    ativo: boolean;
}

interface ClimaConfigData {
    active_provider: "WEATHERAPI" | "OPENWEATHER" | "OPEN_METEO";
    fallback_chain: string[];
    timeout_seconds: number;
    cache_ttl_seconds: number;
    monthly_quota_limit: number;
    force_contingency_mode: boolean;
}

interface MercadoConfigData {
    ptax_cache_ttl_seconds: number;
    macro_cache_ttl_seconds: number;
    max_defasagem_dias: number;
    deral_active_snapshot: string;
}

interface MensagensConfigData {
    aviso_precos_deral: string;
    aviso_ptax: string;
    aviso_macro_bcb: string;
    aviso_ibge: string;
    banner_urgente: string | null;
}

interface FeatureFlagsData {
    clima_enabled: boolean;
    mercado_enabled: boolean;
    byok_enabled: boolean;
    ibge_enabled: boolean;
    calculadoras_enabled: boolean;
}

interface AllConfigsResponse {
    clima: ConfigItem<ClimaConfigData>;
    mercado: ConfigItem<MercadoConfigData>;
    mensagens: ConfigItem<MensagensConfigData>;
    feature_flags: ConfigItem<FeatureFlagsData>;
}

export default function AgroConfiguracoesPage() {
    const queryClient = useQueryClient();
    const canEdit = usePermission("backoffice:agro:config:edit");

    // Estados locais para edição dos formulários
    const [mensagensForm, setMensagensForm] = useState<MensagensConfigData | null>(null);
    const [flagsForm, setFlagsForm] = useState<FeatureFlagsData | null>(null);
    const [mercadoForm, setMercadoForm] = useState<MercadoConfigData | null>(null);

    // Consulta consolidada
    const {
        data: configs,
        isLoading,
        isFetching,
        refetch,
    } = useQuery<AllConfigsResponse>({
        queryKey: ["backoffice", "agro", "configuracoes"],
        queryFn: () => apiFetch<AllConfigsResponse>("/backoffice/agro/configuracoes"),
    });

    // Sincroniza estado dos formulários quando a query responder
    useEffect(() => {
        if (configs) {
            setMensagensForm(configs.mensagens.valor);
            setFlagsForm(configs.feature_flags.valor);
            setMercadoForm(configs.mercado.valor);
        }
    }, [configs]);

    // Mutação de salvamento de configuração
    const updateMutation = useMutation({
        mutationFn: async ({
            chave,
            valor,
            expectedRevision,
        }: {
            chave: string;
            valor: Record<string, unknown>;
            expectedRevision?: number;
        }) => {
            return apiFetch(`/backoffice/agro/configuracoes/${chave}`, {
                method: "PUT",
                body: {
                    valor,
                    expected_revision: expectedRevision,
                },
            });
        },
        onSuccess: (_data, variables) => {
            toast.success("Configuração atualizada com sucesso", {
                description: `A chave ${variables.chave} foi persistida e a invalidação de cache foi propagada.`,
            });
            queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "configuracoes"] });
        },
        onError: (err: unknown) => {
            const error = err as { status?: number; message?: string; detail?: string };
            if (error.status === 409) {
                toast.error("Conflito de Concorrência Detectado", {
                    description: "Outro administrador modificou esta configuração simultaneamente. Recarregando dados...",
                });
                queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "configuracoes"] });
            } else {
                toast.error("Erro ao salvar configuração", {
                    description: error.detail || error.message || "Verifique os dados informados.",
                });
            }
        },
    });

    // Mutação de limpeza manual de cache
    const clearCacheMutation = useMutation({
        mutationFn: async () => {
            return apiFetch<{ message: string }>("/backoffice/agro/configuracoes/cache/clear", {
                method: "POST",
            });
        },
        onSuccess: (res) => {
            toast.success("Caches Invalidados", {
                description: res.message,
            });
            refetch();
        },
        onError: (err: unknown) => {
            const error = err as { message?: string };
            toast.error("Falha ao invalidar cache", {
                description: error.message || "Não foi possível propagar o sinal de expiração.",
            });
        },
    });

    const handleSaveMensagens = (e: React.FormEvent) => {
        e.preventDefault();
        if (!mensagensForm || !configs) return;
        updateMutation.mutate({
            chave: "agro:mensagens:avisos",
            valor: mensagensForm as unknown as Record<string, unknown>,
            expectedRevision: configs.mensagens.meta.revision,
        });
    };

    const handleSaveFlags = (e: React.FormEvent) => {
        e.preventDefault();
        if (!flagsForm || !configs) return;
        updateMutation.mutate({
            chave: "agro:feature_flags",
            valor: flagsForm as unknown as Record<string, unknown>,
            expectedRevision: configs.feature_flags.meta.revision,
        });
    };

    const handleSaveMercado = (e: React.FormEvent) => {
        e.preventDefault();
        if (!mercadoForm || !configs) return;
        updateMutation.mutate({
            chave: "agro:mercado:config",
            valor: mercadoForm as unknown as Record<string, unknown>,
            expectedRevision: configs.mercado.meta.revision,
        });
    };

    if (isLoading) {
        return (
            <div className="p-6 space-y-6">
                <Skeleton className="h-14 w-1/3 rounded-sm" />
                <div className="grid gap-4 md:grid-cols-4">
                    <Skeleton className="h-24 rounded-sm" />
                    <Skeleton className="h-24 rounded-sm" />
                    <Skeleton className="h-24 rounded-sm" />
                    <Skeleton className="h-24 rounded-sm" />
                </div>
                <Skeleton className="h-96 rounded-sm" />
            </div>
        );
    }

    const totalFlagsAtivas = configs?.feature_flags.valor
        ? Object.values(configs.feature_flags.valor).filter(Boolean).length
        : 0;

    return (
        <div className="p-6 space-y-6">
            <PageHeader
                title="Configurações Globais do DeepFarms Agro"
                description="Administração centralizada de parâmetros dinâmicos, textos legais regulatórios e feature flags."
                icon={<Settings className="text-emerald-600 dark:text-emerald-400" size={24} />}
                breadcrumbs={[
                    { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
                    { label: "Agro", href: "/dashboard/backoffice/agro" },
                    { label: "Configurações" },
                ]}
                actions={
                    <div className="flex items-center gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => refetch()}
                            disabled={isFetching}
                            className="rounded-sm gap-1.5 h-8 text-xs font-semibold"
                        >
                            <RefreshCw size={14} className={isFetching ? "animate-spin" : ""} />
                            Recarregar
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => clearCacheMutation.mutate()}
                            disabled={clearCacheMutation.isPending || !canEdit}
                            className="rounded-sm gap-1.5 h-8 text-xs font-semibold text-amber-700 hover:text-amber-800 dark:text-amber-400"
                        >
                            <RotateCcw size={14} className={clearCacheMutation.isPending ? "animate-spin" : ""} />
                            Limpar Cache
                        </Button>
                    </div>
                }
            />

            {/* Aviso de permissão */}
            {!canEdit && (
                <Alert className="rounded-sm border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200">
                    <Lock className="h-4 w-4 text-amber-600" />
                    <AlertTitle className="text-xs font-bold uppercase tracking-wider">Modo Somente Leitura</AlertTitle>
                    <AlertDescription className="text-xs mt-0.5">
                        Seu perfil possui autorização para visualização, mas não possui a permissão{" "}
                        <code className="font-mono text-[11px] bg-amber-500/20 px-1 py-0.5 rounded-sm">
                            backoffice:agro:config:edit
                        </code>{" "}
                        necessária para persistir alterações.
                    </AlertDescription>
                </Alert>
            )}

            {/* Cards de Métricas e Estado Consolidado */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card className="rounded-sm border-l-[3px] border-l-emerald-600 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
                            <Clock size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Revisão Geral
                            </p>
                            <p className="text-lg font-black text-foreground">
                                Rev #{configs?.mensagens.meta.revision ?? 1}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                                {configs?.mensagens.meta.updated_at
                                    ? format(new Date(configs.mensagens.meta.updated_at), "dd/MM/yyyy HH:mm", { locale: ptBR })
                                    : "Padrão inicial"}
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="rounded-sm border-l-[3px] border-l-blue-600 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-700 dark:bg-blue-500/20 dark:text-blue-300">
                            <Flag size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Feature Flags Ativas
                            </p>
                            <p className="text-lg font-black text-foreground">{totalFlagsAtivas} / 5</p>
                            <p className="text-[10px] text-muted-foreground">Módulos operacionais</p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="rounded-sm border-l-[3px] border-l-indigo-600 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300">
                            <TrendingUp size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Cache de Mercado
                            </p>
                            <p className="text-lg font-black text-foreground">
                                {configs?.mercado.valor.ptax_cache_ttl_seconds ?? 1800}s
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                                Tolerância: {configs?.mercado.valor.max_defasagem_dias ?? 14} dias
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="rounded-sm border-l-[3px] border-l-amber-600 shadow-xs">
                    <CardContent className="p-4 flex items-center gap-4">
                        <div className="h-10 w-10 rounded-full bg-amber-500/10 flex items-center justify-center text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">
                            <CloudSun size={20} />
                        </div>
                        <div>
                            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                                Provedor de Clima
                            </p>
                            <p className="text-lg font-black text-foreground">
                                {configs?.clima.valor.active_provider ?? "WEATHERAPI"}
                            </p>
                            <p className="text-[10px] text-muted-foreground">
                                Cota: {((configs?.clima.valor.monthly_quota_limit ?? 100000) / 1000).toFixed(0)}k/mês
                            </p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Painel com Abas de Configuração */}
            <Tabs defaultValue="mensagens" className="w-full">
                <TabsList className="bg-muted/80 rounded-sm p-1 border gap-1">
                    <TabsTrigger value="mensagens" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <MessageSquare size={13} />
                        Avisos Legais & Mensagens
                    </TabsTrigger>
                    <TabsTrigger value="flags" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <Flag size={13} />
                        Feature Flags
                    </TabsTrigger>
                    <TabsTrigger value="mercado" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <TrendingUp size={13} />
                        Mercado & Cache
                    </TabsTrigger>
                    <TabsTrigger value="clima" className="rounded-sm text-xs gap-1.5 font-semibold">
                        <CloudSun size={13} />
                        Políticas Climáticas (01E3)
                    </TabsTrigger>
                </TabsList>

                {/* ABA 1: AVISOS LEGAIS E MENSAGENS */}
                <TabsContent value="mensagens" className="mt-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="pb-3 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Avisos Legais Regulatórios e Banners</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Textos de proveniência exibidos no rodapé de cotações, PTAX e estatísticas oficiais.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Revisão #{configs?.mensagens.meta.revision}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6">
                            <form onSubmit={handleSaveMensagens} className="space-y-4">
                                <div className="space-y-1.5">
                                    <Label htmlFor="aviso_precos_deral" className="text-xs font-semibold">
                                        Aviso Legal — Preços Públicos DERAL/SEAB-PR
                                    </Label>
                                    <Textarea
                                        id="aviso_precos_deral"
                                        value={mensagensForm?.aviso_precos_deral ?? ""}
                                        onChange={(e) =>
                                            setMensagensForm((prev) =>
                                                prev ? { ...prev, aviso_precos_deral: e.target.value } : null
                                            )
                                        }
                                        disabled={!canEdit}
                                        className="h-16 text-xs rounded-sm resize-none"
                                        required
                                        minLength={10}
                                        maxLength={500}
                                    />
                                    <p className="text-[11px] text-muted-foreground">
                                        Exibido no card de preços públicos e no rodapé da página de mercado.
                                    </p>
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="space-y-1.5">
                                        <Label htmlFor="aviso_ptax" className="text-xs font-semibold">
                                            Aviso Legal — Banco Central PTAX
                                        </Label>
                                        <Textarea
                                            id="aviso_ptax"
                                            value={mensagensForm?.aviso_ptax ?? ""}
                                            onChange={(e) =>
                                                setMensagensForm((prev) =>
                                                    prev ? { ...prev, aviso_ptax: e.target.value } : null
                                                )
                                            }
                                            disabled={!canEdit}
                                            className="h-16 text-xs rounded-sm resize-none"
                                            required
                                            minLength={10}
                                            maxLength={500}
                                        />
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="aviso_macro_bcb" className="text-xs font-semibold">
                                            Aviso Legal — Indicadores Macro (SGS/BCB)
                                        </Label>
                                        <Textarea
                                            id="aviso_macro_bcb"
                                            value={mensagensForm?.aviso_macro_bcb ?? ""}
                                            onChange={(e) =>
                                                setMensagensForm((prev) =>
                                                    prev ? { ...prev, aviso_macro_bcb: e.target.value } : null
                                                )
                                            }
                                            disabled={!canEdit}
                                            className="h-16 text-xs rounded-sm resize-none"
                                            required
                                            minLength={10}
                                            maxLength={500}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1.5">
                                    <Label htmlFor="aviso_ibge" className="text-xs font-semibold">
                                        Aviso Legal — Estatísticas Agropecuárias IBGE SIDRA
                                    </Label>
                                    <Textarea
                                        id="aviso_ibge"
                                        value={mensagensForm?.aviso_ibge ?? ""}
                                        onChange={(e) =>
                                            setMensagensForm((prev) =>
                                                prev ? { ...prev, aviso_ibge: e.target.value } : null
                                            )
                                        }
                                        disabled={!canEdit}
                                        className="h-16 text-xs rounded-sm resize-none"
                                        required
                                        minLength={10}
                                        maxLength={500}
                                    />
                                </div>

                                <div className="space-y-1.5 pt-2 border-t">
                                    <Label htmlFor="banner_urgente" className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                                        Banner de Utilidade Pública / Aviso Operacional (Opcional)
                                    </Label>
                                    <Input
                                        id="banner_urgente"
                                        placeholder="Deixe em branco para desativar o banner do topo do app..."
                                        value={mensagensForm?.banner_urgente ?? ""}
                                        onChange={(e) =>
                                            setMensagensForm((prev) =>
                                                prev ? { ...prev, banner_urgente: e.target.value || null } : null
                                            )
                                        }
                                        disabled={!canEdit}
                                        className="h-8 text-xs rounded-sm"
                                        maxLength={300}
                                    />
                                    <p className="text-[11px] text-muted-foreground">
                                        Quando preenchido, exibe uma faixa de alerta urgente no cabeçalho do DeepFarms Agro PWA.
                                    </p>
                                </div>

                                <div className="flex justify-end pt-3">
                                    <Button
                                        type="submit"
                                        variant="outline"
                                        size="sm"
                                        disabled={!canEdit || updateMutation.isPending}
                                        className="rounded-sm gap-1.5 h-8 text-xs font-semibold border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
                                    >
                                        <Save size={14} />
                                        {updateMutation.isPending ? "Salvando..." : "Salvar Avisos Legais"}
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 2: FEATURE FLAGS OPERACIONAIS */}
                <TabsContent value="flags" className="mt-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="pb-3 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Interruptores de Funcionalidades (Feature Flags)</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Controle de ativação granular das capacidades disponibilizadas no PWA dos produtores rurais.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Revisão #{configs?.feature_flags.meta.revision}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6">
                            <form onSubmit={handleSaveFlags} className="space-y-6">
                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="flex items-center justify-between p-3 rounded-sm border bg-muted/20">
                                        <div className="space-y-0.5">
                                            <Label className="text-xs font-bold text-foreground">Inteligência Climática</Label>
                                            <p className="text-[11px] text-muted-foreground">
                                                Previsão agrometeorológica, alertas de geada e dados horários.
                                            </p>
                                        </div>
                                        <Switch
                                            checked={flagsForm?.clima_enabled ?? true}
                                            onCheckedChange={(checked) =>
                                                setFlagsForm((prev) => (prev ? { ...prev, clima_enabled: checked } : null))
                                            }
                                            disabled={!canEdit}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-3 rounded-sm border bg-muted/20">
                                        <div className="space-y-0.5">
                                            <Label className="text-xs font-bold text-foreground">Mercado & Cotações</Label>
                                            <p className="text-[11px] text-muted-foreground">
                                                Preços públicos DERAL, dólar PTAX e indicadores macroeconômicos.
                                            </p>
                                        </div>
                                        <Switch
                                            checked={flagsForm?.mercado_enabled ?? true}
                                            onCheckedChange={(checked) =>
                                                setFlagsForm((prev) => (prev ? { ...prev, mercado_enabled: checked } : null))
                                            }
                                            disabled={!canEdit}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-3 rounded-sm border bg-muted/20">
                                        <div className="space-y-0.5">
                                            <Label className="text-xs font-bold text-foreground">Cofre BYOK Individual</Label>
                                            <p className="text-[11px] text-muted-foreground">
                                                Permite ao produtor cadastrar sua própria chave meteorológica privada.
                                            </p>
                                        </div>
                                        <Switch
                                            checked={flagsForm?.byok_enabled ?? true}
                                            onCheckedChange={(checked) =>
                                                setFlagsForm((prev) => (prev ? { ...prev, byok_enabled: checked } : null))
                                            }
                                            disabled={!canEdit}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-3 rounded-sm border bg-muted/20">
                                        <div className="space-y-0.5">
                                            <Label className="text-xs font-bold text-foreground">Estatísticas IBGE SIDRA</Label>
                                            <p className="text-[11px] text-muted-foreground">
                                                Histórico oficial de produção municipal agrícola e pecuária.
                                            </p>
                                        </div>
                                        <Switch
                                            checked={flagsForm?.ibge_enabled ?? true}
                                            onCheckedChange={(checked) =>
                                                setFlagsForm((prev) => (prev ? { ...prev, ibge_enabled: checked } : null))
                                            }
                                            disabled={!canEdit}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between p-3 rounded-sm border bg-muted/20 md:col-span-2">
                                        <div className="space-y-0.5">
                                            <Label className="text-xs font-bold text-foreground">Calculadoras Agronômicas</Label>
                                            <p className="text-[11px] text-muted-foreground">
                                                Ferramentas de cálculo de calagem, sementes, adubação e defensivos.
                                            </p>
                                        </div>
                                        <Switch
                                            checked={flagsForm?.calculadoras_enabled ?? true}
                                            onCheckedChange={(checked) =>
                                                setFlagsForm((prev) => (prev ? { ...prev, calculadoras_enabled: checked } : null))
                                            }
                                            disabled={!canEdit}
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end pt-2">
                                    <Button
                                        type="submit"
                                        variant="outline"
                                        size="sm"
                                        disabled={!canEdit || updateMutation.isPending}
                                        className="rounded-sm gap-1.5 h-8 text-xs font-semibold border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
                                    >
                                        <Save size={14} />
                                        {updateMutation.isPending ? "Salvando..." : "Salvar Feature Flags"}
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 3: MERCADO & CACHE */}
                <TabsContent value="mercado" className="mt-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="pb-3 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Parâmetros Operacionais de Mercado e Cache</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Políticas de renovação de cache, tolerância de defasagem e ponteiro de snapshot ativo.
                                    </CardDescription>
                                </div>
                                <Badge variant="outline" className="text-[10px] font-mono rounded-sm">
                                    Revisão #{configs?.mercado.meta.revision}
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6">
                            <Alert className="mb-6 rounded-sm border-blue-500/30 bg-blue-500/10 text-blue-900 dark:text-blue-200">
                                <Info className="h-4 w-4 text-blue-600" />
                                <AlertTitle className="text-xs font-bold">Imutabilidade de Cotações Oficiais</AlertTitle>
                                <AlertDescription className="text-xs mt-0.5">
                                    Os valores de preços do DERAL, cotações do Banco Central e dados do IBGE são dados oficiais
                                    somente leitura. O Backoffice permite administrar apenas TTLs de cache e o arquivo de snapshot ativo.
                                </AlertDescription>
                            </Alert>

                            <form onSubmit={handleSaveMercado} className="space-y-4">
                                <div className="grid gap-4 md:grid-cols-3">
                                    <div className="space-y-1.5">
                                        <Label htmlFor="ptax_cache_ttl" className="text-xs font-semibold">
                                            TTL Cache PTAX (segundos)
                                        </Label>
                                        <Input
                                            id="ptax_cache_ttl"
                                            type="number"
                                            value={mercadoForm?.ptax_cache_ttl_seconds ?? 1800}
                                            onChange={(e) =>
                                                setMercadoForm((prev) =>
                                                    prev ? { ...prev, ptax_cache_ttl_seconds: parseInt(e.target.value, 10) || 1800 } : null
                                                )
                                            }
                                            disabled={!canEdit}
                                            min={300}
                                            max={14400}
                                            className="h-8 text-xs rounded-sm"
                                            required
                                        />
                                        <p className="text-[11px] text-muted-foreground">Padrão: 1800s (30 minutos)</p>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="macro_cache_ttl" className="text-xs font-semibold">
                                            TTL Cache Macro SGS (segundos)
                                        </Label>
                                        <Input
                                            id="macro_cache_ttl"
                                            type="number"
                                            value={mercadoForm?.macro_cache_ttl_seconds ?? 1800}
                                            onChange={(e) =>
                                                setMercadoForm((prev) =>
                                                    prev ? { ...prev, macro_cache_ttl_seconds: parseInt(e.target.value, 10) || 1800 } : null
                                                )
                                            }
                                            disabled={!canEdit}
                                            min={300}
                                            max={86400}
                                            className="h-8 text-xs rounded-sm"
                                            required
                                        />
                                        <p className="text-[11px] text-muted-foreground">Padrão: 1800s (30 minutos)</p>
                                    </div>

                                    <div className="space-y-1.5">
                                        <Label htmlFor="max_defasagem_dias" className="text-xs font-semibold">
                                            Tolerância de Defasagem (dias)
                                        </Label>
                                        <Input
                                            id="max_defasagem_dias"
                                            type="number"
                                            value={mercadoForm?.max_defasagem_dias ?? 14}
                                            onChange={(e) =>
                                                setMercadoForm((prev) =>
                                                    prev ? { ...prev, max_defasagem_dias: parseInt(e.target.value, 10) || 14 } : null
                                                )
                                            }
                                            disabled={!canEdit}
                                            min={1}
                                            max={60}
                                            className="h-8 text-xs rounded-sm"
                                            required
                                        />
                                        <p className="text-[11px] text-muted-foreground">Limite para alerta de dados defasados</p>
                                    </div>
                                </div>

                                <div className="space-y-1.5 pt-2">
                                    <Label htmlFor="deral_snapshot" className="text-xs font-semibold">
                                        Snapshot Semanal DERAL Ativo
                                    </Label>
                                    <Input
                                        id="deral_snapshot"
                                        value={mercadoForm?.deral_active_snapshot ?? ""}
                                        onChange={(e) =>
                                            setMercadoForm((prev) =>
                                                prev ? { ...prev, deral_active_snapshot: e.target.value } : null
                                            )
                                        }
                                        disabled={!canEdit}
                                        className="h-8 text-xs rounded-sm font-mono"
                                        pattern="^deral-prp-[0-9]{4}-[0-9]{2}-[0-9]{2}\.json$"
                                        required
                                    />
                                    <p className="text-[11px] text-muted-foreground">
                                        Formato esperado: <code className="font-mono text-[11px]">deral-prp-YYYY-MM-DD.json</code>.
                                        O upload automatizado com validação SHA-256 e rollback será ativado na Fase 01E4.
                                    </p>
                                </div>

                                <div className="flex justify-end pt-3">
                                    <Button
                                        type="submit"
                                        variant="outline"
                                        size="sm"
                                        disabled={!canEdit || updateMutation.isPending}
                                        className="rounded-sm gap-1.5 h-8 text-xs font-semibold border-emerald-600 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-500 dark:text-emerald-300 dark:hover:bg-emerald-500/10"
                                    >
                                        <Save size={14} />
                                        {updateMutation.isPending ? "Salvando..." : "Salvar Parâmetros de Mercado"}
                                    </Button>
                                </div>
                            </form>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* ABA 4: POLÍTICAS CLIMÁTICAS (SOMENTE LEITURA - AGRO-ADMIN-01E3) */}
                <TabsContent value="clima" className="mt-4">
                    <Card className="rounded-sm shadow-xs border">
                        <CardHeader className="pb-3 border-b">
                            <div className="flex items-center justify-between">
                                <div>
                                    <CardTitle className="text-sm font-bold">Políticas Meteorológicas e Limites</CardTitle>
                                    <CardDescription className="text-xs mt-0.5">
                                        Parâmetros canônicos do orquestrador de clima público.
                                    </CardDescription>
                                </div>
                                <Badge variant="secondary" className="text-[10px] font-semibold rounded-sm">
                                    Fase 01E3 (Em Breve)
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="p-6 space-y-4">
                            <Alert className="rounded-sm border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200">
                                <AlertTriangle className="h-4 w-4 text-amber-600" />
                                <AlertTitle className="text-xs font-bold">Consumidor Dinâmico em Implementação</AlertTitle>
                                <AlertDescription className="text-xs mt-0.5">
                                    Os parâmetros abaixo foram persistidos com sucesso na fundação 01E2.
                                    A substituição da inicialização estática em runtime, chaveamento dinâmico sem reinício de container,
                                    gestão de credenciais com criptografia AES-256 e teste de conectividade serão implementados
                                    exclusivamente na subfase <strong>AGRO-ADMIN-01E3</strong>.
                                </AlertDescription>
                            </Alert>

                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="p-3 rounded-sm border bg-muted/10 space-y-1">
                                    <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                        Provedor Meteorológico Ativo
                                    </Label>
                                    <p className="text-sm font-bold text-foreground">
                                        {configs?.clima.valor.active_provider ?? "WEATHERAPI"}
                                    </p>
                                </div>

                                <div className="p-3 rounded-sm border bg-muted/10 space-y-1">
                                    <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                        Cadeia de Contingência
                                    </Label>
                                    <div className="flex items-center gap-1.5">
                                        {configs?.clima.valor.fallback_chain?.map((prov, i) => (
                                            <Badge key={i} variant="outline" className="text-[10px] font-mono rounded-sm">
                                                {i + 1}. {prov}
                                            </Badge>
                                        )) ?? <span className="text-xs text-muted-foreground">Nenhuma</span>}
                                    </div>
                                </div>

                                <div className="p-3 rounded-sm border bg-muted/10 space-y-1">
                                    <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                        Timeout Upstream
                                    </Label>
                                    <p className="text-sm font-bold text-foreground">
                                        {configs?.clima.valor.timeout_seconds ?? 5.0} segundos
                                    </p>
                                </div>

                                <div className="p-3 rounded-sm border bg-muted/10 space-y-1">
                                    <Label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                                        Franquia Mensal Contratada
                                    </Label>
                                    <p className="text-sm font-bold text-foreground">
                                        {(configs?.clima.valor.monthly_quota_limit ?? 100000).toLocaleString("pt-BR")} chamadas
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
