"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import type { ImpersonationInfo, TenantRole, TenantSummary } from "@/types/global";

interface AuthProfileResponse {
    id: string;
    nome_completo: string;
    apelido?: string | null;
    email: string;
    username: string;
    cpf?: string | null;
    telefone?: string | null;
    foto_perfil_url?: string | null;
    is_superuser: boolean;
    navigation_mode: "SIDEBAR" | "MEGA_MENU";
    tenants: TenantSummary[];
    impersonation?: ImpersonationInfo | null;
}

interface AuthBootstrapProps {
    tokenFromCookie: string | null;
    tenantIdFromCookie: string | null;
    fazendaIdFromCookie: string | null;
}

export function AuthBootstrap({
    tokenFromCookie,
    tenantIdFromCookie,
    fazendaIdFromCookie,
}: AuthBootstrapProps) {
    const didBootstrapRef = useRef(false);
    const router = useRouter();
    const { _hasHydrated, setSession } = useAppStore();

    useEffect(() => {
        if (!_hasHydrated || didBootstrapRef.current) {
            return;
        }
        didBootstrapRef.current = true;

        if (!tokenFromCookie) {
            useAppStore.setState({ token: null });
            router.replace("/login");
            return;
        }

        useAppStore.setState((state) => ({
            ...state,
            token: tokenFromCookie,
            activeGrupoId: tenantIdFromCookie ?? state.activeGrupoId,
            activeFazendaId: fazendaIdFromCookie ?? state.activeFazendaId,
        }));

        let cancelled = false;

        apiFetch<AuthProfileResponse>("/auth/me", { suppressErrorLog: true })
            .then((profile) => {
                if (cancelled) {
                    return;
                }

                const grupos = extractTenantContextsFromToken(tokenFromCookie);
                const tenantAtual =
                    profile.tenants.find((tenant) => tenant.tenant_id === tenantIdFromCookie)
                    ?? profile.tenants[0]
                    ?? null;

                const unidadesProdutivas = tenantAtual
                    ? tenantAtual.fazendas.map((fazenda) => ({
                        id: fazenda.unidade_produtiva_id,
                        nome: fazenda.nome,
                        tenant_id: tenantAtual.tenant_id,
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
                        role: tenantAtual.perfil?.nome ?? "operador",
                    }))
                    : [];

                setSession(
                    tokenFromCookie,
                    tenantAtual ? {
                        id: tenantAtual.tenant_id,
                        nome: tenantAtual.nome_tenant,
                        documento: "",
                        slug: "",
                        dominio_customizado: null,
                        branding: { primaryColor: "154 100% 21%" },
                    } : null,
                    {
                        id: profile.id,
                        name: profile.nome_completo,
                        nickname: profile.apelido ?? undefined,
                        email: profile.email,
                        username: profile.username,
                        cpf: profile.cpf ?? undefined,
                        telefone: profile.telefone ?? undefined,
                        foto_perfil_url: profile.foto_perfil_url ?? undefined,
                        is_superuser: profile.is_superuser,
                        navigation_mode: profile.navigation_mode,
                        tenant_role: tenantAtual?.is_owner
                            ? "owner"
                            : ((tenantAtual?.perfil?.nome?.toLowerCase() as TenantRole | undefined) ?? undefined),
                        custom_permissions: tenantAtual?.perfil?.permissoes ?? undefined,
                    },
                    grupos,
                    unidadesProdutivas,
                    profile.tenants,
                );

                if (profile.impersonation) {
                    useAppStore.getState().setImpersonation(profile.impersonation);
                } else {
                    useAppStore.getState().setImpersonation(null);
                }
            })
            .catch(() => {
                if (cancelled) {
                    return;
                }
                useAppStore.setState({
                    token: null,
                    tenant: null,
                    user: null,
                    grupos: [],
                    unidadesProdutivasAutorizadas: [],
                    tenantContexts: [],
                    activeGrupoId: null,
                    activeFazendaId: null,
                    isVisaoGrupo: false,
                    availableTenants: [],
                });
                router.replace("/login");
            });

        return () => {
            cancelled = true;
        };
    }, [
        _hasHydrated,
        tokenFromCookie,
        tenantIdFromCookie,
        fazendaIdFromCookie,
        router,
        setSession,
    ]);

    return null;
}
