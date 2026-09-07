import { ApiError } from "./api-error";
import { cookies } from "next/headers";

// No servidor, usamos BACKEND_URL apontando para a origem do FastAPI.
// O proxy do navegador continua indo por /api/v1, mas o RSC precisa de origem absoluta.
const API_BASE_URL = `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/v1`;

interface FetchOptions extends RequestInit {
    // Parâmetros customizados se quisermos
}

/**
 * apiFetch for Server Components (RSC)
 * Uses cookies instead of localStorage/Zustand
 */
export async function apiFetchServer<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
    const cookieStore = await cookies();
    const token = cookieStore.get("token")?.value;
    const tenantId = cookieStore.get("tenant_id")?.value;
    const fazendaId = cookieStore.get("unidade_produtiva_id")?.value;

    // Headers base
    const headers: Record<string, string> = {
        ...((options.headers as Record<string, string>) || {})
    };

    // Se o corpo não for FormData, definimos como JSON por padrão
    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    // Injetando token e contexto multi-tenant
    if (tenantId) {
        headers["x-tenant-id"] = tenantId;
    }

    if (fazendaId) {
        headers["x-fazenda-id"] = fazendaId;
    }

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const normalizedEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;

    const response = await fetch(`${API_BASE_URL}${normalizedEndpoint}`, {
        ...options,
        headers,
        cache: "no-store", // Sempre buscar dados frescos em RSC
    });

    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch (_) {
            errorData = { message: "Erro desconhecido ao processar requisição." };
        }
        throw new ApiError(
            response.status,
            errorData.detail || errorData.message || `Erro HTTP: ${response.status}`,
            errorData,
            `${API_BASE_URL}${normalizedEndpoint}`,
        );
    }

    // Se a API retornar Empty (204)
    if (response.status === 204) {
        return null as any;
    }

    return response.json();
}
