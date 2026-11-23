"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { ChevronLeft, MapPin, Smartphone, Tablet, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  const locationLabel = localidade
    ? localidade.tipoOrigem === "GPS"
      ? "GPS Ativo"
      : `${localidade.nome}${localidade.uf ? `/${localidade.uf}` : ""}`
    : "";
  const locationClassName =
    "inline-flex items-center gap-1 px-2.5 py-1 md:px-2 rounded-full md:rounded-sm bg-primary/10 text-primary text-xs md:text-[11px] font-medium max-w-[125px] sm:max-w-[180px]";
  const locationContent = (
    <>
      <MapPin className="size-3 shrink-0" />
      <span className="truncate">{locationLabel}</span>
    </>
  );

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
              <Button
                asChild
                variant="ghost"
                size="icon-sm"
                className="md:hidden -ml-1 shrink-0"
              >
                <Link
                  href="/"
                  aria-label="Voltar para início"
                  title="Voltar para tela inicial"
                >
                  <ChevronLeft className="size-5 text-primary" />
                </Link>
              </Button>
            )}

            <Link
              href="/"
              className={cn(
                "flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm group min-w-0",
                isSubpage && "hidden md:flex"
              )}
              title="Ir para página inicial do DeepFarms Agro"
            >
              <div className="relative size-7 shrink-0 rounded-sm bg-primary/10 p-0.5">
                <Image
                  src="/logos/deepfarms-mark.svg"
                  alt="DeepFarms Agro"
                  width={28}
                  height={28}
                  priority
                  className="size-full object-contain"
                />
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5 leading-none">
                  <span className="font-bold tracking-tight text-foreground text-sm truncate">
                    DeepFarms
                  </span>
                  <Badge variant="default" className="text-[10px] px-1.5 py-0 font-bold">
                    Agro
                  </Badge>
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
                <div className="p-2 rounded-lg bg-primary/10 text-primary shrink-0">
                  <ActiveIcon className="size-4" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="font-bold tracking-tight text-foreground text-sm leading-tight truncate">
                    {activeNav.pageTitle}
                  </span>
                  <span className="text-[11px] text-muted-foreground leading-tight truncate">
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
                <Button
                  key={item.href}
                  asChild
                  variant={isActive ? "default" : "ghost"}
                  size="sm"
                >
                  <Link href={item.href}>
                    <Icon className="size-3.5" />
                    <span>{item.label}</span>
                  </Link>
                </Button>
              );
            })}
          </nav>

          {/* Controles Direitos: Localidade Ativa, Indicador de Dispositivo, Conta e Tema */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* Atalho rápido de município ativo na App Bar (oculto em /clima no mobile para evitar duplicação) */}
            {isLoaded && localidade &&
              (pathname === "/clima" ? (
                <span
                  title="Localidade selecionada"
                  aria-label={`Localidade selecionada: ${locationLabel}`}
                  className={cn(locationClassName, "hidden md:inline-flex")}
                >
                  {locationContent}
                </span>
              ) : (
                <Link
                  href="/clima"
                  title="Ver clima da localidade selecionada"
                  className={cn(locationClassName, "hover:bg-primary/15 transition-colors")}
                >
                  {locationContent}
                </Link>
              ))}

            {/* Indicador Adaptativo de Ambiente (Mobile / Tablet / Standalone) */}
            <Badge
              variant="outline"
              data-testid="header-device-badge"
              className="hidden sm:inline-flex"
            >
              {deviceCategory === "mobile" ? (
                <Smartphone className="size-3 text-primary" />
              ) : deviceCategory === "tablet" ? (
                <Tablet className="size-3 text-primary" />
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

            {/* Botão rápido de Minha Conta no Header (Tablet/Desktop; no mobile usa a BottomNav) */}
            <Button
              asChild
              variant={pathname.startsWith("/conta") ? "default" : "outline"}
              size="sm"
              className="hidden md:inline-flex"
            >
              <Link
                href="/conta"
                aria-label="Minha Conta"
                title="Minha Conta Individual"
              >
                <User className="size-3.5" />
                <span className="hidden sm:inline">Minha Conta</span>
              </Link>
            </Button>

            <ThemeToggle />
          </div>
        </div>
      </header>
    </>
  );
}
