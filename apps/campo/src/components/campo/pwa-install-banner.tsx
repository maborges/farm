"use client";

import { useEffect, useState } from "react";
import { Download, Share, Smartphone, X } from "lucide-react";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { CampoButton } from "./ui";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_STORAGE_KEY = "campo:pwa-install-dismissed";

/**
 * Banner adaptativo que orienta o operador de campo a instalar o PWA na tela inicial quando executado em navegador mobile/tablet.
 *
 * Args:
 *   Nenhum argumento.
 *
 * Return:
 *   JSX.Element | null: Banner compacto de instalação nativa ou null se já estiver em modo standalone.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
export function CampoPwaInstallBanner() {
  const { layoutProfile, isHydrated } = useDeviceContext();
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState<boolean>(false);

  useEffect(() => {
    try {
      if (sessionStorage.getItem(DISMISS_STORAGE_KEY) === "1") {
        setDismissed(true);
      }
    } catch {
      // Ignora indisponibilidade de sessionStorage
    }

    const handleBeforeInstallPrompt = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
    };
  }, []);

  if (!isHydrated || !layoutProfile.showInstallBanner || dismissed) {
    return null;
  }

  const handleDismiss = () => {
    setDismissed(true);
    try {
      sessionStorage.setItem(DISMISS_STORAGE_KEY, "1");
    } catch {
      // Ignora
    }
  };

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    setDeferredPrompt(null);
    handleDismiss();
  };

  return (
    <div className="rounded-sm border border-primary/25 bg-primary/8 px-3 py-2 text-xs text-foreground shadow-2xs">
      <div className="flex items-center justify-between gap-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-sm bg-primary text-primary-foreground">
            <Smartphone className="size-3.5" />
          </span>
          <div className="min-w-0">
            <p className="truncate font-bold text-foreground">
              Modo App de Campo disponível
            </p>
            <p className="truncate text-[11px] text-muted-foreground">
              {layoutProfile.platformOS === "ios" ? (
                <span className="inline-flex items-center gap-1">
                  Toque em <Share className="inline size-3" /> e &ldquo;Adicionar à Tela de Início&rdquo;
                </span>
              ) : (
                "Instale no dispositivo para tela cheia e melhor operação offline."
              )}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {deferredPrompt && (
            <CampoButton
              type="button"
              variant="primary"
              size="sm"
              onClick={() => void handleInstall()}
              className="min-h-[32px] px-2.5 py-1 text-[11px]"
            >
              <Download className="size-3.5" />
              Instalar
            </CampoButton>
          )}
          <button
            type="button"
            onClick={handleDismiss}
            aria-label="Dispensar aviso de instalação"
            className="inline-flex size-7 items-center justify-center rounded-sm text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="size-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

