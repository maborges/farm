"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { CloudSun, TrendingUp, Calculator, Home } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { ConnectionStatus } from "./connection-status";
import { AgroBannerAvisos } from "./agro-banner-avisos";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Início", icon: Home },
  { href: "/clima", label: "Clima", icon: CloudSun },
  { href: "/mercado", label: "Mercado", icon: TrendingUp },
  { href: "/calculadoras", label: "Calculadoras", icon: Calculator },
];

export function Header() {
  const pathname = usePathname();

  return (
    <>
      <ConnectionStatus />
      <AgroBannerAvisos />
      <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/80">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Logo & Marca Oficial */}
          <Link
            href="/"
            className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm group"
            title="Ir para página inicial do DeepFarms Agro"
          >
            <div className="relative w-7 h-7 flex-shrink-0">
              <Image
                src="/logos/deepfarms-mark.svg"
                alt="DeepFarms Agro"
                width={28}
                height={28}
                priority
                className="w-full h-full object-contain"
              />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5 leading-none">
                <span className="font-bold tracking-tight text-foreground text-sm">
                  DeepFarms
                </span>
                <span className="text-primary font-bold text-xs px-1.5 py-0.5 rounded-sm bg-primary/10">
                  Agro
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground hidden sm:inline">
                Ferramentas do Produtor
              </span>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Navegação principal">
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
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground font-semibold"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Controls: Theme Toggle */}
          <div className="flex items-center gap-2">
            <ThemeToggle />
          </div>
        </div>
      </header>
    </>
  );
}

