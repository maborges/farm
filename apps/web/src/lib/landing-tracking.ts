"use client";

// Endpoint público — sem autenticação, sem apiFetch
const ENDPOINT = "/api/v1/growth/events";

export type LandingEventName =
  | "landing_view"
  | "scroll_50"
  | "scroll_90"
  | "cta_click"
  | "cta_test_click"
  | "cta_demo_click"
  | "plan_select";

interface LandingEventPayload {
  sessao_id: string;
  evento: LandingEventName | string;
  utm_source?: string | null;
  utm_campaign?: string | null;
  utm_medium?: string | null;
  headline_variant?: string | null;
  path?: string;
  device?: string;
}

// ---------------------------------------------------------------------------
// Sessão — UUID persistido em localStorage
// ---------------------------------------------------------------------------

const SESSION_KEY = "agro_landing_sid";
const VARIANT_KEY = "agro_landing_variant";

function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function getOrCreateSessaoId(): string {
  if (typeof window === "undefined") return "";
  try {
    const existing = localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const id = generateUUID();
    localStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return generateUUID();
  }
}

// ---------------------------------------------------------------------------
// Headline variant — A/B/C, atribuída aleatoriamente e persistida por sessão
// ---------------------------------------------------------------------------

const VARIANTS = ["A", "B", "C"] as const;

export function getOrCreateVariant(): string {
  if (typeof window === "undefined") return "A";
  try {
    const existing = localStorage.getItem(VARIANT_KEY);
    if (existing && VARIANTS.includes(existing as (typeof VARIANTS)[number])) {
      return existing;
    }
    const variant = VARIANTS[Math.floor(Math.random() * VARIANTS.length)];
    localStorage.setItem(VARIANT_KEY, variant);
    return variant;
  } catch {
    return "A";
  }
}

// ---------------------------------------------------------------------------
// UTM params — lidos da URL uma única vez
// ---------------------------------------------------------------------------

function readUtmParams(): Record<string, string | null> {
  if (typeof window === "undefined") return {};
  try {
    const params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get("utm_source"),
      utm_campaign: params.get("utm_campaign"),
      utm_medium: params.get("utm_medium"),
    };
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// trackLanding — fire-and-forget com keepalive
// ---------------------------------------------------------------------------

export function trackLanding(evento: LandingEventName | string, extra?: Partial<LandingEventPayload>): void {
  if (typeof window === "undefined") return;

  const sessao_id = getOrCreateSessaoId();
  const headline_variant = getOrCreateVariant();
  const utm = readUtmParams();

  const payload: LandingEventPayload = {
    sessao_id,
    evento,
    headline_variant,
    path: window.location.pathname,
    ...utm,
    ...extra,
  };

  try {
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      // falha silenciosa — não bloquear navegação
    });
  } catch {
    // SSR guard
  }
}
