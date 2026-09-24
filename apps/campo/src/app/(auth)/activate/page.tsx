"use client";

import { Suspense, useEffect, useId, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import type { FieldError, FieldErrors, Resolver } from "react-hook-form";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import bcrypt from "bcryptjs";
import {
  KeyRound,
  Lock,
  ShieldCheck,
  Eye,
  EyeOff,
  Smartphone,
  CheckCircle2,
  AlertCircle,
  Radio,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Loader2,
} from "lucide-react";

import { consumeSessionClearNotice, useSessionStore, type SessionClearNotice } from "@/lib/stores/session-store";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
import { ThemeToggle } from "@/components/theme-toggle";

const API_BASE = "/api/v1";

const schema = z.object({
  activation_code: z
    .string()
    .min(6, "Código de ativação deve ter ao menos 6 caracteres")
    .max(8, "Código de ativação deve ter no máximo 8 caracteres")
    .toUpperCase(),
  pin: z.string().length(6, "PIN deve ter exatamente 6 dígitos").regex(/^\d+$/, "PIN deve conter apenas números"),
  pin_confirm: z.string(),
});

type FormData = z.infer<typeof schema>;

const resolver: Resolver<FormData> = async (values) => {
  const parsed = schema.safeParse(values);
  if (!parsed.success) {
    const errors = parsed.error.issues.reduce<FieldErrors<FormData>>((acc, issue) => {
      const fieldName = issue.path[0];
      if (typeof fieldName !== "string") return acc;
      acc[fieldName as keyof FormData] = {
        type: issue.code,
        message: issue.message,
      } as FieldError;
      return acc;
    }, {});

    return {
      values: {},
      errors,
    };
  }

  if (parsed.data.pin !== parsed.data.pin_confirm) {
    return {
      values: {},
      errors: {
        pin_confirm: {
          type: "validate",
          message: "Os dois PINs informados não são idênticos",
        },
      },
    };
  }

  return {
    values: parsed.data,
    errors: {},
  };
};

function ActivateForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPin, setShowPin] = useState(false);
  const [showPinConfirm, setShowPinConfirm] = useState(false);
  const { saveSession } = useSessionStore();
  const reason = searchParams.get("reason");
  const activationCodeRef = useRef<HTMLInputElement | null>(null);

  const reasonMessage =
    reason === "device_revoked"
      ? "Este aparelho foi desvinculado no sistema gestor. Insira um novo código de ativação."
      : reason === "device_expired"
        ? "A ativação anterior deste aparelho expirou. Solicite um novo código."
        : reason === "device_invalid"
          ? "Sessão inválida ou não encontrada. Faça uma nova ativação."
          : null;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver,
    defaultValues: {
      activation_code: "",
      pin: "",
      pin_confirm: "",
    },
  });

  const watchPin = watch("pin") || "";
  const watchPinConfirm = watch("pin_confirm") || "";
  const watchActivationCode = watch("activation_code") || "";

  const activationCodeField = register("activation_code");
  const pinField = register("pin");
  const pinConfirmField = register("pin_confirm");
  const [clearNotice, setClearNotice] = useState<SessionClearNotice | null>(null);

  useEffect(() => {
    setClearNotice(consumeSessionClearNotice());
  }, []);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      activationCodeRef.current?.focus();
    });

    return () => cancelAnimationFrame(frame);
  }, []);

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    setError(null);
    try {
      const pin_hash = await bcrypt.hash(data.pin, 10);
      const device_fingerprint = await getDeviceFingerprint();

      const res = await fetch(`${API_BASE}/campo/devices/activate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          activation_code: data.activation_code.trim().toUpperCase(),
          pin_hash,
          device_fingerprint,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Erro ao ativar dispositivo");
      }

      const payload = await res.json();

      await saveSession({
        id: 1,
        user_id: payload.user_id,
        tenant_id: payload.tenant_id,
        device_id: payload.device_id,
        device_token: payload.device_token,
        pin_hash,
        user_name: payload.user_name,
        user_avatar_url: payload.user_avatar_url ?? undefined,
        last_sync_at: null,
        modules: payload.modulos,
        fazenda_ids: payload.fazenda_ids,
        active_fazenda_id: payload.fazenda_ids?.[0],
      });

      router.replace("/home");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro desconhecido ao ativar");
    } finally {
      setLoading(false);
    }
  };

  const isPinComplete = watchPin.length === 6;
  const isPinConfirmComplete = watchPinConfirm.length === 6;
  const pinsMatch = isPinComplete && isPinConfirmComplete && watchPin === watchPinConfirm;
  const pinsMismatch = isPinConfirmComplete && watchPin !== watchPinConfirm;

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
          {/* Rich gradients to ensure perfect text contrast */}
          <div className="absolute inset-0 bg-gradient-to-b from-emerald-950/60 via-background/85 to-background dark:from-emerald-950/80 dark:via-background/90 dark:to-background" />
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 h-72 w-72 rounded-full bg-emerald-500/15 blur-3xl" />
        </div>

        {/* ── Top Mobile Status Bar ── */}
        <header className="relative z-10 flex items-center justify-between px-5 pt-4 sm:px-6 sm:pt-5" style={{ paddingTop: "max(1rem, env(safe-area-inset-top))" }}>
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
              <span>Offline-ready</span>
            </div>
            <ThemeToggle />
          </div>
        </header>

        {/* ── Main Mobile Content ── */}
        <div className="relative z-10 flex flex-1 flex-col justify-center px-5 py-4 md:px-20 xl:px-6 w-full max-w-xl mx-auto">
          {/* Hero Welcome Badge */}
          <div className="mb-4 text-center">
            <div className="relative mx-auto mb-3 flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-800 text-white shadow-lg shadow-emerald-900/30 ring-4 ring-emerald-500/10">
              <Smartphone className="size-7" strokeWidth={1.8} />
              <Sparkles className="absolute -top-1 -right-1 size-4 text-emerald-300 animate-pulse" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Ativar Dispositivo
            </h1>
            <p className="mx-auto mt-1 max-w-[300px] text-xs text-muted-foreground leading-relaxed">
              Vincule este smartphone à sua fazenda para sincronizar tarefas e apontamentos no campo.
            </p>
          </div>

          {/* Reason Notification Alert */}
          {reasonMessage && (
            <div className="mb-3.5 flex items-start gap-2.5 rounded-2xl border border-amber-300/80 bg-amber-500/10 p-3 text-xs font-medium text-amber-900 dark:border-amber-700/60 dark:text-amber-200 backdrop-blur-md animate-in fade-in slide-in-from-top-2 duration-300">
              <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <span>{reasonMessage}</span>
            </div>
          )}

          {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}

          {/* Mobile Card Form */}
          <div className="rounded-3xl border border-border/80 bg-card/90 p-4.5 shadow-xl backdrop-blur-xl dark:bg-card/85 sm:p-5">
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-3.5">
              {/* Código de Ativação */}
              <div className="space-y-1">
                <div className="flex items-center justify-between px-1">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <KeyRound className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    Código de Ativação
                  </label>
                  <span className="text-[10px] text-muted-foreground">Fornecido pelo gestor</span>
                </div>
                <div className="relative flex items-center">
                  <input
                    {...activationCodeField}
                    ref={(element) => {
                      activationCodeField.ref(element);
                      activationCodeRef.current = element;
                    }}
                    type="text"
                    inputMode="text"
                    placeholder="EX: ABCD1234"
                    maxLength={8}
                    className="h-12 w-full rounded-xl border border-border bg-background/80 px-3.5 text-center font-mono text-base font-bold tracking-[0.25em] text-foreground uppercase outline-none placeholder:text-muted-foreground/40 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal placeholder:text-sm focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-all shadow-xs"
                    autoComplete="off"
                    autoCapitalize="characters"
                    autoCorrect="off"
                    spellCheck={false}
                    enterKeyHint="next"
                    onChange={(e) => {
                      const upper = e.target.value.toUpperCase();
                      setValue("activation_code", upper);
                    }}
                  />
                  {watchActivationCode.length >= 6 && (
                    <span className="absolute right-3 text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="size-4" />
                    </span>
                  )}
                </div>
                {errors.activation_code && (
                  <p className="px-1 text-[11px] font-medium text-rose-500">
                    {errors.activation_code.message}
                  </p>
                )}
              </div>

              {/* Criar PIN */}
              <div className="space-y-1">
                <div className="flex items-center justify-between px-1">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Lock className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    Criar PIN de Acesso
                  </label>
                  {/* Visual 6-dot indicator */}
                  <div className="flex items-center gap-1">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <span
                        key={i}
                        className={`size-2 rounded-full transition-all duration-200 ${
                          i < watchPin.length
                            ? "bg-emerald-600 dark:bg-emerald-400 scale-110 shadow-xs"
                            : "bg-muted-foreground/20"
                        }`}
                      />
                    ))}
                  </div>
                </div>
                <div className="relative flex items-center">
                  <input
                    {...pinField}
                    type={showPin ? "text" : "password"}
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="••••••"
                    className="h-12 w-full rounded-xl border border-border bg-background/80 px-3.5 text-center font-mono text-base font-bold tracking-[0.35em] text-foreground outline-none placeholder:text-muted-foreground/40 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal placeholder:text-sm focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-all shadow-xs"
                    autoComplete="new-password"
                    enterKeyHint="next"
                    onChange={(e) => {
                      const clean = e.target.value.replace(/\D/g, "").slice(0, 6);
                      setValue("pin", clean);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPin(!showPin)}
                    className="absolute right-3 text-muted-foreground hover:text-foreground p-1 transition-colors"
                    aria-label={showPin ? "Ocultar PIN" : "Mostrar PIN"}
                  >
                    {showPin ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {errors.pin && (
                  <p className="px-1 text-[11px] font-medium text-rose-500">{errors.pin.message}</p>
                )}
              </div>

              {/* Confirmar PIN */}
              <div className="space-y-1">
                <div className="flex items-center justify-between px-1">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400" />
                    Confirmar PIN
                  </label>
                  {pinsMatch && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                      <CheckCircle2 className="size-3" /> PINs conferem
                    </span>
                  )}
                  {pinsMismatch && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-rose-500">
                      <ShieldAlert className="size-3" /> Diferentes
                    </span>
                  )}
                </div>
                <div className="relative flex items-center">
                  <input
                    {...pinConfirmField}
                    type={showPinConfirm ? "text" : "password"}
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="••••••"
                    className={`h-12 w-full rounded-xl border bg-background/80 px-3.5 text-center font-mono text-base font-bold tracking-[0.35em] text-foreground outline-none placeholder:text-muted-foreground/40 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal placeholder:text-sm focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/20 transition-all shadow-xs ${
                      pinsMatch
                        ? "border-emerald-500/80 bg-emerald-500/5"
                        : pinsMismatch
                          ? "border-rose-400 bg-rose-500/5"
                          : "border-border"
                    }`}
                    autoComplete="new-password"
                    enterKeyHint="done"
                    onChange={(e) => {
                      const clean = e.target.value.replace(/\D/g, "").slice(0, 6);
                      setValue("pin_confirm", clean);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPinConfirm(!showPinConfirm)}
                    className="absolute right-3 text-muted-foreground hover:text-foreground p-1 transition-colors"
                    aria-label={showPinConfirm ? "Ocultar PIN" : "Mostrar PIN"}
                  >
                    {showPinConfirm ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {errors.pin_confirm && (
                  <p className="px-1 text-[11px] font-medium text-rose-500">
                    {errors.pin_confirm.message}
                  </p>
                )}
              </div>

              {/* Error Message */}
              {error && (
                <div className="flex items-start gap-2 rounded-xl border border-rose-300/80 bg-rose-500/10 p-3 text-xs font-medium text-rose-700 dark:border-rose-800/60 dark:text-rose-300 animate-in fade-in duration-200">
                  <AlertCircle className="size-4 shrink-0 text-rose-500 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Botão de Ativação Mobile */}
              <button
                type="submit"
                disabled={loading}
                className="mt-2 flex h-13 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-700 via-emerald-600 to-emerald-700 font-semibold text-white shadow-lg shadow-emerald-900/30 transition-all active:scale-[0.98] hover:from-emerald-600 hover:to-emerald-500 disabled:opacity-50 disabled:pointer-events-none"
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin text-white" />
                    <span>Conectando e ativando...</span>
                  </>
                ) : (
                  <>
                    <span>Ativar Dispositivo</span>
                    <ArrowRight className="size-4.5" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* ── Mobile Footer ── */}
        <footer className="relative z-10 px-5 pb-4 pt-1 text-center sm:px-6" style={{ paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          <div className="flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground/85 font-medium">
            <ShieldCheck className="size-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>Operação 100% offline após o pareamento inicial</span>
          </div>
        </footer>
      </div>
    </main>
  );
}

export default function ActivatePage() {
  return (
    <Suspense>
      <ActivateForm />
    </Suspense>
  );
}

async function getDeviceFingerprint(): Promise<string> {
  const parts = [
    navigator.userAgent,
    navigator.language,
    screen.width,
    screen.height,
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  ].join("|");
  const encoder = new TextEncoder();
  const data = encoder.encode(parts);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

