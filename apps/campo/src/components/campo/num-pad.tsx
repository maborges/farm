"use client";

import { useEffect, useRef } from "react";
import { CampoPill, CampoSurface } from "./ui";

interface NumPadProps {
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
  label?: string;
}

export function NumPad({ value, onChange, suffix, label }: NumPadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      inputRef.current?.focus();
    });

    return () => cancelAnimationFrame(frame);
  }, []);

  const sanitizeValue = (nextValue: string) => {
    const normalized = nextValue.replace(",", ".").replace(/[^0-9.]/g, "");
    const [integerPart, ...decimalParts] = normalized.split(".");
    return decimalParts.length > 0
      ? `${integerPart}.${decimalParts.join("")}`
      : integerPart;
  };

  const handleKey = (k: string) => {
    if (k === "⌫") {
      onChange(value.slice(0, -1));
    } else if (k === "." && value.includes(".")) {
      return; // só um ponto decimal
    } else {
      onChange(value + k);
    }
  };

  const keys = ["7", "8", "9", "4", "5", "6", "1", "2", "3", ".", "0", "⌫"];

  return (
    <CampoSurface className="flex flex-col gap-3 p-3.5 sm:p-4">
      <div className="flex items-center justify-between gap-3">
        {label && <p className="text-sm font-semibold text-foreground">{label}</p>}
        {suffix && <CampoPill>{suffix}</CampoPill>}
      </div>
      <div
        className="rounded-sm border border-border bg-muted px-4 py-3 text-center shadow-sm sm:px-5 sm:py-4"
        onClick={() => inputRef.current?.focus()}
      >
        <input
          ref={inputRef}
          type="text"
          inputMode="decimal"
          enterKeyHint="done"
          autoComplete="off"
          value={value}
          onChange={(e) => onChange(sanitizeValue(e.target.value))}
          placeholder="0"
          className="w-full bg-transparent text-center text-3xl font-semibold tabular-nums tracking-tight text-foreground outline-none placeholder:text-foreground sm:text-4xl"
        />
        {suffix && <span className="mt-1 block text-sm text-muted-foreground sm:text-base">{suffix}</span>}
      </div>
      <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
        {keys.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => handleKey(k)}
            className={`h-12 rounded-sm border text-lg font-semibold transition-all active:scale-95 sm:h-14 ${
              k === "⌫"
                ? "border-border bg-muted text-muted-foreground hover:bg-secondary"
                : "border-border bg-card text-foreground shadow-sm hover:bg-muted"
            }`}
          >
            {k}
          </button>
        ))}
      </div>
    </CampoSurface>
  );
}
