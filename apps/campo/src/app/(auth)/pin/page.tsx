"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { ThemeToggle } from "@/components/theme-toggle";
import { useCachedCampoImage } from "@/lib/campo-assets";
import {
  Delete,
  Lock,
  LogOut,
  Radio,
  ShieldCheck,
  User,
  Sparkles,
  Loader2,
} from "lucide-react";

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
  const cachedAvatarSrc = useCachedCampoImage(
    "user_avatar",
    session?.user_id,
    session?.user_avatar_url,
  );
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const pinInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    loadSession().then(() => {
      const s = useSessionStore.getState().session;
      if (!s) {
        router.replace("/activate?reason=device_invalid");
        return;
      }
      validateDeviceSession().then((valid) => {
        if (!valid) router.replace("/activate?reason=device_revoked");
      });
    });
  }, []);

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
    <main className="relative flex min-h-dvh w-full items-center justify-center bg-gradient-to-b from-stone-900 via-stone-950 to-black p-0 sm:p-4 md:p-6 overflow-x-hidden selection:bg-emerald-500/30">
      {/* Mobile Frame Container */}
      <div className="relative flex h-dvh w-full flex-col justify-between overflow-y-auto xl:h-[840px] xl:max-h-[94vh] xl:max-w-[420px] xl:rounded-[36px] xl:border xl:border-white/10 xl:shadow-[0_25px_60px_-15px_rgba(0,0,0,0.85)] bg-background">
        {/* Ambient Agtech Background with subtle glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <img
            src="/images/login-bg.png"
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover object-center opacity-30 select-none dark:opacity-20 transition-opacity"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-emerald-950/60 via-background/85 to-background dark:from-emerald-950/80 dark:via-background/90 dark:to-background" />
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-72 w-72 rounded-full bg-emerald-500/15 blur-3xl" />
        </div>

        {/* Hidden input for software keyboards if needed */}
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

        {/* ── Top Mobile Status Bar ── */}
        <header
          className="relative z-10 flex items-center justify-between px-5 pt-4 sm:px-6 sm:pt-5"
          style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}
        >
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-xl bg-card/80 p-1.5 shadow-md border border-border/70 backdrop-blur-md">
              <img
                src="/logos/deepfarms-mark.svg"
                alt="DeepFarms"
                className="size-full object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold tracking-tight text-foreground">DeepFarms</span>
                <span className="rounded-full bg-emerald-600/15 px-1.5 py-0.2 text-[9px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                  Campo
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-600/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 dark:text-emerald-300 backdrop-blur-md">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Conectado</span>
            </div>
            <ThemeToggle />
          </div>
        </header>

        {/* ── Center Content: Avatar & PIN Indicators ── */}
        <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 py-2 md:py-10 max-w-xl mx-auto w-full">
          {/* Operator Avatar */}
          <div className="relative mb-3 flex flex-col items-center">
            <div className="relative flex size-18 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-emerald-800 p-0.5 shadow-xl ring-4 ring-emerald-500/15">
              {cachedAvatarSrc ?? session?.user_avatar_url ? (
                <img
                  src={cachedAvatarSrc ?? session?.user_avatar_url ?? undefined}
                  alt={session?.user_name ?? "Operador"}
                  className="size-full rounded-full object-cover"
                />
              ) : (
                <div className="flex size-full items-center justify-center rounded-full bg-emerald-700 font-bold text-2xl text-white">
                  {userInitial}
                </div>
              )}
              <span className="absolute bottom-0 right-0 flex size-5 items-center justify-center rounded-full border-2 border-background bg-emerald-500 text-white">
                <ShieldCheck className="size-3" />
              </span>
            </div>

            <h1 className="mt-2 text-xl font-bold tracking-tight text-foreground">
              {session?.user_name?.split(" ")[0] ?? "Operador"}
            </h1>
            <p className="text-xs text-muted-foreground">
              Digite seu PIN de 6 dígitos para entrar
            </p>
          </div>

          {/* 6-Dot PIN Indicator */}
          <div
            className="my-3 flex items-center justify-center gap-4 cursor-pointer"
            onClick={() => pinInputRef.current?.focus()}
          >
            {Array.from({ length: PIN_LENGTH }).map((_, i) => {
              const isFilled = i < digits.length;
              return (
                <div
                  key={i}
                  className={`size-3.5 rounded-full transition-all duration-200 ${
                    error
                      ? "border-2 border-rose-500 bg-rose-500/30 scale-110"
                      : isFilled
                        ? "border-2 border-emerald-600 bg-emerald-600 scale-120 shadow-md shadow-emerald-600/40"
                        : "border-2 border-border bg-card/60"
                  }`}
                />
              );
            })}
          </div>

          {/* Error Message */}
          {error ? (
            <p className="mt-1 h-5 text-center text-xs font-semibold text-rose-500 animate-in fade-in slide-in-from-top-1">
              {error}
            </p>
          ) : (
            <div className="mt-1 h-5 flex items-center justify-center gap-1 text-[11px] text-muted-foreground/75">
              {loading ? (
                <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium">
                  <Loader2 className="size-3 animate-spin" /> Verificando PIN...
                </span>
              ) : (
                <span>Acesso seguro ao módulo de campo</span>
              )}
            </div>
          )}

          {/* ── Native-Style Numeric Keypad ── */}
          <div className="mt-4 grid w-full max-w-[320px] grid-cols-3 gap-x-5 gap-y-3 justify-items-center md:gap-y-6 md:gap-x-8 xl:gap-y-3 xl:gap-x-5 xl:max-w-[280px]">
            {KEYPAD_KEYS.map((item, idx) => {
              if (!item) return <div key={idx} className="size-16" />;
              const isDelete = item.digit === "⌫";

              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => (isDelete ? handleDelete() : handleDigit(item.digit))}
                  disabled={loading}
                  className={`
                    relative flex size-16 flex-col items-center justify-center rounded-full transition-all active:scale-90 select-none
                    ${
                      isDelete
                        ? "text-muted-foreground hover:text-foreground active:bg-muted/50"
                        : "border border-border/80 bg-card/85 text-foreground shadow-sm hover:border-emerald-600/40 active:bg-emerald-600/15"
                    }
                    disabled:opacity-40
                  `}
                >
                  {isDelete ? (
                    <Delete className="size-6 text-muted-foreground" strokeWidth={1.5} />
                  ) : (
                    <>
                      <span className="text-2xl font-semibold leading-none">{item.digit}</span>
                      {item.sub && (
                        <span className="mt-0.5 text-[9px] font-bold tracking-widest text-muted-foreground uppercase leading-none">
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

        {/* ── Mobile Footer: Trocar Usuário / Reativar ── */}
        <footer
          className="relative z-10 flex flex-col items-center gap-2 px-5 pb-4 pt-1 sm:px-6"
          style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}
        >
          <button
            type="button"
            onClick={() => router.push("/activate")}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:text-foreground active:scale-95"
          >
            <LogOut className="size-3.5" />
            <span>Trocar operador ou reativar</span>
          </button>
        </footer>
      </div>
    </main>
  );
}
