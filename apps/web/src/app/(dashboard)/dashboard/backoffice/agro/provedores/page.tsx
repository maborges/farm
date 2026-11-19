"use client";

import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  CloudSun,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Zap,
  KeyRound,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Activity,
  Server,
  Layers,
  ArrowRightLeft,
  AlertOctagon,
  Clock,
  ExternalLink,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { usePermission } from "@/hooks/use-permission";
import { PageHeader } from "@/components/shared/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ProviderOperationalStatusItem {
  slug: string;
  nome: string;
  is_active: boolean;
  is_fallback: boolean;
  fallback_priority?: number | null;
  status: string;
  has_credentials: boolean;
  requires_credentials: boolean;
  is_licensed: boolean;
  monthly_quota_limit: number;
  monthly_calls: number;
  quota_percentage: number;
  key_preview?: string | null;
  last_error?: string | null;
  last_tested_at?: string | null;
  latency_p95_ms?: number | null;
}

interface ProviderOperationalStatusResponse {
  active_provider: string;
  contingency_mode: boolean;
  contingency_provider?: string | null;
  providers: ProviderOperationalStatusItem[];
  fallback_chain: string[];
  timeout_seconds: number;
  cache_ttl_seconds: number;
  monthly_quota_limit: number;
  current_month_calls: number;
  quota_percentage: number;
  revision: number;
}

interface ConnectivityTestResponse {
  provider_slug: string;
  success: boolean;
  latency_ms: number;
  message: string;
  tested_at: string;
}

export default function BackofficeProvedoresClimaticosPage() {
  const queryClient = useQueryClient();
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    setHasMounted(true);
  }, []);

  // A sessão persistida no Zustand só existe no navegador. Mantém as permissões
  // desativadas no SSR e na primeira renderização do cliente para evitar markup
  // diferente durante a hidratação; após montar, aplica as permissões reais.
  const hasEditConfigPermission = usePermission("backoffice:agro:config:edit");
  const hasManageCredentialsPermission = usePermission("backoffice:agro:credentials:manage");
  const hasTriggerContingencyPermission = usePermission("backoffice:agro:contingency:trigger");
  const hasTestConnectivityPermission = usePermission("backoffice:agro:connectivity:test");
  const canEditConfig = hasMounted && hasEditConfigPermission;
  const canManageCredentials = hasMounted && hasManageCredentialsPermission;
  const canTriggerContingency = hasMounted && hasTriggerContingencyPermission;
  const canTestConnectivity = hasMounted && (hasTestConnectivityPermission || canManageCredentials);

  // Estados de modal
  const [selectedProviderForCreds, setSelectedProviderForCreds] = useState<string | null>(null);
  const [newApiKey, setNewApiKey] = useState("");
  const [forceOnIncident, setForceOnIncident] = useState(false);
  const [incidentJustification, setIncidentJustification] = useState("");
  const [contingencyDialogOpen, setContingencyDialogOpen] = useState(false);
  const [contingencyMotivo, setContingencyMotivo] = useState("");
  const [targetContingencyProvider, setTargetContingencyProvider] = useState<string>("OPEN_METEO");

  // Estado de teste de conexão
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [lastTestResult, setLastTestResult] = useState<ConnectivityTestResponse | null>(null);

  // Busca situação operacional dos provedores
  const {
    data: statusData,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery<ProviderOperationalStatusResponse>({
    queryKey: ["backoffice", "agro", "provedores"],
    queryFn: async () => {
      return await apiFetch<ProviderOperationalStatusResponse>("/backoffice/agro/provedores");
    },
    refetchInterval: 30000,
  });

  // Mutação para testar conectividade
  const testMutation = useMutation({
    mutationFn: async (providerSlug: string) => {
      setTestingProvider(providerSlug);
      return await apiFetch<ConnectivityTestResponse>("/backoffice/agro/provedores/test-connection", {
        method: "POST",
        body: JSON.stringify({ provider_slug: providerSlug }),
      });
    },
    onSuccess: (data) => {
      setLastTestResult(data);
      if (data.success) {
        toast.success(`Conexão OK com ${data.provider_slug}: ${data.latency_ms}ms`, {
          description: data.message,
        });
      } else {
        toast.error(`Falha no teste de ${data.provider_slug}`, {
          description: data.message,
        });
      }
    },
    onError: (err: any) => {
      toast.error("Erro ao executar teste de conectividade", {
        description: err.message || "Falha de rede ao contatar o backend.",
      });
    },
    onSettled: () => {
      setTestingProvider(null);
    },
  });

  // Mutação para atualizar credencial
  const credentialMutation = useMutation({
    mutationFn: async ({
      providerSlug,
      apiKey,
      force,
      justification,
    }: {
      providerSlug: string;
      apiKey: string;
      force?: boolean;
      justification?: string;
    }) => {
      return await apiFetch("/backoffice/agro/provedores/credentials", {
        method: "POST",
        body: JSON.stringify({
          provider_slug: providerSlug,
          api_key: apiKey,
          key_version: 1,
          force_on_upstream_incident: force || false,
          incident_justification: justification || undefined,
        }),
      });
    },
    onSuccess: () => {
      toast.success("Credencial atualizada com sucesso no cofre seguro!", {
        description: "A chave foi criptografada em repouso e invalidada entre os workers.",
      });
      setSelectedProviderForCreds(null);
      setNewApiKey("");
      setForceOnIncident(false);
      setIncidentJustification("");
      queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "provedores"] });
    },
    onError: (err: any) => {
      toast.error("Erro ao salvar credencial", {
        description: err.message || "Não foi possível persistir a credencial.",
      });
    },
  });

  // Mutação para acionar/desativar contingência
  const contingencyMutation = useMutation({
    mutationFn: async ({ enable, target, motivo }: { enable: boolean; target?: string; motivo: string }) => {
      return await apiFetch("/backoffice/agro/provedores/contingency/toggle", {
        method: "POST",
        body: JSON.stringify({
          enable_contingency: enable,
          target_provider: target,
          motivo: motivo,
        }),
      });
    },
    onSuccess: (res: any) => {
      toast.success(
        res.contingency_active
          ? `Contingência ATIVADA com sucesso! Provedor atual: ${res.active_provider}`
          : `Contingência DESATIVADA! Provedor primário restaurado: ${res.active_provider}`
      );
      setContingencyDialogOpen(false);
      setContingencyMotivo("");
      queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "provedores"] });
    },
    onError: (err: any) => {
      toast.error("Erro ao alternar contingência", {
        description: err.message || "Falha na transição de contingência.",
      });
    },
  });

  // Mutação para alterar provedor ativo (Hot-Swap)
  const hotSwapMutation = useMutation({
    mutationFn: async (targetSlug: string) => {
      if (!statusData) return;
      return await apiFetch("/backoffice/agro/provedores/config", {
        method: "PUT",
        body: JSON.stringify({
          active_provider: targetSlug,
          fallback_chain: statusData.fallback_chain,
          timeout_seconds: statusData.timeout_seconds,
          cache_ttl_seconds: statusData.cache_ttl_seconds,
          monthly_quota_limit: statusData.monthly_quota_limit,
          contingency_provider: statusData.contingency_provider,
        }),
      });
    },
    onSuccess: (_, targetSlug) => {
      toast.success(`Hot-swap concluído! Provedor ativo alterado para ${targetSlug}.`, {
        description: "A nova política foi propagada para os workers sem reiniciar a aplicação.",
      });
      queryClient.invalidateQueries({ queryKey: ["backoffice", "agro", "provedores"] });
    },
    onError: (err: any) => {
      toast.error("Não foi possível ativar o provedor", {
        description: err.message || "Verifique se a credencial e a licença estão válidas.",
      });
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "OPERACIONAL":
      case "ONLINE":
        return <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 bg-emerald-500/10 rounded-sm">Operacional</Badge>;
      case "SEM_CREDENCIAL":
        return <Badge variant="outline" className="border-amber-500/40 text-amber-600 bg-amber-500/10 rounded-sm">Sem Credencial</Badge>;
      case "NAO_LICENCIADO":
        return <Badge variant="outline" className="border-red-500/40 text-red-600 bg-red-500/10 rounded-sm">Não Licenciado</Badge>;
      case "COTA_EXCEDIDA":
        return <Badge variant="outline" className="border-purple-500/40 text-purple-600 bg-purple-500/10 rounded-sm">Cota Esgotada</Badge>;
      default:
        return <Badge variant="outline" className="rounded-sm">{status}</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <PageHeader
        title="Provedores Climáticos e Contingência"
        description="Administração dinâmica, cofre seguro de credenciais, cadeia de fallback e governança agrometeorológica."
        icon={<CloudSun className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />}
        breadcrumbs={[
          { label: "Backoffice", href: "/dashboard/backoffice/dashboard" },
          { label: "Agro", href: "/dashboard/backoffice/agro" },
          { label: "Provedores" },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="rounded-sm"
            >
              <RefreshCw className={`h-4 w-4 mr-1.5 ${isRefetching ? "animate-spin" : ""}`} />
              Atualizar
            </Button>
            {statusData && (
              <Button
                variant={statusData.contingency_mode ? "destructive" : "outline"}
                size="sm"
                onClick={() => setContingencyDialogOpen(true)}
                disabled={!canTriggerContingency}
                className="rounded-sm"
              >
                <AlertOctagon className="h-4 w-4 mr-1.5" />
                {statusData.contingency_mode ? "Desativar Contingência" : "Acionar Contingência"}
              </Button>
            )}
          </div>
        }
      />

      {/* Alerta de Modo de Contingência Ativo */}
      {statusData?.contingency_mode && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle className="font-semibold">
            Atenção: Modo de Contingência Operacional Ativado!
          </AlertTitle>
          <AlertDescription className="text-xs">
            As requisições públicas de previsão estão sendo atendidas pelo provedor de emergência:{" "}
            <strong>{statusData.active_provider}</strong>. O provedor primário anterior foi isolado.
          </AlertDescription>
        </Alert>
      )}

      {/* Cartões de Indicadores Gerais */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="rounded-sm shadow-sm border border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Provedor Ativo (RSC)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-7 w-28 rounded-sm" />
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-xl font-bold tracking-tight text-foreground">
                  {statusData?.active_provider}
                </span>
                <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary rounded-sm text-xs">
                  Primário
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm border border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Consumo Mensal
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-7 w-28 rounded-sm" />
            ) : (
              <div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xl font-bold tracking-tight text-foreground">
                    {statusData?.current_month_calls.toLocaleString("pt-BR")}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {statusData?.monthly_quota_limit
                      ? `de ${statusData.monthly_quota_limit.toLocaleString("pt-BR")}`
                      : "Ilimitado"}
                  </span>
                </div>
                {statusData && statusData.monthly_quota_limit > 0 && (
                  <div className="w-full bg-muted rounded-full h-1.5 mt-2 overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        statusData.quota_percentage >= 95
                          ? "bg-red-500"
                          : statusData.quota_percentage >= 80
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min(statusData.quota_percentage, 100)}%` }}
                    />
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm border border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Timeout Upstream
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-7 w-28 rounded-sm" />
            ) : (
              <div className="flex items-center justify-between">
                <span className="text-xl font-bold tracking-tight text-foreground">
                  {statusData?.timeout_seconds}s
                </span>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm shadow-sm border border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Cadeia de Fallback
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-7 w-28 rounded-sm" />
            ) : (
              <div className="text-xs text-muted-foreground truncate">
                {statusData?.fallback_chain.join(" → ") || "Nenhum fallback"}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Grid de Provedores Homologados */}
      <Card className="rounded-sm border border-border">
        <CardHeader>
          <CardTitle className="text-base font-medium">Adaptadores Meteorológicos Homologados</CardTitle>
          <CardDescription className="text-xs">
            Gerencie credenciais criptografadas em repouso (AES-256-GCM), execute testes de conectividade prévios e alterne o provedor em tempo de execução.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full rounded-sm" />
              <Skeleton className="h-20 w-full rounded-sm" />
              <Skeleton className="h-20 w-full rounded-sm" />
            </div>
          ) : (
            <div className="divide-y divide-border">
              {statusData?.providers.map((p) => {
                const isSelectedActive = statusData.active_provider === p.slug;
                const isTesting = testingProvider === p.slug;

                return (
                  <div key={p.slug} className="py-4 first:pt-0 last:pb-0 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{p.nome}</span>
                        {getStatusBadge(p.status)}
                        {isSelectedActive && (
                          <Badge variant="outline" className="border-primary/50 text-primary bg-primary/5 rounded-sm text-[10px]">
                            EM PRODUÇÃO
                          </Badge>
                        )}
                        {p.fallback_priority && (
                          <Badge variant="outline" className="rounded-sm text-[10px]">
                            Fallback #{p.fallback_priority}
                          </Badge>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        <span>
                          Credencial:{" "}
                          <strong className="font-mono text-foreground">
                            {p.requires_credentials ? p.key_preview || "Não configurada" : "Livre de chave"}
                          </strong>
                        </span>
                        {p.last_tested_at && (
                          <span>
                            Atualizado em:{" "}
                            {format(new Date(p.last_tested_at), "dd/MM/yyyy HH:mm", { locale: ptBR })}
                          </span>
                        )}
                        {p.monthly_calls > 0 && (
                          <span>
                            Chamadas no mês: <strong>{p.monthly_calls.toLocaleString("pt-BR")}</strong>
                          </span>
                        )}
                        {p.last_error && (
                          <span className="text-amber-500 font-medium">
                            Última falha: {p.last_error}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start md:self-auto">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => testMutation.mutate(p.slug)}
                        disabled={isTesting || !canTestConnectivity || (!p.has_credentials && p.requires_credentials)}
                        className="rounded-sm text-xs"
                      >
                        <Activity className={`h-3.5 w-3.5 mr-1 ${isTesting ? "animate-spin" : ""}`} />
                        {isTesting ? "Testando..." : "Testar Conexão"}
                      </Button>

                      {p.requires_credentials && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedProviderForCreds(p.slug);
                            setNewApiKey("");
                            setForceOnIncident(false);
                            setIncidentJustification("");
                          }}
                          disabled={!canManageCredentials}
                          className="rounded-sm text-xs"
                        >
                          <KeyRound className="h-3.5 w-3.5 mr-1" />
                          Gerenciar Chave
                        </Button>
                      )}

                      {!isSelectedActive && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => hotSwapMutation.mutate(p.slug)}
                          disabled={!canEditConfig || (!p.has_credentials && p.requires_credentials) || !p.is_licensed}
                          className="rounded-sm text-xs border-primary/40 hover:bg-primary/10 text-primary"
                        >
                          <Zap className="h-3.5 w-3.5 mr-1" />
                          Ativar
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal para Gerenciar Credencial */}
      <Dialog open={!!selectedProviderForCreds} onOpenChange={(open) => !open && setSelectedProviderForCreds(null)}>
        <DialogContent className="rounded-sm sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <Lock className="h-4 w-4 text-primary" />
              Cofre de Credenciais: {selectedProviderForCreds}
            </DialogTitle>
            <DialogDescription className="text-xs">
              A chave informada será pré-validada contra o endpoint do provedor e cifrada com AES-256-GCM sob chave KEK isolada.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="apiKey" className="text-xs">
                Nova Chave de API
              </Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="Insira o segredo do provedor..."
                value={newApiKey}
                onChange={(e) => setNewApiKey(e.target.value)}
                className="rounded-sm text-xs font-mono h-8"
              />
              <p className="text-[11px] text-muted-foreground">
                Mínimo de 8 caracteres. O segredo nunca será exibido em texto plano após a gravação.
              </p>
            </div>

            <div className="space-y-2 pt-1 border-t border-border/40">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="chkIncident"
                  checked={forceOnIncident}
                  onChange={(e) => setForceOnIncident(e.target.checked)}
                  className="h-3.5 w-3.5 rounded-sm"
                />
                <label htmlFor="chkIncident" className="text-[11px] text-muted-foreground cursor-pointer">
                  Forçar gravação em caso de incidente upstream do provedor
                </label>
              </div>

              {forceOnIncident && (
                <div className="space-y-1">
                  <Label htmlFor="incidentJustification" className="text-[11px] text-amber-500 font-semibold">
                    Justificativa Operacional do Incidente (Mínimo 5 caracteres)
                  </Label>
                  <Input
                    id="incidentJustification"
                    placeholder="Ex: Instabilidade no provedor confirmada via status page..."
                    value={incidentJustification}
                    onChange={(e) => setIncidentJustification(e.target.value)}
                    className="rounded-sm text-xs h-8"
                  />
                </div>
              )}
            </div>

            <Alert variant="info" className="py-2">
              <ShieldCheck />
              <AlertDescription className="text-xs">
                A rotação atualizará a revisão criptográfica sem interromper requisições ativas.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedProviderForCreds(null)}
              className="rounded-sm text-xs"
            >
              Cancelar
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (selectedProviderForCreds && newApiKey.trim()) {
                  credentialMutation.mutate({
                    providerSlug: selectedProviderForCreds,
                    apiKey: newApiKey.trim(),
                    force: forceOnIncident,
                    justification: forceOnIncident ? incidentJustification.trim() : undefined,
                  });
                }
              }}
              disabled={
                credentialMutation.isPending ||
                !newApiKey.trim() ||
                (forceOnIncident && incidentJustification.trim().length < 5)
              }
              className="rounded-sm text-xs bg-primary text-primary-foreground hover:bg-primary/90"
            >
              <Lock className="h-3.5 w-3.5 mr-1" />
              {credentialMutation.isPending ? "Validando & Criptografando..." : "Salvar no Cofre"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal para Alternar Modo de Contingência */}
      <Dialog open={contingencyDialogOpen} onOpenChange={setContingencyDialogOpen}>
        <DialogContent className="rounded-sm sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <AlertOctagon className="h-4 w-4 text-red-500" />
              {statusData?.contingency_mode ? "Desativar Contingência" : "Acionar Modo de Contingência Manual"}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {statusData?.contingency_mode
                ? "Deseja desativar a contingência e retornar ao provedor primário homologado?"
                : "O acionamento de contingência desviará o tráfego público do provedor ativo para o adaptador de emergência."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {!statusData?.contingency_mode && (
              <div className="space-y-1.5">
                <Label className="text-xs">Provedor de Destino da Emergência</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    type="button"
                    variant={targetContingencyProvider === "OPEN_METEO" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTargetContingencyProvider("OPEN_METEO")}
                    className="rounded-sm text-xs"
                  >
                    Open-Meteo
                  </Button>
                  <Button
                    type="button"
                    variant={targetContingencyProvider === "OPENWEATHER" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setTargetContingencyProvider("OPENWEATHER")}
                    className="rounded-sm text-xs"
                  >
                    OpenWeather
                  </Button>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="motivoContingencia" className="text-xs">
                Justificativa Operacional (Obrigatória para Auditoria)
              </Label>
              <Input
                id="motivoContingencia"
                placeholder="Ex: Instabilidade severa ou timeout upstream na WeatherAPI..."
                value={contingencyMotivo}
                onChange={(e) => setContingencyMotivo(e.target.value)}
                className="rounded-sm text-xs h-8"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setContingencyDialogOpen(false)}
              className="rounded-sm text-xs"
            >
              Cancelar
            </Button>
            <Button
              variant={statusData?.contingency_mode ? "default" : "destructive"}
              size="sm"
              onClick={() => {
                contingencyMutation.mutate({
                  enable: !statusData?.contingency_mode,
                  target: targetContingencyProvider,
                  motivo: contingencyMotivo.trim() || "Acionamento operacional no Backoffice",
                });
              }}
              disabled={contingencyMutation.isPending || (!statusData?.contingency_mode && contingencyMotivo.trim().length < 3)}
              className="rounded-sm text-xs"
            >
              {contingencyMutation.isPending
                ? "Processando..."
                : statusData?.contingency_mode
                ? "Confirmar Retorno"
                : "Confirmar Contingência"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
