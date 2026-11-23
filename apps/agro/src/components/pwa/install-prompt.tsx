"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { Download, Share, Smartphone, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform?: string }>;
}

const DISMISSED_KEY = "deepfarms_agro_install_invite_dismissed_v1";
const DISMISSED_EVENT = "deepfarms-agro-install-dismissed";

function subscribeStandalone(callback: () => void) {
  const media = window.matchMedia("(display-mode: standalone)");
  media.addEventListener("change", callback);
  window.addEventListener("appinstalled", callback);
  return () => {
    media.removeEventListener("change", callback);
    window.removeEventListener("appinstalled", callback);
  };
}

function subscribeDismissed(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(DISMISSED_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(DISMISSED_EVENT, callback);
  };
}

function getDismissed(): boolean {
  try {
    return window.localStorage.getItem(DISMISSED_KEY) === "true";
  } catch {
    return false;
  }
}

function isStandalone(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in window.navigator &&
      Boolean((window.navigator as Navigator & { standalone?: boolean }).standalone))
  );
}

function isAppleMobile(): boolean {
  const { userAgent, platform, maxTouchPoints } = window.navigator;
  return /iphone|ipad|ipod/i.test(userAgent) || (platform === "MacIntel" && maxTouchPoints > 1);
}

function isSafari(): boolean {
  const { userAgent } = window.navigator;
  return /safari/i.test(userAgent) && !/crios|fxios|edgios|opios/i.test(userAgent);
}

export function InstallPrompt() {
  const standalone = useSyncExternalStore(subscribeStandalone, isStandalone, () => false);
  const appleMobile = useSyncExternalStore(() => () => {}, isAppleMobile, () => false);
  const safari = useSyncExternalStore(() => () => {}, isSafari, () => false);
  const dismissed = useSyncExternalStore(subscribeDismissed, getDismissed, () => false);
  const [dismissedThisSession, setDismissedThisSession] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const handleBeforeInstall = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
    };
    const handleAppInstalled = () => {
      setInstalled(true);
      setDeferredPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleAppInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleAppInstalled);
    };
  }, []);

  const dismiss = () => {
    setDismissedThisSession(true);
    try {
      window.localStorage.setItem(DISMISSED_KEY, "true");
    } catch {
      // A dispensa vale para a sessão atual mesmo sem acesso ao armazenamento local.
    }
    window.dispatchEvent(new Event(DISMISSED_EVENT));
  };

  const install = async () => {
    if (!deferredPrompt) return;
    const prompt = deferredPrompt;
    setDeferredPrompt(null);
    try {
      await prompt.prompt();
      await prompt.userChoice;
    } catch {
      setShowInstructions(true);
    }
  };

  if (standalone || installed || dismissed || dismissedThisSession) return null;

  return (
    <Card
      size="sm"
      aria-label="Instale o DeepFarms Agro"
      className="relative border-primary/30 bg-gradient-to-r from-primary/10 via-primary/5 to-card"
      data-testid="install-invite"
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        onClick={dismiss}
        aria-label="Dispensar convite de instalação"
        className="absolute right-2 top-2"
      >
        <X className="size-4" aria-hidden="true" />
      </Button>

      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-col gap-3 pr-9 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span
              className="mt-0.5 rounded-xl md:rounded-sm bg-primary text-primary-foreground p-2.5 shadow-sm shrink-0"
              aria-hidden="true"
            >
              {appleMobile ? (
                <Share className="size-4 sm:size-5" />
              ) : (
                <Smartphone className="size-4 sm:size-5" />
              )}
            </span>
            <div className="flex flex-col gap-0.5 min-w-0">
              <h2 className="text-xs sm:text-sm font-bold text-foreground">
                Leve o DeepFarms Agro para o campo!
              </h2>
              <p className="text-xs leading-relaxed text-muted-foreground">
                Tenha previsão do tempo, indicadores do mercado e calculadoras agrícolas sempre à mão.
              </p>
              <p className="text-xs font-semibold text-primary">
                Gratuito. Sem cadastro. Direto no seu celular.
              </p>
              <p className="text-[10px] text-muted-foreground hidden sm:block">
                Instalação rápida, sem precisar procurar na loja de aplicativos.
              </p>
            </div>
          </div>

          <div className="flex shrink-0 flex-row sm:flex-col items-center sm:items-end gap-2">
            {deferredPrompt ? (
              <Button
                type="button"
                variant="default"
                onClick={install}
                size="sm"
                className="w-full sm:w-auto font-semibold"
              >
                <Download className="size-3.5" aria-hidden="true" />
                <span>Instalar aplicativo</span>
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setShowInstructions((current) => !current)}
                aria-expanded={showInstructions}
                aria-controls="install-instructions"
                className="w-full sm:w-auto"
              >
                Como instalar
              </Button>
            )}
          </div>
        </div>

        {showInstructions && (
          <div
            id="install-instructions"
            className="border-t border-border/70 pt-2.5 text-xs leading-relaxed text-muted-foreground"
            data-testid="install-instructions"
          >
            {appleMobile ? (
              <p>
                {safari ? (
                  <>
                    No Safari, toque em <strong className="text-foreground">Compartilhar</strong> e escolha{" "}
                    <strong className="text-foreground">Adicionar à Tela de Início</strong>.
                  </>
                ) : (
                  <>
                    No iPhone ou iPad, abra esta página no Safari, toque em{" "}
                    <strong className="text-foreground">Compartilhar</strong> e escolha{" "}
                    <strong className="text-foreground">Adicionar à Tela de Início</strong>.
                  </>
                )}
              </p>
            ) : (
              <p>
                No menu do navegador, procure <strong className="text-foreground">Instalar aplicativo</strong> ou{" "}
                <strong className="text-foreground">Adicionar à tela inicial</strong>. A opção pode variar conforme o navegador.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
