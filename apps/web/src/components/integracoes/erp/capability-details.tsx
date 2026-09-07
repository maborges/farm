"use client";

import { Activity, ArrowRightLeft, Clock3, Settings2, Wrench } from "lucide-react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  ErpCapabilityHealthBadge,
  ErpCapabilityMaturityBadge,
  ErpCapabilityStatusBadge,
  ErpCapabilitySyncModeBadge,
} from "./capability-status-badge";
import type { ErpCapabilityDetailsViewModel } from "./types";

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Não informado";
  }
  return new Date(value).toLocaleString("pt-BR");
}

interface ErpCapabilityDetailsProps {
  details: ErpCapabilityDetailsViewModel;
  onSyncManual?: (capabilityCode: string) => void;
  onConfigure?: () => void;
  syncing?: boolean;
  configurationTargetId?: string;
}

export function ErpCapabilityDetails({
  details,
  onSyncManual,
  onConfigure,
  syncing = false,
  configurationTargetId = "erp-configuracao",
}: ErpCapabilityDetailsProps) {
  const { capability } = details;
  const hasOperationalActions =
    capability.actions.canSyncManually || capability.actions.canConfigure;

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-6 overflow-y-auto px-4 pb-6">
        <section className="space-y-3" aria-labelledby={`erp-capability-details-title-${capability.code}`}>
          <div className="flex flex-wrap items-center gap-2">
            <ErpCapabilityStatusBadge status={capability.status} />
            <ErpCapabilityMaturityBadge maturity={capability.maturity} />
            <ErpCapabilityHealthBadge healthStatus={details.health.status} />
            <ErpCapabilitySyncModeBadge mode={capability.syncMode} />
          </div>
          <div className="space-y-2">
            <h3 id={`erp-capability-details-title-${capability.code}`} className="text-base font-semibold">
              {capability.name}
            </h3>
            <p className="text-sm text-muted-foreground">{capability.description}</p>
            {details.ownership.operationalBoundary ? (
              <p className="rounded-sm border bg-muted/20 p-3 text-sm text-muted-foreground">
                {details.ownership.operationalBoundary}
              </p>
            ) : null}
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2" aria-label="Resumo operacional">
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Sistema responsável</p>
            <p className="mt-1 text-sm font-medium">{details.ownership.masterSystem}</p>
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Sentido da atualização</p>
            <p className="mt-1 text-sm font-medium">{details.ownership.directionLabel}</p>
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Forma de atualização</p>
            <p className="mt-1 text-sm font-medium">{details.execution.syncModeLabel}</p>
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Executado pelo conector</p>
            <p className="mt-1 text-sm font-medium">{details.provider.executorLabel || "Não informado"}</p>
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2" aria-label="Datas de execução">
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Última atualização</p>
            <p className="mt-1 text-sm font-medium">{formatDateTime(details.execution.lastSyncAt)}</p>
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Última execução</p>
            <p className="mt-1 text-sm font-medium">{formatDateTime(details.execution.lastJobAt)}</p>
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <div className="flex items-center gap-1">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Próxima atualização prevista</p>
              {details.execution.nextRunIsShared ? (
                <Clock3 className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              ) : null}
            </div>
            <p className="mt-1 text-sm font-medium">{formatDateTime(details.execution.nextRunAt)}</p>
            {details.execution.nextRunIsShared ? (
              <p className="mt-1 text-xs text-muted-foreground">
                A programação pode ser compartilhada pela integração e não representa agenda exclusiva desta capability.
              </p>
            ) : null}
          </div>
          <div className="rounded-sm border bg-muted/10 p-3">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Situação geral do conector</p>
            <p className="mt-1 text-sm font-medium">{details.health.label}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {details.health.summary || "A integração está saudável, mas esta capability pode possuir limitações próprias."}
            </p>
          </div>
        </section>

        <section className="space-y-3" aria-label="Ações disponíveis">
          <div className="flex flex-wrap gap-2">
            {capability.actions.canSyncManually ? (
              <Button
                type="button"
                size="sm"
                className="rounded-sm"
                onClick={() => onSyncManual?.(capability.code)}
                disabled={syncing}
                aria-label={`Sincronizar ${capability.name}`}
              >
                <ArrowRightLeft className="mr-2 h-4 w-4" />
                {syncing ? `Sincronizando ${capability.name.toLowerCase()}...` : `Sincronizar ${capability.name.toLowerCase()}`}
              </Button>
            ) : null}

            {capability.actions.canConfigure ? (
              !onConfigure ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="rounded-sm"
                  asChild
                  aria-label={`Ir para configuração de ${capability.name}`}
                >
                  <a href={`#${configurationTargetId}`}>
                    <Settings2 className="h-4 w-4" />
                    Configurar
                  </a>
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="rounded-sm"
                  onClick={onConfigure}
                  aria-label={`Ir para configuração de ${capability.name}`}
                >
                  <Settings2 className="h-4 w-4" />
                  Configurar
                </Button>
              )
            ) : null}

          </div>
          {!hasOperationalActions ? (
            <p className="text-sm text-muted-foreground">Nenhuma ação operacional disponível neste momento.</p>
          ) : null}
        </section>

        <p className="rounded-sm border bg-muted/20 p-3 text-sm text-muted-foreground">
          Execuções, histórico e associações ficam nas respectivas abas da integração.
        </p>

        <Accordion type="single" collapsible className="rounded-sm border px-3">
          <AccordionItem value="technical" className="border-none">
            <AccordionTrigger className="text-sm font-semibold">
              <span className="inline-flex items-center gap-2">
                <Wrench className="h-4 w-4" />
                Informações técnicas sanitizadas
              </span>
            </AccordionTrigger>
            <AccordionContent className="space-y-4 text-sm">
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground">Provider</p>
                <p className="mt-1 font-medium">{details.provider.name}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground">Sistema externo</p>
                <p className="mt-1 font-medium">{details.technical.externalSystemLabel || "Não informado"}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-muted-foreground">Operações internas</p>
                {details.technical.internalOperationLabels.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                    {details.technical.internalOperationLabels.map((label) => (
                      <li key={label} className="flex items-center gap-2">
                        <Activity className="h-3.5 w-3.5" />
                        <span>{label}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-muted-foreground">Não informado</p>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
}
