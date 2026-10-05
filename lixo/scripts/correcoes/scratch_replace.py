import re

with open("apps/web/src/components/integracoes/erp-console.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Add types
types_to_insert = """
export interface ProviderFieldSelectOption {
  value: string | number | boolean;
  label: string;
}

export interface ProviderFieldDefinition {
  key: string;
  label: string;
  type: "string" | "secret" | "select" | "boolean" | "integer" | "url";
  required: boolean;
  secret: boolean;
  placeholder?: string | null;
  help_text?: string | null;
  default?: any | null;
  order: number;
  options?: ProviderFieldSelectOption[] | null;
}

export interface ProviderSchemaDefinition {
  schema_version: number;
  required: string[];
  optional: string[];
  fields: ProviderFieldDefinition[];
}

export interface ProviderPublicIdentity {
  id: number;
  slug: string;
  nome: string;
  provider_type: string;
  ativa: boolean;
}

export interface ProviderSchemaResponse {
  provider: ProviderPublicIdentity;
  schema_version: number;
  connection_schema: ProviderSchemaDefinition | null;
  credential_schema: ProviderSchemaDefinition | null;
}
"""

content = content.replace('interface CapabilityMatrixItem {', types_to_insert + '\ninterface CapabilityMatrixItem {')

# Change function signature
content = content.replace('export function ErpConsole() {', 'export function DynamicErpConsole({ providerSlug = "sankhya" }: { providerSlug?: string }) {')

# Add schema state
content = content.replace('const [config, setConfig] = useState<SankhyaConfig | null>(null);', 'const [schema, setSchema] = useState<ProviderSchemaResponse | null>(null);\n  const [config, setConfig] = useState<SankhyaConfig | null>(null);')

# Update formData state to be fully dynamic (just {} initially)
content = re.sub(r'const \[formData, setFormData\] = useState\(\{[^}]*\}\);', 'const [formData, setFormData] = useState<Record<string, any>>({});', content, flags=re.DOTALL)

# Update handleTestConnection to use dynamic endpoint
content = content.replace('"/integracoes/sankhya/config/testar-conexao"', '`/integracoes/${providerSlug}/config/testar-conexao`')

# Update handleSync
content = content.replace('`/integracoes/sankhya/sync/${tipo}`', '`/integracoes/${providerSlug}/sync/${tipo}`')

# Update loadConsole to load schema and use dynamic urls
loadConsoleRegex = re.compile(r'const loadConsole = useCallback\(async \(\) => \{.*?(const \[diagnosisData, configData, statusData, healthData, jobsData, logsData, timelineData\] = await Promise\.all\(\[).*?fetchJson<SankhyaConfig>\("/integracoes/sankhya/config"\).*?(\]\);).*?if \(configData\) \{.*?setFormData\(\{.*?\}\);.*?\}', re.DOTALL)

loadConsoleReplace = r"""const loadConsole = useCallback(async () => {
    setLoading(true);
    try {
      const [schemaData, diagnosisData, configData, statusData, healthData, jobsData, logsData, timelineData] = await Promise.all([
        fetchJson<ProviderSchemaResponse>(`/integracoes/erp/providers/${providerSlug}/schema`),
        fetchJson<SankhyaDiagnosis>("/integracoes/erp/diagnostico"),
        fetchJson<SankhyaConfig>(`/integracoes/${providerSlug}/config`),
        fetchJson<SankhyaStatus>("/integracoes/erp/status"),
        fetchJson<SankhyaHealth>("/integracoes/erp/health"),
        fetchJson<SankhyaJob[]>("/integracoes/erp/jobs?limit=5"),
        fetchJson<SyncLog[]>(`/integracoes/${providerSlug}/logs?limit=10`),
        fetchJson<ErpTimelineItem[]>("/integracoes/erp/timeline?limit=12"),
      ]);

      setSchema(schemaData);
      setDiagnosis(diagnosisData);
      setConfig(configData);
      setStatus(statusData);
      setHealth(healthData);
      setJobs(jobsData || []);
      setLogs(logsData || []);
      setTimeline(timelineData || []);

      if (schemaData) {
        const initialForm: Record<string, any> = {};
        const allFields = [
          ...(schemaData.connection_schema?.fields || []),
          ...(schemaData.credential_schema?.fields || [])
        ];
        
        allFields.forEach(f => {
          if (configData && (configData as any)[f.key] !== undefined) {
             initialForm[f.key] = (configData as any)[f.key];
          } else if (f.default !== undefined && f.default !== null) {
             initialForm[f.key] = f.default;
          } else {
             initialForm[f.key] = f.type === "boolean" ? false : "";
          }
        });
        
        // Preserve legacy values if any
        if (configData?.sankhya_environment) initialForm.sankhya_environment = configData.sankhya_environment;
        
        setFormData(initialForm);
      }
"""

content = loadConsoleRegex.sub(loadConsoleReplace, content, count=1)

# Update save
content = content.replace('await apiFetch("/integracoes/sankhya/config", {', 'await apiFetch(`/integracoes/${providerSlug}/config`, {')


# Dynamic form rendering function
dynamic_form_render = r"""
function renderField(field: ProviderFieldDefinition) {
  const value = formData[field.key] ?? (field.type === "boolean" ? false : "");
  
  return (
    <div key={field.key} className="space-y-2">
      <Label htmlFor={field.key}>
        {field.label}
        {field.required && <span className="text-destructive ml-1">*</span>}
      </Label>
      
      {field.type === "boolean" ? (
        <div className="flex items-center gap-2 h-8">
           <input type="checkbox" id={field.key} className="h-4 w-4 rounded border-gray-300" checked={value} onChange={e => setFormData(cur => ({ ...cur, [field.key]: e.target.checked }))} />
           <span className="text-sm text-muted-foreground">{field.help_text}</span>
        </div>
      ) : field.type === "select" ? (
        <select 
          id={field.key} 
          className="flex h-8 w-full items-center justify-between rounded-sm border border-input bg-transparent px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          value={value}
          onChange={e => setFormData(cur => ({ ...cur, [field.key]: e.target.value }))}
        >
           <option value="" disabled>Selecione...</option>
           {field.options?.map(opt => (
             <option key={String(opt.value)} value={String(opt.value)}>{opt.label}</option>
           ))}
        </select>
      ) : (
        <Input
          id={field.key}
          type={field.secret || field.type === "secret" ? "password" : "text"}
          className="h-8 rounded-sm text-sm"
          placeholder={field.placeholder || ""}
          value={value}
          onChange={e => setFormData(cur => ({ ...cur, [field.key]: e.target.value }))}
        />
      )}
      
      {field.help_text && field.type !== "boolean" && (
        <p className="mt-1 text-xs text-muted-foreground">{field.help_text}</p>
      )}
    </div>
  );
}

"""

# Insert the renderField function right before the return (
content = content.replace('  return (\n    <div className="space-y-6">', dynamic_form_render + '  return (\n    <div className="space-y-6">')

# Replace the specific hardcoded grids
# Find the start of the card content containing the form
start_pattern = r'<div className="grid gap-4 md:grid-cols-2">[^<]*<div>[^<]*<Label htmlFor="sankhya_environment">'
end_pattern = r'</p>[^<]*</div>[^<]*<div className="flex flex-wrap gap-2">'

card_content_regex = re.compile(start_pattern + r'.*?' + end_pattern, re.DOTALL)

replacement_form = r"""
          {schema?.connection_schema?.fields?.length ? (
            <div className="space-y-4">
              <h3 className="text-sm font-medium border-b pb-2">Configurações de Conexão</h3>
              <div className="grid gap-4 md:grid-cols-2">
                {schema.connection_schema.fields.map(renderField)}
              </div>
            </div>
          ) : null}

          {schema?.credential_schema?.fields?.length ? (
            <div className="space-y-4 mt-6">
              <h3 className="text-sm font-medium border-b pb-2 text-destructive">Credenciais e Segredos</h3>
              <div className="grid gap-4 md:grid-cols-2">
                {schema.credential_schema.fields.map(renderField)}
              </div>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2 mt-6">
"""

content = card_content_regex.sub(replacement_form, content, count=1)


with open("apps/web/src/components/integracoes/erp-console.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
