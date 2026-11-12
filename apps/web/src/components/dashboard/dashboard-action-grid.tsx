"use client";

import { useEffect, useState } from "react";
import {
  Beef,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Clock3,
  Package,
  Sprout,
  Wallet,
} from "lucide-react";
import { QuickActionGrid, type QuickActionItem } from "@/components/ui/quick-action-grid";
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

  const actions: QuickActionItem[] = [];

  if (hasAgriculture && canViewSafras) {
    actions.push({
      title: "Safras",
      description: "Painéis e ciclos produtivos",
      icon: Sprout,
      href: "/agricola/safras",
    });
  }

  if (canViewTarefas) {
    actions.push({
      title: "Tarefas",
      description: "Operações e apontamentos de campo",
      icon: ClipboardList,
      href: "/dashboard/operacional/campo/tarefas",
    });
  }

  if (canViewEstoque) {
    actions.push({
      title: "Estoque",
      description: "Insumos, posições e saldos",
      icon: Package,
      href: "/suprimentos/estoque",
    });
  }

  if (hasFinance && canViewFinanceiro) {
    actions.push({
      title: "Financeiro",
      description: "Fluxo de caixa, conciliação e DRE",
      icon: Wallet,
      href: "/dashboard/financeiro",
    });
  }

  if (hasLivestock && canViewPecuaria) {
    actions.push({
      title: "Rebanho",
      description: "Lotes, piquetes e manejo zootécnico",
      icon: Beef,
      href: "/dashboard/pecuaria",
    });
  }

  if (lastRecent) {
    actions.push({
      title: "Continuar",
      description: `Retomar: ${lastRecent.label}`,
      icon: Clock3,
      href: lastRecent.href,
    });
  }

  actions.push({
    title: "Copiloto IA",
    description: "Análises preditivas e resumo inteligente",
    icon: BrainCircuit,
    href: "/dashboard/ia/resumo",
  });

  actions.push({
    title: "Manual",
    description: "Guia da plataforma e documentação operacional",
    icon: BookOpen,
    href: "/aprendizado",
  });

  return (
    <QuickActionGrid
      label="Ações & Atalhos Operacionais"
      columnsClassName="grid-cols-2 sm:grid-cols-4 lg:grid-cols-8"
      actions={actions}
    />
  );
}
