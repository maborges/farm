"use client";

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
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-neutral-400">{label}</label>
      {options.length <= 6 ? (
        // Grid de botões para listas curtas — toque fácil com luva
        <div className="grid grid-cols-2 gap-2">
          {options.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => onChange(opt.id)}
              className={`rounded-xl px-3 py-4 text-left transition-colors ${
                value === opt.id
                  ? "bg-green-600 text-white"
                  : "bg-neutral-800 text-neutral-200 hover:bg-neutral-700"
              }`}
            >
              <p className="text-sm font-semibold leading-tight">{opt.label}</p>
              {opt.sublabel && (
                <p className="text-xs text-neutral-400 mt-0.5">{opt.sublabel}</p>
              )}
            </button>
          ))}
        </div>
      ) : (
        // Select nativo para listas longas
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="bg-neutral-800 border border-neutral-700 rounded-xl px-4 py-4 text-base outline-none focus:border-green-500 w-full"
        >
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
