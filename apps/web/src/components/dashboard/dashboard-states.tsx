"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionSkeleton } from "@/components/dashboard/dashboard-section";

export function DashboardPageSkeleton() {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-4 w-[28rem]" />
      </div>
      <SectionSkeleton cards={4} columnsClassName="md:grid-cols-2 xl:grid-cols-4" />
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, index) => (
          <Card key={index} className="overflow-hidden border shadow-sm">
            <CardHeader className="pb-3">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-72" />
            </CardHeader>
            <CardContent className="p-5">
              <div className="grid gap-4 md:grid-cols-4">
                {Array.from({ length: 4 }).map((__, metricIndex) => (
                  <Skeleton key={metricIndex} className="h-24 rounded-sm" />
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function TenantSelectionPrompt() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background p-6">
      <div className="w-full max-w-xl rounded-sm border border-border bg-card p-6 shadow-sm">
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-primary">Contexto pendente</p>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Selecione o produtor ativo</h1>
          <p className="text-sm text-muted-foreground">
            Sua conta tem acesso a mais de um produtor. Escolha qual produtor deve ser carregado antes de abrir o dashboard.
          </p>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/selecionar-tenant">
            <Button size="sm" className="rounded-sm">
              Escolher produtor
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
