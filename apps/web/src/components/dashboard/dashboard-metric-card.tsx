"use client";

import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type MetricCardProps = {
  label: string;
  value: string;
  description?: string;
  icon: ReactNode;
  tone: string;
};

export function MetricCard({ label, value, description, icon, tone }: MetricCardProps) {
  return (
    <Card className="overflow-hidden border border-border/50 bg-card shadow-sm hover:shadow-md transition-shadow group">
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className={cn("flex size-11 shrink-0 items-center justify-center rounded-sm ring-1 ring-inset ring-black/5 dark:ring-white/5", tone)}>{icon}</div>
          <div className="min-w-0 space-y-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
            <p className="text-balance text-2xl font-light tracking-tight text-foreground tabular-nums group-hover:text-primary transition-colors">{value}</p>
            {description ? <p className="text-[11px] font-medium text-muted-foreground">{description}</p> : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export type DomainMiniCardProps = {
  title: string;
  resumo: {
    pendentes: number;
    em_execucao: number;
    atrasadas: number;
    concluidas: number;
  };
};

export function DomainMiniCard({ title, resumo }: DomainMiniCardProps) {
  return (
    <Card className="border border-border/60 shadow-sm bg-card">
      <CardHeader className="pb-3 border-b border-border/40 bg-muted/10">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        <CardDescription className="text-[11px]">Quebra por domínio operacional</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-3">
        <SmallStat label="Pendentes" value={resumo.pendentes} />
        <SmallStat label="Em execução" value={resumo.em_execucao} />
        <SmallStat label="Atrasadas" value={resumo.atrasadas} />
        <SmallStat label="Concluídas" value={resumo.concluidas} />
      </CardContent>
    </Card>
  );
}

export type SmallStatProps = {
  label: string;
  value: number;
};

export function SmallStat({ label, value }: SmallStatProps) {
  return (
    <div className="rounded-sm border border-border/50 bg-muted/20 p-3 shadow-inner">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-light tabular-nums text-foreground">{value.toLocaleString("pt-BR")}</p>
    </div>
  );
}
