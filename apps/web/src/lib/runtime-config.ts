const DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8000";
const DEFAULT_BACKEND_WS_ORIGIN = "ws://127.0.0.1:8000";
const DEFAULT_API_PATH = "/api/v1";

function trimTrailingSlash(value: string) {
    return value.replace(/\/$/, "");
}

function normalizeApiBase(value: string) {
    const trimmed = trimTrailingSlash(value);

    if (trimmed.endsWith(DEFAULT_API_PATH)) {
        return trimmed;
    }

    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        return `${trimmed}${DEFAULT_API_PATH}`;
    }

    if (trimmed === DEFAULT_API_PATH) {
        return trimmed;
    }

    return `${trimmed}${DEFAULT_API_PATH}`;
}

function normalizeWsOrigin(value: string) {
    const trimmed = trimTrailingSlash(value);
    const origin = trimmed.endsWith(DEFAULT_API_PATH)
        ? trimmed.slice(0, -DEFAULT_API_PATH.length)
        : trimmed;

    return origin.replace(/^http/, "ws");
}

function getServerBackendOrigin() {
    return trimTrailingSlash(
        process.env.BACKEND_URL || DEFAULT_BACKEND_ORIGIN,
    );
}

export function getApiBaseUrl() {
    /*
     * Browser:
     * mantém as chamadas same-origin através do proxy do Next.js.
     *
     * Server Components:
     * acessam diretamente o FastAPI pela rede interna usando BACKEND_URL.
     */
    if (typeof window !== "undefined") {
        const raw = process.env.NEXT_PUBLIC_API_URL?.trim();

        if (!raw) {
            return DEFAULT_API_PATH;
        }

        return normalizeApiBase(raw);
    }

    return `${getServerBackendOrigin()}${DEFAULT_API_PATH}`;
}

export function getApiOrigin() {
    if (typeof window !== "undefined") {
        const apiBase = getApiBaseUrl();

        if (apiBase.startsWith("http://") || apiBase.startsWith("https://")) {
            return new URL(apiBase).origin;
        }

        return window.location.origin;
    }

    return getServerBackendOrigin();
}

export function getWsBaseUrl() {
    const configured = process.env.NEXT_PUBLIC_WS_URL?.trim();
    if (configured) {
        return `${normalizeWsOrigin(configured)}${DEFAULT_API_PATH}`;
    }

    const publicApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
    if (publicApiUrl?.startsWith("http://") || publicApiUrl?.startsWith("https://")) {
        return `${normalizeWsOrigin(publicApiUrl)}${DEFAULT_API_PATH}`;
    }

    return `${DEFAULT_BACKEND_WS_ORIGIN}${DEFAULT_API_PATH}`;
}

export function getWhatsappComercialUrl(mensagem: string) {
    const numero = process.env.NEXT_PUBLIC_WHATSAPP_COMERCIAL?.trim();

    if (!numero) {
        return null;
    }

    return `https://wa.me/${numero}?text=${encodeURIComponent(mensagem)}`;
}

export function resolveAssetUrl(url?: string | null) {
    if (!url) {
        return undefined;
    }

    if (url.startsWith("http://") || url.startsWith("https://")) {
        return url;
    }

    const path = url.startsWith("/") ? url : `/${url}`;

    if (path.startsWith("/static/")) {
        return path;
    }

    return `${getApiOrigin()}${path}`;
}
