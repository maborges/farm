"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus, House, RefreshCw, Sprout, Wheat, Scale, Syringe, type LucideIcon } from "lucide-react";
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

  const shouldShow = pathname === "/home" || pathname === "/sync";
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
      ? "Sincronizando"
      : !isOnline
      ? "Sem conexão"
      : pendingCount > 0
      ? `${pendingCount} pendentes`
      : "Pronto";

  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-40 lg:hidden transition-all duration-200 ease-out",
        shouldShow ? "translate-y-0 opacity-100" : "translate-y-5 opacity-0"
      )}
    >
      <div className="mx-auto max-w-[720px] px-4 pb-3">
        <div className="pointer-events-none relative">
          <Link
            href="/home#nova-atividade"
            onClick={handleTap}
            aria-label="Nova atividade manual"
            className={cn(
              "pointer-events-auto absolute left-1/2 top-0 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1 rounded-full border border-emerald-300/25 bg-gradient-to-b from-emerald-400 via-emerald-300 to-lime-200 px-5 py-3 text-emerald-950 shadow-[0_16px_32px_rgba(16,185,129,0.24)] transition-all duration-200 ease-out active:scale-[0.96]",
              hasScrolled ? "-translate-y-[54%] scale-[1.03] shadow-[0_18px_38px_rgba(16,185,129,0.28)]" : ""
            )}
          >
            <Plus className="size-5" />
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em]">Novo</span>
          </Link>
        </div>

        <nav
          aria-label="Navegação principal"
          className={cn(
            "animate-[campo-nav-in_240ms_cubic-bezier(0.16,1,0.3,1)] rounded-[28px] border border-white/10 bg-[#07110e]/95 p-2 pt-6 backdrop-blur-xl transition-shadow duration-200",
            hasScrolled
              ? "shadow-[0_-24px_54px_rgba(0,0,0,0.38)]"
              : "shadow-[0_-18px_40px_rgba(0,0,0,0.3)]"
          )}
          style={{ paddingBottom: "calc(0.5rem + env(safe-area-inset-bottom))" }}
        >
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
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
                    "group flex min-h-[68px] flex-col items-center justify-center gap-1 rounded-[22px] border px-2 py-2 text-center transition-all duration-200 ease-out active:scale-[0.96]",
                    active
                      ? "border-emerald-300/30 bg-gradient-to-b from-emerald-400/18 to-emerald-400/8 text-emerald-50 shadow-[0_10px_24px_rgba(16,185,129,0.16)] translate-y-[-1px]"
                      : "border-transparent text-white/62 hover:border-white/10 hover:bg-white/[0.05] hover:text-white"
                  )}
                >
                  <span
                    className={cn(
                      "h-1 w-8 rounded-full transition-all duration-200",
                      active ? "bg-emerald-300/90 shadow-[0_0_0_1px_rgba(52,211,153,0.25)]" : "bg-transparent"
                    )}
                  />
                  <Icon className={cn("size-5 transition-transform duration-200", active && "scale-105")} />
                  <span
                    className={cn(
                      "max-w-full truncate text-[11px] font-medium leading-none transition-colors duration-200",
                      active ? "text-emerald-50" : "text-white/62"
                    )}
                  >
                    {item.label}
                  </span>
                  {item.key === "sync" && (
                    <span
                      className={cn(
                        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]",
                        status === "syncing"
                          ? "bg-sky-400/18 text-sky-50 shadow-[0_0_0_1px_rgba(125,211,252,0.12)]"
                          : !isOnline
                          ? "bg-white/8 text-white/55"
                          : pendingCount > 0
                          ? "bg-amber-400/15 text-amber-100"
                          : "bg-emerald-400/12 text-emerald-100"
                      )}
                    >
                      <span
                        className={cn(
                          "size-1.5 rounded-full",
                          status === "syncing"
                            ? "animate-pulse bg-sky-200"
                            : !isOnline
                            ? "bg-white/40"
                            : pendingCount > 0
                            ? "bg-amber-300"
                            : "bg-emerald-300"
                        )}
                      />
                      {syncMeta}
                    </span>
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
