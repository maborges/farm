"use client";

import { useEffect, useRef, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "@/lib/stores/app-store";
import { apiFetch } from "@/lib/api";
import { extractTenantContextsFromToken } from "@/lib/jwt";
import type { UnidadeProdutiva, TenantSummary } from "@/types/global";

/**
 * Componente invisível que re-sincroniza os contextos de tenant/fazendas do Zustand store
 * com os dados reais do servidor a cada 60s e após mutações.
 *
 * Resolve o problema de "fazenda aparece no header mas não no cadastro":
 * os contextos no Zustand são um snapshot do JWT no login e nunca eram atualizados.
 */
export function FazendasSync() {
    const { token, setSession, tenant, user, availableTenants, grupos, loadTenantContexts, _hasHydrated, unidadesProdutivasAutorizadas } = useAppStore();
    const queryClient = useQueryClient();
    const lastSyncRef = useRef<string | null>(null);
    const hasTenantContext = !!tenant?.id && !user?.is_superuser;

    // Buscar tenants disponíveis do servidor (garante que switcher reflita estado real)
    const { data: meData } = useQuery<{ tenants: TenantSummary[] }>({
        queryKey: ["auth-me-tenants"],
        queryFn: () => apiFetch("/auth/my-tenants", { suppressErrorLog: true }),
        enabled: _hasHydrated && !!token,
        refetchOnWindowFocus: true,
        staleTime: 60_000,
        retry: false,
    });

    // Sincronizar availableTenants quando /auth/me responder
    useEffect(() => {
        if (!meData?.tenants) return;
        const store = useAppStore.getState();
        const currentJson = JSON.stringify(store.availableTenants);
        const newJson = JSON.stringify(meData.tenants);
        if (currentJson !== newJson) {
            store.setSession(
                store.token!,
                store.tenant,
                store.user,
                store.grupos,
                store.unidadesProdutivasAutorizadas,
                meData.tenants,
            );
        }
    }, [meData]);

    // Buscar unidades produtivas atualizadas do servidor
    const { data: unidadesServer } = useQuery<UnidadeProdutiva[]>({
        queryKey: ["unidades-produtivas"],
        queryFn: async () => {
            if (!token) {
                return unidadesProdutivasAutorizadas;
            }
            try {
                return await apiFetch("/unidades-produtivas", { suppressErrorLog: true });
            } catch (error) {
                if (unidadesProdutivasAutorizadas.length > 0) {
                    return unidadesProdutivasAutorizadas;
                }
                throw error;
            }
        },
        enabled: _hasHydrated && hasTenantContext && (!!token || unidadesProdutivasAutorizadas.length > 0),
        refetchOnWindowFocus: true,
        refetchInterval: 60_000,
        staleTime: 30_000,
        retry: false,
    });

    // Re-sincronizar quando os dados do servidor chegarem
    useEffect(() => {
        if (!token || !hasTenantContext || !unidadesServer) return;

        // Criar chave de sync baseada nos dados atuais
        const syncKey = `${unidadesServer.length}`;
        if (lastSyncRef.current === syncKey) return;
        lastSyncRef.current = syncKey;

        // Extrair contextos atualizados do JWT (contém modules, plan_tier, limites)
        const jwtGrupos = extractTenantContextsFromToken(token);

        // Enriquecer contextos do JWT com unidades produtivas reais do servidor
        const gruposAtualizados = jwtGrupos.map((jwtGrupo) => {
            const unidadesDoGrupo = unidadesServer.filter((u) => u.ativo);

            return {
                ...jwtGrupo,
                fazendas: unidadesDoGrupo.map((u) => ({
                    id: u.id,
                    nome: u.nome,
                    ativo: u.ativo,
                })),
            };
        });

        // Se houve mudança significativa, atualizar o store
        const gruposChanged = JSON.stringify(gruposAtualizados) !== JSON.stringify(grupos);
        if (gruposChanged && gruposAtualizados.length > 0) {
            setSession(token, tenant, user, gruposAtualizados, unidadesServer, availableTenants);
            // Carrega contextos após sincronizar unidades produtivas
            loadTenantContexts();
        }
    }, [unidadesServer, token, hasTenantContext, tenant, setSession, loadTenantContexts, availableTenants, grupos, user]);

    // Escutar eventos de storage para mutações em outras tabs
    useEffect(() => {
        const handleStorage = (e: StorageEvent) => {
            if (e.key?.includes("fazendas-sync")) {
                // Invalidar cache do React Query para forçar re-fetch
                queryClient.invalidateQueries({ queryKey: ["unidades-produtivas"] });
            }
        };
        window.addEventListener("storage", handleStorage);
        return () => window.removeEventListener("storage", handleStorage);
    }, [queryClient]);

    return null;
}

/**
 * Hook para invalidar o cache de contextos/fazendas após mutações.
 * Use em formulários de criar/editar/deletar fazendas.
 *
 * Exemplo:
 *   const invalidate = useInvalidateFazendasCache();
 *   // após sucesso da mutação:
 *   invalidate();
 */
export function useInvalidateFazendasCache() {
    const queryClient = useQueryClient();

    return useCallback(() => {
        // Disparar evento cross-tab
        localStorage.setItem("fazendas-sync", Date.now().toString());

        // Invalidar queries do React Query para forçar re-fetch imediato
        queryClient.invalidateQueries({ queryKey: ["unidades-produtivas"] });
    }, [queryClient]);
}
