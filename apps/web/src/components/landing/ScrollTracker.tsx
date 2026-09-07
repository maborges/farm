"use client";

import { useEffect, useRef } from "react";
import { trackLanding, getOrCreateSessaoId, getOrCreateVariant } from "@/lib/landing-tracking";

/**
 * Componente invisível inserido na landing page.
 * Responsável por:
 * - Disparar landing_view uma única vez ao montar
 * - Disparar scroll_50 e scroll_90 na primeira vez que o threshold é atingido
 * - Delegar cliques em elementos com data-track-event
 */
export function LandingTracker() {
  const firedView = useRef(false);
  const fired50 = useRef(false);
  const fired90 = useRef(false);

  // landing_view — dispara uma vez por sessão de página
  useEffect(() => {
    if (firedView.current) return;
    firedView.current = true;

    // Inicializa sessão e variante antes de qualquer evento
    getOrCreateSessaoId();
    getOrCreateVariant();

    trackLanding("landing_view");
  }, []);

  // scroll_50 e scroll_90
  useEffect(() => {
    const handleScroll = () => {
      if (fired50.current && fired90.current) return;

      const scrolled = window.scrollY + window.innerHeight;
      const total = document.documentElement.scrollHeight;
      if (total === 0) return;

      const pct = (scrolled / total) * 100;

      if (!fired50.current && pct >= 50) {
        fired50.current = true;
        trackLanding("scroll_50");
      }
      if (!fired90.current && pct >= 90) {
        fired90.current = true;
        trackLanding("scroll_90");
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Delegação de cliques via data-track-event
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest("[data-track-event]");
      if (!target) return;

      const evento = target.getAttribute("data-track-event");
      const plan = target.getAttribute("data-track-plan");

      if (evento) {
        trackLanding(evento, plan ? { path: `/?plan=${plan}` } : undefined);
      }
    };

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  return null;
}
