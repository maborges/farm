"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/stores/session-store";
import { CampoPill, CampoSectionTitle, CampoSurface } from "@/components/campo/ui";

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
    <main className="flex min-h-dvh items-center justify-center p-4 sm:p-6">
      <CampoSurface className="w-full max-w-[440px] p-6 sm:p-7">
        <div className="flex flex-col gap-4">
          <CampoPill className="border-emerald-400/20 bg-emerald-400/12 text-emerald-100">
            Dispositivo ativado
          </CampoPill>
          <div className="flex items-center gap-3">
            <div className="flex size-14 items-center justify-center rounded-[20px] bg-gradient-to-br from-emerald-400 to-lime-300 text-3xl text-emerald-950 shadow-lg shadow-emerald-950/20">
              🌱
            </div>
            <CampoSectionTitle
              eyebrow="Acesso"
              title={`Bem-vindo, ${session?.user_name ?? "Operador"}`}
              description="Digite seu PIN para acessar o app de campo."
            />
          </div>
        </div>

      <div className="mt-6 flex gap-3">
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <div
            key={i}
            className={`size-4 rounded-full border-2 transition-colors ${
              i < digits.length
                ? "border-emerald-400 bg-emerald-400"
                : "border-white/20 bg-transparent"
            }`}
          />
        ))}
      </div>

      {error && (
        <p className="mt-4 rounded-2xl border border-rose-400/20 bg-rose-400/12 px-4 py-2.5 text-sm text-rose-100">
          {error}
        </p>
      )}

      <div className="mt-6 grid w-full grid-cols-3 gap-3">
        {keys.map((key, i) => {
          if (key === "") return <div key={i} />;
          const isDelete = key === "⌫";
          return (
            <button
              key={i}
              onClick={() => (isDelete ? handleDelete() : handleDigit(key))}
              disabled={loading}
              className={`
                h-16 rounded-2xl border text-xl font-semibold transition-all active:scale-95
                ${isDelete
                  ? "border-white/10 bg-white/[0.05] text-white/75 hover:bg-white/[0.09]"
                  : "border-white/10 bg-white/[0.04] text-white hover:bg-white/[0.09]"
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
