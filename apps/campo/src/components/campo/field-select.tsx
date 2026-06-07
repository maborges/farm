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
    <CampoSurface className="flex flex-col gap-2.5 p-3.5 sm:p-4">
      <div className="flex items-center justify-between gap-2.5">
        <label className="text-sm font-semibold text-foreground">{label}</label>
        {placeholder && <CampoPill>{placeholder}</CampoPill>}
      </div>
      {options.length <= 6 ? (
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
          {options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className={`rounded-sm border px-3.5 py-3 text-left transition-all active:scale-[0.98] ${
                value === opt.id
                  ? "border-primary/40 bg-accent text-accent-foreground shadow-sm"
                  : "border-border bg-card text-foreground hover:bg-muted"
              }`}
            >
              <p className="text-sm font-semibold leading-tight">{opt.label}</p>
              {opt.sublabel && (
                <p className="mt-1 text-xs text-muted-foreground">{opt.sublabel}</p>
              )}
            </button>
          ))}
        </div>
      ) : (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-lg border border-input bg-card px-3.5 py-3 text-base text-foreground outline-none focus:border-ring"
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
