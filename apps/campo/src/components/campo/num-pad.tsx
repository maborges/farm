"use client";

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
    <div className="flex flex-col gap-3">
      {label && <p className="text-sm font-medium text-neutral-400">{label}</p>}
      <div className="bg-neutral-800 rounded-2xl px-4 py-4 text-center">
        <span className="text-4xl font-bold tabular-nums">
          {value || "0"}
        </span>
        {suffix && <span className="text-lg text-neutral-400 ml-2">{suffix}</span>}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {keys.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => handleKey(k)}
            className={`h-14 rounded-2xl text-xl font-semibold transition-all active:scale-95 ${
              k === "⌫"
                ? "bg-neutral-700 text-neutral-300"
                : "bg-neutral-800 hover:bg-neutral-700 text-white"
            }`}
          >
            {k}
          </button>
        ))}
      </div>
    </div>
  );
}
