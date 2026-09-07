"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getOrCreateVariant } from "@/lib/landing-tracking";
import { getWhatsappComercialUrl } from "@/lib/runtime-config";
import { Skeleton } from "@/components/ui/skeleton";

const headlines = {
  A: "Reduza até 20% do custo da sua frota",
  B: "Veja o custo real da sua frota em menos de 7 dias",
  C: "Evite quebras e saiba o custo real de cada máquina",
};

const subheadlines = {
  A: "O AgroSaaS Frota identifica gargalos de combustível e manutenção. Redução real de custos comprovada em centenas de fazendas.",
  B: "Implantação rápida e diagnósticos imediatos. Em uma semana você tem a visão total do custo por hora de cada equipamento.",
  C: "O sistema monitora preventivas e alertas críticos. Não deixe sua produção parar por falta de controle operacional.",
};

export function FrotaHeroContent() {
  const [variant, setVariant] = useState<string | null>(null);

  useEffect(() => {
    // Garante que o variant seja selecionado apenas no cliente para evitar hydration mismatch
    setVariant(getOrCreateVariant());
  }, []);

  if (!variant) {
    return (
      <div className="space-y-8 py-12">
        <Skeleton className="h-20 w-3/4 max-w-2xl" />
        <Skeleton className="h-12 w-1/2 max-w-xl" />
        <div className="flex gap-4">
          <Skeleton className="h-12 w-40" />
          <Skeleton className="h-12 w-40" />
        </div>
      </div>
    );
  }

  const ctaPrimary = {
    A: "Quero reduzir o custo da minha frota",
    B: "Testar grátis por 14 dias",
    C: "Quero ver isso na minha fazenda",
  };

  const primaryLabel = ctaPrimary[variant as keyof typeof ctaPrimary] || ctaPrimary.B;
  const headline = headlines[variant as keyof typeof headlines] || headlines.A;
  const subheadline = subheadlines[variant as keyof typeof subheadlines] || subheadlines.A;

  const whatsappMessages = {
    A: "Olá! Gostaria de reduzir o custo da minha frota. Como funciona?",
    B: "Olá! Quero ver o custo real da minha frota. Vi que dá pra reduzir combustível e manutenção.",
    C: "Olá! Vi que vocês ajudam a identificar custos ocultos de até 20%. Quero entender para minha frota.",
  };

  const currentMsg = whatsappMessages[variant as keyof typeof whatsappMessages] || whatsappMessages.B;
  const WHATSAPP_URL = getWhatsappComercialUrl(currentMsg) ?? "/register";

  return (
    <div className="flex flex-col items-center text-center space-y-10 py-12 lg:py-20">
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-5xl font-black leading-[1.05] tracking-tight text-balance md:text-7xl">
          {headline}
        </h1>
        <p className="mx-auto max-w-2xl text-xl leading-8 text-muted-foreground">
          {subheadline}
        </p>
      </div>

      <div className="flex flex-col items-center gap-4">
        <div className="flex flex-wrap justify-center gap-4">
          <Button asChild size="lg" className="h-14 px-10 text-lg font-bold shadow-xl shadow-primary/30">
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" data-track-event={`cta_whatsapp_click_${variant}`}>
              {primaryLabel}
              <ArrowRight className="ml-2 size-5" />
            </a>
          </Button>
          <Button asChild variant="outline" size="lg" className="h-14 px-8 text-lg font-bold border-primary/20 bg-background/80 hover:bg-primary/5">
            <a href={WHATSAPP_URL} target="_blank" rel="noopener noreferrer" data-track-event={`cta_demo_click_${variant}`}>
              Agendar demonstração
              <ChevronRight className="ml-2 size-5" />
            </a>
          </Button>
        </div>
        
        {/* Microcopy de decisão */}
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs font-bold uppercase tracking-wider text-muted-foreground/80">
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Sem instalar equipamentos. 100% software.
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Sem cartão de crédito
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Você começa a usar em poucos dias
          </span>
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Cancelamento simples
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground pt-4">
        <Sparkles className="size-4 text-primary" />
        <span>Usado por produtores que operam tratores, colhedoras e pulverizadores</span>
      </div>
    </div>
  );
}
