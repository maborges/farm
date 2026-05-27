"use client";

import { CampoPill, CampoSurface } from "./ui";

interface NumPadProps {
  value: string;
  onChange: (v: string) => void;
  suffix?: string;
  label?: string;
}

export function NumPad({ value, onChange, suffix, label }: NumPadProps) {
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
    <CampoSurface className="flex flex-col gap-4 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        {label && <p className="text-sm font-semibold text-white/85">{label}</p>}
        {suffix && <CampoPill className="border-white/10 bg-white/6 text-white/65">{suffix}</CampoPill>}
      </div>
      <div className="rounded-[28px] border border-white/10 bg-white/[0.04] px-4 py-5 text-center shadow-[0_18px_40px_rgba(0,0,0,0.18)] sm:px-5 sm:py-6">
        <span className="text-4xl font-semibold tabular-nums tracking-tight text-white sm:text-5xl">
          {value || "0"}
        </span>
        {suffix && <span className="ml-2 text-base text-white/45 sm:text-lg">{suffix}</span>}
      </div>
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        {keys.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => handleKey(k)}
            className={`h-14 rounded-2xl border text-xl font-semibold transition-all active:scale-95 sm:h-16 ${
              k === "⌫"
                ? "border-white/10 bg-white/[0.05] text-white/75 hover:bg-white/[0.09]"
                : "border-white/10 bg-white/[0.04] text-white hover:bg-white/[0.09]"
            }`}
          >
            {k}
          </button>
        ))}
      </div>
    </CampoSurface>
  );
}
