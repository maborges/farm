/**
 * Utilitário de tracking comercial.
 * Conectar a PostHog / Mixpanel / GA4 quando disponível.
 * Por ora registra no console em dev e acumula em window.__cta_events para QA.
 */

export type CtaEvent =
    | "monetization_cta_viewed"
    | "monetization_cta_clicked"
    | "upgrade_intention_created";

export type CtaContext =
    | "dashboard_financeiro_insight"
    | "primeiro_custo_lancado"
    | "cenarios_avancados"
    | "dashboard_proximo_passo";

interface TrackPayload {
    event: CtaEvent;
    context: CtaContext;
    meta?: Record<string, unknown>;
}

export function trackCTA({ event, context, meta }: TrackPayload): void {
    if (typeof window === "undefined") return;

    const entry = { event, context, meta, ts: Date.now() };

    // Acumular para QA/testes
    (window as unknown as Record<string, unknown[]>).__cta_events ??= [];
    ((window as unknown as Record<string, unknown[]>).__cta_events).push(entry);

    if (process.env.NODE_ENV !== "production") {
        console.debug("[CTA]", event, context, meta ?? "");
    }

    // TODO: conectar provider
    // posthog?.capture(event, { context, ...meta });
    // analytics.track(event, { context, ...meta });
}
