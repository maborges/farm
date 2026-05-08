"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";

const PIN_LENGTH = 6;

export default function PinPage() {
  const router = useRouter();
  const { loginWithPIN, session, loadSession } = useSessionStore();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadSession().then(() => {
      const s = useSessionStore.getState().session;
      if (!s) router.replace("/activate");
    });
  }, []);

  const handleDigit = async (d: string) => {
    if (loading) return;
    setError(null);
    const next = [...digits, d];
    setDigits(next);

    if (next.length === PIN_LENGTH) {
      setLoading(true);
      const pin = next.join("");
      const ok = await loginWithPIN(pin);
      if (ok) {
        router.replace("/home");
      } else {
        setError("PIN incorreto. Tente novamente.");
        setDigits([]);
      }
      setLoading(false);
    }
  };

  const handleDelete = () => {
    setDigits((d) => d.slice(0, -1));
    setError(null);
  };

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-8 p-6">
      <div className="flex flex-col items-center gap-2">
        <div className="size-16 rounded-2xl bg-green-600 flex items-center justify-center text-3xl">🌱</div>
        <h1 className="text-xl font-bold">Bem-vindo, {session?.user_name ?? "Operador"}</h1>
        <p className="text-sm text-neutral-400">Digite seu PIN para acessar</p>
      </div>

      {/* Indicador de dígitos */}
      <div className="flex gap-3">
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <div
            key={i}
            className={`size-4 rounded-full border-2 transition-colors ${
              i < digits.length
                ? "bg-green-500 border-green-500"
                : "bg-transparent border-neutral-600"
            }`}
          />
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-400 bg-red-950 border border-red-800 rounded-xl px-4 py-2">
          {error}
        </p>
      )}

      {/* Teclado numérico */}
      <div className="grid grid-cols-3 gap-3 w-full max-w-xs">
        {keys.map((key, i) => {
          if (key === "") return <div key={i} />;
          const isDelete = key === "⌫";
          return (
            <button
              key={i}
              onClick={() => (isDelete ? handleDelete() : handleDigit(key))}
              disabled={loading}
              className={`
                h-16 rounded-2xl text-xl font-semibold transition-all active:scale-95
                ${isDelete
                  ? "bg-neutral-800 hover:bg-neutral-700 text-neutral-300"
                  : "bg-neutral-800 hover:bg-neutral-700 text-white"
                }
                disabled:opacity-50
              `}
            >
              {key}
            </button>
          );
        })}
      </div>
    </main>
  );
}
