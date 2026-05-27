"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import bcrypt from "bcryptjs";
import { CampoButton, CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const schema = z.object({
  activation_code: z.string().min(6).max(8).toUpperCase(),
  pin: z.string().min(4).max(6).regex(/^\d+$/, "PIN deve conter apenas números"),
  pin_confirm: z.string(),
}).refine((d) => d.pin === d.pin_confirm, {
  message: "PINs não conferem",
  path: ["pin_confirm"],
});

type FormData = z.infer<typeof schema>;

export default function ActivatePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { saveSession } = useSessionStore();

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

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
        last_sync_at: null,
        modules: payload.modulos,
        fazenda_ids: payload.fazenda_ids,
      });

      router.replace("/home");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-dvh items-center justify-center p-4 sm:p-6">
      <CampoSurface className="w-full max-w-[440px] p-6 sm:p-7">
        <div className="flex flex-col gap-4">
          <CampoPill className="border-emerald-400/20 bg-emerald-400/12 text-emerald-100">
            Campo offline-first
          </CampoPill>
          <div className="flex items-center gap-3">
            <div className="flex size-14 items-center justify-center rounded-[20px] bg-gradient-to-br from-emerald-400 to-lime-300 text-3xl text-emerald-950 shadow-lg shadow-emerald-950/20">
              🌱
            </div>
            <CampoSectionTitle
              eyebrow="Acesso"
              title="Ativar dispositivo"
              description="Use o código do gestor e crie seu PIN de acesso."
            />
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 flex w-full flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-white/70">Código de ativação</label>
            <input
              {...register("activation_code")}
              placeholder="Ex: ABCD1234"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3.5 text-lg tracking-[0.22em] text-center uppercase text-white outline-none transition-colors placeholder:text-white/20 focus:border-emerald-400/50 focus:bg-white/[0.06]"
              autoComplete="off"
              autoCapitalize="characters"
            />
            {errors.activation_code && (
              <p className="text-xs text-rose-300">{errors.activation_code.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-white/70">Criar PIN (4–6 dígitos)</label>
            <input
              {...register("pin")}
              type="password"
              inputMode="numeric"
              placeholder="••••"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3.5 text-lg tracking-[0.28em] text-center text-white outline-none transition-colors placeholder:text-white/20 focus:border-emerald-400/50 focus:bg-white/[0.06]"
            />
            {errors.pin && <p className="text-xs text-rose-300">{errors.pin.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-white/70">Confirmar PIN</label>
            <input
              {...register("pin_confirm")}
              type="password"
              inputMode="numeric"
              placeholder="••••"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3.5 text-lg tracking-[0.28em] text-center text-white outline-none transition-colors placeholder:text-white/20 focus:border-emerald-400/50 focus:bg-white/[0.06]"
            />
            {errors.pin_confirm && (
              <p className="text-xs text-rose-300">{errors.pin_confirm.message}</p>
            )}
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-400/20 bg-rose-400/12 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}

          <CampoButton type="submit" disabled={loading} className="mt-1 w-full" size="lg">
            {loading ? "Ativando..." : "Ativar dispositivo"}
          </CampoButton>
        </form>
      </CampoSurface>
    </main>
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
