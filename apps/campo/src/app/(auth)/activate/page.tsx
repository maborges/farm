"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import bcrypt from "bcryptjs";
import { CampoButton, CampoPill, CampoSurface } from "@/components/campo/ui";

const API_BASE = "/api/v1";

const schema = z.object({
  activation_code: z
    .string()
    .min(6, "Código de ativação deve ter ao menos 6 caracteres")
    .max(8, "Código de ativação deve ter no máximo 8 caracteres")
    .toUpperCase(),
  pin: z.string().length(6, "PIN deve ter 6 dígitos").regex(/^\d+$/, "PIN deve conter apenas números"),
  pin_confirm: z.string(),
}).refine((d) => d.pin === d.pin_confirm, {
  message: "PINs não conferem",
  path: ["pin_confirm"],
});

type FormData = z.infer<typeof schema>;

function ActivateForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { saveSession } = useSessionStore();
  const reason = searchParams.get("reason");
  const activationCodeRef = useRef<HTMLInputElement | null>(null);

  const reasonMessage = reason === "device_revoked"
    ? "O dispositivo anterior foi revogado. Gere uma nova ativação."
    : reason === "device_expired"
      ? "O dispositivo anterior expirou. Gere uma nova ativação."
      : reason === "device_invalid"
        ? "A sessão local não é mais válida. Faça uma nova ativação."
        : null;

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });
  const activationCodeField = register("activation_code");
  const pinField = register("pin");
  const pinConfirmField = register("pin_confirm");

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
          activation_code: data.activation_code,
          pin_hash,
          device_fingerprint,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Erro na ativação");
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
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex h-dvh overflow-hidden items-center justify-center bg-[radial-gradient(circle_at_top,_hsla(18,68%,68%,0.18),_transparent_42%),linear-gradient(180deg,hsl(var(--background)),hsl(var(--muted)))] p-0 sm:p-4">
      <CampoSurface
        className="relative flex h-dvh w-full flex-col overflow-hidden rounded-none border-0 bg-transparent shadow-none animate-in fade-in zoom-in-95 slide-in-from-bottom-4 duration-700 sm:h-[calc(100dvh-2rem)] sm:max-w-[430px] sm:rounded-[32px]"
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <img
            src="/AgroSaaS-icone.webp"
            alt=""
            aria-hidden="true"
            className="h-auto w-[88%] translate-y-[-8%] opacity-40 select-none object-contain"
          />
        </div>
        <div className="absolute inset-0 bg-card/30" />

        <div className="relative z-[1] flex flex-1 flex-col">
          <section className="px-5 pb-3 pt-5 sm:px-6 sm:pt-6">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-3">
                <img
                  src="/AgroSaaS-icone.webp"
                  alt="AgroSaaS Campo"
                  className="h-12 w-12 object-contain"
                />
                <CampoPill className="shrink-0 border-primary/20 bg-accent/70 text-accent-foreground shadow-sm">
                  Campo offline-first
                </CampoPill>
              </div>

              <div className="space-y-2 text-center">
                <h1 className="text-xl font-semibold tracking-tight text-foreground">
                  Ativar dispositivo
                </h1>
                <p className="text-sm leading-5 text-muted-foreground">
                  Use o código do gestor e crie um PIN de 6 dígitos.
                </p>
                <div className="space-y-1 pt-2 text-[11px] leading-5 text-muted-foreground">
                  <p>Use um PIN fácil de lembrar para o operador, mas difícil de adivinhar.</p>
                  <p>Depois da ativação, o app poderá continuar operando mesmo sem sinal.</p>
                </div>
              </div>
            </div>
          </section>

          <section className="relative z-[2] flex flex-1 flex-col justify-center rounded-t-[32px] bg-card/30 px-5 pb-5 pt-4 animate-in fade-in slide-in-from-bottom-6 duration-700 sm:px-6">
            {reasonMessage && (
              <div className="mb-4 rounded-[20px] border border-amber-200/80 bg-amber-50/92 px-4 py-2.5 text-sm text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
                {reasonMessage}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="flex w-full flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="px-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">Código de ativação</label>
                <input
                  {...activationCodeField}
                  ref={(element) => {
                    activationCodeField.ref(element);
                    activationCodeRef.current = element;
                  }}
                  type="text"
                  inputMode="text"
                  placeholder="Ex: ABCD1234"
                  className="w-full rounded-[22px] border border-border/70 bg-card/92 px-4 py-3 text-center text-base uppercase tracking-[0.18em] text-foreground outline-none shadow-sm placeholder:text-muted-foreground/50 focus:border-primary focus:ring-4 focus:ring-primary/10"
                  autoComplete="off"
                  autoCapitalize="characters"
                  autoCorrect="off"
                  spellCheck={false}
                  enterKeyHint="next"
                />
                {errors.activation_code && (
                  <p className="px-2 text-xs text-rose-500">{errors.activation_code.message}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="px-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">Criar PIN</label>
                <input
                  {...pinField}
                  type="password"
                  inputMode="numeric"
                  placeholder="••••••"
                  className="w-full rounded-[22px] border border-border/70 bg-card/92 px-4 py-3 text-center text-base tracking-[0.24em] text-foreground outline-none shadow-sm placeholder:text-muted-foreground/50 focus:border-primary focus:ring-4 focus:ring-primary/10"
                  autoComplete="new-password"
                  enterKeyHint="next"
                />
                {errors.pin && <p className="px-2 text-xs text-rose-500">{errors.pin.message}</p>}
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="px-1 text-xs font-medium tracking-[0.01em] text-muted-foreground">Confirmar PIN</label>
                <input
                  {...pinConfirmField}
                  type="password"
                  inputMode="numeric"
                  placeholder="••••••"
                  className="w-full rounded-[22px] border border-border/70 bg-card/92 px-4 py-3 text-center text-base tracking-[0.24em] text-foreground outline-none shadow-sm placeholder:text-muted-foreground/50 focus:border-primary focus:ring-4 focus:ring-primary/10"
                  autoComplete="new-password"
                  enterKeyHint="done"
                />
                {errors.pin_confirm && (
                  <p className="px-2 text-xs text-rose-500">{errors.pin_confirm.message}</p>
                )}
              </div>

              {error && (
                <div className="rounded-[20px] border border-rose-200 bg-rose-50/92 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
                  {error}
                </div>
              )}

              <CampoButton type="submit" disabled={loading} className="mt-1 w-full rounded-[22px] py-3.5 text-sm shadow-md shadow-primary/20" size="lg">
                {loading ? "Ativando..." : "Ativar dispositivo"}
              </CampoButton>
            </form>
          </section>

          <div className="relative z-[2] px-5 pb-4 pt-2 text-center text-[10px] leading-4 text-muted-foreground sm:px-6">
            Ao ativar, este dispositivo será vinculado ao ambiente autorizado pelo gestor.
          </div>
        </div>
      </CampoSurface>
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
