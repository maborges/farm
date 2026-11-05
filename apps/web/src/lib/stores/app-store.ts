import { create } from "zustand";
import { persist } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import { Tenant, User, ModuleId, UnidadeProdutiva, TenantContext, PlanTierId, AssinaturaInfo, TenantSummary, TenantCustomPermissions, ImpersonationInfo } from "@/types/global";
import { apiFetch } from "@/lib/api";
import { getApiOrigin } from "@/lib/runtime-config";
import { normalizePlanTier } from "@/lib/constants/planos";
import { extractTenantContextsFromToken } from "@/lib/jwt";

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
    backoffice_role?: string | null;
}

interface AppState {
    // Dados Vitais Autenticados
    tenant: Tenant | null;
    user: User | null;

    // Impersonação / Acesso Assistido
    impersonation: ImpersonationInfo | null;
    setImpersonation: (info: ImpersonationInfo | null) => void;
    switchImpersonationMode: (modo: "READ_ONLY" | "READ_WRITE", motivo: string) => Promise<void>;
    stopImpersonation: () => Promise<string>;

    // Grupos com assinaturas (nova estrutura — substitui campos flat)
    grupos: TenantContext[];
    unidadesProdutivasAutorizadas: UnidadeProdutiva[];
    tenantContexts: AssinaturaInfo[]; // contextos disponíveis do usuário

    // Contexto Ativo
    activeGrupoId: string | null;
    activeFazendaId: string | null;
    isVisaoGrupo: boolean;

    token: string | null;
    availableTenants: TenantSummary[];

    // UI Preferences
    modoEssencial: boolean;
    setModoEssencial: (value: boolean) => void;

    // Controle de hidratação — evita redirect prematuro no refresh
    _hasHydrated: boolean;
    setHasHydrated: (value: boolean) => void;

    // Ações de mutação
    setSession: (token: string, tenant: Tenant | null, user: User | null, grupos: TenantContext[], unidadesProdutivas: UnidadeProdutiva[], availableTenants?: TenantSummary[]) => void;
    loadTenantContexts: () => Promise<void>;
    switchTenantContext: (tenantId: string) => Promise<void>;
    setActiveFazenda: (id: string, visaoGrupo?: boolean) => void;
    setActiveGrupo: (grupoId: string) => void;
    /** Atualiza as permissões do usuário sem afetar o resto da sessão — usado ao
     * trocar de UP, já que o override de perfil por fazenda não vem no token. */
    setCustomPermissions: (permissoes: TenantCustomPermissions | undefined) => void;
    hasModule: (moduleId: ModuleId) => boolean;
    /** Módulos do grupo ativo (ou union de todos se visão grupo) */
    activeModules: () => ModuleId[];
    /** Tier do grupo ativo */
    activePlanTier: () => PlanTierId;
    logout: () => Promise<void>;
}

const initialState = {
    token: null,
    tenant: null,
    user: null,
    impersonation: null,
    grupos: [],
    unidadesProdutivasAutorizadas: [],
    tenantContexts: [],
    activeGrupoId: null,
    activeFazendaId: null,
    isVisaoGrupo: false,
    availableTenants: [],
    modoEssencial: true,
    _hasHydrated: false,
};

export const useAppStore = create<AppState>()(
    persist(
        immer((set, get) => ({
            ...initialState,

            setHasHydrated: (value) => set((s) => { s._hasHydrated = value; }),

            setModoEssencial: (value) => set((s) => { s.modoEssencial = value; }),

            setSession: (token, tenant, user, grupos, unidadesProdutivas, availableTenants = []) => set((s) => {
                const previousTenantId = s.tenant?.id ?? null;
                s.token = token;
                s.tenant = tenant;
                s.user = user;
                s.grupos = grupos;
                s.unidadesProdutivasAutorizadas = unidadesProdutivas;
                s.availableTenants = availableTenants;
                if (!tenant) {
                    s.activeGrupoId = null;
                    s.activeFazendaId = null;
                    s.isVisaoGrupo = false;
                    return;
                }

                // Reseta contexto ativo apenas se o tenant mudou
                const tenantChanged = previousTenantId !== tenant.id;
                if (tenantChanged || !s.activeGrupoId) {
                    s.activeGrupoId = grupos.length > 0 ? grupos[0].id : null;
                    s.activeFazendaId = grupos[0]?.fazendas?.[0]?.id ?? null;
                    s.isVisaoGrupo = false;
                }

                const activeGrupo = grupos.find((grupo) => grupo.id === s.activeGrupoId) ?? grupos[0] ?? null;
                if (activeGrupo && !grupos.some((grupo) => grupo.id === s.activeGrupoId)) {
                    s.activeGrupoId = activeGrupo.id;
                }

                const fazendaAutorizada = grupos.some((grupo) =>
                    grupo.fazendas.some((fazenda) => fazenda.id === s.activeFazendaId)
                );
                if (!s.isVisaoGrupo && !fazendaAutorizada) {
                    s.activeGrupoId = activeGrupo?.id ?? null;
                    s.activeFazendaId = activeGrupo?.fazendas[0]?.id ?? null;
                }
            }),

            loadTenantContexts: async () => {
                try {
                    const { token, tenant, user } = get();
                    if (!token || !tenant?.id || user?.is_superuser) {
                        return;
                    }

                    const response = await apiFetch<{ tenants: TenantSummary[] }>("/auth/my-tenants");
                    const assinaturas = (response.tenants || []).map((t) => ({
                        tenant_id: t.tenant_id,
                        tenant_nome: t.nome_tenant,
                        plano_nome: t.perfil?.nome ?? "Produtor",
                        plano_tier: t.plan_tier ?? "BASICO",
                        status: t.is_owner ? "ATIVA" : "VINCULADO",
                        total_fazendas: t.fazendas?.length ?? 0,
                        fazendas: (t.fazendas ?? []).map((f) => ({
                            id: f.unidade_produtiva_id,
                            nome: f.nome,
                        })),
                        modulos: t.modulos ?? ["CORE"],
                        is_ativa: true,
                    })) as AssinaturaInfo[];
                    set((s) => {
                        s.tenantContexts = assinaturas;
                    });
                } catch (error) {
                    console.warn("Erro ao carregar contextos:", error);
                }
            },

            switchTenantContext: async (tenantId: string) => {
                try {
                    const response = await apiFetch<{ access_token: string }>("/auth/switch-tenant", {
                        method: "POST",
                        headers: { "x-tenant-id": tenantId },
                    });

                    set((s) => {
                        s.token = response.access_token;
                    });

                    const profile = await apiFetch<AuthProfileResponse>("/auth/me");
                    const tenantAtual = profile.tenants.find((t) => t.tenant_id === tenantId);
                    if (!tenantAtual) {
                        throw new Error("Produtor selecionado não encontrado no perfil atualizado.");
                    }

                    const { setAuthCookies } = await import("@/app/actions/auth");
                    await setAuthCookies(response.access_token);
                    await setAuthCookies(
                        response.access_token,
                        tenantAtual.tenant_id,
                        tenantAtual.fazendas[0]?.unidade_produtiva_id
                    );

                    const grupos = extractTenantContextsFromToken(response.access_token);
                    const unidadesProdutivas = tenantAtual.fazendas.map((f) => ({
                        id: f.unidade_produtiva_id,
                        nome: f.nome,
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
                    }));

                    get().setSession(
                        response.access_token,
                        {
                            id: tenantAtual.tenant_id,
                            nome: tenantAtual.nome_tenant,
                            documento: "",
                            slug: "",
                            dominio_customizado: null,
                            branding: { primaryColor: "154 100% 21%" },
                        },
                        {
                            id: profile.id,
                            name: profile.nome_completo,
                            nickname: profile.apelido ?? undefined,
                            email: profile.email,
                            username: profile.username,
                            cpf: profile.cpf,
                            telefone: profile.telefone,
                            foto_perfil_url: profile.foto_perfil_url,
                            is_superuser: profile.is_superuser,
                            navigation_mode: profile.navigation_mode,
                            tenant_role: tenantAtual.is_owner
                                ? "owner"
                                : ((tenantAtual.perfil?.nome?.toLowerCase() as User["tenant_role"]) ?? "operador"),
                            custom_permissions: tenantAtual.perfil?.permissoes,
                        },
                        grupos,
                        unidadesProdutivas,
                        profile.tenants,
                    );

                    localStorage.setItem("agrosaas-last-activity", String(Date.now()));

                    // Recarrega a página para atualizar o contexto
                    window.location.href = "/dashboard";
                } catch (error) {
                    console.error("Erro ao alternar assinatura:", error);
                    throw error;
                }
            },

            setActiveFazenda: (id, visaoGrupo = false) => set((s) => {
                if (!visaoGrupo) {
                    const grupo = get().grupos.find(g => g.fazendas.some(f => f.id === id));
                    if (!grupo) return;
                    s.activeGrupoId = grupo.id;
                }
                s.activeFazendaId = id;
                s.isVisaoGrupo = visaoGrupo;
            }),

            setCustomPermissions: (permissoes) => set((s) => {
                if (!s.user) return;
                s.user.custom_permissions = permissoes;
            }),

            setActiveGrupo: (grupoId) => set((s) => {
                const grupo = get().grupos.find(g => g.id === grupoId);
                if (!grupo) return;
                s.activeGrupoId = grupoId;
                s.isVisaoGrupo = false;
                // Seleciona a primeira fazenda do grupo
                if (grupo?.fazendas.length) s.activeFazendaId = grupo.fazendas[0].id;
            }),

            activeModules: () => {
                const { grupos, activeGrupoId, isVisaoGrupo } = get();
                if (isVisaoGrupo || !activeGrupoId) {
                    // Union de todos os grupos
                    return [...new Set(grupos.flatMap(g => g.modules))] as ModuleId[];
                }
                return grupos.find(g => g.id === activeGrupoId)?.modules ?? [];
            },

            activePlanTier: () => {
                const { grupos, activeGrupoId } = get();
                return normalizePlanTier(grupos.find(g => g.id === activeGrupoId)?.plan_tier) ?? "BASICO";
            },

            hasModule: (id) => get().activeModules().includes(id),

            setImpersonation: (info) => set((s) => {
                s.impersonation = info;
            }),

            switchImpersonationMode: async (modo, motivo) => {
                const response = await apiFetch<{ access_token: string; modo: "READ_ONLY" | "READ_WRITE" }>("/backoffice/impersonate/mode", {
                    method: "PATCH",
                    body: JSON.stringify({ modo, motivo }),
                });

                set((s) => {
                    s.token = response.access_token;
                    if (s.impersonation) {
                        s.impersonation.mode = response.modo;
                    }
                });

                const { updateImpersonationTokenCookie } = await import("@/app/actions/auth");
                await updateImpersonationTokenCookie(response.access_token);
            },

            stopImpersonation: async () => {
                const currentImpId = get().impersonation?.impersonation_id;
                try {
                    await apiFetch("/backoffice/impersonate/stop", {
                        method: "POST",
                        body: JSON.stringify({ impersonation_id: currentImpId }),
                    });
                } catch (err) {
                    console.warn("Aviso ao encerrar impersonação no backend:", err);
                }

                const { stopImpersonationCookies } = await import("@/app/actions/auth");
                const { returnPath, returnToken } = await stopImpersonationCookies();

                set((s) => {
                    s.impersonation = null;
                    if (returnToken) {
                        s.token = returnToken;
                    }
                });

                return returnPath;
            },

            logout: async () => {
                // Notifica o backend para encerrar a sessão em segundo plano — não bloqueia o redirect,
                // pois o resultado já era ignorado (o estado local sempre é limpo de qualquer forma).
                const token = get().token;
                if (token) {
                    const API_URL = getApiOrigin();
                    fetch(`${API_URL}/api/v1/auth/sessions/logout`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${token}`,
                            "Content-Type": "application/json",
                        },
                    }).catch((error) => {
                        console.warn("Erro ao encerrar sessão no servidor:", error);
                    });
                }
                try {
                    const { clearAuthCookies } = await import("@/app/actions/auth");
                    await clearAuthCookies();
                } catch (e) {
                    console.error("Erro ao limpar cookies:", e);
                }
                set({ ...initialState, _hasHydrated: true });
                if (typeof window !== "undefined") {
                    localStorage.removeItem("agrosaas-last-activity");
                    window.location.href = "/login";
                }
            },
        })),
        {
            name: "agrosaas-auth-storage",
            // Proteção de segurança: Guardamos TOKEN aqui para o apiFetch funcionar sem cookies complexos por enquanto
            // Mas em produção real, preferiríamos cookies HttpOnly
            partialize: (state) => ({
                token: state.token,
                tenant: state.tenant,
                user: state.user,
                impersonation: state.impersonation,
                grupos: state.grupos,
                unidadesProdutivasAutorizadas: state.unidadesProdutivasAutorizadas,
                tenantContexts: state.tenantContexts,
                activeGrupoId: state.activeGrupoId,
                activeFazendaId: state.activeFazendaId,
                isVisaoGrupo: state.isVisaoGrupo,
                availableTenants: state.availableTenants,
                modoEssencial: state.modoEssencial,
            }),
            onRehydrateStorage: () => (state) => {
                state?.setHasHydrated(true);
            },
        }
    )
);
