export interface ErpPersonGovernanceStatus {
  configurado: boolean;
}

export interface ErpPersonGovernancePolicy {
  feature_code: string;
  feature_enabled: boolean;
  ativa: boolean;
}

export function isErpPeopleManaged(
  status: ErpPersonGovernanceStatus | undefined,
  policies: ErpPersonGovernancePolicy[],
): boolean {
  if (!status?.configurado) return false;
  const people = policies.find((policy) => policy.feature_code === 'pessoas');
  return Boolean(people?.feature_enabled);
}
