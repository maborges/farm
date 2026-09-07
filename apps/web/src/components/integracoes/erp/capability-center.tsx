"use client";

import { AlertTriangle, Boxes, Clock3, ShieldAlert } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { StatCard } from "@/components/shared/stat-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErpCapabilityCard } from "./capability-card";
import type { ErpCapabilityDetailsViewModel, ErpCapabilityViewModel } from "./types";

interface ErpCapabilityCenterProps {
  capabilities: ErpCapabilityViewModel[];
  capabilityDetails?: Record<string, ErpCapabilityDetailsViewModel>;
  loading?: boolean;
  error?: string | null;
  configured?: boolean;
  providerName?: string | null;
  onRetry?: () => void;
  onSyncManual?: (capabilityCode: string) => void;
  syncing?: Record<string, boolean>;
  onConfigure?: () => void;
  onAssociations?: () => void;
  configurationTargetId?: string;
}

function buildSummary(capabilities: ErpCapabilityViewModel[]) {
  return capabilities.reduce(
    (accumulator, item) => {
      if (item.status === "ACTIVE") {
        accumulator.active += 1;
      }
      if (item.status === "PARTIAL" || item.status === "DEGRADED" || item.status === "FAILED") {
        accumulator.attention += 1;
      }
      if (item.status === "DECLARED" || item.maturity === "P2") {
        accumulator.planned += 1;
      }
      return accumulator;
    },
    { active: 0, attention: 0, planned: 0 },
  );
}

export function getErpCapabilitySectionCopy(providerName?: string | null) {
  return {
    title: "Dados sincronizados",
    description: `O que ${providerName ? `o ${providerName}` : "o ERP"} troca com o AgroSaaS e a situação de cada fluxo.`,
  };
}

export function ErpCapabilityCenter({
  capabilities,
  capabilityDetails = {},
  loading = false,
  error = null,
  configured = true,
  providerName,
  onRetry,
  onSyncManual,
  syncing = {},
  onConfigure,
  onAssociations,
  configurationTargetId = "erp-configuracao",
}: ErpCapabilityCenterProps) {
  const summary = buildSummary(capabilities);
  const sectionCopy = getErpCapabilitySectionCopy(providerName);

  return (
    <section id="erp-capability-center" className="space-y-4" aria-labelledby="erp-capability-center-title">
      <Card className="rounded-sm border-border/70">
        <CardHeader className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <CardTitle id="erp-capability-center-title" className="text-lg">
                {sectionCopy.title}
              </CardTitle>
              <CardDescription>
                {sectionCopy.description}
              </CardDescription>
            </div>
            {!loading && capabilities.length > 0 ? (
              <p className="text-sm text-muted-foreground">
                {capabilities.length} {capabilities.length === 1 ? "fluxo disponível" : "fluxos disponíveis"}
              </p>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="space-y-4" aria-label="Carregando dados sincronizados">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-24 rounded-sm" />
                ))}
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {Array.from({ length: 2 }).map((_, index) => (
                  <Skeleton key={index} className="h-72 rounded-sm" />
                ))}
              </div>
            </div>
          ) : error ? (
            <EmptyState
              icon={<AlertTriangle />}
              title="Não foi possível carregar os dados sincronizados."
              description={error}
              action={onRetry ? { label: "Tentar novamente", onClick: onRetry } : undefined}
              secondaryAction={onConfigure
                ? { label: "Ir para configuração", onClick: onConfigure }
                : { label: "Ir para configuração", href: `#${configurationTargetId}` }}
            />
          ) : !configured ? (
            <EmptyState
              icon={<ShieldAlert />}
              title="Configure o ERP para visualizar os dados sincronizados."
              description="Depois de salvar e validar a conexão, esta área mostra quais dados podem circular entre o ERP e o AgroSaaS."
              action={onConfigure
                ? { label: "Abrir configuração", onClick: onConfigure }
                : { label: "Abrir configuração", href: `#${configurationTargetId}` }}
            />
          ) : capabilities.length === 0 ? (
            <EmptyState
              icon={<Boxes />}
              title="Nenhum fluxo de dados foi informado pelo ERP."
              description="A conexão existe, mas o provider ainda não publicou quais dados podem ser sincronizados. Atualize a situação ou revise a configuração."
              action={onRetry ? { label: "Atualizar situação", onClick: onRetry } : undefined}
              secondaryAction={onConfigure
                ? { label: "Abrir configuração", onClick: onConfigure }
                : { label: "Abrir configuração", href: `#${configurationTargetId}` }}
            />
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard icon={Boxes} color="success" label="Em operação" value={summary.active} subtitle="Fluxos disponíveis para uso" />
                <StatCard icon={AlertTriangle} color="warning" label="Precisam de atenção" value={summary.attention} subtitle="Fluxos parciais, degradados ou com falha" />
                <StatCard icon={Clock3} color="muted" label="Planejados" value={summary.planned} subtitle="Fluxos ainda não disponíveis" />
              </div>

              <Alert>
                <AlertDescription>
                  A situação geral da conexão é compartilhada pelos fluxos. Datas só são exibidas como específicas quando o ERP informa a execução daquele tipo de dado.
                </AlertDescription>
              </Alert>

              <div className="grid gap-4 lg:grid-cols-2">
                {capabilities.map((capability) => (
                  <ErpCapabilityCard
                    key={capability.code}
                    capability={capability}
                    details={capabilityDetails[capability.code]}
                    onSyncManual={onSyncManual}
                    onConfigure={onConfigure}
                    onAssociations={onAssociations}
                    syncing={Boolean(syncing[capability.code])}
                    configurationTargetId={configurationTargetId}
                  />
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
