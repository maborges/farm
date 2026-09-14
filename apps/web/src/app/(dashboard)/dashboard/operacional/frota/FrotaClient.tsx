"use client";

import { useQuery } from "@tanstack/react-query";
import { ShieldAlert, Tractor } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { useAppStore } from "@/lib/stores/app-store";

import { FrotaToolbar } from "./_components/FrotaToolbar";
import { FrotaEmptyState } from "./_components/FrotaEmptyState";
import { FrotaResumoCards } from "./_components/FrotaResumoCards";
import { FrotaEquipamentosTable } from "./_components/FrotaEquipamentosTable";
import { FrotaManutencoesPanel } from "./_components/FrotaManutencoesPanel";
import { FrotaAlertasPanel } from "./_components/FrotaAlertasPanel";
import { FrotaConsumoAlertas, FrotaEficienciaRanking } from "./_components/FrotaConsumoPanel";
import { FrotaDisponibilidadeKPICards, FrotaDisponibilidadePanel } from "./_components/FrotaDisponibilidadePanel";
import { FrotaCustosKPICards, FrotaCustosPanel } from "./_components/FrotaCustosPanel";
import { FrotaInteligenciaPanel } from "./_components/FrotaInteligenciaPanel";
import { FrotaUsoAgricolaPanel } from "./_components/FrotaUsoAgricolaPanel";
import { FrotaTabs } from "./_components/FrotaTabs";
import {
  FrotaDashboard,
  FrotaConsumoDashboard,
  FrotaDisponibilidadeDashboard,
  FrotaCustoDashboard,
  FrotaInteligenciaDashboard,
  FrotaAgriculturaDashboard,
} from "./_components/types";

interface FrotaClientProps {
  initialData: FrotaDashboard | null;
  serverFazendaId: string;
}

export function FrotaClient({ initialData, serverFazendaId }: FrotaClientProps) {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const hasEnterpriseTier = useHasTier("ENTERPRISE");

  const isServerDataMatching =
    (!activeFazendaId && !serverFazendaId) ||
    (activeFazendaId === serverFazendaId);

  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery<FrotaDashboard>({
    queryKey: ["frota", "dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/dashboard", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    initialData: isServerDataMatching ? (initialData ?? undefined) : undefined,
  });

  const { data: consumoData } = useQuery<FrotaConsumoDashboard>({
    queryKey: ["frota", "consumo-dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/consumo", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const { data: disponibilidadeData } = useQuery<FrotaDisponibilidadeDashboard>({
    queryKey: ["frota", "disponibilidade-dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/disponibilidade", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const { data: custosData } = useQuery<FrotaCustoDashboard>({
    queryKey: ["frota", "custos-dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/custos", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const { data: inteligenciaData } = useQuery<FrotaInteligenciaDashboard>({
    queryKey: ["frota", "inteligencia-dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/inteligencia", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasEnterpriseTier,
  });

  const { data: agriculturaData } = useQuery<FrotaAgriculturaDashboard>({
    queryKey: ["frota", "agricultura-dashboard", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/agricultura/resumo", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasEnterpriseTier,
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Painel Executivo da Frota"
        description="Visão consolidada de custos, ordens de serviço, manutenção, abastecimento e risco operacional."
        icon={<Tractor className="text-primary" size={22} />}
        breadcrumbs={[{ label: "Operacional", href: "/operacional" }, { label: "Frota" }]}
        actions={
          <FrotaToolbar
            hasProfessionalTier={hasProfessionalTier}
            hasEnterpriseTier={hasEnterpriseTier}
          />
        }
      />

      <FrotaTabs />

      {isLoading ? <DashboardSkeleton /> : null}

      {!isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar o painel da frota"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {!isLoading && !isError && data ? (
        <>
          <FrotaResumoCards resumo={data.resumo} />

          <FrotaDisponibilidadeKPICards
            disponibilidadeData={disponibilidadeData}
            hasProfessionalTier={hasProfessionalTier}
          />

          <FrotaCustosKPICards
            custosData={custosData}
            hasProfessionalTier={hasProfessionalTier}
          />

          {data.resumo.total_equipamentos === 0 ? (
            <FrotaEmptyState />
          ) : (
            <>
              <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
                <FrotaEquipamentosTable equipamentos={data.equipamentos} />

                <FrotaManutencoesPanel
                  rankingMaiorCusto={data.ranking_maior_custo}
                  ultimosAbastecimentos={data.ultimos_abastecimentos}
                  ultimasJornadas={data.ultimas_jornadas}
                />
              </div>

              <FrotaAlertasPanel alertas={data.alertas_operacionais} />

              <FrotaConsumoAlertas
                consumoData={consumoData}
                hasProfessionalTier={hasProfessionalTier}
              />

              <FrotaDisponibilidadePanel
                disponibilidadeData={disponibilidadeData}
                hasProfessionalTier={hasProfessionalTier}
              />

              <FrotaCustosPanel
                custosData={custosData}
                resumo={data.resumo}
                hasProfessionalTier={hasProfessionalTier}
              />

              <FrotaInteligenciaPanel
                inteligenciaData={inteligenciaData}
                hasEnterpriseTier={hasEnterpriseTier}
              />

              <FrotaEficienciaRanking
                consumoData={consumoData}
                hasProfessionalTier={hasProfessionalTier}
              />

              <FrotaUsoAgricolaPanel
                agriculturaData={agriculturaData}
                hasEnterpriseTier={hasEnterpriseTier}
              />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,1fr)]">
        <Skeleton className="h-[560px] rounded-sm" />
        <div className="space-y-6">
          <Skeleton className="h-[260px] rounded-sm" />
          <Skeleton className="h-[260px] rounded-sm" />
        </div>
      </div>
      <Skeleton className="h-[260px] rounded-sm" />
    </div>
  );
}
