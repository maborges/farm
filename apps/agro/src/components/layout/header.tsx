"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { ChevronLeft, MapPin, Smartphone, Tablet, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useLocalidadeClima } from "@/lib/clima/localidade-store";
import { useDeviceContext } from "@/lib/device/use-device-context";
import { cn } from "@/lib/utils";
import { AgroBannerAvisos } from "./agro-banner-avisos";
import { ConnectionStatus } from "./connection-status";
import { AGRO_NAV_ITEMS, getActiveNavItem } from "./nav-items";
import { ThemeToggle } from "./theme-toggle";

export function Header(): React.ReactElement {
  const pathname = usePathname();
  const { deviceCategory, executionMode } = useDeviceContext();
  const { localidade, isLoaded } = useLocalidadeClima();

  const activeNav = getActiveNavItem(pathname);
  const ActiveIcon = activeNav.icon;
  const isSubpage = pathname !== "/";
  const topNavItems = AGRO_NAV_ITEMS.filter((item) => item.showInTopNav);

  return (
    <>
      <ConnectionStatus />
      <AgroBannerAvisos />
      <header
        data-testid="agro-app-header"
        data-device={deviceCategory}
        className="sticky top-0 z-40 w-full border-b border-border/80 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/85 safe-area-pt select-none"
      >
        <div className="max-w-7xl mx-auto px-3 sm:px-6 h-14 flex items-center justify-between gap-2 sm:gap-4">
          {/* Bloco Esquerdo: Identidade ou App Bar Contextual no Mobile */}
          <div className="flex items-center gap-2 min-w-0">
            {isSubpage && (
              <Link
                href="/"
                aria-label="Voltar para início"
                title="Voltar para tela inicial"
                className="md:hidden inline-flex items-center justify-center w-9 h-9 -ml-1 rounded-sm text-foreground hover:bg-muted active:scale-95 transition-all shrink-0"
              >
                <ChevronLeft className="w-5 h-5 text-primary" />
              </Link>
            )}

            <Link
              href="/"
              className={cn(
                "flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm group min-w-0",
                isSubpage && "hidden md:flex"
              )}
              title="Ir para página inicial do DeepFarms Agro"
            >
              <div className="relative w-7 h-7 flex-shrink-0 rounded-sm bg-primary/10 p-0.5">
                <Image
                  src="/logos/deepfarms-mark.svg"
                  alt="DeepFarms Agro"
                  width={28}
                  height={28}
                  priority
                  className="w-full h-full object-contain"
                />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5 leading-none">
                  <span className="font-bold tracking-tight text-foreground text-sm truncate">
                    DeepFarms
                  </span>
                  <span className="text-primary font-bold text-xs px-1.5 py-0.5 rounded-sm bg-primary/10">
                    Agro
                  </span>
                </div>
                <span className="text-[10px] text-muted-foreground hidden sm:inline truncate">
                  {executionMode === "standalone"
                    ? "Aplicativo de Campo (PWA)"
                    : "Ferramentas do Produtor"}
                </span>
              </div>
            </Link>

            {/* Título Contextual de App Nativo quando em subpágina no Mobile */}
            {isSubpage && (
              <div className="flex md:hidden items-center gap-2 min-w-0">
                <div className="p-1.5 rounded-sm bg-primary/10 text-primary shrink-0">
                  <ActiveIcon className="w-4 h-4" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-bold tracking-tight text-foreground text-sm leading-tight truncate">
                    {activeNav.pageTitle}
                  </span>
                  <span className="text-[10px] text-muted-foreground leading-tight truncate">
                    {activeNav.pageSubtitle}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Navegação Horizontal para Tablet/Desktop */}
          <nav
            className="hidden lg:flex items-center gap-1"
            aria-label="Navegação principal"
          >
            {topNavItems.map((item) => {
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

          {/* Controles Direitos: Localidade Ativa, Indicador de Dispositivo, Conta e Tema */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* Atalho rápido de município ativo na App Bar */}
            {isLoaded && localidade && pathname !== "/clima" && (
              <Link
                href="/clima"
                title="Ver clima da localidade selecionada"
                className="inline-flex items-center gap-1 px-2 py-1 rounded-sm bg-primary/10 text-primary hover:bg-primary/15 text-[11px] font-medium transition-colors max-w-[130px] sm:max-w-[180px]"
              >
                <MapPin className="w-3 h-3 shrink-0" />
                <span className="truncate">
                  {localidade.tipoOrigem === "GPS"
                    ? "GPS Ativo"
                    : `${localidade.nome}${localidade.uf ? `/${localidade.uf}` : ""}`}
                </span>
              </Link>
            )}

            {/* Indicador Adaptativo de Ambiente (Mobile / Tablet / Standalone) */}
            <Badge
              variant="outline"
              data-testid="header-device-badge"
              className="hidden sm:inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-sm border-primary/25 text-muted-foreground"
            >
              {deviceCategory === "mobile" ? (
                <Smartphone className="w-3 h-3 text-primary" />
              ) : deviceCategory === "tablet" ? (
                <Tablet className="w-3 h-3 text-primary" />
              ) : null}
              <span>
                {executionMode === "standalone"
                  ? "PWA"
                  : deviceCategory === "mobile"
                  ? "Mobile"
                  : deviceCategory === "tablet"
                  ? "Tablet"
                  : "Web"}
              </span>
            </Badge>

            {/* Botão rápido de Minha Conta no Header (acessível em qualquer viewport) */}
            <Link
              href="/conta"
              aria-label="Minha Conta"
              title="Minha Conta Individual"
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm text-xs font-medium border transition-colors min-h-[34px]",
                pathname.startsWith("/conta")
                  ? "border-primary bg-primary/10 text-primary font-semibold"
                  : "border-border bg-background hover:bg-accent text-foreground"
              )}
            >
              <User className="w-3.5 h-3.5 text-primary" />
              <span className="hidden sm:inline">Minha Conta</span>
            </Link>

            <ThemeToggle />
          </div>
        </div>
      </header>
    </>
  );
}
