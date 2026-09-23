"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle2, Loader2, MonitorCog, Plus, RefreshCw, Scale, Shield, UserRound, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";

type TaraConfig = { id: number; tenant_id: string; base_url: string; client_id: string; client_secret_configured: boolean; client_system?: string | null; client_tenant_id?: string | null; tara_client_id?: string | null; status: string };
type TaraOperator = { id?: string; codigo?: string; external_id?: string; identificador_externo?: string; display_name?: string; nome_exibicao?: string; status?: string };
type StationForm = { station_id: string; name: string };

function asOperators(value: unknown): TaraOperator[] {
  const rows = Array.isArray(value) ? value : typeof value === "object" && value !== null && "items" in value && Array.isArray(value.items) ? value.items : [];
  return rows.filter((row): row is TaraOperator => typeof row === "object" && row !== null);
}

function statusLabel(value?: string) { return value === "ATIVO" || value === "ACTIVE" ? "Ativo" : value === "REVOGADO" ? "Revogado" : value ?? "Desconhecido"; }

function taraErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message.trim()) return error.message;
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  return fallback;
}

export function TaraConsole({ section = "overview" }: { section?: "overview" | "config" | "operators" | "stations" | "weighings" }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [configForm, setConfigForm] = useState({ base_url: "", client_id: "", client_secret: "", client_system: "", client_tenant_id: "" });
  const [operatorForm, setOperatorForm] = useState({ external_id: "", display_name: "" });
  const [stationForm, setStationForm] = useState<StationForm>({ station_id: "", name: "" });
  const configQuery = useQuery({ queryKey: ["tara-config"], queryFn: () => apiFetch<TaraConfig>("/integracoes/tara/config", { suppressErrorLog: true }), enabled: section === "config", retry: false });
  const operatorsQuery = useQuery({ queryKey: ["tara-operators"], queryFn: async () => asOperators(await apiFetch<unknown>("/integracoes/tara/operators")), enabled: section === "operators" });
  const weighingsQuery = useQuery({ queryKey: ["tara-weighings"], queryFn: () => apiFetch<{ items: Record<string, unknown>[]; next_cursor: string | null }>("/integracoes/tara/weighings", { params: { limit: 100 } }), enabled: section === "weighings" });
  const saveConfig = useMutation({ mutationFn: (payload: { base_url: string; client_id: string; client_secret?: string; client_system: string; client_tenant_id: string }) => apiFetch<TaraConfig>("/integracoes/tara/config", { method: "PUT", body: payload }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tara-config"] }); toast({ title: "Configuração salva", description: "A conexão TARA foi atualizada." }); } });
  const testConnection = useMutation({ mutationFn: () => apiFetch<{ status: string; message: string }>("/integracoes/tara/config/testar-conexao", { method: "POST", body: {}, suppressErrorLog: true }), onSuccess: (result) => { toast({ title: result.status === "CONNECTED" ? "Conexão validada" : "Diagnóstico da conexão", description: result.message, variant: result.status === "CONNECTED" ? "default" : "destructive" }); }, onError: (error) => { toast({ title: "Falha ao testar conexão", description: taraErrorMessage(error, "Verifique a configuração salva, as credenciais e a disponibilidade da TARA."), variant: "destructive" }); } });
  const createOperator = useMutation({ mutationFn: (payload: typeof operatorForm) => apiFetch<unknown>("/integracoes/tara/operators", { method: "POST", body: { external_id: payload.external_id, display_name: payload.display_name, status: "ATIVO" } }), onSuccess: () => { setOperatorForm({ external_id: "", display_name: "" }); queryClient.invalidateQueries({ queryKey: ["tara-operators"] }); toast({ title: "Operador sincronizado" }); } });
  const revokeOperator = useMutation({ mutationFn: (id: string) => apiFetch<unknown>(`/integracoes/tara/operators/${encodeURIComponent(id)}/revoke`, { method: "POST", body: {} }), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tara-operators"] }); toast({ title: "Revogação enviada" }); } });
  const activateStation = useMutation({ mutationFn: (payload: StationForm) => apiFetch<unknown>("/integracoes/tara/stations/activate", { method: "POST", body: { external_id: payload.station_id, name: payload.name } }), onSuccess: () => { setStationForm({ station_id: "", name: "" }); toast({ title: "Ativação solicitada" }); } });

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
    if (!configForm.base_url.trim() || !configForm.client_id.trim() || !configForm.client_system.trim() || !configForm.client_tenant_id.trim() || (!configForm.client_secret.trim() && !config?.client_secret_configured)) {
      toast({ title: "Preencha os dados obrigatórios", description: "URL, Client ID, sistema cliente e identificador do Cliente TARA são obrigatórios; o Client Secret é necessário na primeira configuração.", variant: "destructive" });
      return;
    }
    const payload = configForm.client_secret.trim()
      ? configForm
      : { base_url: configForm.base_url, client_id: configForm.client_id, client_system: configForm.client_system, client_tenant_id: configForm.client_tenant_id };
    saveConfig.mutate(payload);
  }
  function submitOperator(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (operatorForm.external_id.trim() && operatorForm.display_name.trim()) createOperator.mutate(operatorForm); }
  function submitStation(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (stationForm.station_id.trim()) activateStation.mutate(stationForm); }

  const config = configQuery.data;
  return <div className="flex flex-col gap-6">
    {section === "config" && <Card className="border-primary/15 shadow-sm">
      <CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle className="flex items-center gap-2"><Activity className="h-4 w-4 text-primary" /> Conexão TARA</CardTitle><CardDescription>Integração pública por API e Webhook, isolada por produtor.</CardDescription></div><Badge variant={config?.status === "ACTIVE" ? "default" : "secondary"}>{config?.status ?? "Não configurada"}</Badge></div></CardHeader>
      <CardContent><form onSubmit={submitConfig} className="grid gap-4 md:grid-cols-2"><div className="space-y-2 md:col-span-2"><Label htmlFor="tara-url">URL base da TARA</Label><Input id="tara-url" placeholder="https://tara.exemplo.com" value={configForm.base_url || config?.base_url || ""} onChange={(e) => setConfigForm({ ...configForm, base_url: e.target.value })} /></div><div className="space-y-2"><Label htmlFor="tara-client">Client ID da API Key</Label><Input id="tara-client" value={configForm.client_id || config?.client_id || ""} onChange={(e) => setConfigForm({ ...configForm, client_id: e.target.value })} /></div><div className="space-y-2"><Label htmlFor="tara-system">Sistema cliente</Label><Input id="tara-system" placeholder="deepfarms" value={configForm.client_system || config?.client_system || ""} onChange={(e) => setConfigForm({ ...configForm, client_system: e.target.value })} /></div><div className="space-y-2"><Label htmlFor="tara-client-tenant">Identificador do Cliente TARA</Label><Input id="tara-client-tenant" placeholder="fazenda-123" value={configForm.client_tenant_id || config?.client_tenant_id || ""} onChange={(e) => setConfigForm({ ...configForm, client_tenant_id: e.target.value })} /></div><div className="space-y-2 md:col-span-2"><Label htmlFor="tara-secret">Client Secret</Label><Input id="tara-secret" type="password" placeholder={config?.client_secret_configured ? "Segredo já configurado" : "Informe o segredo"} value={configForm.client_secret} onChange={(e) => setConfigForm({ ...configForm, client_secret: e.target.value })} /></div><div className="flex flex-wrap items-center gap-3 md:col-span-2"><Button type="submit" disabled={saveConfig.isPending}>{saveConfig.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Salvar conexão</Button><Button type="button" variant="outline" disabled={testConnection.isPending || !config?.client_secret_configured || !config?.client_system || !config?.client_tenant_id} onClick={() => testConnection.mutate()}>{testConnection.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}Testar conexão</Button>{config?.client_secret_configured && <span className="flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 className="h-3.5 w-3.5" /> Credencial armazenada com segurança</span>}</div></form></CardContent>
    </Card>}

    {section === "overview" && <div className="grid gap-4 md:grid-cols-3"><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><UserRound className="h-4 w-4 text-primary" /> Operadores</CardTitle><CardDescription>Projeção de operadores para a TARA.</CardDescription></CardHeader><CardContent><Button variant="outline" asChild><a href="/dashboard/operacional/balanca/operadores">Administrar operadores</a></Button></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><MonitorCog className="h-4 w-4 text-primary" /> Estações</CardTitle><CardDescription>Ativação por contrato público da TARA.</CardDescription></CardHeader><CardContent><Button variant="outline" asChild><a href="/dashboard/operacional/balanca/estacoes">Administrar estações</a></Button></CardContent></Card><Card><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Scale className="h-4 w-4 text-primary" /> Pesagens</CardTitle><CardDescription>Consulta via API e recebimento por Webhook.</CardDescription></CardHeader><CardContent><Button variant="outline" asChild><a href="/dashboard/operacional/balanca/pesagens">Acompanhar pesagens</a></Button></CardContent></Card></div>}

    {section === "operators" && <Card><CardHeader><CardTitle>Operadores</CardTitle><CardDescription>O cadastro local permanece no DeepFarms; a TARA recebe somente a projeção técnica.</CardDescription></CardHeader><CardContent className="space-y-6"><form onSubmit={submitOperator} className="grid gap-3 md:grid-cols-[1fr_1fr_auto]"><Input aria-label="Identificador externo" placeholder="Identificador externo" value={operatorForm.external_id} onChange={(e) => setOperatorForm({ ...operatorForm, external_id: e.target.value })} /><Input aria-label="Nome de exibição" placeholder="Nome de exibição" value={operatorForm.display_name} onChange={(e) => setOperatorForm({ ...operatorForm, display_name: e.target.value })} /><Button type="submit" disabled={createOperator.isPending}><Plus className="mr-2 h-4 w-4" />Sincronizar</Button></form><Separator />{operatorsQuery.isLoading ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Carregando operadores...</div> : operatorsQuery.isError ? <Alert variant="destructive"><XCircle className="h-4 w-4" /><AlertTitle>Não foi possível carregar</AlertTitle><AlertDescription>{taraErrorMessage(operatorsQuery.error, "Verifique a configuração e os escopos da TARA.")}</AlertDescription></Alert> : <div className="space-y-2">{(operatorsQuery.data ?? []).length === 0 ? <p className="rounded-sm border border-dashed p-6 text-center text-sm text-muted-foreground">Nenhum operador retornado pela TARA.</p> : operatorsQuery.data?.map((operator, index) => <div key={operator.id ?? operator.external_id ?? operator.identificador_externo ?? operator.codigo ?? index} className="flex items-center justify-between rounded-sm border p-3"><div><p className="font-medium">{operator.display_name ?? operator.nome_exibicao ?? "Operador sem nome"}</p><p className="text-xs text-muted-foreground">{operator.external_id ?? operator.identificador_externo ?? operator.codigo ?? "Sem identificador externo"}</p></div><div className="flex items-center gap-3"><Badge variant={operator.status === "ATIVO" || operator.status === "ACTIVE" ? "default" : "secondary"}>{statusLabel(operator.status)}</Badge>{operator.id && operator.status !== "REVOGADO" && <Button size="sm" variant="ghost" onClick={() => revokeOperator.mutate(operator.id!)}>Revogar</Button>}</div></div>)}</div>}</CardContent></Card>}

    {section === "stations" && <Card><CardHeader><CardTitle>Estações</CardTitle><CardDescription>Solicite a ativação de uma estação usando somente a API pública da TARA.</CardDescription></CardHeader><CardContent><form onSubmit={submitStation} className="grid gap-4 md:grid-cols-2"><div className="space-y-2"><Label htmlFor="station-id">Identificador externo</Label><Input id="station-id" placeholder="estacao-01" value={stationForm.station_id} onChange={(e) => setStationForm({ ...stationForm, station_id: e.target.value })} /></div><div className="space-y-2"><Label htmlFor="station-name">Nome</Label><Input id="station-name" placeholder="Balança principal" value={stationForm.name} onChange={(e) => setStationForm({ ...stationForm, name: e.target.value })} /></div><div className="md:col-span-2"><Button type="submit" disabled={activateStation.isPending}><Shield className="mr-2 h-4 w-4" />Solicitar ativação</Button></div></form></CardContent></Card>}

    {section === "weighings" && <Card><CardHeader><CardTitle>Pesagens recentes</CardTitle><CardDescription>Consulta somente leitura da TARA. O peso físico permanece sob responsabilidade da plataforma oficial.</CardDescription></CardHeader><CardContent>{weighingsQuery.isLoading ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Consultando TARA...</div> : weighingsQuery.isError ? <Alert variant="destructive"><XCircle className="h-4 w-4" /><AlertTitle>Falha na consulta</AlertTitle><AlertDescription>{taraErrorMessage(weighingsQuery.error, "Verifique a credencial e a disponibilidade da TARA.")}</AlertDescription></Alert> : (weighingsQuery.data?.items ?? []).length === 0 ? <p className="rounded-sm border border-dashed p-6 text-center text-sm text-muted-foreground">Nenhuma pesagem retornada.</p> : <div className="space-y-2">{weighingsQuery.data?.items.map((weighing, index) => <div key={String(weighing.id ?? weighing.local_id ?? index)} className="grid gap-2 rounded-sm border p-3 text-sm md:grid-cols-4"><span><strong>Identificador:</strong> {String(weighing.local_id ?? weighing.id ?? "—")}</span><span><strong>Peso aferido:</strong> {String(weighing.peso_aferido_kg ?? "—")} kg</span><span><strong>Status:</strong> {String(weighing.reconciliation_status ?? weighing.status ?? "—")}</span><span><strong>Data:</strong> {String(weighing.captured_at ?? weighing.data_pesagem ?? "—")}</span></div>)}</div>}</CardContent></Card>}
  </div>;
}
