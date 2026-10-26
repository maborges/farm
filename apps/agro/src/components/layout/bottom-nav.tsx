"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CloudSun, TrendingUp, Calculator, Home } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Início", icon: Home },
  { href: "/clima", label: "Clima", icon: CloudSun },
  { href: "/mercado", label: "Mercado", icon: TrendingUp },
  { href: "/calculadoras", label: "Calculadoras", icon: Calculator },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/85 safe-area-pb"
      aria-label="Navegação móvel"
    >
      <div className="flex items-center justify-around h-14 max-w-lg mx-auto px-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center flex-1 py-1 min-h-[44px] rounded-sm transition-all text-[11px] font-medium active:scale-95",
                isActive
                  ? "text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <div
                className={cn(
                  "p-1 rounded-sm transition-colors",
                  isActive && "bg-primary/10 text-primary"
                )}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span className="leading-tight mt-0.5">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
