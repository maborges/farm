"use client";

import { useState } from "react";
import { ArrowRightLeft, Link2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getErpSyncDirectionLabel, getErpCapabilityCatalogEntry } from "./capability-labels";
import { ErpCapabilityDetails } from "./capability-details";
import {
  ErpCapabilityMaturityBadge,
  ErpCapabilityStatusBadge,
  ErpCapabilitySyncModeBadge,
} from "./capability-status-badge";
import type { ErpCapabilityDetailsViewModel, ErpCapabilityViewModel } from "./types";

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Não informado";
  }
  return new Date(value).toLocaleString("pt-BR");
}

interface ErpCapabilityCardProps {
  capability: ErpCapabilityViewModel;
  details?: ErpCapabilityDetailsViewModel;
  onSyncManual?: (capabilityCode: string) => void;
  onConfigure?: () => void;
  onAssociations?: () => void;
  syncing?: boolean;
  configurationTargetId?: string;
}

export function ErpCapabilityCard({
  capability,
  details,
  onSyncManual,
  onConfigure,
  onAssociations,
  syncing = false,
  configurationTargetId = "erp-configuracao",
}: ErpCapabilityCardProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const catalogEntry = getErpCapabilityCatalogEntry(capability.code);

  return (
    <>
      <Card className="rounded-sm border-border/70 bg-background/95">
        <CardHeader className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <CardTitle className="text-base">{capability.name}</CardTitle>
                <ErpCapabilityStatusBadge status={capability.status} />
                <ErpCapabilityMaturityBadge maturity={capability.maturity} />
              </div>
              <CardDescription className="max-w-2xl text-sm">{capability.description}</CardDescription>
              {catalogEntry?.planningNote ? (
                <p className="text-xs text-muted-foreground">{catalogEntry.planningNote}</p>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {capability.actions.canViewDetails ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="rounded-sm"
                  onClick={() => setDetailsOpen(true)}
                >
                  Ver detalhes
                </Button>
              ) : (
                <Button type="button" variant="outline" size="sm" className="rounded-sm" disabled>
                  Detalhes em preparação
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-sm border bg-muted/20 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Origem principal</p>
              <p className="mt-1 text-sm font-medium">{capability.masterSystem}</p>
            </div>
            <div className="rounded-sm border bg-muted/20 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Fluxo dos dados</p>
              <p className="mt-1 text-sm font-medium">{getErpSyncDirectionLabel(capability.direction)}</p>
            </div>
            <div className="rounded-sm border bg-muted/20 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Atualização</p>
              <div className="mt-1">
                <ErpCapabilitySyncModeBadge mode={capability.syncMode} />
              </div>
            </div>
            <div className="rounded-sm border bg-muted/20 p-3">
              <p className="text-xs font-semibold uppercase text-muted-foreground">Última atualização</p>
              <p className="mt-1 text-sm font-medium">{formatDateTime(capability.lastJobAt || capability.lastSyncAt)}</p>
            </div>
          </div>

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

            {capability.actions.canReconcile && onAssociations ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="rounded-sm"
                onClick={onAssociations}
                aria-label={`Ir para pendências de associação de ${capability.name}`}
              >
                <Link2 className="mr-2 h-4 w-4" />
                Ver pendências
              </Button>
            ) : null}

          </div>
        </CardContent>
      </Card>

      <Sheet open={detailsOpen} onOpenChange={setDetailsOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{capability.name}</SheetTitle>
            <SheetDescription>
              Como este fluxo de dados funciona e quais ações estão disponíveis.
            </SheetDescription>
          </SheetHeader>
          {details ? (
            <ErpCapabilityDetails
              details={details}
              onSyncManual={onSyncManual}
              onConfigure={onConfigure}
              syncing={syncing}
              configurationTargetId={configurationTargetId}
            />
          ) : null}
        </SheetContent>
      </Sheet>
    </>
  );
}
