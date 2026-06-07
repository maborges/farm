"use client";

import { CampoButton, CampoSurface } from "./ui";

export function CampoStepNav({
  onBack,
  onNext,
  nextLabel,
  nextDisabled,
  backLabel = "Voltar",
}: {
  onBack: () => void;
  onNext: () => void;
  nextLabel: string;
  nextDisabled?: boolean;
  backLabel?: string;
}) {
  return (
    <div className="sticky bottom-0 mt-auto grid grid-cols-[1fr_1.35fr] gap-2.5 rounded-sm border border-border bg-card p-2.5 shadow-md">
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
  icon,
  title,
  description,
  primaryLabel,
  onPrimary,
  secondaryLabel = "Voltar ao Início",
  onSecondary,
}: {
  icon: string;
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
        <div className="mx-auto flex size-16 items-center justify-center rounded-sm border border-primary/20 bg-accent text-3xl text-accent-foreground shadow-sm">
          {icon}
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
