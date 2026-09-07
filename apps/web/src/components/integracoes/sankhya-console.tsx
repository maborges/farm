"use client";

import { DynamicErpConsole } from "@/components/integracoes/erp-console";

const SANKHYA_ENDPOINTS = {
  getConfig: "/integracoes/sankhya/config",
  saveConfig: "/integracoes/sankhya/config",
  removeConfig: "/integracoes/sankhya/config",
  testConnection: "/integracoes/sankhya/config/testar-conexao",
  sync: (tipo: string) => `/integracoes/sankhya/sync/${tipo}`,
  getLogs: "/integracoes/sankhya/logs?limit=10",
  listPeople: "/integracoes/sankhya/pessoas?limit=20",
} as const;

const SANKHYA_OPERATIONAL_CONFIG = {
  manualSyncCapabilities: ["produtos"] as string[],
  adapterLabel: "Conector Sankhya",
};

export function SankhyaConsole() {
  return (
    <DynamicErpConsole
      providerSlug="sankhya"
      endpoints={SANKHYA_ENDPOINTS}
      operationalConfig={SANKHYA_OPERATIONAL_CONFIG}
    />
  );
}
