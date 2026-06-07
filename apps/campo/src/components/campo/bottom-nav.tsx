"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, House, RefreshCw, BookText, Sprout, Wheat, Scale, Syringe, type LucideIcon } from "lucide-react";
import { useSessionStore } from "@/lib/stores/session-store";
import { useSyncStore } from "@/lib/stores/sync-store";

function cn(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

type NavItem = {
  key: string;
  label: string;
  href: string;
  icon: LucideIcon;
};

const BASE_ITEMS: NavItem[] = [
  { key: "home", label: "Início", href: "/home", icon: House },
  { key: "sync", label: "Sincronizar", href: "/sync", icon: RefreshCw },
  { key: "caderno", label: "Caderno", href: "/caderno", icon: BookText },
];

function getQuickItems(modules: string[]): NavItem[] {
  const hasAgricola = modules.includes("agricola");
  const hasPecuaria = modules.includes("pecuaria");

  if (hasAgricola && hasPecuaria) {
    return [
      { key: "aplicacao", label: "Aplicação", href: "/campo/aplicacao", icon: Sprout },
      { key: "pesagem", label: "Pesagem", href: "/campo/pesagem", icon: Scale },
    ];
  }

  if (hasAgricola) {
    return [
      { key: "aplicacao", label: "Aplicação", href: "/campo/aplicacao", icon: Sprout },
      { key: "colheita", label: "Colheita", href: "/campo/colheita", icon: Wheat },
    ];
  }

  if (hasPecuaria) {
    return [
      { key: "pesagem", label: "Pesagem", href: "/campo/pesagem", icon: Scale },
      { key: "vacinacao", label: "Vacinação", href: "/campo/vacinacao", icon: Syringe },
    ];
  }

  return [];
}

export function CampoBottomNav() {
  const pathname = usePathname();
  const { session } = useSessionStore();
  const { isOnline, pendingCount, status } = useSyncStore();

  const shouldShow = pathname === "/home" || pathname === "/sync" || pathname === "/caderno";
  const quickItems = getQuickItems(session?.modules ?? []);
  const items = [...BASE_ITEMS, ...quickItems];
  const [isRendered, setIsRendered] = useState(shouldShow);
  const [hasScrolled, setHasScrolled] = useState(false);

  useEffect(() => {
    if (shouldShow) {
      setIsRendered(true);
      return;
    }

    const timer = window.setTimeout(() => setIsRendered(false), 180);
    return () => window.clearTimeout(timer);
  }, [shouldShow]);

  useEffect(() => {
    const update = () => setHasScrolled(window.scrollY > 12);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  if ((!isRendered && !shouldShow) || items.length === 0) {
    return null;
  }

  const handleTap = () => {
    if (typeof navigator !== "undefined" && "vibrate" in navigator) {
      navigator.vibrate(10);
    }
  };

  const syncMeta =
    status === "syncing"
      ? "Sync"
      : pendingCount > 0
      ? `${pendingCount}`
      : "";

  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 lg:hidden transition-all duration-200 ease-out",
        shouldShow ? "translate-y-0 opacity-100" : "translate-y-5 opacity-0"
      )}
    >
      <div className="w-full px-4">
        <div className="pointer-events-none relative">
          <Link
            href="/home#nova-atividade"
            onClick={handleTap}
            aria-label="Nova atividade manual"
            className={cn(
              "pointer-events-auto absolute left-1/2 top-0 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1 rounded-full border border-primary bg-primary px-3 py-2 text-primary-foreground shadow-md transition-all duration-200 ease-out active:scale-[0.96]",
              hasScrolled ? "-translate-y-[48%] scale-[1.02] shadow-lg" : ""
            )}
          >
            <Plus className="size-3.5" />
            <span className="text-[9px] font-semibold uppercase tracking-[0.12em]">Novo</span>
          </Link>
        </div>

        <nav
          aria-label="Navegação principal"
          className={cn(
            "animate-[campo-nav-in_240ms_cubic-bezier(0.16,1,0.3,1)] border-x border-t border-border/80 bg-card/95 p-1 pt-4 text-card-foreground shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/88 transition-shadow duration-200",
            hasScrolled ? "shadow-xl" : "shadow-lg"
          )}
          style={{ paddingBottom: "calc(0.2rem + env(safe-area-inset-bottom))" }}
        >
          <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
            {items.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              const Icon = item.icon;

              return (
                <Link
                  key={item.key}
                  href={item.href}
                  onClick={handleTap}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group flex min-h-[54px] flex-col items-center justify-center gap-0.5 rounded-sm border px-1 py-1 text-center transition-all duration-200 ease-out active:scale-[0.96]",
                    active
                      ? "translate-y-[-1px] border-primary/30 bg-accent text-accent-foreground shadow-sm"
                      : "border-transparent text-muted-foreground hover:border-border hover:bg-muted hover:text-foreground"
                  )}
                >
                  <span
                    className={cn(
                      "h-0.5 w-7 rounded-full transition-all duration-200",
                      active ? "bg-primary" : "bg-transparent"
                    )}
                  />
                  <Icon className={cn("size-4.5 transition-transform duration-200", active && "scale-105")} />
                  <span
                    className={cn(
                      "max-w-full truncate text-[10px] font-medium leading-none transition-colors duration-200",
                      active ? "text-accent-foreground" : "text-muted-foreground"
                    )}
                  >
                    {item.label}
                  </span>
                  {item.key === "sync" && (
                    syncMeta && (
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[0.12em]",
                          status === "syncing"
                            ? "bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-200"
                            : pendingCount > 0
                              ? "bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
                              : "bg-muted text-muted-foreground"
                        )}
                      >
                        <span
                          className={cn(
                            "size-1.5 rounded-full",
                            status === "syncing"
                              ? "animate-pulse bg-sky-200"
                              : pendingCount > 0
                                ? "bg-amber-500"
                                : "bg-muted-foreground"
                          )}
                        />
                        {syncMeta}
                      </span>
                    )
                  )}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
