"use client";

import { useState } from "react";
import { Delete } from "lucide-react";

const PIN_LENGTH = 6;

export function PinPad({
  loading,
  error,
  onSubmit,
}: {
  loading: boolean;
  error: string | null;
  onSubmit: (pin: string) => void;
}) {
  const [digits, setDigits] = useState<string[]>([]);

  const handleDigit = (d: string) => {
    if (loading || digits.length >= PIN_LENGTH) return;
    const next = [...digits, d];
    setDigits(next);
    if (next.length === PIN_LENGTH) {
      onSubmit(next.join(""));
      setDigits([]);
    }
  };

  const handleDelete = () => setDigits((d) => d.slice(0, -1));

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

  return (
    <div className="flex w-full flex-col items-center">
      <div className="mb-6 flex justify-center gap-4">
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <div
            key={i}
            className={`size-3.5 rounded-full transition-colors ${
              i < digits.length ? "bg-primary" : "bg-primary/20"
            }`}
          />
        ))}
      </div>

      {error && (
        <p className="mb-4 text-center text-sm font-medium text-destructive">{error}</p>
      )}

      <div className="grid w-full grid-cols-3 gap-x-6 gap-y-3 justify-items-center">
        {keys.map((key, i) => {
          if (key === "") return <div key={i} />;
          const isDelete = key === "⌫";
          return (
            <button
              key={i}
              type="button"
              onClick={() => (isDelete ? handleDelete() : handleDigit(key))}
              disabled={loading}
              className={`flex items-center justify-center size-14 sm:size-16 rounded-full text-xl sm:text-2xl font-normal transition-all active:scale-90 disabled:opacity-50 ${
                isDelete
                  ? "bg-transparent text-muted-foreground"
                  : "bg-secondary/40 text-foreground hover:bg-secondary/60"
              }`}
            >
              {isDelete ? <Delete className="size-6" strokeWidth={1.5} /> : key}
            </button>
          );
        })}
      </div>
    </div>
  );
}
