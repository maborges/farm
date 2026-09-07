import { apiFetch } from "@/lib/api";

export type UXEvento = 
    | "essential_view_loaded"
    | "essential_cta_clicked"
    | "essential_action_executed"
    | "advanced_mode_opened"
    | "nudge_visualized"
    | "friccao_detectada";

export type UXModo = "ESSENCIAL" | "AVANCADO";

export interface TelemetryPayload {
    evento: UXEvento;
    modo: UXModo;
    metadados?: Record<string, any>;
    sessao_id?: string;
}

/**
 * Utilitário para registrar eventos de telemetria de UX da IA.
 */
export const trackIAUXEvento = async (payload: TelemetryPayload) => {
    try {
        await apiFetch("/ia/ux/track", {
            method: "POST",
            body: payload,
            suppressErrorLog: true,
        });
    } catch (error) {
        // Falha silenciosa para não quebrar a UX do usuário
        if (process.env.NODE_ENV !== "production") {
            console.warn("Falha ao registrar telemetria IA UX:", error);
        }
    }
};

/**
 * Hook para gerenciar o tempo de decisão.
 */
export const useIATimer = () => {
    const startTime = performance.now();

    const getElapsedTime = () => {
        return Math.round(performance.now() - startTime);
    };

    return { getElapsedTime };
};
