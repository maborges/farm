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
    <div className="sticky bottom-0 mt-auto grid grid-cols-[1fr_1.35fr] gap-3 rounded-[24px] border border-white/10 bg-[#07110e]/92 p-3 shadow-[0_-18px_40px_rgba(0,0,0,0.22)] backdrop-blur-xl">
      <CampoButton variant="secondary" size="lg" onClick={onBack}>
        {backLabel}
      </CampoButton>
      <CampoButton variant="primary" size="lg" onClick={onNext} disabled={nextDisabled}>
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
      <CampoSurface className="w-full max-w-[420px] p-6 text-center">
        <div className="mx-auto flex size-20 items-center justify-center rounded-[28px] bg-gradient-to-br from-emerald-400 to-lime-300 text-4xl text-emerald-950 shadow-lg shadow-emerald-950/20">
          {icon}
        </div>
        <h2 className="mt-5 text-2xl font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-white/55">{description}</p>
        <div className="mt-6 grid gap-3">
          <CampoButton variant="primary" size="lg" onClick={onPrimary}>
            {primaryLabel}
          </CampoButton>
          <CampoButton variant="secondary" size="lg" onClick={onSecondary}>
            {secondaryLabel}
          </CampoButton>
        </div>
      </CampoSurface>
    </div>
  );
}
