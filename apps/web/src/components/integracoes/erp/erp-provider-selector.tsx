"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, ChevronRight, Loader2, Target } from "lucide-react";
import Image from "next/image";

import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ERP_PROVIDER_CONSOLES } from "./erp-provider-registry";

interface MarketplaceErp {
  id: number;
  nome: string;
  slug: string;
  descricao: string | null;
  logo_url: string | null;
}

export function getSupportedErpProviders(erps: MarketplaceErp[]): MarketplaceErp[] {
  const supportedSlugs = new Set(Object.keys(ERP_PROVIDER_CONSOLES));
  const listedSlugs = new Set<string>();

  return erps.filter((erp) => {
    if (!supportedSlugs.has(erp.slug) || listedSlugs.has(erp.slug)) {
      return false;
    }
    listedSlugs.add(erp.slug);
    return true;
  });
}

interface ErpProviderSelectorProps {
  onSelect: (slug: string) => void;
  onSkip?: () => void;
  showSkipOption?: boolean;
}

export function ErpProviderSelector({
  onSelect,
  onSkip,
  showSkipOption = false,
}: ErpProviderSelectorProps) {
  const { data: erps, isLoading, error, refetch } = useQuery({
    queryKey: ["marketplace-erps"],
    queryFn: () => apiFetch<MarketplaceErp[]>("/integracoes/marketplace/erps?ativa=true"),
  });
  const supportedErps = getSupportedErpProviders(erps || []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-full rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card variant="destructive">
        <CardHeader>
          <CardTitle>Erro ao carregar provedores</CardTitle>
          <CardDescription>
            Não foi possível carregar a lista de ERPs disponíveis. Tente novamente mais tarde.
          </CardDescription>
        </CardHeader>
        {(showSkipOption || onSkip) && (
          <CardContent className="flex gap-3 pt-0">
            <Button variant="outline" size="sm" onClick={() => void refetch()}>
              Tentar novamente
            </Button>
            <Button variant="secondary" size="sm" onClick={() => onSkip?.()}>
              Configurar depois
            </Button>
          </CardContent>
        )}
      </Card>
    );
  }

  if (supportedErps.length === 0) {
    return (
      <Card className="border-dashed">
        <CardHeader className="text-center">
          <CardTitle>Nenhum ERP disponível</CardTitle>
          <CardDescription>
            No momento não há integrações de ERP ativas no catálogo.
          </CardDescription>
        </CardHeader>
        {(showSkipOption || onSkip) && (
          <CardContent className="flex justify-center pt-0">
            <Button variant="secondary" size="sm" onClick={() => onSkip?.()}>
              Configurar depois
            </Button>
          </CardContent>
        )}
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Escolha o ERP que deseja configurar</h2>
        <p className="text-muted-foreground mt-1">
          Selecione o sistema de gestão que sua empresa utiliza para iniciar a configuração da integração.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {supportedErps.map((erp) => {
          const isSupported = erp.slug in ERP_PROVIDER_CONSOLES;

          return (
            <Card key={erp.slug} className="flex flex-col hover:border-primary/50 transition-colors">
              <CardHeader className="flex-1">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted/50 p-2">
                  {erp.logo_url ? (
                    <Image
                      src={erp.logo_url}
                      alt={`Logo ${erp.nome}`}
                      width={48}
                      height={48}
                      className="object-contain"
                    />
                  ) : (
                    <Target className="h-6 w-6 text-muted-foreground" />
                  )}
                </div>
                <CardTitle className="text-lg">{erp.nome}</CardTitle>
                <CardDescription className="line-clamp-2">
                  {erp.descricao || "Integração oficial de ERP."}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0 mt-auto">
                <Button
                  className="w-full justify-between"
                  variant={isSupported ? "outline" : "secondary"}
                  onClick={() => onSelect(erp.slug)}
                >
                  {isSupported ? "Configurar integração" : "Selecionar ERP"}
                  <ChevronRight className="h-4 w-4 opacity-50" />
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {showSkipOption ? (
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" onClick={() => onSkip?.()}>
            Configurar depois
          </Button>
        </div>
      ) : null}
    </div>
  );
}
