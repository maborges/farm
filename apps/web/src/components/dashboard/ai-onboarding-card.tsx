"use client";

import Link from "next/link";
import { ArrowRight, BrainCircuit } from "lucide-react";
import { Button } from "@/components/ui/button";

export function AiOnboardingCard() {
  return (
    <section className="rounded-sm border border-primary/20 bg-primary/5 p-4" aria-labelledby="ai-onboarding-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3"><span className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary"><BrainCircuit className="size-5" aria-hidden="true" /></span><div><h2 id="ai-onboarding-title" className="text-sm font-semibold">Configure seu Copiloto IA</h2><p className="mt-1 text-xs text-muted-foreground">Veja como interpretar prioridades, alertas e recomendações para sua operação.</p></div></div>
        <Button asChild size="sm" className="shrink-0"><Link href="/dashboard/ia/resumo">Começar guia <ArrowRight className="ml-1 size-3.5" aria-hidden="true" /></Link></Button>
      </div>
    </section>
  );
}

