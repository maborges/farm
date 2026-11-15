"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  Check,
  CheckCircle2,
  Loader2,
  MonitorCog,
  Plus,
  RefreshCw,
  Scale,
  Shield,
  UserRound,
  WifiOff,
  X,
  XCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { TaraWeighingsTable } from "@/components/balanca/tara-weighings-table";

type TaraConfig = {
  id: number;
  tenant_id: string;
  base_url: string;
  client_id: string;
  client_secret_configured: boolean;
  client_system?: string | null;
  client_tenant_id?: string | null;
  tara_client_id?: string | null;
  status: string;
};

type TaraOperator = {
  id?: string;
  codigo?: string;
  external_id?: string;
  identificador_externo?: string;
  display_name?: string;
  nome_exibicao?: string;
  status?: string;
};

type StationForm = { station_id: string; name: string };

function asOperators(value: unknown): TaraOperator[] {
  const rows = Array.isArray(value)
    ? value
    : typeof value === "object" && value !== null && "items" in value && Array.isArray(value.items)
    ? value.items
    : [];
  return rows.filter((row): row is TaraOperator => typeof row === "object" && row !== null);
}

function statusLabel(value?: string) {
  return value === "ATIVO" || value === "ACTIVE"
    ? "Ativo"
    : value === "REVOGADO"
    ? "Revogado"
    : value ?? "Desconhecido";
}

function getFriendlyTaraConnectionMessage(
  result?: { status: string; message: string } | null,
  error?: unknown
) {
  if (result) {
    if (result.status === "CONNECTED") {
      return {
        title: "Conexão validada com sucesso!",
        message:
          "A comunicação com a Plataforma Pondaxis e a identificação do cliente foram validadas com sucesso.",
        variant: "default" as const,
        isSuccess: true,
      };
    }

    if (result.status === "INVALID_CREDENTIALS") {
      return {
        title: "Credenciais não autorizadas",
        message:
          "Não foi possível autenticar no Pondaxis. Confira se o Client ID e o Client Secret informados estão corretos e salvos.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    if (result.status === "CLIENT_NOT_AUTHORIZED") {
      return {
        title: "Cliente Pondaxis não autorizado",
        message:
          "A credencial informada não tem permissão para este cliente. Verifique os campos 'Sistema cliente' e 'Identificador do Cliente Pondaxis'.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    if (result.status === "CLIENT_NOT_REGISTERED") {
      return {
        title: "Cliente não cadastrado no Pondaxis",
        message:
          "O identificador de cliente informado ainda não existe na Plataforma Pondaxis. Verifique as configurações.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    if (
      result.status === "CONFIG_INCOMPLETE" ||
      result.status === "CLIENT_IDENTITY_INCOMPLETE"
    ) {
      return {
        title: "Configuração incompleta",
        message:
          result.message ||
          "Preencha todos os campos obrigatórios e clique em 'Salvar conexão' antes de testar.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    // TARA_UNAVAILABLE ou mensagem da API
    return {
      title: "Sem conexão com a Balança Pondaxis",
      message:
        result.message ||
        "Não conseguimos estabelecer comunicação com o servidor do Pondaxis. Verifique se o endereço da URL base está correto e se o serviço da balança está ligado.",
      variant: "destructive" as const,
      isSuccess: false,
    };
  }

  if (error) {
    let raw = "";
    if (error instanceof Error) raw = error.message;
    else if (typeof error === "object" && error !== null && "detail" in error) {
      raw = String((error as { detail?: unknown }).detail || "");
    }

    if (raw.includes("401") || raw.toLowerCase().includes("credencial")) {
      return {
        title: "Falha na autenticação com o Pondaxis",
        message:
          "Credenciais recusadas pelo servidor do Pondaxis. Verifique o Client ID e o Client Secret configurados.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    if (raw.includes("403") || raw.toLowerCase().includes("autorizad")) {
      return {
        title: "Acesso não autorizado no Pondaxis",
        message:
          "A credencial do sistema cliente não possui permissão para executar esta operação no Pondaxis.",
        variant: "destructive" as const,
        isSuccess: false,
      };
    }

    return {
      title: "Não foi possível conectar à Balança Pondaxis",
      message:
        "Não conseguimos estabelecer comunicação com o servidor do Pondaxis. Verifique se a URL informada está acessível na rede, se o serviço da balança está ativo e tente novamente.",
      variant: "destructive" as const,
      isSuccess: false,
    };
  }

  return {
    title: "Não foi possível conectar à Balança Pondaxis",
    message:
      "Verifique a URL informada, suas credenciais salvas e se o serviço da balança está em execução.",
    variant: "destructive" as const,
    isSuccess: false,
  };
}

export function TaraConsole({
  section = "overview",
}: {
  section?: "overview" | "config" | "operators" | "stations" | "weighings";
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [configForm, setConfigForm] = useState({
    base_url: "",
    client_id: "",
    client_secret: "",
    client_system: "",
    client_tenant_id: "",
  });
  const [operatorForm, setOperatorForm] = useState({ external_id: "", display_name: "" });
  const [stationForm, setStationForm] = useState<StationForm>({ station_id: "", name: "" });

  // Estado para exibir o diagnóstico amigável inline após testar conexão
  const [diagnostico, setDiagnostico] = useState<{
    status: "success" | "error";
    title: string;
    message: string;
  } | null>(null);

  const configQuery = useQuery({
    queryKey: ["tara-config"],
    queryFn: () => apiFetch<TaraConfig>("/integracoes/tara/config", { suppressErrorLog: true }),
    enabled: section === "config",
    retry: false,
  });

  const operatorsQuery = useQuery({
    queryKey: ["tara-operators"],
    queryFn: async () => asOperators(await apiFetch<unknown>("/integracoes/tara/operators")),
    enabled: section === "operators",
  });

  const saveConfig = useMutation({
    mutationFn: (payload: {
      base_url: string;
      client_id: string;
      client_secret?: string;
      client_system: string;
      client_tenant_id: string;
    }) => apiFetch<TaraConfig>("/integracoes/tara/config", { method: "PUT", body: payload }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tara-config"] });
      setDiagnostico(null);
      toast({
        title: "Configuração salva com sucesso!",
        description: "Os dados de conexão com a Plataforma Pondaxis foram atualizados.",
      });
    },
  });

  const testConnection = useMutation({
    mutationFn: () =>
      apiFetch<{ status: string; message: string }>("/integracoes/tara/config/testar-conexao", {
        method: "POST",
        body: {},
        suppressErrorLog: true,
      }),
    onSuccess: (result) => {
      const friendly = getFriendlyTaraConnectionMessage(result, null);
      setDiagnostico({
        status: friendly.isSuccess ? "success" : "error",
        title: friendly.title,
        message: friendly.message,
      });
      toast({
        title: friendly.title,
        description: friendly.message,
        variant: friendly.variant,
      });
    },
    onError: (error) => {
      const friendly = getFriendlyTaraConnectionMessage(null, error);
      setDiagnostico({
        status: "error",
        title: friendly.title,
        message: friendly.message,
      });
      toast({
        title: friendly.title,
        description: friendly.message,
        variant: "destructive",
      });
    },
  });

  const createOperator = useMutation({
    mutationFn: (payload: typeof operatorForm) =>
      apiFetch<unknown>("/integracoes/tara/operators", {
        method: "POST",
        body: { external_id: payload.external_id, display_name: payload.display_name, status: "ATIVO" },
      }),
    onSuccess: () => {
      setOperatorForm({ external_id: "", display_name: "" });
      queryClient.invalidateQueries({ queryKey: ["tara-operators"] });
      toast({ title: "Operador sincronizado com sucesso!" });
    },
  });

  const revokeOperator = useMutation({
    mutationFn: (id: string) =>
      apiFetch<unknown>(`/integracoes/tara/operators/${encodeURIComponent(id)}/revoke`, {
        method: "POST",
        body: {},
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tara-operators"] });
      toast({ title: "Revogação enviada ao Pondaxis." });
    },
  });

  const activateStation = useMutation({
    mutationFn: (payload: StationForm) =>
      apiFetch<unknown>("/integracoes/tara/stations/activate", {
        method: "POST",
        body: { external_id: payload.station_id, name: payload.name },
      }),
    onSuccess: () => {
      setStationForm({ station_id: "", name: "" });
      toast({ title: "Solicitação de ativação enviada ao Pondaxis." });
    },
  });

  useEffect(() => {
    const config = configQuery.data;
    if (!config) return;
    setConfigForm((current) => ({
      base_url: current.base_url || config.base_url,
      client_id: current.client_id || config.client_id,
      client_secret: current.client_secret,
      client_system: current.client_system || config.client_system || "",
      client_tenant_id: current.client_tenant_id || config.client_tenant_id || "",
    }));
  }, [configQuery.data]);

  function submitConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !configForm.base_url.trim() ||
      !configForm.client_id.trim() ||
      !configForm.client_system.trim() ||
      !configForm.client_tenant_id.trim() ||
      (!configForm.client_secret.trim() && !config?.client_secret_configured)
    ) {
      toast({
        title: "Preencha os dados obrigatórios",
        description:
          "URL base, Client ID, sistema cliente e identificador do Cliente Pondaxis são obrigatórios; o Client Secret é necessário na primeira configuração.",
        variant: "destructive",
      });
      return;
    }
    const payload = configForm.client_secret.trim()
      ? configForm
      : {
          base_url: configForm.base_url,
          client_id: configForm.client_id,
          client_system: configForm.client_system,
          client_tenant_id: configForm.client_tenant_id,
        };
    saveConfig.mutate(payload);
  }

  function submitOperator(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (operatorForm.external_id.trim() && operatorForm.display_name.trim()) {
      createOperator.mutate(operatorForm);
    }
  }

  function submitStation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (stationForm.station_id.trim()) {
      activateStation.mutate(stationForm);
    }
  }

  const config = configQuery.data;

  return (
    <div className="flex flex-col gap-6">
      {section === "config" && (
        <Card className="border-primary/15 shadow-xs rounded-sm">
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2 text-base font-semibold">
                  <Activity className="h-4 w-4 text-primary" /> Conexão Balança Pondaxis
                </CardTitle>
                <CardDescription className="text-xs">
                  Integração por API e Webhook para pesagem de carga e animais, isolada por produtor.
                </CardDescription>
              </div>
              <Badge variant={config?.status === "ACTIVE" ? "default" : "secondary"} className="rounded-sm text-xs">
                {config?.status ?? "Não configurada"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitConfig} className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="tara-url" className="text-xs">URL base do Pondaxis *</Label>
                <Input
                  id="tara-url"
                  placeholder="https://pondaxis.exemplo.com ou http://192.168.1.50:8010"
                  value={configForm.base_url || config?.base_url || ""}
                  onChange={(e) => setConfigForm({ ...configForm, base_url: e.target.value })}
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tara-client" className="text-xs">Client ID da API Key *</Label>
                <Input
                  id="tara-client"
                  value={configForm.client_id || config?.client_id || ""}
                  onChange={(e) => setConfigForm({ ...configForm, client_id: e.target.value })}
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tara-system" className="text-xs">Sistema cliente *</Label>
                <Input
                  id="tara-system"
                  placeholder="deepfarms"
                  value={configForm.client_system || config?.client_system || ""}
                  onChange={(e) => setConfigForm({ ...configForm, client_system: e.target.value })}
                  className="h-8 text-xs rounded-sm"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="tara-client-tenant" className="text-xs">Identificador do Cliente Pondaxis *</Label>
                <Input
                  id="tara-client-tenant"
                  placeholder="fazenda-123"
                  value={configForm.client_tenant_id || config?.client_tenant_id || ""}
                  onChange={(e) => setConfigForm({ ...configForm, client_tenant_id: e.target.value })}
                  className="h-8 text-xs rounded-sm"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="tara-secret" className="text-xs">
                  Client Secret {config?.client_secret_configured ? "(já configurado)" : "*"}
                </Label>
                <Input
                  id="tara-secret"
                  type="password"
                  placeholder={
                    config?.client_secret_configured
                      ? "Segredo já configurado com segurança (preencha apenas se quiser alterar)"
                      : "Informe o segredo de autenticação"
                  }
                  value={configForm.client_secret}
                  onChange={(e) => setConfigForm({ ...configForm, client_secret: e.target.value })}
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>

              {/* Botões de Ação */}
              <div className="flex flex-wrap items-center gap-2.5 md:col-span-2 pt-1">
                <Button
                  type="submit"
                  size="sm"
                  disabled={saveConfig.isPending}
                  className="rounded-sm gap-1.5"
                >
                  {saveConfig.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Check className="h-3.5 w-3.5" />
                  )}
                  Salvar conexão
                </Button>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={
                    testConnection.isPending ||
                    !config?.client_secret_configured ||
                    !config?.client_system ||
                    !config?.client_tenant_id
                  }
                  onClick={() => testConnection.mutate()}
                  className="rounded-sm gap-1.5"
                >
                  {testConnection.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" />
                  )}
                  Testar conexão
                </Button>

                {config?.client_secret_configured && (
                  <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 pl-1">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Credencial armazenada com segurança
                  </span>
                )}
              </div>

              {/* Painel de Diagnóstico Amigável da Conexão */}
              {diagnostico && (
                <div className="md:col-span-2 pt-2">
                  {diagnostico.status === "success" ? (
                    <Alert className="border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 rounded-sm">
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                      <div className="flex items-start justify-between w-full">
                        <div>
                          <AlertTitle className="font-semibold text-sm">
                            {diagnostico.title}
                          </AlertTitle>
                          <AlertDescription className="text-xs mt-1">
                            {diagnostico.message}
                          </AlertDescription>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                          onClick={() => setDiagnostico(null)}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </Alert>
                  ) : (
                    <Alert className="border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-200 rounded-sm">
                      <WifiOff className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      <div className="flex items-start justify-between w-full">
                        <div className="space-y-2 flex-1 pr-2">
                          <AlertTitle className="font-semibold text-sm">
                            {diagnostico.title}
                          </AlertTitle>
                          <AlertDescription className="text-xs space-y-2">
                            <p>{diagnostico.message}</p>
                            <div className="text-[11px] text-muted-foreground pt-2 border-t border-amber-500/20">
                              <span className="font-medium text-foreground">Dicas para resolver:</span>
                              <ul className="list-disc list-inside mt-1 space-y-0.5">
                                <li>
                                  Confira se a <strong>URL base</strong> (<code>{configForm.base_url || config?.base_url || "não preenchida"}</code>) está correta e inclui o protocolo (ex: <code>http://...</code> ou <code>https://...</code>).
                                </li>
                                <li>
                                  Verifique se o computador ou servidor da Balança Pondaxis está ligado e conectado à rede.
                                </li>
                                <li>
                                  Caso tenha feito alterações recentes nas credenciais ou identificadores, clique primeiro em <strong>Salvar conexão</strong> antes de testar novamente.
                                </li>
                              </ul>
                            </div>
                          </AlertDescription>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground shrink-0"
                          onClick={() => setDiagnostico(null)}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </Alert>
                  )}
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      )}

      {section === "overview" && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="rounded-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UserRound className="h-4 w-4 text-primary" /> Operadores
              </CardTitle>
              <CardDescription className="text-xs">
                Projeção de operadores para o Pondaxis.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" className="rounded-sm text-xs" asChild>
                <a href="/dashboard/operacional/balanca/operadores">Administrar operadores</a>
              </Button>
            </CardContent>
          </Card>
          <Card className="rounded-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MonitorCog className="h-4 w-4 text-primary" /> Estações
              </CardTitle>
              <CardDescription className="text-xs">
                Ativação por contrato público do Pondaxis.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" className="rounded-sm text-xs" asChild>
                <a href="/dashboard/operacional/balanca/estacoes">Administrar estações</a>
              </Button>
            </CardContent>
          </Card>
          <Card className="rounded-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Scale className="h-4 w-4 text-primary" /> Pesagens
              </CardTitle>
              <CardDescription className="text-xs">
                Consulta via API e recebimento por Webhook.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" className="rounded-sm text-xs" asChild>
                <a href="/dashboard/operacional/balanca/pesagens">Acompanhar pesagens</a>
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {section === "operators" && (
        <Card className="rounded-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Operadores</CardTitle>
            <CardDescription className="text-xs">
              O cadastro local permanece no DeepFarms; o Pondaxis recebe somente a projeção técnica.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <form onSubmit={submitOperator} className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
              <Input
                aria-label="Identificador externo"
                placeholder="Identificador externo"
                value={operatorForm.external_id}
                onChange={(e) => setOperatorForm({ ...operatorForm, external_id: e.target.value })}
                className="h-8 text-xs rounded-sm"
              />
              <Input
                aria-label="Nome de exibição"
                placeholder="Nome de exibição"
                value={operatorForm.display_name}
                onChange={(e) => setOperatorForm({ ...operatorForm, display_name: e.target.value })}
                className="h-8 text-xs rounded-sm"
              />
              <Button type="submit" size="sm" disabled={createOperator.isPending} className="rounded-sm gap-1 text-xs">
                <Plus className="h-3.5 w-3.5" />
                Sincronizar
              </Button>
            </form>
            <Separator />
            {operatorsQuery.isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Carregando operadores...
              </div>
            ) : operatorsQuery.isError ? (
              <Alert variant="destructive" className="rounded-sm">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Não foi possível carregar</AlertTitle>
                <AlertDescription className="text-xs">
                  Verifique a configuração e se o serviço do Pondaxis está acessível.
                </AlertDescription>
              </Alert>
            ) : (
              <div className="space-y-2">
                {(operatorsQuery.data ?? []).length === 0 ? (
                  <p className="rounded-sm border border-dashed p-6 text-center text-sm text-muted-foreground">
                    Nenhum operador retornado pelo Pondaxis.
                  </p>
                ) : (
                  operatorsQuery.data?.map((operator, index) => (
                    <div
                      key={operator.id ?? operator.external_id ?? operator.identificador_externo ?? operator.codigo ?? index}
                      className="flex items-center justify-between rounded-sm border p-3"
                    >
                      <div>
                        <p className="font-medium text-sm">
                          {operator.display_name ?? operator.nome_exibicao ?? "Operador sem nome"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {operator.external_id ?? operator.identificador_externo ?? operator.codigo ?? "Sem identificador externo"}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={operator.status === "ATIVO" || operator.status === "ACTIVE" ? "default" : "secondary"}
                          className="rounded-sm text-xs"
                        >
                          {statusLabel(operator.status)}
                        </Badge>
                        {operator.id && operator.status !== "REVOGADO" && (
                          <Button size="sm" variant="ghost" className="rounded-sm text-xs" onClick={() => revokeOperator.mutate(operator.id!)}>
                            Revogar
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {section === "stations" && (
        <Card className="rounded-sm">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Estações</CardTitle>
            <CardDescription className="text-xs">
              Solicite a ativação de uma estação usando somente a API pública do Pondaxis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitStation} className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="station-id" className="text-xs">Identificador externo</Label>
                <Input
                  id="station-id"
                  placeholder="estacao-01"
                  value={stationForm.station_id}
                  onChange={(e) => setStationForm({ ...stationForm, station_id: e.target.value })}
                  className="h-8 text-xs rounded-sm font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="station-name" className="text-xs">Nome</Label>
                <Input
                  id="station-name"
                  placeholder="Balança principal"
                  value={stationForm.name}
                  onChange={(e) => setStationForm({ ...stationForm, name: e.target.value })}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
              <div className="md:col-span-2">
                <Button type="submit" size="sm" disabled={activateStation.isPending} className="rounded-sm gap-1.5 text-xs">
                  <Shield className="h-3.5 w-3.5" />
                  Solicitar ativação
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {section === "weighings" && <TaraWeighingsTable />}
    </div>
  );
}
