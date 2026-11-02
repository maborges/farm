"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm, type FieldError, type FieldErrors, type Resolver } from "react-hook-form";
import bcrypt from "bcryptjs";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
} from "lucide-react";
import { z } from "zod";
import { CampoSessionClearNotice } from "@/components/campo/session-clear-notice";
import { ThemeToggle } from "@/components/theme-toggle";
import { useDeviceContext } from "@/lib/device/use-device-context";
import {
  consumeSessionClearNotice,
  useSessionStore,
  type SessionClearNotice,
} from "@/lib/stores/session-store";

const API_BASE = "/api/v1";

const schema = z.object({
  activation_code: z
    .string()
    .min(6, "Código de ativação deve ter ao menos 6 caracteres")
    .max(8, "Código de ativação deve ter no máximo 8 caracteres")
    .toUpperCase(),
  pin: z
    .string()
    .length(6, "PIN deve ter exatamente 6 dígitos")
    .regex(/^\d+$/, "PIN deve conter apenas números"),
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
  const { layoutProfile } = useDeviceContext();
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
  const pinsMatch =
    isPinComplete && isPinConfirmComplete && watchPin === watchPinConfirm;
  const pinsMismatch = isPinConfirmComplete && watchPin !== watchPinConfirm;

  return (
    <div
      data-device-category={layoutProfile.deviceCategory}
      data-execution-mode={layoutProfile.executionMode}
      className="min-h-dvh flex flex-col bg-background text-foreground safe-area-px"
    >
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
                Ativação de Dispositivo Operacional
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-sm border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Offline-ready</span>
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Conteúdo Central */}
      <main className="flex-1 flex flex-col justify-center w-full max-w-md mx-auto px-3 sm:px-5 py-6">
        <div className="flex flex-col gap-4">
          {/* Cabeçalho da Página */}
          <div className="flex flex-col gap-1 border-b border-border pb-3">
            <div className="flex items-center gap-2 text-primary">
              <Smartphone className="w-4 h-4 text-primary" />
              <span className="text-[11px] font-semibold uppercase tracking-wider">
                Pareamento de Dispositivo
              </span>
            </div>
            <h1 className="text-base sm:text-xl font-bold tracking-tight text-foreground">
              Ativar Dispositivo no Campo
            </h1>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Vincule este aparelho à sua fazenda para sincronizar tarefas e apontamentos offline.
            </p>
          </div>

          {reasonMessage && (
            <div className="flex items-start gap-2.5 rounded-sm border border-amber-500/30 bg-amber-500/15 p-3 text-xs font-medium text-amber-800 dark:text-amber-300">
              <AlertCircle className="size-4 shrink-0 text-amber-600 dark:text-amber-400 mt-0.5" />
              <span>{reasonMessage}</span>
            </div>
          )}

          {clearNotice && <CampoSessionClearNotice notice={clearNotice} />}

          {/* Card de Formulário no padrão Agro */}
          <div className="rounded-sm border border-border bg-card p-4 sm:p-5 shadow-2xs">
            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
              {/* Código de Ativação */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <KeyRound className="size-3.5 text-primary" />
                    Código de Ativação
                  </label>
                  <span className="text-[10px] text-muted-foreground">
                    Fornecido pelo gestor
                  </span>
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
                    className="h-10 sm:h-9 w-full rounded-sm border border-input bg-background px-3 text-center font-mono text-sm font-bold tracking-[0.25em] text-foreground uppercase outline-none placeholder:text-muted-foreground/50 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal focus:border-ring transition-all shadow-2xs"
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
                    <span className="absolute right-3 text-primary">
                      <CheckCircle2 className="size-4" />
                    </span>
                  )}
                </div>
                {errors.activation_code && (
                  <p className="text-[11px] font-medium text-destructive">
                    {errors.activation_code.message}
                  </p>
                )}
              </div>

              {/* Criar PIN */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <Lock className="size-3.5 text-primary" />
                    Criar PIN de Acesso
                  </label>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <span
                        key={i}
                        className={`size-2 rounded-full transition-all duration-200 ${
                          i < watchPin.length ? "bg-primary scale-110" : "bg-muted-foreground/25"
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
                    className="h-10 sm:h-9 w-full rounded-sm border border-input bg-background px-3 text-center font-mono text-sm font-bold tracking-[0.35em] text-foreground outline-none placeholder:text-muted-foreground/50 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal focus:border-ring transition-all shadow-2xs"
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
                    className="absolute right-2.5 text-muted-foreground hover:text-foreground p-1 transition-colors"
                    aria-label={showPin ? "Ocultar PIN" : "Mostrar PIN"}
                  >
                    {showPin ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
                {errors.pin && (
                  <p className="text-[11px] font-medium text-destructive">
                    {errors.pin.message}
                  </p>
                )}
              </div>

              {/* Confirmar PIN */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
                    <ShieldCheck className="size-3.5 text-primary" />
                    Confirmar PIN
                  </label>
                  {pinsMatch && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-primary">
                      <CheckCircle2 className="size-3" /> PINs conferem
                    </span>
                  )}
                  {pinsMismatch && (
                    <span className="flex items-center gap-1 text-[10px] font-semibold text-destructive">
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
                    className={`h-10 sm:h-9 w-full rounded-sm border bg-background px-3 text-center font-mono text-sm font-bold tracking-[0.35em] text-foreground outline-none placeholder:text-muted-foreground/50 placeholder:tracking-normal placeholder:font-sans placeholder:font-normal focus:border-ring transition-all shadow-2xs ${
                      pinsMatch
                        ? "border-primary bg-primary/5"
                        : pinsMismatch
                          ? "border-destructive bg-destructive/5"
                          : "border-input"
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
                    className="absolute right-2.5 text-muted-foreground hover:text-foreground p-1 transition-colors"
                    aria-label={showPinConfirm ? "Ocultar PIN" : "Mostrar PIN"}
                  >
                    {showPinConfirm ? (
                      <EyeOff className="size-4" />
                    ) : (
                      <Eye className="size-4" />
                    )}
                  </button>
                </div>
                {errors.pin_confirm && (
                  <p className="text-[11px] font-medium text-destructive">
                    {errors.pin_confirm.message}
                  </p>
                )}
              </div>

              {error && (
                <div className="flex items-start gap-2 rounded-sm border border-rose-500/30 bg-rose-500/15 p-3 text-xs font-medium text-rose-700 dark:text-rose-300">
                  <AlertCircle className="size-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-1 flex h-10 w-full items-center justify-center gap-2 rounded-sm bg-primary px-4 text-xs font-semibold text-primary-foreground shadow-2xs transition-all hover:bg-primary/90 active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none"
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    <span>Conectando e ativando...</span>
                  </>
                ) : (
                  <>
                    <span>Ativar Dispositivo</span>
                    <ArrowRight className="size-4" />
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </main>

      <footer className="border-t border-border/60 bg-muted/20 py-3 px-4 text-center safe-area-pb">
        <div className="flex items-center justify-center gap-1.5 text-[11px] text-muted-foreground font-medium">
          <ShieldCheck className="size-3.5 text-primary shrink-0" />
          <span>Operação 100% offline após o pareamento inicial</span>
        </div>
      </footer>
    </div>
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
