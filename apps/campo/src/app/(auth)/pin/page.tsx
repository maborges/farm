"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Delete, Loader2, LogOut, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useCachedCampoImage } from "@/lib/campo-assets";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useSessionStore } from "@/lib/stores/session-store";

const PIN_LENGTH = 6;

interface KeypadConfig {
  digit: string;
  sub?: string;
}

const KEYPAD_KEYS: Array<KeypadConfig | null> = [
  { digit: "1" },
  { digit: "2", sub: "ABC" },
  { digit: "3", sub: "DEF" },
  { digit: "4", sub: "GHI" },
  { digit: "5", sub: "JKL" },
  { digit: "6", sub: "MNO" },
  { digit: "7", sub: "PQRS" },
  { digit: "8", sub: "TUV" },
  { digit: "9", sub: "WXYZ" },
  null,
  { digit: "0" },
  { digit: "⌫" },
];

export default function PinPage() {
  const router = useRouter();
  const { loginWithPIN, session, loadSession, validateDeviceSession } = useSessionStore();
  const { layoutProfile } = useDeviceContext();
  const cachedAvatarSrc = useCachedCampoImage(
    "user_avatar",
    session?.user_id,
    session?.user_avatar_url
  );
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const pinInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    void loadSession().then(() => {
      const s = useSessionStore.getState().session;
      if (!s) {
        router.replace("/activate?reason=device_invalid");
        return;
      }
      void validateDeviceSession().then((valid) => {
        if (!valid) router.replace("/activate?reason=device_revoked");
      });
    });
  }, [loadSession, router, validateDeviceSession]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      pinInputRef.current?.focus();
    });

    return () => cancelAnimationFrame(frame);
  }, []);

  const submitPin = async (pin: string) => {
    setLoading(true);
    const ok = await loginWithPIN(pin);
    if (ok) {
      router.replace("/home");
    } else {
      const current = useSessionStore.getState().session;
      if (!current) {
        setError("Dispositivo revogado ou expirado. Gere uma nova ativação.");
        setTimeout(() => router.replace("/activate?reason=device_revoked"), 1200);
      } else {
        setError("PIN incorreto. Tente novamente.");
      }
      setDigits([]);
    }
    setLoading(false);
  };

  const handleDigit = async (d: string) => {
    if (loading) return;
    if (digits.length >= PIN_LENGTH) return;
    setError(null);
    const next = [...digits, d];
    setDigits(next);
    if (next.length === PIN_LENGTH) {
      await submitPin(next.join(""));
    }
  };

  const handleDelete = () => {
    setDigits((d) => d.slice(0, -1));
    setError(null);
  };

  const handlePinInputChange = async (rawValue: string) => {
    if (loading) return;

    const normalized = rawValue.replace(/\D/g, "").slice(0, PIN_LENGTH);
    setError(null);
    setDigits(normalized.split(""));

    if (normalized.length === PIN_LENGTH) {
      await submitPin(normalized);
    }
  };

  const userInitial = (session?.user_name ?? "O").trim().charAt(0).toUpperCase();

  return (
    <div
      data-device-category={layoutProfile.deviceCategory}
      data-execution-mode={layoutProfile.executionMode}
      className="min-h-dvh flex flex-col bg-background text-foreground safe-area-px"
    >
      <input
        ref={pinInputRef}
        type="password"
        inputMode="numeric"
        pattern="[0-9]*"
        autoComplete="current-password"
        enterKeyHint="done"
        value={digits.join("")}
        onChange={(e) => void handlePinInputChange(e.target.value)}
        className="pointer-events-none absolute left-0 top-0 h-px w-px opacity-0"
        aria-label="PIN do dispositivo"
      />

      {/* Top App Bar Unificado (mesmo padrão visual do Agro) */}
      <header className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/85 safe-area-pt select-none">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 h-14 flex items-center justify-between gap-2 sm:gap-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="relative w-7 h-7 shrink-0 rounded-sm bg-primary/10 p-0.5">
              <Image
                src="/logos/deepfarms-mark.svg"
                alt="DeepFarms Campo"
                width={28}
                height={28}
                priority
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="font-bold tracking-tight text-foreground text-sm truncate">
                  DeepFarms
                </span>
                <span className="text-primary font-bold text-xs px-1.5 py-0.5 rounded-sm bg-primary/10">
                  Campo
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground hidden sm:inline truncate">
                Desbloqueio por PIN Operacional
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Conectado</span>
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Conteúdo Central */}
      <main className="flex-1 flex flex-col items-center justify-center w-full max-w-md mx-auto px-4 py-6">
        <div className="w-full rounded-sm border border-border bg-card p-5 shadow-2xs flex flex-col items-center">
          {/* Avatar do Operador */}
          <div className="relative mb-2 flex flex-col items-center">
            <div className="relative flex size-16 items-center justify-center rounded-sm bg-primary/10 text-primary p-0.5 border border-primary/20">
              {cachedAvatarSrc ?? session?.user_avatar_url ? (
                <img
                  src={cachedAvatarSrc ?? session?.user_avatar_url ?? undefined}
                  alt={session?.user_name ?? "Operador"}
                  className="size-full rounded-sm object-cover"
                />
              ) : (
                <div className="flex size-full items-center justify-center rounded-sm bg-primary font-bold text-xl text-primary-foreground">
                  {userInitial}
                </div>
              )}
              <span className="absolute -bottom-1 -right-1 flex size-5 items-center justify-center rounded-sm border border-background bg-primary text-primary-foreground">
                <ShieldCheck className="size-3" />
              </span>
            </div>

            <h1 className="mt-2.5 text-base sm:text-lg font-bold tracking-tight text-foreground">
              {session?.user_name?.split(" ")[0] ?? "Operador"}
            </h1>
            <p className="text-xs text-muted-foreground">
              Digite seu PIN de 6 dígitos para entrar
            </p>
          </div>

          {/* Indicador de 6 dígitos */}
          <div
            className="my-3 flex items-center justify-center gap-3.5 cursor-pointer"
            onClick={() => pinInputRef.current?.focus()}
          >
            {Array.from({ length: PIN_LENGTH }).map((_, i) => {
              const isFilled = i < digits.length;
              return (
                <div
                  key={i}
                  className={`size-3 rounded-full transition-all duration-200 ${
                    error
                      ? "border-2 border-destructive bg-destructive/30 scale-110"
                      : isFilled
                        ? "border-2 border-primary bg-primary scale-110"
                        : "border-2 border-border bg-muted"
                  }`}
                />
              );
            })}
          </div>

          {error ? (
            <p className="h-5 text-center text-xs font-semibold text-destructive">
              {error}
            </p>
          ) : (
            <div className="h-5 flex items-center justify-center gap-1 text-[11px] text-muted-foreground">
              {loading ? (
                <span className="flex items-center gap-1.5 text-primary font-medium">
                  <Loader2 className="size-3 animate-spin" /> Verificando PIN...
                </span>
              ) : (
                <span>Acesso seguro ao módulo de campo</span>
              )}
            </div>
          )}

          {/* Teclado Numérico no padrão rounded-sm do Agro */}
          <div className="mt-4 grid w-full max-w-[280px] grid-cols-3 gap-2.5 justify-items-center">
            {KEYPAD_KEYS.map((item, idx) => {
              if (!item) return <div key={idx} className="h-13 w-full" />;
              const isDelete = item.digit === "⌫";

              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => (isDelete ? handleDelete() : void handleDigit(item.digit))}
                  disabled={loading}
                  className={`flex h-13 w-full flex-col items-center justify-center rounded-sm border transition-all active:scale-95 select-none disabled:opacity-40 ${
                    isDelete
                      ? "border-transparent bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
                      : "border-border bg-background text-foreground shadow-2xs hover:border-primary/50 hover:bg-accent"
                  }`}
                >
                  {isDelete ? (
                    <Delete className="size-5 text-muted-foreground" strokeWidth={1.75} />
                  ) : (
                    <>
                      <span className="text-lg font-bold leading-none">{item.digit}</span>
                      {item.sub && (
                        <span className="mt-0.5 text-[8px] font-semibold tracking-widest text-muted-foreground uppercase leading-none">
                          {item.sub}
                        </span>
                      )}
                    </>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </main>

      <footer className="border-t border-border/60 bg-muted/20 py-3 px-4 flex justify-center safe-area-pb">
        <button
          type="button"
          onClick={() => router.push("/activate")}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground active:scale-95"
        >
          <LogOut className="size-3.5 text-primary" />
          <span>Trocar operador ou reativar dispositivo</span>
        </button>
      </footer>
    </div>
  );
}
