"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { Download, X, Share } from "lucide-react";
import { Button } from "@/components/ui/button";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let isHydrated = false;

function subscribeClient(callback: () => void) {
  isHydrated = true;
  queueMicrotask(() => {
    callback();
  });
  return () => {};
}

function getIsStandalone() {
  if (!isHydrated || typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in window.navigator &&
      Boolean((window.navigator as unknown as { standalone?: boolean }).standalone))
  );
}

function getIsIOS() {
  if (!isHydrated || typeof window === "undefined") return false;
  return /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const isStandalone = useSyncExternalStore(subscribeClient, getIsStandalone, () => false);
  const isIOS = useSyncExternalStore(subscribeClient, getIsIOS, () => false);

  useEffect(() => {
    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    const handleAppInstalled = () => {
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleAppInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setDeferredPrompt(null);
    }
  };

  // Se já está instalado ou foi dispensado, não exibe
  if (isStandalone || dismissed) {
    return null;
  }

  // Banner para Android/Chromium quando evento nativo disparado
  if (deferredPrompt) {
    return (
      <aside
        aria-label="Instalação do aplicativo"
        className="mb-4 p-3 rounded-sm border border-primary/30 bg-primary/5 flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-sm bg-primary/10 text-primary flex-shrink-0">
            <Download className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-foreground truncate">
              Instalar DeepFarms Agro
            </p>
            <p className="text-[11px] text-muted-foreground truncate">
              Acesso rápido e funcionamento offline na lavoura
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <Button
            variant="default"
            size="sm"
            onClick={handleInstallClick}
            className="text-xs"
          >
            Instalar
          </Button>
          <button
            onClick={() => setDismissed(true)}
            aria-label="Fechar aviso de instalação"
            className="p-1 rounded-sm text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </aside>
    );
  }

  // Guia discreto para iOS Safari
  if (isIOS) {
    return (
      <aside
        aria-label="Instalação no iPhone ou iPad"
        className="mb-4 p-3 rounded-sm border border-border bg-card text-xs flex items-center justify-between gap-3"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-sm bg-muted text-foreground flex-shrink-0">
            <Share className="w-4 h-4" />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Para instalar no iPhone/iPad: toque em{" "}
            <span className="font-semibold text-foreground">Compartilhar</span> e depois em{" "}
            <span className="font-semibold text-foreground">Adicionar à Tela de Início</span>.
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          aria-label="Fechar dica"
          className="p-1 rounded-sm text-muted-foreground hover:text-foreground flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </aside>
    );
  }

  return null;
}
