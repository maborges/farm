"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ClipboardCheck, MapPinned, PackagePlus, Plus, Sprout, Wallet } from "lucide-react";

import { useModules } from "@/hooks/use-has-module";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type QuickAddAction = {
  label: string;
  description: string;
  href: string;
  icon: typeof MapPinned;
  enabled: boolean;
};

const AGRICULTURE_MODULES = ["A1_PLANEJAMENTO", "A2_CAMPO", "A3_DEFENSIVOS", "A4_PRECISAO", "A5_COLHEITA"];
const FINANCE_MODULES = ["F1_TESOURARIA", "F2_CUSTOS_ABC", "F3_FISCAL", "F4_HEDGING"];

export function QuickAddMenu() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const activeModules = useModules();
  const hasAgriculture = activeModules.some((moduleId) => AGRICULTURE_MODULES.includes(moduleId));
  const hasFinance = activeModules.some((moduleId) => FINANCE_MODULES.includes(moduleId));

  const actions: QuickAddAction[] = [
    {
      label: "Nova propriedade",
      description: "Cadastre uma unidade produtiva",
      href: "/cadastros/propriedades",
      icon: MapPinned,
      enabled: true,
    },
    {
      label: "Nova safra",
      description: "Inicie um novo planejamento agrícola",
      href: "/agricola/safras",
      icon: Sprout,
      enabled: hasAgriculture,
    },
    {
      label: "Nova tarefa",
      description: "Registre uma atividade operacional",
      href: "/dashboard/operacional/campo/tarefas",
      icon: ClipboardCheck,
      enabled: true,
    },
    {
      label: "Novo produto",
      description: "Adicione um item ao catálogo",
      href: "/cadastros/produtos",
      icon: PackagePlus,
      enabled: true,
    },
    {
      label: "Novo lançamento",
      description: "Registre uma receita ou despesa",
      href: "/dashboard/financeiro/lancamentos",
      icon: Wallet,
      enabled: hasFinance,
    },
  ].filter((action) => action.enabled);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, [contenteditable='true']")) return;
      if (event.altKey && event.shiftKey && event.key.toLowerCase() === "a") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    };

    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 border-primary/30 bg-primary/10 text-primary hover:border-primary/50 hover:bg-primary/15 hover:text-primary"
          aria-label="Adicionar novo registro"
        >
          <Plus className="size-4" aria-hidden="true" />
          <span className="hidden md:inline">Adicionar</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" sideOffset={8} className="w-72">
        <DropdownMenuLabel className="px-3 py-2">
          <span className="block text-sm">Adicionar rapidamente</span>
          <span className="mt-1 block text-xs font-normal text-muted-foreground">
            Acesse os cadastros mais usados.
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <DropdownMenuItem
              key={action.href}
              className="gap-3 px-3 py-2.5"
              onClick={() => {
                setOpen(false);
                router.push(action.href);
              }}
            >
              <Icon className="size-4 shrink-0 text-primary" aria-hidden="true" />
              <span className="min-w-0 text-left">
                <span className="block text-sm font-medium">{action.label}</span>
                <span className="block truncate text-xs text-muted-foreground">{action.description}</span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
