"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

const PIN_LENGTH = 6;

export default function PinPage() {
  const router = useRouter();
  const { loginWithPIN, session, loadSession, validateDeviceSession } = useSessionStore();
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

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

  return (
    <main className="flex min-h-dvh items-center justify-center p-4 sm:p-5">
      <CampoSurface className="relative w-full max-w-[400px] p-5 sm:p-6">
        <input
          ref={pinInputRef}
          type="password"
          inputMode="numeric"
          autoComplete="current-password"
          enterKeyHint="done"
          value={digits.join("")}
          onChange={(e) => void handlePinInputChange(e.target.value)}
          className="pointer-events-none absolute left-0 top-0 h-px w-px opacity-0"
          aria-label="PIN do dispositivo"
        />
        <div className="flex flex-col gap-3">
          <CampoPill className="border-primary/20 bg-accent text-accent-foreground">
            Dispositivo ativado
          </CampoPill>
          <div className="flex items-center gap-2.5">
            <div className="flex size-11 items-center justify-center rounded-sm border border-primary/20 bg-accent text-2xl text-accent-foreground shadow-sm">
              🌱
            </div>
            <CampoSectionTitle
              eyebrow="Acesso"
              title={`Bem-vindo, ${session?.user_name ?? "Operador"}`}
              description="Digite seu PIN para entrar no app."
            />
          </div>
        </div>

      <button
        type="button"
        className="mt-5 flex w-full justify-center gap-2.5"
        onClick={() => pinInputRef.current?.focus()}
      >
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <div
            key={i}
            className={`size-3.5 rounded-full border-2 transition-colors ${
              i < digits.length
                ? "border-emerald-400 bg-emerald-400"
                : "border-border bg-transparent"
            }`}
          />
        ))}
      </button>

      {error && (
        <p className="mt-4 rounded-sm border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-200">
          {error}
        </p>
      )}

      <div className="mt-5 grid w-full grid-cols-3 gap-2.5">
        {keys.map((key, i) => {
          if (key === "") return <div key={i} />;
          const isDelete = key === "⌫";
          return (
            <button
              key={i}
              onClick={() => (isDelete ? handleDelete() : handleDigit(key))}
              disabled={loading}
              className={`
                h-14 rounded-sm border text-lg font-semibold transition-all active:scale-95
                ${isDelete
                  ? "border-border bg-muted text-muted-foreground hover:bg-secondary"
                  : "border-border bg-card text-foreground shadow-sm hover:bg-muted"
                }
                disabled:opacity-50
              `}
            >
              {key}
            </button>
          );
        })}
      </div>
      </CampoSurface>
    </main>
  );
}
