"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { db } from "@/lib/db";
import { useSessionStore } from "@/lib/stores/session-store";
import bcrypt from "bcryptjs";

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
    <main className="flex min-h-dvh flex-col items-center justify-center gap-8 p-6">
      <div className="flex flex-col items-center gap-2">
        <div className="size-16 rounded-2xl bg-green-600 flex items-center justify-center text-3xl">🌱</div>
        <h1 className="text-2xl font-bold">Ativar Dispositivo</h1>
        <p className="text-sm text-neutral-400 text-center">
          Insira o código fornecido pelo seu gestor e crie seu PIN de acesso
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-sm flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-neutral-300">Código de Ativação</label>
          <input
            {...register("activation_code")}
            placeholder="Ex: ABCD1234"
            className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-lg tracking-widest text-center uppercase outline-none focus:border-green-500"
            autoComplete="off"
            autoCapitalize="characters"
          />
          {errors.activation_code && (
            <p className="text-xs text-red-400">{errors.activation_code.message}</p>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-neutral-300">Criar PIN (4–6 dígitos)</label>
          <input
            {...register("pin")}
            type="password"
            inputMode="numeric"
            placeholder="••••"
            className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-lg tracking-widest text-center outline-none focus:border-green-500"
          />
          {errors.pin && <p className="text-xs text-red-400">{errors.pin.message}</p>}
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-neutral-300">Confirmar PIN</label>
          <input
            {...register("pin_confirm")}
            type="password"
            inputMode="numeric"
            placeholder="••••"
            className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-3 text-lg tracking-widest text-center outline-none focus:border-green-500"
          />
          {errors.pin_confirm && (
            <p className="text-xs text-red-400">{errors.pin_confirm.message}</p>
          )}
        </div>

        {error && (
          <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-xl py-4 text-base font-semibold transition-colors"
        >
          {loading ? "Ativando..." : "Ativar Dispositivo"}
        </button>
      </form>
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
