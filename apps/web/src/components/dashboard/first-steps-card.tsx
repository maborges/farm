"use client";

import Link from "next/link";
import { CheckCircle2, Circle, MapPinned, Sprout, Wallet, Wrench } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type FirstStepsCardProps = {
  isLoading: boolean;
  hasProperty: boolean;
  hasHarvest: boolean;
  hasOperation: boolean;
  hasFinance: boolean;
  hasFinanceData: boolean;
};

type Step = {
  label: string;
  description: string;
  href: string;
  completed: boolean;
  icon: typeof MapPinned;
};

export function FirstStepsCard({
  isLoading,
  hasProperty,
  hasHarvest,
  hasOperation,
  hasFinance,
  hasFinanceData,
}: FirstStepsCardProps) {
  if (isLoading) {
    return <Skeleton className="h-44 w-full rounded-sm" />;
  }

  const steps: Step[] = [
    {
      label: "Cadastre uma propriedade",
      description: "Defina o contexto da sua operação.",
      href: "/cadastros/propriedades",
      completed: hasProperty,
      icon: MapPinned,
    },
    {
      label: "Crie sua primeira safra",
      description: "Comece a acompanhar o planejamento agrícola.",
      href: "/agricola/safras",
      completed: hasHarvest,
      icon: Sprout,
    },
    {
      label: "Registre uma atividade",
      description: "Dê o primeiro passo no controle operacional.",
      href: "/dashboard/operacional/campo/tarefas",
      completed: hasOperation,
      icon: Wrench,
    },
    ...(hasFinance
      ? [{
          label: "Configure o financeiro",
          description: "Tenha uma visão inicial de receitas e despesas.",
          href: "/dashboard/financeiro",
          completed: hasFinanceData,
          icon: Wallet,
        }]
      : []),
  ];

  const completedCount = steps.filter((step) => step.completed).length;
  if (completedCount === steps.length) return null;

  return (
    <Card className="rounded-sm border-primary/20 bg-primary/[0.03] shadow-sm">
      <CardHeader className="gap-2 pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">Primeiros passos</CardTitle>
          <span className="text-xs font-medium text-muted-foreground">
            {completedCount} de {steps.length} concluídos
          </span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-primary/10"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={steps.length}
          aria-valuenow={completedCount}
          aria-label="Progresso dos primeiros passos"
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-300"
            style={{ width: `${(completedCount / steps.length) * 100}%` }}
          />
        </div>
      </CardHeader>
      <CardContent className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <Link
              key={step.label}
              href={step.href}
              className={cn(
                "group flex min-h-16 items-start gap-2 rounded-sm border border-border/50 bg-background/60 p-3 transition-colors hover:border-primary/50 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                step.completed && "border-primary/20 bg-primary/[0.04]"
              )}
            >
              {step.completed ? (
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
              ) : (
                <Circle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              )}
              <span className="min-w-0">
                <span className="flex items-center gap-1 text-xs font-semibold">
                  <Icon className="size-3.5 text-primary" aria-hidden="true" />
                  {step.label}
                </span>
                <span className="mt-1 block text-[11px] leading-snug text-muted-foreground">
                  {step.completed ? "Concluído" : step.description}
                </span>
              </span>
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}
