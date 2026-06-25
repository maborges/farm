"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { CampoPill } from "@/components/campo/ui";
import { Sprout, Delete } from "lucide-react";

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
    <main className="flex min-h-dvh flex-col items-center justify-center p-4 sm:p-5 bg-background">
      <div className="relative w-full max-w-[340px] flex flex-col items-center">
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
        
        <CampoPill className="mb-6 border-primary/20 bg-primary/5 text-primary">
          Dispositivo ativado
        </CampoPill>

        <div className="flex flex-col items-center text-center gap-4">
          <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Sprout className="size-8" strokeWidth={1.5} />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Olá, {session?.user_name?.split(" ")[0] ?? "Operador"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Digite seu PIN para acessar.
            </p>
          </div>
        </div>

        <button
          type="button"
          className="mt-8 mb-6 flex w-full justify-center gap-4"
          onClick={() => pinInputRef.current?.focus()}
        >
          {Array.from({ length: PIN_LENGTH }).map((_, i) => (
            <div
              key={i}
              className={`size-4 rounded-full transition-colors ${
                i < digits.length
                  ? "bg-primary"
                  : "bg-primary/20"
              }`}
            />
          ))}
        </button>

        {error && (
          <p className="mb-4 text-center text-sm font-medium text-destructive animate-in fade-in slide-in-from-top-1">
            {error}
          </p>
        )}

        <div className="grid w-full grid-cols-3 gap-x-6 gap-y-4 justify-items-center">
          {keys.map((key, i) => {
            if (key === "") return <div key={i} />;
            const isDelete = key === "⌫";
            return (
              <button
                key={i}
                onClick={() => (isDelete ? handleDelete() : handleDigit(key))}
                disabled={loading}
                className={`
                  flex items-center justify-center size-16 sm:size-20 rounded-full text-2xl sm:text-3xl font-normal transition-all active:scale-90
                  ${isDelete
                    ? "bg-transparent text-muted-foreground"
                    : "bg-secondary/40 text-foreground hover:bg-secondary/60"
                  }
                  disabled:opacity-50
                `}
              >
                {isDelete ? <Delete className="size-7 sm:size-8" strokeWidth={1.5} /> : key}
              </button>
            );
          })}
        </div>
      </div>
    </main>
  );
}
