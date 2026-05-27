"use client";

import { CampoPill, CampoSurface } from "./ui";

interface Option {
  id: string;
  label: string;
  sublabel?: string;
}

interface FieldSelectProps {
  label: string;
  options: Option[];
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
}

export function FieldSelect({ label, options, value, onChange, placeholder }: FieldSelectProps) {
  return (
    <CampoSurface className="flex flex-col gap-3 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-semibold text-white/85">{label}</label>
        {placeholder && <CampoPill className="border-white/10 bg-white/6 text-white/55">{placeholder}</CampoPill>}
      </div>
      {options.length <= 6 ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className={`rounded-[22px] border px-4 py-4 text-left transition-all active:scale-[0.98] ${
                value === opt.id
                  ? "border-emerald-400/30 bg-emerald-400/14 text-white shadow-[0_12px_30px_rgba(16,185,129,0.16)]"
                  : "border-white/10 bg-white/[0.04] text-white/82 hover:border-white/15 hover:bg-white/[0.07]"
              }`}
            >
              <p className="text-sm font-semibold leading-tight">{opt.label}</p>
              {opt.sublabel && (
                <p className="mt-1 text-xs text-white/45">{opt.sublabel}</p>
              )}
            </button>
          ))}
        </div>
      ) : (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-[22px] border border-white/10 bg-white/[0.04] px-4 py-4 text-base text-white outline-none transition-colors focus:border-emerald-400/50 focus:bg-white/[0.06]"
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
      )}
    </CampoSurface>
  );
}
