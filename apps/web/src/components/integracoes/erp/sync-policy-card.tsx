import { Badge } from "@/components/ui/badge";
import type { ErpSyncPolicyViewModel } from "./sync-center-view-model";

interface ErpSyncPolicyCardProps {
  policy: ErpSyncPolicyViewModel;
}

function getImplementationVariant(status: string) {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    IMPLEMENTED_ACTIVE: "default",
    IMPLEMENTED_INACTIVE: "secondary",
    CONFIGURED: "outline",
    DECLARED: "outline",
    NOT_AVAILABLE: "destructive",
    P2_FORBIDDEN: "destructive",
  };
  return map[status] || "secondary";
}

function formatImplementationStatus(status: string) {
  const map: Record<string, string> = {
    IMPLEMENTED_ACTIVE: "Ativa",
    IMPLEMENTED_INACTIVE: "Inativa",
    CONFIGURED: "Configurada",
    DECLARED: "Declarada",
    NOT_AVAILABLE: "Indisponível",
    P2_FORBIDDEN: "Planejado (Fase 2)",
  };
  return map[status] || status;
}

export function ErpSyncPolicyCard({ policy }: ErpSyncPolicyCardProps) {
  return (
    <div className="rounded-sm border bg-muted/20 p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="font-medium">{policy.capabilityName}</p>
          <p className="text-xs text-muted-foreground">
            Escopo: {policy.scopeLabel} · Provider: {policy.providerName}
          </p>
        </div>
        <Badge variant={getImplementationVariant(policy.implementationStatus)}>
          {formatImplementationStatus(policy.implementationStatus)}
        </Badge>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-muted-foreground text-xs block">Gatilho Principal</span>
          <span className="font-medium">{policy.triggerLabel}</span>
        </div>
        {policy.scheduleLabel && (
          <div>
            <span className="text-muted-foreground text-xs block">Expressão de agendamento</span>
            <span className="font-medium">{policy.scheduleLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
}
