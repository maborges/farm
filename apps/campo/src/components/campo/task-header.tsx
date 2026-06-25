"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, type LucideIcon } from "lucide-react";
import { GpsBadge } from "./gps-badge";
import { TaskDomainBadge } from "./task-domain-badge";
import { CampoButton, CampoPill, CampoSurface } from "./ui";
import type { TaskDomain } from "@/lib/task-domain";

interface TaskHeaderProps {
  title: string;
  icon: LucideIcon;
  gpsStatus: "DISPONIVEL" | "INDISPONIVEL" | "AGUARDANDO";
  step?: number;
  totalSteps?: number;
  domain?: TaskDomain;
}

export function TaskHeader(props: TaskHeaderProps) {
  const { title, gpsStatus, step, totalSteps, domain } = props;
  const router = useRouter();

  return (
    <CampoSurface className="p-3.5 sm:p-4">
      <div className="flex items-start gap-2.5">
        <CampoButton variant="secondary" size="sm" onClick={() => router.back()} className="size-10 px-0 shrink-0 border-border bg-card shadow-sm flex items-center justify-center">
          <ArrowLeft className="size-5 text-muted-foreground" />
        </CampoButton>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2.5">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
              <props.icon className="size-5" strokeWidth={2} />
            </span>
            <div>
              <p className="text-[10px] uppercase tracking-[0.16em] text-primary">Registro</p>
              <h1 className="text-lg font-semibold leading-tight sm:text-xl">{title}</h1>
            </div>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            <GpsBadge status={gpsStatus} />
            {domain && <TaskDomainBadge domain={domain} />}
            {step !== undefined && totalSteps !== undefined && (
              <CampoPill className="border-border bg-muted text-muted-foreground">
                Etapa {step}/{totalSteps}
              </CampoPill>
            )}
          </div>
        </div>
      </div>

      {step !== undefined && totalSteps !== undefined && (
        <div className="mt-3 flex gap-1">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i < step ? "bg-primary" : "bg-muted"
              }`}
            />
          ))}
        </div>
      )}
    </CampoSurface>
  );
}
