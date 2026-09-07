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

    elements.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  return null;
}
