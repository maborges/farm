"use client";

import { useRouter } from "next/navigation";
import { GpsBadge } from "./gps-badge";
import { CampoButton, CampoPill, CampoSurface } from "./ui";

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
    <CampoSurface className="p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <CampoButton variant="secondary" size="sm" onClick={() => router.back()}>
          ←
        </CampoButton>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-[18px] bg-white/[0.06] text-2xl">
              {icon}
            </span>
            <div>
              <p className="text-[11px] uppercase tracking-[0.22em] text-emerald-300/80">Registro de campo</p>
              <h1 className="text-xl font-semibold leading-tight sm:text-2xl">{title}</h1>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <GpsBadge status={gpsStatus} />
            {step !== undefined && totalSteps !== undefined && (
              <CampoPill className="border-white/10 bg-white/6 text-white/70">
                Etapa {step}/{totalSteps}
              </CampoPill>
            )}
          </div>
        </div>
      </div>

      {step !== undefined && totalSteps !== undefined && (
        <div className="mt-4 flex gap-1.5">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i < step ? "bg-gradient-to-r from-emerald-400 to-lime-300" : "bg-white/10"
              }`}
            />
          ))}
        </div>
      )}
    </CampoSurface>
  );
}
