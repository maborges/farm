import { ApiError } from "./api-error";

// Removido import estático para evitar dependência circular com app-store.ts
// import { useAppStore } from "./stores/app-store";

const configuredUrl =
    typeof window !== "undefined"
        ? "/api/v1"
        : `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/v1`;

// Normalizar base URL: garantir que não tenha barra no final
const BASE_URL = configuredUrl.replace(/\/$/, "");

interface FetchOptions extends Omit<RequestInit, "body"> {
    // Suprimir log de erro no console (útil para erros esperados)
    suppressErrorLog?: boolean;
    // Parâmetros de consulta (query string)
    params?: Record<string, string | number | boolean | undefined | null>;
    // Permitir passar objeto que será convertido em JSON automaticamente
    body?: BodyInit | Record<string, any> | any[] | null;
    // Tipo de resposta esperada
    responseType?: 'json' | 'blob' | 'text';
}

export async function apiFetch<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    // Importação dinâmica para quebrar dependência circular
    const { useAppStore } = await import("./stores/app-store");
    const state = useAppStore.getState();
    let { token, tenant, activeGrupoId, activeFazendaId, isVisaoGrupo, _hasHydrated } = state;
    const usesNextProxy = !BASE_URL.startsWith("http");

    // Fallback: se o Zustand não hidratou, ler token diretamente do localStorage
    // apenas quando precisamos chamar a API diretamente por URL absoluta.
    if (!usesNextProxy && !token && typeof window !== "undefined") {
        try {
            const raw = localStorage.getItem("agrosaas-auth-storage");
            if (raw) {
                const parsed = JSON.parse(raw);
                token = parsed.state?.token || null;
                // Extrair tenant e contexto do localStorage também
                if (!tenant) tenant = parsed.state?.tenant || null;
                if (!activeGrupoId) activeGrupoId = parsed.state?.activeGrupoId || null;
                if (!activeFazendaId) activeFazendaId = parsed.state?.activeFazendaId || null;
                if (isVisaoGrupo === undefined || isVisaoGrupo === null) {
                    isVisaoGrupo = parsed.state?.isVisaoGrupo || false;
                }
            }
        } catch {
            // Ignora erros de parsing
        }
    }

    // Normalizar endpoint: garantir que comece com / e não tenha duplicação de path /api/v1
    let normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
    if (normalizedEndpoint.startsWith("/api/v1/")) {
        normalizedEndpoint = normalizedEndpoint.replace(/^\/api\/v1/, "");
    }

    // Rotas públicas que não exigem autenticação
    const publicRoutes = [
        "/onboarding/verificar-documento",
        "/onboarding/assinante",
        "/onboarding/ativar",
        "/onboarding/confirmar-cadastro",
        "/onboarding/ativacao/reenviar",
        "/billing/plans",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/verify-reset-token",
        "/auth/reset-password",
    ];

    const isPublicRoute = publicRoutes.some(route => normalizedEndpoint.startsWith(route));

    // Debug: verificar se o store foi hidratado
    if (!token && !isPublicRoute) {
        console.warn(`⚠️ [apiFetch] Token ausente para ${endpoint}. Hydrated: ${_hasHydrated}`);
    }

    // Headers base
    const headers: Record<string, string> = {
        ...((options.headers as Record<string, string>) || {})
    };

    // Se o corpo não for FormData, definimos como JSON por padrão
    let body = options.body;
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
        // Converter body para JSON string
        if (body && typeof body === 'object') {
            body = JSON.stringify(body);
        }
    }

    // Injetando Proteção e Contexto Multi-Tenant via interceptor nativo
    // Não sobrescrever x-tenant-id se já foi passado explicitamente (ex: switch-tenant)
    const hasCustomTenantId = "x-tenant-id" in headers || "X-Tenant-Id" in headers;
    const tenantId = tenant?.id ?? activeGrupoId;
    if (tenantId && !hasCustomTenantId) {
        headers["x-tenant-id"] = tenantId;
    }

    const hasCustomFazendaId = "x-fazenda-id" in headers || "X-Fazenda-Id" in headers;
    if (activeFazendaId && !isVisaoGrupo && !hasCustomFazendaId) {
        headers["x-fazenda-id"] = activeFazendaId;
    } else if (isVisaoGrupo) {
        headers["x-context-scope"] = "grupo";
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
        headers["x-access-token"] = token;
        if (typeof window !== "undefined") {
            const lastActivity = Number(localStorage.getItem("agrosaas-last-activity") || 0);
            if (lastActivity && Date.now() - lastActivity < 60_000) {
                headers["x-user-activity"] = "true";
            }
        }
    } else if (!isPublicRoute) {
        // Sem token em rota protegida = não autenticado
        console.error(`❌ [apiFetch] Requisição sem token para: ${endpoint}`);
    }
    
    // Construir URL final
    let url = `${BASE_URL}${normalizedEndpoint}`;

    // Adicionar params se existirem
    if (options.params) {
        const searchParams = new URLSearchParams();
        Object.entries(options.params).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                searchParams.append(key, String(value));
            }
        });
        const queryString = searchParams.toString();
        if (queryString) {
            url += (url.includes("?") ? "&" : "?") + queryString;
        }
    }

    console.log(`📡 API Request: ${options.method || 'GET'} ${url}`, {
        hasAuthorization: Boolean(headers["Authorization"] || headers["authorization"]),
        tenantId: headers["x-tenant-id"] || headers["X-Tenant-Id"] || null,
        unidadeProdutivaId: headers["x-fazenda-id"] || headers["X-Fazenda-Id"] || null,
        isVisaoGrupo: Boolean(isVisaoGrupo),
    });

    try {
        const response = await fetch(url, {
            ...options,
            body: body as any,
            headers,
            credentials: usesNextProxy ? "same-origin" : "include",
        });

        if (!response.ok) {
            const rawBody = await response.text();
            let errorData: any = {};

            try {
                errorData = JSON.parse(rawBody);
            } catch (_) {
                // Se falhar ao parsear JSON, usa o texto puro no erro
                errorData = { message: rawBody || "Erro desconhecido ao processar requisição." };
            }

            // Log detalhado para debugging (pode ser suprimido)
            if (!options.suppressErrorLog) {
                console.error(`❌ API Error [${response.status}] ${options.method || 'GET'} ${normalizedEndpoint}:`, JSON.stringify(errorData));
                console.error(`   → Status: ${response.status}, Raw body:`, rawBody ? rawBody : '(empty)');
            }

            // Notificação global para o usuário em caso de indisponibilidade (500, 502, 503, 504)
            if (!options.suppressErrorLog && (response.status === 500 || response.status === 502 || response.status === 503 || response.status === 504)) {
                if (typeof window !== "undefined") {
                    import("sonner").then(({ toast }) => {
                        toast.error(response.status === 500 ? "Erro Interno no Servidor" : "Servidor temporariamente indisponível", {
                            description: response.status === 500 
                                ? "Ocorreu um problema no servidor ao processar sua requisição. Tente novamente em instantes."
                                : (errorData.detail || errorData.message || "O sistema está com alta carga ou em manutenção. Tente novamente em instantes."),
                            duration: 10000,
                        });
                    });
                }
            }

            // Trata erro de conta bloqueada (423) explicitamente
            if (response.status === 423) {
                throw new ApiError(
                    response.status,
                    errorData.detail || errorData.message || "Conta bloqueada por segurança.",
                    errorData,
                    url,
                );
            }

            // Um 401 da integração TARA representa falha da credencial técnica
            // do sistema cliente, não expiração da sessão humana do DeepFarms.
            // Não deslogar o operador nesse caso: a tela de integração deve
            // apresentar a mensagem de acesso negado e permitir a correção da
            // configuração.
            const isTaraIntegrationRoute = normalizedEndpoint.startsWith("/integracoes/tara");
            if (response.status === 401 && token && !isPublicRoute && !isTaraIntegrationRoute && typeof window !== "undefined") {
                const { useAppStore } = await import("./stores/app-store");
                void useAppStore.getState().logout();
            }

            // Trata erro de pagamento requerido (402)
            if (response.status === 402) {
                throw new ApiError(
                    response.status,
                    errorData.detail || errorData.message || "Pagamento requerido. Verifique sua assinatura.",
                    errorData,
                    url,
                );
            }

            // Construir mensagem de erro mais informativa quando o corpo está vazio
            const errorMessage = errorData.detail || errorData.message;
            if (!errorMessage || errorMessage.trim() === "") {
                throw new ApiError(
                    response.status,
                    `Erro ${response.status} em ${options.method || "GET"} ${normalizedEndpoint}`,
                    errorData,
                    url,
                );
            }

            throw new ApiError(response.status, errorMessage, errorData, url);
        }

        // Se a API retornar Empty (204)
        if (response.status === 204) {
            return null as any;
        }

        if (options.responseType === 'blob') {
            return response.blob() as any;
        }
        
        if (options.responseType === 'text') {
            return response.text() as any;
        }

        return response.json();
    } catch (error: any) {
        if (error?.name === "AbortError" || `${error?.message ?? ""}`.toLowerCase().includes("aborted")) {
            throw error;
        }
        // Erro de rede (Failed to fetch)
        if (error.message === "Failed to fetch" || error.name === "TypeError") {
            console.error("❌ Erro de conexão com a API. URL:", url);
            throw new Error(
                "Não foi possível conectar ao servidor. Verifique se:\n" +
                "1. O backend está rodando\n" +
                "2. A URL da API está correta no arquivo .env.local\n" +
                "3. Não há bloqueio de CORS"
            );
        }
        throw error;
    }
}
