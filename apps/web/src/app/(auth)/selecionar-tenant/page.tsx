"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Building2, ChevronRight, Loader2, Trees, Layers3 } from "lucide-react";

import { AuthLayout } from "@/components/auth/auth-layout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { useAppStore } from "@/lib/stores/app-store";
import type { TenantSummary } from "@/types/global";

interface MyTenantsResponse {
    tenants: TenantSummary[];
}

export default function SelectTenantPage() {
    const router = useRouter();
    const { token, availableTenants, switchTenantContext, _hasHydrated } = useAppStore();
    const [loadingTenantId, setLoadingTenantId] = useState<string | null>(null);
    const autoSelectRef = useRef(false);

    const { data, isLoading, isError, error, refetch } = useQuery<MyTenantsResponse>({
        queryKey: ["selecionar-tenant-my-tenants"],
        queryFn: () => apiFetch("/auth/my-tenants", { suppressErrorLog: true }),
        enabled: !!token && availableTenants.length === 0,
        retry: false,
        staleTime: 60_000,
    });

    const tenants = useMemo(
        () => (availableTenants.length > 0 ? availableTenants : (data?.tenants ?? [])),
        [availableTenants, data?.tenants],
    );

    useEffect(() => {
        if (_hasHydrated && !token) {
            router.replace("/login");
        }
    }, [router, token, _hasHydrated]);

    useEffect(() => {
        if (!_hasHydrated || !token || tenants.length !== 1 || autoSelectRef.current || isError) {
            return;
        }

        autoSelectRef.current = true;
        void switchTenantContext(tenants[0].tenant_id);
    }, [switchTenantContext, tenants, token, _hasHydrated, isError]);

    const handleSelect = async (tenantId: string) => {
        setLoadingTenantId(tenantId);
        try {
            await switchTenantContext(tenantId);
        } finally {
            setLoadingTenantId(null);
        }
    };

    if (!_hasHydrated || !token) {
        return (
            <div className="flex min-h-dvh items-center justify-center bg-background p-6">
                <div className="rounded-sm border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm">
                    Carregando autenticação...
                </div>
            </div>
        );
    }

    if (isError) {
        return (
            <AuthLayout
                badgeLabel="Erro de Conexão"
                title="Ops! Servidor indisponível."
                description={error instanceof Error ? error.message : "Ocorreu um erro ao carregar suas organizações. O sistema pode estar com alta carga."}
                stats={[
                    { value: "Falha", label: "Status" },
                    { value: "Erro", label: "Conexão" },
                ]}
            >
                <div className="flex flex-col items-center justify-center space-y-4 py-8">
                    <p className="text-sm text-center text-muted-foreground">
                        Não foi possível carregar as informações do seu perfil no momento.
                    </p>
                    <Button onClick={() => refetch()} variant="outline" size="sm" className="rounded-sm">
                        Tentar novamente
                    </Button>
                </div>
            </AuthLayout>
        );
    }

    if (isLoading && tenants.length === 0) {
        return (
            <AuthLayout
                badgeLabel="Contexto multi-tenant"
                title="Carregando seus tenants."
                description="Estamos buscando as organizações vinculadas à sua conta para você escolher o contexto correto."
                stats={[
                    { value: "1", label: "Conta autenticada" },
                    { value: "0", label: "Tenant ativo" },
                    { value: "Seguro", label: "Troca de contexto" },
                ]}
            >
                <div className="flex items-center justify-center py-10">
                    <Loader2 className="size-8 animate-spin text-primary" />
                </div>
            </AuthLayout>
        );
    }

    if (tenants.length === 1) {
        return (
            <AuthLayout
                badgeLabel="Contexto automático"
                title="Selecionando seu tenant."
                description="Como você tem apenas uma organização vinculada, estamos abrindo o contexto automaticamente."
                stats={[
                    { value: "1", label: "Tenant disponível" },
                    { value: "Auto", label: "Seleção" },
                    { value: "Pronto", label: "Redirecionamento" },
                ]}
            >
                <div className="flex items-center justify-center py-10">
                    <Loader2 className="size-8 animate-spin text-primary" />
                </div>
            </AuthLayout>
        );
    }

    return (
        <AuthLayout
            badgeLabel="Multi-tenant"
            title="Escolha o tenant ativo."
            description="Selecione a organização que você quer abrir agora. Você poderá trocar de contexto depois pelo topo do dashboard."
            stats={[
                { value: String(tenants.length), label: "Organizações" },
                { value: "1", label: "Contexto por vez" },
                { value: "Rápido", label: "Troca segura" },
            ]}
        >
            <div className="space-y-4">
                <div className="rounded-sm border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                    Sua conta tem acesso a mais de um tenant. Escolher o contexto agora evita carregar dados do produtor errado.
                </div>

                <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
                    {tenants.map((tenant) => {
                        const isBusy = loadingTenantId === tenant.tenant_id;
                        const isSingleFarm = tenant.fazendas.length === 1;

                        return (
                            <Card key={tenant.tenant_id} className="rounded-sm border-border bg-card/80 p-4 shadow-sm">
                                <div className="flex items-start gap-3">
                                    <div className="flex size-10 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
                                        <Building2 className="size-4" />
                                    </div>

                                    <div className="min-w-0 flex-1 space-y-2">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <h2 className="truncate text-sm font-bold text-foreground">
                                                {tenant.nome_tenant}
                                            </h2>
                                            <Badge variant="outline" className="rounded-sm text-[10px] uppercase tracking-wider">
                                                {tenant.perfil?.nome ?? "Tenant"}
                                            </Badge>
                                        </div>

                                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                            <span className="inline-flex items-center gap-1">
                                                <Trees className="size-3.5" />
                                                {tenant.fazendas.length} fazenda(s)
                                            </span>
                                            <span className="inline-flex items-center gap-1">
                                                <Layers3 className="size-3.5" />
                                                {tenant.modulos?.length ?? 0} módulo(s)
                                            </span>
                                            {isSingleFarm && (
                                                <Badge variant="secondary" className="rounded-sm text-[10px]">
                                                    Contexto único
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4 flex items-center justify-between gap-3">
                                    <p className="text-[11px] text-muted-foreground">
                                        {tenant.is_owner ? "Conta proprietária" : "Acesso vinculado"}
                                    </p>

                                    <Button
                                        type="button"
                                        size="sm"
                                        className="rounded-sm gap-2"
                                        onClick={() => void handleSelect(tenant.tenant_id)}
                                        disabled={isBusy}
                                    >
                                        {isBusy ? (
                                            <Loader2 className="size-4 animate-spin" />
                                        ) : (
                                            <ChevronRight className="size-4" />
                                        )}
                                        Acessar
                                    </Button>
                                </div>
                            </Card>
                        );
                    })}
                </div>
            </div>
        </AuthLayout>
    );
}
