"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Briefcase, ChevronDown, Loader2, Check, Plus } from "lucide-react";
import { NewSubscriptionWizard } from "@/components/auth/new-subscription-wizard";
import { setAuthCookies } from "@/app/actions/auth";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import type { TenantSummary, UnidadeProdutiva } from "@/types/global";

interface CurrentProfileResponse {
    tenants: TenantSummary[];
}

export function TenantSwitcher() {
    const { availableTenants, tenant, setSession, user, token, loadTenantContexts } = useAppStore();
    const router = useRouter();
    const [switching, setSwitching] = useState(false);
    const [wizardOpen, setWizardOpen] = useState(false);

    // Busca lista de tenants diretamente do servidor (sem billing guard)
    const { data: myTenantsData } = useQuery<{ tenants: TenantSummary[] }>({
        queryKey: ["my-tenants"],
        queryFn: () => apiFetch("/auth/my-tenants"),
        enabled: !!token,
        staleTime: 120_000,
        retry: 1,
    });

    // Usa dados frescos do servidor; fallback para store se ainda carregando
    const tenants: TenantSummary[] = myTenantsData?.tenants?.length
        ? myTenantsData.tenants
        : availableTenants;

    useEffect(() => {
        if (tenant) loadTenantContexts();
    }, [tenant, loadTenantContexts]);

    const activeTenantId = String(tenant?.id ?? "");

    const switchTenant = async (targetTenant: TenantSummary) => {
        const targetId = String(targetTenant.tenant_id);
        if (targetId === activeTenantId) return;

        setSwitching(true);
        try {
            const { access_token } = await apiFetch<{ access_token: string }>("/auth/switch-tenant", {
                method: "POST",
                headers: { "x-tenant-id": targetId },
            });

            useAppStore.setState({ token: access_token });
            await setAuthCookies(access_token);
            const profile = await apiFetch<CurrentProfileResponse>("/auth/me");
            const tenantAtual = profile.tenants?.find((t: TenantSummary) => String(t.tenant_id) === targetId) ?? targetTenant;
            const grupos = extractTenantContextsFromToken(access_token);

            await setAuthCookies(
                access_token,
                tenantAtual.tenant_id,
                tenantAtual.fazendas?.[0]?.unidade_produtiva_id
            );

            setSession(
                access_token,
                {
                    id: tenantAtual.tenant_id,
                    nome: tenantAtual.nome_tenant,
                    documento: "",
                    slug: "",
                    dominio_customizado: null,
                    branding: { primaryColor: "142 71% 45%" },
                },
                user,
                grupos,
                (tenantAtual.fazendas ?? []).map<UnidadeProdutiva>((f) => ({
                    id: f.unidade_produtiva_id,
                    nome: f.nome,
                    tenant_id: targetTenant.tenant_id,
                    tipo_propriedade: null,
                    cpf_cnpj: null,
                    inscricao_estadual: null,
                    codigo_car: null,
                    nirf: null,
                    ccir: null,
                    sigef_codigo: null,
                    cep: null,
                    logradouro: null,
                    numero: null,
                    complemento: null,
                    bairro: null,
                    municipio: null,
                    uf: null,
                    ibge_municipio_codigo: null,
                    area_total_ha: null,
                    area_app_ha: null,
                    area_rl_ha: null,
                    coordenadas_sede: null,
                    geometria: null,
                    logo_url: null,
                    ativo: true,
                    numero_matricula: null,
                    area_total_calculada_ha: null,
                    created_at: "",
                    updated_at: "",
                })),
                tenants,
            );

            toast.success(`Contexto alterado para ${tenantAtual.nome_tenant}`);
            loadTenantContexts();
            router.push("/dashboard");
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Erro ao trocar de produtor. Tente novamente.";
            toast.error(message);
        } finally {
            setSwitching(false);
        }
    };

    // Single tenant — label + botão nova conta
    if (tenants.length <= 1) {
        return (
            <>
                <NewSubscriptionWizard open={wizardOpen} onOpenChange={setWizardOpen} />
                <div className="flex items-center gap-1">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-sm border border-border bg-muted/20">
                        <Briefcase size={14} className="text-primary shrink-0" />
                        <div className="flex flex-col leading-none">
                            <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider">Produtor</span>
                            <span className="text-xs font-semibold text-foreground truncate max-w-[120px]">
                                {tenant?.nome || "—"}
                            </span>
                        </div>
                    </div>
                    <button
                        onClick={() => setWizardOpen(true)}
                        className="flex size-6 items-center justify-center rounded-sm border border-border text-muted-foreground hover:text-primary hover:border-primary/50 transition-colors"
                        title="Nova conta de produtor"
                    >
                        <Plus size={12} />
                    </button>
                </div>
            </>
        );
    }

    // Multi-tenant — dropdown
    return (
        <>
        <NewSubscriptionWizard open={wizardOpen} onOpenChange={setWizardOpen} />
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="ghost"
                    size="sm"
                    className="min-w-0 gap-1.5 rounded-full px-1.5 hover:bg-muted/60 hover:text-foreground aria-expanded:bg-muted/70 aria-expanded:text-foreground focus-visible:ring-primary/20"
                    disabled={switching}
                    aria-label="Selecionar produtor"
                >
                    <Briefcase className="size-4 shrink-0 text-primary" />
                    <span className="hidden max-w-[110px] text-left md:flex md:flex-col md:justify-center">
                        <span className="text-[11px] font-medium leading-tight text-foreground truncate">
                            {tenant?.nome || "Selecionar"}
                        </span>
                    </span>
                    <ChevronDown className="hidden size-3.5 shrink-0 text-primary transition-transform duration-200 md:block group-aria-expanded/button:rotate-180" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
                <DropdownMenuLabel className="flex flex-col gap-1 px-3 py-2">
                    <span className="text-sm font-semibold text-foreground leading-none">Trocar Produtor</span>
                    <span className="text-xs text-muted-foreground truncate max-w-48">{tenant?.nome ?? ""}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                {tenants.map((t) => {
                    const isActive = String(t.tenant_id) === activeTenantId;
                    return (
                        <DropdownMenuItem
                            key={t.tenant_id}
                            onClick={() => switchTenant(t)}
                            disabled={switching || isActive}
                            className="gap-2 cursor-pointer"
                        >
                            <div className="flex flex-1 flex-col gap-0.5">
                                <span className={`text-sm font-medium leading-none ${isActive ? "text-primary" : "text-foreground"}`}>
                                    {t.nome_tenant}
                                </span>
                                <span className="text-[11px] text-muted-foreground truncate">
                                    {t.perfil?.nome ?? "Membro"}
                                </span>
                            </div>
                            {isActive && <Check className="size-4 shrink-0 text-primary" />}
                        </DropdownMenuItem>
                    );
                })}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                    onClick={() => setWizardOpen(true)}
                    className="gap-2 cursor-pointer text-primary"
                >
                    <Plus size={12} />
                    Nova conta de produtor
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
        </>
    );
}
