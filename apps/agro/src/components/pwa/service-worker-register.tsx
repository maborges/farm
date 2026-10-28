"use client";

import { useEffect } from "react";

const SW_CONTROLLED_RELOAD_KEY = "deepfarms_agro_sw_controlled_reload_v1";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    try {
      if (
        navigator.serviceWorker.controller &&
        sessionStorage.getItem(SW_CONTROLLED_RELOAD_KEY) === "pending"
      ) {
        sessionStorage.setItem(SW_CONTROLLED_RELOAD_KEY, "done");
      }
    } catch {
      // Storage bloqueado não impede o registro nem a navegação online.
    }

    const handleControllerChange = () => {
      if (!navigator.serviceWorker.controller) return;

      try {
        if (sessionStorage.getItem(SW_CONTROLLED_RELOAD_KEY) === "pending") return;
        sessionStorage.setItem(SW_CONTROLLED_RELOAD_KEY, "pending");
      } catch {
        // Não recarrega sem um marcador persistente que evite ciclos.
        return;
      }

      // O primeiro documento foi carregado antes de o SW controlar os bundles.
      // Recarrega uma vez para que o cache de /_next/ receba o JavaScript da rota.
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener("controllerchange", handleControllerChange);
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((registration) => {
        void registration.update();
        registration.onupdatefound = () => {
          const installingWorker = registration.installing;
          if (installingWorker) {
            installingWorker.onstatechange = () => {
              if (
                installingWorker.state === "installed" &&
                navigator.serviceWorker.controller
              ) {
                console.log(
                  "[PWA Agro] Nova versão disponível. Atualize para ver novidades."
                );
              }
            };
          }
        };
      })
      .catch((error) => {
        console.warn("[PWA Agro] Falha ao registrar Service Worker:", error);
      });

    return () => {
      navigator.serviceWorker.removeEventListener("controllerchange", handleControllerChange);
    };
  }, []);

  return null;
}
