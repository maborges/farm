import re

with open("apps/web/src/components/integracoes/erp-console.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Add interface
new_props = """
export interface DynamicErpConsoleProps {
  providerSlug?: string;
  endpoints?: {
    getConfig: string;
    saveConfig: string;
    testConnection: string;
    sync: (tipo: string) => string;
    getLogs: string;
  };
}

export function DynamicErpConsole({ providerSlug = "sankhya", endpoints }: DynamicErpConsoleProps) {
"""

content = content.replace(
    'export function DynamicErpConsole({ providerSlug = "sankhya" }: { providerSlug?: string }) {',
    new_props.strip()
)

# In loadConsole:
# replace `/integracoes/${providerSlug}/config`
content = content.replace(
    '`/integracoes/${providerSlug}/config`',
    'endpoints?.getConfig || `/integracoes/${providerSlug}/config`'
)

# replace `/integracoes/${providerSlug}/logs?limit=10`
content = content.replace(
    '`/integracoes/${providerSlug}/logs?limit=10`',
    'endpoints?.getLogs || `/integracoes/${providerSlug}/logs?limit=10`'
)

# In save config:
content = content.replace(
    'await apiFetch(`/integracoes/${providerSlug}/config`, {',
    'await apiFetch(endpoints?.saveConfig || `/integracoes/${providerSlug}/config`, {'
)

# In test connection:
content = content.replace(
    'await apiFetch<{ sucesso: boolean; mensagem: string }>(`/integracoes/${providerSlug}/config/testar-conexao`, {',
    'await apiFetch<{ sucesso: boolean; mensagem: string }>(endpoints?.testConnection || `/integracoes/${providerSlug}/config/testar-conexao`, {'
)

# In sync:
content = content.replace(
    'await apiFetch(`/integracoes/${providerSlug}/sync/${tipo}`, {',
    'await apiFetch(endpoints?.sync ? endpoints.sync(tipo) : `/integracoes/${providerSlug}/sync/${tipo}`, {'
)


with open("apps/web/src/components/integracoes/erp-console.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Fix applied to erp-console.tsx")
