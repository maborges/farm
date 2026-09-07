"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  CloudSun,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Save,
  TestTube2,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useAppStore } from "@/lib/stores/app-store";
import { useToast } from "@/hooks/use-toast";
import {
  fetchOpenWeatherDashboard,
  fetchOpenWeatherOperationalDashboard,
  saveOpenWeatherConfig,
  saveOpenWeatherConfigForUnit,
  syncOpenWeatherCurrentWeather,
  syncOpenWeatherCurrentWeatherForUnit,
  testOpenWeatherConnection,
  testOpenWeatherConnectionForUnit,
  type OpenWeatherConfigUpsert,
} from "@/lib/integracoes/openweather-api";

const DEFAULT_FORM: OpenWeatherConfigUpsert = {
  api_key: "",
  api_base_url: "https://api.openweathermap.org",
  environment: "production",
  location_query: "Sao Paulo,BR",
  units: "metric",
  language: "pt_br",
  timeout_seconds: 20,
  cache_ttl_seconds: 1800,
  daily_quota: 1000,
  sync_frequency_minutes: 60,
};

function formatDateTime(value?: string | null) {
  if (!value) return "Não disponível";
  return new Date(value).toLocaleString("pt-BR");
}

function formatLabel(value?: string | null) {
  if (!value) return "Não disponível";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function statusVariant(value?: string | null) {
  if (!value) return "secondary" as const;
  if (["CONNECTED", "SUCCESS"].includes(value)) return "default" as const;
  if (["AUTH_ERROR", "CONFIG_ERROR", "DISCONNECTED", "FAILED"].includes(value)) return "destructive" as const;
  return "secondary" as const;
}

function translateStatus(value?: string | null) {
  if (!value) return "Desconhecido";
  const map: Record<string, string> = {
    // health / conexão
    CONNECTED: "Conectado",
    DISCONNECTED: "Desconectado",
    DEGRADED: "Instável",
    PARTIAL_FAILURE: "Falha Parcial",
    // resultados de operação
    SUCCESS: "Concluído",
    FAILED: "Falhou",
    PENDING: "Aguardando",
    RUNNING: "Em Andamento",
    PARTIAL: "Parcial",
    SKIPPED: "Ignorado",
    CANCELLED: "Cancelado",
    // erros
    AUTH_ERROR: "Erro de Autenticação",
    CONFIG_ERROR: "Erro de Configuração",
    TIMEOUT: "Tempo Esgotado",
    NETWORK_ERROR: "Erro de Rede",
    UNKNOWN_ERROR: "Erro Desconhecido",
    // estados de ciclo de vida e conexão (vindo da API)
    ACTIVE: "Ativo",
    INACTIVE: "Inativo",
    CONFIGURED: "Configurado",
    NOT_CONFIGURED: "Não Configurado",
    ERROR: "Com Erro",
    HEALTHY: "Saudável",
    UNHEALTHY: "Com Problemas",
    // minusculas
    active: "Ativo",
    inactive: "Inativo",
    configured: "Configurado",
    pending: "Aguardando Configuração",
    disabled: "Desativado",
    suspended: "Suspenso",
    // status_conexao específicos
    pendente_teste: "Aguardando Teste",
    teste_pendente: "Aguardando Teste",
    aguardando_teste: "Aguardando Teste",
    sem_conexao: "Sem Conexão",
    erro_conexao: "Erro de Conexão",
    conexao_ok: "Conexão OK",
    // status_degradacao
    none: "Normal",
    low: "Leve",
    medium: "Moderado",
    high: "Crítico",
    critical: "Crítico",
    NONE: "Normal",
    LOW: "Leve",
    MEDIUM: "Moderado",
    HIGH: "Crítico",
    CRITICAL: "Crítico",
  };
  // Fallback genérico: se não encontrar no mapa, converte snake_case/SCREAMING_SNAKE para texto legível
  return map[value] ?? value.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function translateFeature(value?: string | null) {
  if (!value) return "";
  const map: Record<string, string> = {
    current_weather: "Clima Atual",
    forecast: "Previsão do Tempo",
    rainfall: "Índice de Chuva",
    wind: "Vento",
    humidity: "Umidade",
    temperature: "Temperatura",
  };
  return map[value] ?? value;
}

function translateMode(value?: string | null) {
  if (!value) return "";
  const map: Record<string, string> = {
    PULL: "Automático",
    PUSH: "Manual",
    pull: "Automático",
    push: "Manual",
  };
  return map[value] ?? value;
}

function translateTriggerType(value?: string | null) {
  if (!value) return "";
  const map: Record<string, string> = {
    manual: "Manual",
    scheduler: "Agendado",
    api: "Via API",
    webhook: "Automático (Webhook)",
    cron: "Agendado",
  };
  return map[value.toLowerCase()] ?? value;
}

function translateCronExpression(value?: string | null) {
  if (!value) return "";
  // Padrões comuns de cron expressos em português para o campo
  const common: Record<string, string> = {
    "*/15 * * * *": "A cada 15 minutos",
    "*/30 * * * *": "A cada 30 minutos",
    "0 * * * *": "A cada hora",
    "0 */2 * * *": "A cada 2 horas",
    "0 */6 * * *": "A cada 6 horas",
    "0 0 * * *": "Diariamente à meia-noite",
    "0 6 * * *": "Diariamente às 6h",
    "0 12 * * *": "Diariamente ao meio-dia",
  };
  return common[value.trim()] ?? `Agendado (${value})`;
}

function translateEventType(value?: string | null) {
  if (!value) return "consulta climática";
  const map: Record<string, string> = {
    "integrations.sync_completed": "Sincronização concluída",
    "integrations.sync_failed": "Falha na sincronização",
    "integrations.config_saved": "Configuração salva",
    "integrations.connection_tested": "Teste de conexão",
    "integrations.connection_ok": "Conexão verificada",
    "integrations.connection_failed": "Falha na conexão",
    "weather.fetched": "Clima obtido",
    "weather.fetch_failed": "Falha ao obter clima",
  };
  return map[value] ?? value.replace(/[._]/g, " ");
}

function translateOrigemDado(value?: string | null) {
  if (!value) return "";
  const map: Record<string, string> = {
    api: "API Externa",
    cache: "Cache Local",
    manual: "Manual",
    scheduler: "Agendamento Automático",
    canonical: "Padrão do Sistema",
  };
  return map[value.toLowerCase()] ?? value;
}

function translateTipoRegistro(value?: string | null) {
  if (!value) return "";
  const map: Record<string, string> = {
    weather_sync: "Atualização Climática",
    config_change: "Alteração de Configuração",
    connection_test: "Teste de Conexão",
    sync_completed: "Sincronização Concluída",
    sync_failed: "Falha de Sincronização",
    health_check: "Verificação de Saúde",
  };
  const key = value.toLowerCase();
  return (
    map[key] ??
    value.split("_").map((p) => p.charAt(0).toUpperCase() + p.slice(1).toLowerCase()).join(" ")
  );
}

function userFacingError(error: unknown, fallback: string) {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "object" && error && "detail" in error) {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return fallback;
}

export function OpenWeatherConsole() {
  const { activeFazendaId } = useAppStore();
  const queryClient = useQueryClient();
  const coreQuery = useQuery({
    queryKey: ["openweather-dashboard", activeFazendaId],
    queryFn: () => fetchOpenWeatherDashboard(activeFazendaId),
    staleTime: 30_000,
  });
  const operationalQuery = useQuery({
    queryKey: ["openweather-dashboard-operational", activeFazendaId],
    queryFn: () => fetchOpenWeatherOperationalDashboard(activeFazendaId),
    enabled: !!coreQuery.data,
    staleTime: 30_000,
  });
  const data = coreQuery.data
    ? { ...coreQuery.data, ...(operationalQuery.data ?? {}) }
    : undefined;
  const { isLoading, error, refetch } = coreQuery;

  const [form, setForm] = useState<OpenWeatherConfigUpsert>(DEFAULT_FORM);
  const { toast } = useToast();

  useEffect(() => {
    if (!data?.config) return;
    // A tela precisa refletir a configuração carregada ao abrir a página.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setForm({
      api_key: "",
      api_base_url: String(data.config.connection_payload?.api_base_url || DEFAULT_FORM.api_base_url),
      environment: String(data.config.connection_payload?.environment || DEFAULT_FORM.environment),
      location_query: String(data.config.connection_payload?.location_query || DEFAULT_FORM.location_query),
      units: (String(data.config.connection_payload?.units || DEFAULT_FORM.units) as OpenWeatherConfigUpsert["units"]),
      language: String(data.config.connection_payload?.language || DEFAULT_FORM.language),
      timeout_seconds: Number(data.config.connection_payload?.timeout_seconds || DEFAULT_FORM.timeout_seconds),
      cache_ttl_seconds: Number(data.config.connection_payload?.cache_ttl_seconds || DEFAULT_FORM.cache_ttl_seconds),
      daily_quota: Number(data.config.connection_payload?.daily_quota || DEFAULT_FORM.daily_quota),
      sync_frequency_minutes: Number(data.config.connection_payload?.sync_frequency_minutes || DEFAULT_FORM.sync_frequency_minutes),
    });
  }, [data?.config]);

  const currentHealth = data?.health?.status ?? data?.status?.health_status ?? "DISCONNECTED";
  const readinessLabel = useMemo(() => {
    if (!data?.status?.configurado) return "Não configurado";
    if (currentHealth === "CONNECTED") return "Operacional";
    if (currentHealth === "DEGRADED") return "Atenção";
    if (currentHealth === "AUTH_ERROR") return "Credencial";
    return "Requer revisão";
  }, [currentHealth, data?.status?.configurado]);

  const saveMutation = useMutation({
    mutationFn: (payload: OpenWeatherConfigUpsert) => activeFazendaId
      ? saveOpenWeatherConfigForUnit(activeFazendaId, payload)
      : saveOpenWeatherConfig(payload),
    onSuccess: async () => {
      toast({ variant: "success", title: "Configuração Salva", description: "Configuração OpenWeather atualizada com sucesso." });
      await queryClient.invalidateQueries({ queryKey: ["openweather-dashboard", activeFazendaId] });
      await queryClient.invalidateQueries({ queryKey: ["openweather-dashboard-operational", activeFazendaId] });
    },
    onError: (error) => toast({
      variant: "destructive",
      title: "Erro ao salvar",
      description: userFacingError(error, "Não foi possível salvar a configuração."),
    }),
  });

  const testMutation = useMutation({
    mutationFn: () => activeFazendaId
      ? testOpenWeatherConnectionForUnit(activeFazendaId)
      : testOpenWeatherConnection(),
    onSuccess: (res) => {
      if (res.sucesso) {
        toast({ variant: "success", title: "Conexão Testada", description: res.mensagem });
      } else {
        toast({ variant: "destructive", title: "Falha na conexão", description: res.mensagem });
      }
      queryClient.invalidateQueries({ queryKey: ["openweather-dashboard", activeFazendaId] });
    },
    onError: (error) => toast({
      variant: "destructive",
      title: "Erro no teste",
      description: userFacingError(error, "Falha de comunicação no teste de conexão."),
    }),
  });

  const syncMutation = useMutation({
    mutationFn: () => activeFazendaId
      ? syncOpenWeatherCurrentWeatherForUnit(activeFazendaId)
      : syncOpenWeatherCurrentWeather(),
    onSuccess: async () => {
      toast({ variant: "success", title: "Sincronização", description: "Consulta climática atual executada." });
      await queryClient.invalidateQueries({ queryKey: ["openweather-dashboard", activeFazendaId] });
      await queryClient.invalidateQueries({ queryKey: ["openweather-dashboard-operational", activeFazendaId] });
    },
    onError: (error) => toast({
      variant: "destructive",
      title: "Erro na sincronização",
      description: userFacingError(error, "Falha ao consultar o clima atual."),
    }),
  });

  const handleSave = async () => {
    await saveMutation.mutateAsync(form);
  };

  if (isLoading) {
    return (
      <Card className="rounded-sm">
        <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando console OpenWeather...
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rounded-sm">
        <CardHeader>
          <CardTitle>OpenWeather</CardTitle>
          <CardDescription>Falha ao carregar os dados da integração climática.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Alert variant="destructive">
            <ShieldAlert className="h-4 w-4" />
            <AlertTitle>Não foi possível carregar</AlertTitle>
            <AlertDescription>Verifique sua conexão e tente novamente. Se o problema persistir, contate o suporte.</AlertDescription>
          </Alert>
          <Button onClick={() => void refetch()}>Tentar novamente</Button>
        </CardContent>
      </Card>
    );
  }

  const status = data?.status;
  const health = data?.health;
  const jobs = data?.jobs ?? [];
  const timeline = data?.timeline ?? [];
  const diagnosis = data?.diagnosis;
  const config = data?.config;

  return (
    <div className="space-y-6">
      <Card className="rounded-sm border-border/60 bg-gradient-to-br from-background to-primary/5">
        <CardContent className="grid gap-4 p-6 md:grid-cols-4">
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Situação</p>
            <p className="text-sm font-medium">{translateStatus(status?.status_canonico) || "Não configurado"}</p>
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Conexão</p>
            <p className="text-sm font-medium">{translateStatus(health?.status) || "Desconectado"}</p>
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Última Busca</p>
            <p className="text-sm font-medium">{formatDateTime(status?.ultimo_sync || health?.checked_at)}</p>
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Próxima Busca</p>
            <p className="text-sm font-medium">{formatDateTime(status?.proximo_sync)}</p>
          </div>
          <div className="md:col-span-4 flex flex-wrap items-center gap-2 pt-2">
            <Badge variant={statusVariant(health?.status ?? status?.status_canonico ?? null)}>
              {readinessLabel}
            </Badge>
            {status?.status_conexao && status.status_conexao !== "sem status" ? (
              <Badge variant="outline">{translateStatus(status.status_conexao)}</Badge>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="visao_geral" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="visao_geral">Visão Geral</TabsTrigger>
          <TabsTrigger value="configuracao">Configuração</TabsTrigger>
          <TabsTrigger value="logs">Logs do Sistema</TabsTrigger>
        </TabsList>

        <TabsContent value="visao_geral" className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-2">
            <div className="space-y-6">
              <Card className="rounded-sm">
                <CardHeader>
                  <CardTitle>Última leitura climática</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 p-6 text-sm">
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Local</p>
                    <p className="font-medium">{status?.latest_weather?.location || "Não disponível"}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Condição</p>
                    <p className="font-medium">{status?.latest_weather?.condition || "Não disponível"}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Temperatura</p>
                    <p className="font-medium">
                      {status?.latest_weather?.temperature ?? "—"} {status?.latest_weather?.units === "metric" ? "°C" : status?.latest_weather?.units === "imperial" ? "°F" : status?.latest_weather?.units === "standard" ? "K" : (status?.latest_weather?.units || "")}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Umidade</p>
                    <p className="font-medium">{status?.latest_weather?.humidity ?? "—"}%</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Chuva</p>
                    <p className="font-medium">{status?.latest_weather?.rainfall_mm ?? "—"} mm</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase text-muted-foreground">Vento</p>
                    <p className="font-medium">{status?.latest_weather?.wind_speed ?? "—"} m/s</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs uppercase text-muted-foreground">Atualizado em</p>
                    <p className="font-medium">{formatDateTime(status?.latest_weather?.observed_at)}</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-sm">
                <CardHeader>
                  <CardTitle>Diagnóstico da Conexão</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 p-6">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Situação Atual</p>
                      <p className="font-medium">{translateStatus(health?.status) || "Desconectado"}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Falhas Seguidas</p>
                      <p className="font-medium">{health?.consecutive_failures ?? 0}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Último sucesso</p>
                      <p className="font-medium">{formatDateTime(health?.last_success_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs uppercase text-muted-foreground">Última falha</p>
                      <p className="font-medium">{formatDateTime(health?.last_failure_at)}</p>
                    </div>
                  </div>
                  <Separator />
                  <p className="text-sm text-muted-foreground">{health?.summary || diagnosis?.recomendacao_operacional || "Aguardando validação inicial."}</p>
                  <Separator />
                  <div className="space-y-2">
                    <p className="text-xs uppercase text-muted-foreground">Regras de Sincronização</p>
                    <div className="flex flex-wrap gap-2">
                      {(status?.policies_resumidas?.length ? status.policies_resumidas : [{ feature_code: "current_weather", mode: "PULL", ativa: true }]).map((policy) => (
                        <Badge key={String(policy.feature_code)} variant={policy.ativa ? "default" : "secondary"}>
                          {translateFeature(String(policy.feature_code))} · {translateMode(String(policy.mode))}
                          {policy.trigger_expression ? ` · ${translateCronExpression(String(policy.trigger_expression))}` : ""}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              <Card className="rounded-sm">
                <CardHeader>
                  <CardTitle>Recursos Ativados</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2 p-6">
                  {(status?.features_habilitadas?.length ? status.features_habilitadas : ["current_weather"]).map((feature) => (
                    <Badge key={feature} variant={feature === "current_weather" ? "default" : "secondary"}>
                      {translateFeature(feature)}
                    </Badge>
                  ))}
                </CardContent>
              </Card>

              <Card className="rounded-sm">
                <CardHeader>
                  <CardTitle>Resumo do Diagnóstico</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 p-6 text-sm">
                  <p><strong>Último sucesso:</strong> {formatDateTime(diagnosis?.ultimo_sucesso_at)}</p>
                  <p><strong>Última falha:</strong> {formatDateTime(diagnosis?.ultima_falha_at)}</p>
                  <p><strong>Recurso com Problemas:</strong> {translateFeature(diagnosis?.feature_mais_problematica) || "Nenhum"}</p>
                  <p><strong>Recomendação:</strong> {diagnosis?.recomendacao_operacional || "Executar uma consulta de teste."}</p>
                </CardContent>
              </Card>

              <Card className="rounded-sm">
                <CardHeader>
                  <CardTitle>Últimas Tarefas Executadas</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 p-6">
                  {jobs.length === 0 ? (
                    <p className="text-sm text-muted-foreground">Nenhuma tarefa registrada.</p>
                  ) : jobs.map((job) => (
                    <div key={job.id} className="rounded-sm border p-3 text-sm">
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant={statusVariant(job.job_status)}>{translateStatus(job.job_status) || job.job_status}</Badge>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{translateFeature(job.feature_code) || "Clima Atual"}</span>
                          {job.trigger_type ? <span className="text-xs text-muted-foreground">· {translateTriggerType(job.trigger_type)}</span> : null}
                        </div>
                      </div>
                      <p className="mt-2 text-muted-foreground">
                        {job.processados} processado(s) · {job.sucessos} com sucesso · {job.erros} com erro
                      </p>
                      <p className="text-xs text-muted-foreground">{formatDateTime(job.started_at)} → {formatDateTime(job.finished_at)}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="configuracao" className="space-y-6">
          <Card className="rounded-sm">
            <CardHeader>
              <CardTitle>Configurações da Conta</CardTitle>
              <CardDescription>Chave de acesso e parâmetros de conexão para buscar os dados de clima.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 p-6 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="api_key" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  API Key
                </Label>
                <Input
                  id="api_key"
                  className="h-8 rounded-sm text-sm"
                  type="password"
                  value={form.api_key ?? ""}
                  onChange={(event) => setForm((prev) => ({ ...prev, api_key: event.target.value }))}
                  placeholder={config?.api_key_configured ? "Atualizar apenas se necessário" : "Informe a API Key"}
                />
                <p className="text-xs text-muted-foreground">
                  A credencial é mascarada na resposta e nunca exibida em texto puro.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="api_base_url" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Endereço do Serviço (URL Base)
                </Label>
                <Input
                  id="api_base_url"
                  className="h-8 rounded-sm text-sm"
                  value={form.api_base_url}
                  onChange={(event) => setForm((prev) => ({ ...prev, api_base_url: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="environment" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Ambiente
                </Label>
                <Input
                  id="environment"
                  className="h-8 rounded-sm text-sm"
                  value={form.environment}
                  onChange={(event) => setForm((prev) => ({ ...prev, environment: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="location_query" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Localização
                </Label>
                <Input
                  id="location_query"
                  className="h-8 rounded-sm text-sm"
                  value={form.location_query}
                  onChange={(event) => setForm((prev) => ({ ...prev, location_query: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="units" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Unidades
                </Label>
                <Input
                  id="units"
                  className="h-8 rounded-sm text-sm"
                  value={form.units}
                  onChange={(event) => setForm((prev) => ({ ...prev, units: event.target.value as OpenWeatherConfigUpsert["units"] }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="language" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Idioma
                </Label>
                <Input
                  id="language"
                  className="h-8 rounded-sm text-sm"
                  value={form.language}
                  onChange={(event) => setForm((prev) => ({ ...prev, language: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timeout_seconds" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Tempo limite de espera (segundos)
                </Label>
                <Input
                  id="timeout_seconds"
                  type="number"
                  className="h-8 rounded-sm text-sm"
                  min={5}
                  max={120}
                  value={form.timeout_seconds}
                  onChange={(event) => setForm((prev) => ({ ...prev, timeout_seconds: Number(event.target.value || 20) }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cache_ttl_seconds" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Tempo de armazenamento local (segundos)
                </Label>
                <Input
                  id="cache_ttl_seconds"
                  type="number"
                  className="h-8 rounded-sm text-sm"
                  min={60}
                  max={86400}
                  value={form.cache_ttl_seconds}
                  onChange={(event) => setForm((prev) => ({ ...prev, cache_ttl_seconds: Number(event.target.value || 1800) }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="daily_quota" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Cota Diária (Requisições)
                </Label>
                <Input
                  id="daily_quota"
                  type="number"
                  className="h-8 rounded-sm text-sm"
                  min={0}
                  max={1000000}
                  value={form.daily_quota}
                  onChange={(event) => setForm((prev) => ({ ...prev, daily_quota: Number(event.target.value || 1000) }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sync_frequency_minutes" className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Periodicidade (Minutos)
                </Label>
                <Input
                  id="sync_frequency_minutes"
                  type="number"
                  className="h-8 rounded-sm text-sm"
                  min={15}
                  max={1440}
                  value={form.sync_frequency_minutes}
                  onChange={(event) => setForm((prev) => ({ ...prev, sync_frequency_minutes: Number(event.target.value || 60) }))}
                />
              </div>

              <div className="flex flex-wrap gap-2 md:col-span-2">
                <Button size="sm" onClick={() => void handleSave()} disabled={saveMutation.isPending || !activeFazendaId}>
                  {saveMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                  Salvar configuração
                </Button>
                <Button size="sm" variant="secondary" onClick={() => void testMutation.mutateAsync()} disabled={testMutation.isPending || !config}>
                  {testMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <TestTube2 className="mr-2 h-4 w-4" />}
                  Testar conexão
                </Button>
                <Button size="sm" variant="outline" onClick={() => void syncMutation.mutateAsync()} disabled={syncMutation.isPending || !config}>
                  {syncMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  Consultar clima atual
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card className="rounded-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Logs de Integração
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-6">
              {timeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhuma atividade registrada.</p>
              ) : timeline.map((item) => (
                <div key={item.id} className="rounded-sm border p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={statusVariant(item.status)}>{translateStatus(item.status)}</Badge>
                    {item.origem_dado ? <Badge variant="outline">{translateOrigemDado(item.origem_dado)}</Badge> : null}
                    {item.tipo_registro ? <Badge variant="secondary">{translateTipoRegistro(item.tipo_registro)}</Badge> : null}
                    {item.feature_code ? <Badge variant="secondary">{translateFeature(item.feature_code)}</Badge> : null}
                  </div>
                  <p className="mt-2 font-medium">{item.resumo}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDateTime(item.occurred_at)} · {translateEventType(item.event_type)} · {item.processados} processado(s) · {item.erros} com erro
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
