"use client";

import { type LucideIcon } from "lucide-react";
import { type ReactNode } from "react";
import { CampoButton, CampoSurface } from "./ui";

export function CampoStepNav({
  onBack,
  onNext,
  nextLabel,
  nextDisabled,
  backLabel = "Voltar",
  aboveBottomNav = false,
}: {
  onBack: () => void;
  onNext: () => void;
  nextLabel: ReactNode;
  nextDisabled?: boolean;
  backLabel?: ReactNode;
  aboveBottomNav?: boolean;
}) {
  return (
    <div
      className={
        aboveBottomNav
          ? "sticky bottom-[calc(4.5rem+env(safe-area-inset-bottom,0px))] md:bottom-0 mt-auto grid grid-cols-[1fr_1.35fr] gap-2.5 rounded-xl md:rounded-sm border border-border bg-card/95 backdrop-blur-sm p-2.5 shadow-md"
          : "sticky bottom-0 mt-auto grid grid-cols-[1fr_1.35fr] gap-2.5 rounded-xl md:rounded-sm border border-border bg-card/95 backdrop-blur-sm p-2.5 pb-[calc(0.625rem+env(safe-area-inset-bottom,0px))] md:pb-2.5 shadow-md"
      }
    >
      <CampoButton variant="secondary" size="md" onClick={onBack}>
        {backLabel}
      </CampoButton>
      <CampoButton variant="primary" size="md" onClick={onNext} disabled={nextDisabled}>
        {nextLabel}
      </CampoButton>
    </div>
  );
}

export function CampoSuccessScreen({
  icon: Icon,
  title,
  description,
  primaryLabel,
  onPrimary,
  secondaryLabel = "Voltar ao Início",
  onSecondary,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  primaryLabel: string;
  onPrimary: () => void;
  secondaryLabel?: string;
  onSecondary: () => void;
}) {
  return (
    <div className="flex min-h-[calc(100dvh-2rem)] items-center justify-center p-4">
      <CampoSurface className="w-full max-w-[400px] p-5 text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-xl md:rounded-sm border border-primary/20 bg-primary/10 text-primary shadow-sm">
          <Icon className="size-8" strokeWidth={1.5} />
        </div>
        <h2 className="mt-4 text-xl font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-5 text-muted-foreground">{description}</p>
        <div className="mt-5 grid gap-2.5">
          <CampoButton variant="primary" size="md" onClick={onPrimary}>
            {primaryLabel}
          </CampoButton>
          <CampoButton variant="secondary" size="md" onClick={onSecondary}>
            {secondaryLabel}
          </CampoButton>
        </div>
      </CampoSurface>
    </div>
  );
}
