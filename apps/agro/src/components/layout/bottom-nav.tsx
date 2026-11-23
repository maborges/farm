"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { cn } from "@/lib/utils";
import { AGRO_NAV_ITEMS } from "./nav-items";

const DOCK_ITEMS = AGRO_NAV_ITEMS.filter((item) => item.showInBottomDock);

export function BottomNav(): React.ReactElement {
  const pathname = usePathname();
  const { executionMode } = useDeviceContext();

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
        {DOCK_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              aria-label={item.label}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "relative flex flex-col items-center justify-center h-full min-h-[48px] rounded-lg transition-all text-[11px] font-medium active:scale-95",
                isActive
                  ? "text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {/* Indicador de aba ativa superior */}
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
                {item.shortLabel}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
