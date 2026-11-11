"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Beef,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Clock3,
  Package,
  Sprout,
  Wallet
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getRecentNavigationLabel, type RecentNavigationItem } from "@/components/layout/recent-navigation-tracker";

const RECENT_STORAGE_KEY = "agrosaas-recent-navigation";

type DashboardActionGridProps = {
  hasAgriculture: boolean;
  hasFinance: boolean;
  hasLivestock: boolean;
  canViewSafras: boolean;
  canViewTarefas: boolean;
  canViewEstoque: boolean;
  canViewFinanceiro: boolean;
  canViewPecuaria: boolean;
};

export function DashboardActionGrid({
  hasAgriculture,
  hasFinance,
  hasLivestock,
  canViewSafras,
  canViewTarefas,
  canViewEstoque,
  canViewFinanceiro,
  canViewPecuaria,
}: DashboardActionGridProps) {
  const [lastRecent, setLastRecent] = useState<RecentNavigationItem | null>(null);

  useEffect(() => {
    try {
      const storedRecent = JSON.parse(localStorage.getItem(RECENT_STORAGE_KEY) ?? "[]") as RecentNavigationItem[];
      const valid = storedRecent.filter((item) => item.href !== "/dashboard");
      if (valid.length > 0) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setLastRecent({
          ...valid[0],
          label: getRecentNavigationLabel(valid[0].href),
        });
      }
    } catch {
      setLastRecent(null);
    }
  }, []);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          Ações & Atalhos Operacionais
        </h3>
        <span className="text-[11px] text-muted-foreground">Comandos disponíveis para seu perfil</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-8 gap-2.5">
        {/* SAFRAS */}
        {hasAgriculture && canViewSafras && (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-primary/60 hover:bg-primary/[0.03] transition-all group"
          >
            <Link href="/agricola/safras">
              <div className="size-8 rounded-sm bg-primary/10 text-primary flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Sprout className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <span className="block text-xs font-semibold text-foreground truncate">Safras</span>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                  Painéis e ciclos
                </span>
              </div>
            </Link>
          </Button>
        )}

        {/* TAREFAS */}
        {canViewTarefas && (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-amber-500/60 hover:bg-amber-500/[0.03] transition-all group"
          >
            <Link href="/dashboard/operacional/campo/tarefas">
              <div className="size-8 rounded-sm bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 group-hover:bg-amber-600 group-hover:text-white transition-colors">
                <ClipboardList className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <span className="block text-xs font-semibold text-foreground truncate">Tarefas</span>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                  Operações de campo
                </span>
              </div>
            </Link>
          </Button>
        )}

        {/* ESTOQUE */}
        {canViewEstoque && (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-blue-500/60 hover:bg-blue-500/[0.03] transition-all group"
          >
            <Link href="/suprimentos/estoque">
              <div className="size-8 rounded-sm bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Package className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <span className="block text-xs font-semibold text-foreground truncate">Estoque</span>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                  Insumos e saldos
                </span>
              </div>
            </Link>
          </Button>
        )}

        {/* FINANCEIRO */}
        {hasFinance && canViewFinanceiro && (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-emerald-500/60 hover:bg-emerald-500/[0.03] transition-all group"
          >
            <Link href="/dashboard/financeiro">
              <div className="size-8 rounded-sm bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                <Wallet className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <span className="block text-xs font-semibold text-foreground truncate">Financeiro</span>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                  Fluxo e DRE
                </span>
              </div>
            </Link>
          </Button>
        )}

        {/* PECUÁRIA */}
        {hasLivestock && canViewPecuaria && (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-indigo-500/60 hover:bg-indigo-500/[0.03] transition-all group"
          >
            <Link href="/dashboard/pecuaria">
              <div className="size-8 rounded-sm bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Beef className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <span className="block text-xs font-semibold text-foreground truncate">Rebanho</span>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                  Lotes e manejo
                </span>
              </div>
            </Link>
          </Button>
        )}

        {/* CONTINUAR DE ONDE PAROU (Última tela visitada com acesso direto) */}
        {lastRecent ? (
          <Button
            asChild
            variant="outline"
            className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-primary/60 hover:bg-primary/[0.03] transition-all group"
          >
            <Link href={lastRecent.href}>
              <div className="size-8 rounded-sm bg-muted text-foreground flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Clock3 className="size-4.5" />
              </div>
              <div className="w-full mt-2 min-w-0">
                <div className="flex items-center justify-between gap-1">
                  <span className="block text-xs font-semibold text-foreground truncate">Continuar</span>
                  <ArrowRight className="size-3 text-muted-foreground shrink-0" />
                </div>
                <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5" title={lastRecent.label}>
                  {lastRecent.label}
                </span>
              </div>
            </Link>
          </Button>
        ) : null}

        {/* COPILOTO IA */}
        <Button
          asChild
          variant="outline"
          className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-primary/30 bg-primary/[0.02] hover:border-primary/70 hover:bg-primary/[0.06] transition-all group"
        >
          <Link href="/dashboard/ia/resumo">
            <div className="size-8 rounded-sm bg-primary/10 text-primary flex items-center justify-center shrink-0 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
              <BrainCircuit className="size-4.5" />
            </div>
            <div className="w-full mt-2 min-w-0">
              <span className="block text-xs font-semibold text-primary truncate">Copiloto IA</span>
              <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                Análises da fazenda
              </span>
            </div>
          </Link>
        </Button>

        {/* APRENDIZADO / MANUAL */}
        <Button
          asChild
          variant="outline"
          className="h-auto min-h-[92px] p-3 flex flex-col items-start justify-between text-left rounded-sm border-border/70 hover:border-slate-500/60 hover:bg-slate-500/[0.03] transition-all group"
        >
          <Link href="/aprendizado">
            <div className="size-8 rounded-sm bg-slate-500/10 text-slate-600 dark:text-slate-400 flex items-center justify-center shrink-0 group-hover:bg-slate-600 group-hover:text-white transition-colors">
              <BookOpen className="size-4.5" />
            </div>
            <div className="w-full mt-2 min-w-0">
              <span className="block text-xs font-semibold text-foreground truncate">Manual</span>
              <span className="block text-[11px] text-muted-foreground line-clamp-1 leading-tight mt-0.5">
                Guia da plataforma
              </span>
            </div>
          </Link>
        </Button>
      </div>
    </div>
  );
}

