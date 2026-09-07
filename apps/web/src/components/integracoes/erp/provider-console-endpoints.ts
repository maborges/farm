export interface ProviderConsoleEndpoints {
  getConfig: string;
  saveConfig: string;
  removeConfig: string;
  testConnection: string;
  sync: (tipo: string) => string;
  getLogs: string;
}

export function resolveProviderConsoleEndpoints(
  providerSlug: string,
  endpoints?: Partial<ProviderConsoleEndpoints>,
): ProviderConsoleEndpoints {
  return {
    getConfig: endpoints?.getConfig || `/integracoes/${providerSlug}/config`,
    saveConfig: endpoints?.saveConfig || endpoints?.getConfig || `/integracoes/${providerSlug}/config`,
    removeConfig:
      endpoints?.removeConfig || endpoints?.getConfig || `/integracoes/${providerSlug}/config`,
    testConnection:
      endpoints?.testConnection || `/integracoes/${providerSlug}/config/testar-conexao`,
    sync: endpoints?.sync || ((tipo: string) => `/integracoes/${providerSlug}/sync/${tipo}`),
    getLogs: endpoints?.getLogs || `/integracoes/${providerSlug}/logs?limit=10`,
  };
}
