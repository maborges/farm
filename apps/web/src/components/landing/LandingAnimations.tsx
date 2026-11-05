"use client";

import { useEffect } from "react";

/**
 * Observa elementos com data-animate e aplica a classe .is-visible
 * quando entram no viewport, disparando animações CSS de fade-in-up.
 *
 * @returns null — componente invisível montado na landing page.
 */
export function LandingAnimations() {
  useEffect(() => {
    const elements = document.querySelectorAll("[data-animate], [data-animate-stagger]");
    if (elements.length === 0) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion || !("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"));
      document.documentElement.classList.add("landing-animations-ready");
      return () => document.documentElement.classList.remove("landing-animations-ready");
    }

    const initialViewportBottom = window.innerHeight - 40;
    elements.forEach((element) => {
      const rect = element.getBoundingClientRect();
      if (rect.top < initialViewportBottom && rect.bottom > 0) {
        element.classList.add("is-visible");
      }
    });
    document.documentElement.classList.add("landing-animations-ready");

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    elements.forEach((element) => {
      if (!element.classList.contains("is-visible")) observer.observe(element);
    });

    return () => {
      observer.disconnect();
      document.documentElement.classList.remove("landing-animations-ready");
    };
  }, []);

  return null;
}
