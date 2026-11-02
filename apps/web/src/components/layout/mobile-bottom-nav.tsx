"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Beef,
  BookOpen,
  Building2,
  ClipboardList,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Package,
  Sprout,
  Wallet,
} from "lucide-react";
import { useSidebar } from "@/components/ui/sidebar";
import { useModules } from "@/hooks/use-has-module";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";
import type { ModuleId } from "@/types/global";

interface MobileDockItem {
  key: string;
  href: string;
  label: string;
  icon: React.ElementType;
  matchPrefixes: string[];
  exact?: boolean;
}

const AGRICULTURE_MODULES: ModuleId[] = [
  "A1_PLANEJAMENTO",
  "A2_CAMPO",
  "A3_DEFENSIVOS",
  "A4_PRECISAO",
  "A5_COLHEITA",
];
const LIVESTOCK_MODULES: ModuleId[] = [
  "P1_REBANHO",
  "P2_GENETICA",
  "P3_CONFINAMENTO",
  "P4_LEITE",
];
const FINANCE_MODULES: ModuleId[] = [
  "F1_TESOURARIA",
  "F2_CUSTOS_ABC",
  "F3_FISCAL",
  "F4_HEDGING",
];

/**
 * Resolve os 4 atalhos primários da barra inferior mobile conforme módulos contratados.
 *
 * Args:
 *   activeModules: Lista de identificadores de módulos ativos no tenant.
 *   isBackofficeOnly: Indica se o usuário está em visão exclusiva de administração SaaS.
 *
 * Return:
 *   Lista ordenada de 4 itens de navegação para a dock inferior.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function resolveMobileDockItems(
  activeModules: ModuleId[],
  isBackofficeOnly: boolean
): MobileDockItem[] {
  if (isBackofficeOnly) {
    return [
      {
        key: "bo-dashboard",
        href: "/dashboard/backoffice/dashboard",
        label: "Painel",
        icon: LayoutDashboard,
        matchPrefixes: ["/dashboard/backoffice/dashboard", "/dashboard"],
        exact: true,
      },
      {
        key: "bo-tenants",
        href: "/dashboard/backoffice/tenants",
        label: "Clientes",
        icon: Building2,
        matchPrefixes: ["/dashboard/backoffice/tenants"],
      },
      {
        key: "bo-plans",
        href: "/dashboard/backoffice/plans",
        label: "Planos",
        icon: Wallet,
        matchPrefixes: ["/dashboard/backoffice/plans"],
      },
      {
        key: "bo-manual",
        href: "/manual",
        label: "Manual",
        icon: BookOpen,
        matchPrefixes: ["/manual"],
      },
    ];
  }

  const hasAgro = activeModules.some((m) => AGRICULTURE_MODULES.includes(m));
  const hasPecuaria = activeModules.some((m) => LIVESTOCK_MODULES.includes(m));
  const hasFinanceiro = activeModules.some((m) => FINANCE_MODULES.includes(m));

  const primaryDomainItem: MobileDockItem = hasAgro
    ? {
        key: "agricola",
        href: "/agricola/safras",
        label: "Agrícola",
        icon: Sprout,
        matchPrefixes: ["/agricola", "/dashboard/agricola"],
      }
    : hasPecuaria
    ? {
        key: "pecuaria",
        href: "/dashboard/pecuaria",
        label: "Pecuária",
        icon: Beef,
        matchPrefixes: ["/dashboard/pecuaria"],
      }
    : {
        key: "cadastros",
        href: "/cadastros",
        label: "Cadastros",
        icon: FolderKanban,
        matchPrefixes: ["/cadastros"],
      };

  const fourthItem: MobileDockItem = hasFinanceiro
    ? {
        key: "financeiro",
        href: "/dashboard/financeiro",
        label: "Financeiro",
        icon: Wallet,
        matchPrefixes: ["/dashboard/financeiro"],
      }
    : {
        key: "estoque",
        href: "/suprimentos/estoque",
        label: "Estoque",
        icon: Package,
        matchPrefixes: ["/suprimentos"],
      };

  return [
    {
      key: "inicio",
      href: "/dashboard",
      label: "Início",
      icon: LayoutDashboard,
      matchPrefixes: ["/dashboard"],
      exact: true,
    },
    primaryDomainItem,
    {
      key: "operacoes",
      href: "/dashboard/operacional/campo/tarefas",
      label: "Operações",
      icon: ClipboardList,
      matchPrefixes: ["/dashboard/operacional", "/operacional"],
    },
    fourthItem,
  ];
}

/**
 * Verifica se um item da dock inferior corresponde à rota atual.
 *
 * Args:
 *   item: Item configurado da dock inferior.
 *   pathname: Caminho de rota atual.
 *
 * Return:
 *   Verdadeiro quando o item deve ser destacado como ativo.
 *
 * Raises:
 *   Nenhuma exceção é lançada.
 */
function isDockItemActive(item: MobileDockItem, pathname: string): boolean {
  if (item.exact) {
    return item.matchPrefixes.includes(pathname);
  }
  return item.matchPrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}

export function MobileBottomNav(): React.ReactElement {
  const pathname = usePathname();
  const { executionMode } = useDeviceContext();
  const { openMobile, setOpenMobile } = useSidebar();
  const tenant = useAppStore((state) => state.tenant);
  const user = useAppStore((state) => state.user);
  const activeModules = useModules();

  const isBackofficeOnly = Boolean(user?.is_superuser && !tenant);
  const dockItems = React.useMemo(
    () => resolveMobileDockItems(activeModules, isBackofficeOnly),
    [activeModules, isBackofficeOnly]
  );

  return (
    <nav
      className={cn(
        "md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/80 bg-card/95 backdrop-blur-lg supports-[backdrop-filter]:bg-card/85 shadow-[0_-2px_12px_rgba(0,0,0,0.06)] safe-area-pb select-none",
        executionMode === "standalone" && "pb-1"
      )}
      aria-label="Navegação móvel"
      data-testid="mobile-bottom-dock"
    >
      <div className="grid grid-cols-5 items-center h-16 max-w-lg mx-auto px-1">
        {dockItems.map((item) => {
          const Icon = item.icon;
          const isActive = !openMobile && isDockItemActive(item, pathname);

          return (
            <Link
              key={item.key}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex flex-col items-center justify-center h-full min-h-[48px] rounded-sm transition-all text-[11px] font-medium active:scale-95",
                isActive
                  ? "text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {isActive && (
                <span
                  className="absolute top-0 left-1/2 -translate-x-1/2 w-7 h-0.5 rounded-full bg-primary"
                  aria-hidden="true"
                />
              )}

              <div
                className={cn(
                  "px-3 py-1 rounded-full transition-colors flex items-center justify-center",
                  isActive ? "bg-primary/15 text-primary" : "text-current"
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span className="leading-tight mt-0.5 truncate max-w-[68px]">
                {item.label}
              </span>
            </Link>
          );
        })}

        {/* Botão de Módulos (abre a gaveta de navegação completa no mobile) */}
        <button
          type="button"
          onClick={() => setOpenMobile(true)}
          aria-expanded={openMobile}
          aria-label="Abrir todos os módulos"
          className={cn(
            "relative flex flex-col items-center justify-center h-full min-h-[48px] rounded-sm transition-all text-[11px] font-medium active:scale-95 cursor-pointer",
            openMobile
              ? "text-primary font-semibold"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {openMobile && (
            <span
              className="absolute top-0 left-1/2 -translate-x-1/2 w-7 h-0.5 rounded-full bg-primary"
              aria-hidden="true"
            />
          )}
          <div
            className={cn(
              "px-3 py-1 rounded-full transition-colors flex items-center justify-center",
              openMobile ? "bg-primary/15 text-primary" : "text-current"
            )}
          >
            <Menu className="w-4 h-4" />
          </div>
          <span className="leading-tight mt-0.5 truncate max-w-[68px]">
            Módulos
          </span>
        </button>
      </div>
    </nav>
  );
}

