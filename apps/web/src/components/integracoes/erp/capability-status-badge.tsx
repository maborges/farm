"use client";

import { Badge } from "@/components/ui/badge";
import {
  getErpCapabilityMaturityLabel,
  getErpOperationalStatusLabel,
  getErpSyncModeLabel,
  getIntegrationHealthOperationalLabel,
} from "./capability-labels";
import type {
  ErpCapabilityMaturity,
  ErpCapabilityOperationalStatus,
  ErpSyncMode,
} from "./types";

function getStatusVariant(status: ErpCapabilityOperationalStatus): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "ACTIVE":
      return "default";
    case "PARTIAL":
    case "DEGRADED":
    case "PENDING_CONFIGURATION":
    case "DISABLED":
      return "secondary";
    case "DECLARED":
      return "outline";
    case "FAILED":
    case "NOT_AVAILABLE":
      return "destructive";
    default:
      return "secondary";
  }
}

export function ErpCapabilityStatusBadge({
  status,
  className,
}: {
  status: ErpCapabilityOperationalStatus;
  className?: string;
}) {
  return (
    <Badge
      variant={getStatusVariant(status)}
      className={className}
      aria-label={`Situação da capability: ${getErpOperationalStatusLabel(status)}`}
    >
      {getErpOperationalStatusLabel(status)}
    </Badge>
  );
}

export function ErpCapabilityMaturityBadge({
  maturity,
  className,
}: {
  maturity: ErpCapabilityMaturity;
  className?: string;
}) {
  return (
    <Badge variant="outline" className={className} aria-label={`Maturidade: ${getErpCapabilityMaturityLabel(maturity)}`}>
      {getErpCapabilityMaturityLabel(maturity)}
    </Badge>
  );
}

export function ErpCapabilitySyncModeBadge({
  mode,
  className,
}: {
  mode: ErpSyncMode;
  className?: string;
}) {
  return (
    <Badge variant="outline" className={className} aria-label={`Forma de atualização: ${getErpSyncModeLabel(mode)}`}>
      {getErpSyncModeLabel(mode)}
    </Badge>
  );
}

export function ErpCapabilityHealthBadge({
  healthStatus,
  className,
}: {
  healthStatus?: string | null;
  className?: string;
}) {
  const label = getIntegrationHealthOperationalLabel(healthStatus);
  const variant =
    healthStatus === "CONNECTED"
      ? "default"
      : healthStatus === "DEGRADED" || healthStatus === "PARTIAL_FAILURE" || healthStatus === "RATE_LIMITED"
        ? "secondary"
        : healthStatus
          ? "destructive"
          : "outline";

  return (
    <Badge variant={variant} className={className} aria-label={`Situação geral da integração: ${label}`}>
      {label}
    </Badge>
  );
}
