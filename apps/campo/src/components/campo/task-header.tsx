"use client";

import { useRouter } from "next/navigation";
import { GpsBadge } from "./gps-badge";

interface TaskHeaderProps {
  title: string;
  icon: string;
  gpsStatus: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
  step?: number;
  totalSteps?: number;
}

export function TaskHeader({ title, icon, gpsStatus, step, totalSteps }: TaskHeaderProps) {
  const router = useRouter();

  return (
    <div className="flex flex-col gap-3 pt-2">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="text-neutral-400 text-xl">←</button>
        <div className="flex items-center gap-2 flex-1">
          <span className="text-2xl">{icon}</span>
          <h1 className="text-lg font-bold">{title}</h1>
        </div>
        <GpsBadge status={gpsStatus} />
      </div>

      {step !== undefined && totalSteps !== undefined && (
        <div className="flex gap-1.5">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i < step ? "bg-green-500" : "bg-neutral-700"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
