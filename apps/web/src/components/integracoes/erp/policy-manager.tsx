"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Loader2, Settings2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";

interface ErpPolicy {
  feature_code: string;
  feature_name: string;
  feature_description?: string | null;
  feature_enabled: boolean;
  mode: "MANUAL" | "AGENDADO" | string;
  record_scope: "LINKED_ONLY" | "ALL_EXTERNAL";
  ativa: boolean;
  prioridade: "LOW" | "NORMAL" | "HIGH" | "URGENT" | string;
  retry_ativo: boolean;
  retry_limite: number;
  batch_size: number;
  backoff_seconds: number;
  timeout_seconds: number;
  trigger_expression?: string | null;
  supported_modes: string[];
  endpoint_url?: string | null;
  endpoint_service?: string | null;
  endpoint_entity?: string | null;
}

const SCHEDULES = [
  { value: "*/5 * * * *", label: "A cada 5 minutos" },
  { value: "*/15 * * * *", label: "A cada 15 minutos" },
  { value: "*/30 * * * *", label: "A cada 30 minutos" },
  { value: "0 * * * *", label: "A cada hora" },
  { value: "0 */6 * * *", label: "A cada 6 horas" },
  { value: "0 */12 * * *", label: "A cada 12 horas" },
  { value: "0 0 * * *", label: "Uma vez por dia" },
] as const;

function scheduleLabel(expression?: string | null) {
  return (
    SCHEDULES.find((item) => item.value === expression)?.label || "Sem frequência definida"
  );
}

function policyModeLabel(mode: string) {
  if (mode === "AGENDADO" || mode === "SCHEDULED") return "Agendada";
  if (mode === "MANUAL" || mode === "ON_DEMAND") return "Manual";
  if (mode === "PULL" || mode === "POLLING") return "Consulta por período";
  if (mode === "EVENT" || mode === "EVENTO" || mode === "WEBHOOK") return "Por evento";
  return mode;
}

function canEditPolicy(policy: ErpPolicy) {
  return policy.supported_modes.some(
    (mode) => mode === "MANUAL" || mode === "AGENDADO" || mode === "PULL",
  );
}

export function ErpPolicyManager({ onUpdated }: { onUpdated?: () => void }) {
  const [editing, setEditing] = useState<ErpPolicy | null>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const query = useQuery({
    queryKey: ["erp-sync-policies"],
    queryFn: () => apiFetch<ErpPolicy[]>("/integracoes/erp/policies"),
  });
  const mutation = useMutation({
    mutationFn: (policy: ErpPolicy) =>
      apiFetch<ErpPolicy>(`/integracoes/erp/policies/${policy.feature_code}`, {
        method: "PATCH",
        body: {
          mode: policy.mode,
          record_scope: policy.record_scope,
          ativa: policy.ativa,
          prioridade: policy.prioridade,
          retry_ativo: policy.retry_ativo,
          retry_limite: policy.retry_limite,
          batch_size: policy.batch_size,
          backoff_seconds: policy.backoff_seconds,
          timeout_seconds: policy.timeout_seconds,
          trigger_expression: policy.mode === "AGENDADO" ? policy.trigger_expression : null,
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["erp-sync-policies"] });
      setEditing(null);
      onUpdated?.();
      toast({
        title: "Política atualizada",
        description: "A regra de sincronização foi salva.",
      });
    },
    onError: (error) => {
      toast({
        title: "Não foi possível salvar",
        description: error instanceof Error ? error.message : "Revise a regra de sincronização.",
        variant: "destructive",
      });
    },
  });

  if (query.isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="size-6 animate-spin" />
      </div>
    );
  }
  if (query.error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Não foi possível carregar as regras de atualização.
        </AlertDescription>
      </Alert>
    );
  }

  const policies = query.data || [];
  return (
    <Card className="rounded-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="size-4" />
          Regras de atualização
        </CardTitle>
        <CardDescription>
          Defina como cada fluxo busca dados no ERP. As alterações usam a política oficial
          existente.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {policies.length === 0 ? (
          <Alert>
            <AlertDescription>
              Nenhuma política foi materializada para esta integração.
            </AlertDescription>
          </Alert>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {policies.map((policy) => (
              <Card key={policy.feature_code} size="sm">
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <CardTitle>{policy.feature_name}</CardTitle>
                      <CardDescription>{policy.feature_description}</CardDescription>
                    </div>
                    <Badge variant={policy.ativa ? "default" : "secondary"}>
                      {policy.ativa ? "Ativa" : "Inativa"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Execução</p>
                    <p className="font-medium">
                      {policyModeLabel(policy.mode)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Frequência</p>
                    <p className="font-medium">
                      {policy.mode === "AGENDADO"
                        ? scheduleLabel(policy.trigger_expression)
                        : "Sob demanda"}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-xs text-muted-foreground">API consumida</p>
                    <p className="break-all font-mono text-xs">
                      {policy.endpoint_url || "Endpoint ainda não mapeado para este recurso"}
                    </p>
                  </div>
                </CardContent>
                <CardFooter>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!canEditPolicy(policy)}
                    onClick={() => setEditing({ ...policy })}
                  >
                    <Settings2 data-icon="inline-start" />
                    {canEditPolicy(policy) ? "Configurar" : "Gerenciado pelo ERP"}
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </CardContent>

      <Dialog open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] gap-0 rounded-sm p-0 sm:max-w-lg">
          <DialogHeader className="border-b">
            <div className="flex items-start gap-3 pr-8">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Settings2 className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <DialogTitle className="truncate">
                  Configurar {editing?.feature_name}
                </DialogTitle>
                <DialogDescription>
                  Defina como e quando este cadastro consulta o ERP.
                </DialogDescription>
              </div>
              {editing ? (
                <Badge variant={editing.ativa ? "default" : "secondary"}>
                  {editing.ativa ? "Ativa" : "Inativa"}
                </Badge>
              ) : null}
            </div>
          </DialogHeader>
          {editing ? (
            <form
              className="flex min-h-0 flex-1 flex-col"
              onSubmit={(event) => {
                event.preventDefault();
                mutation.mutate(editing);
              }}
            >
              <DialogBody className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto py-5">
                <Alert className="rounded-sm bg-muted/30">
                  <AlertDescription className="flex flex-col gap-1.5">
                    <span className="font-medium">API consumida por este cadastro</span>
                    <code className="break-all rounded-sm bg-background px-2 py-1.5 text-xs ring-1 ring-border">
                      {editing.endpoint_url || "Endpoint ainda não mapeado para este recurso"}
                    </code>
                    {editing.endpoint_service || editing.endpoint_entity ? (
                      <span className="text-xs text-muted-foreground">
                        Serviço: {editing.endpoint_service || "não informado"} · Entidade: {" "}
                        {editing.endpoint_entity || "não informada"}
                      </span>
                    ) : null}
                  </AlertDescription>
                </Alert>

                <div className="flex flex-col gap-4">
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor={`policy-mode-${editing.feature_code}`}>
                      Forma de execução
                    </Label>
                    <Select
                      value={editing.mode}
                      onValueChange={(mode) =>
                        setEditing({
                          ...editing,
                          mode,
                          record_scope:
                            mode === "AGENDADO" ? editing.record_scope : "LINKED_ONLY",
                        })
                      }
                    >
                      <SelectTrigger id={`policy-mode-${editing.feature_code}`}>
                        <SelectValue placeholder="Selecione a forma de execução" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {editing.supported_modes.includes("MANUAL") ? (
                            <SelectItem value="MANUAL">Manual por ID no cadastro</SelectItem>
                          ) : null}
                          {editing.supported_modes.includes("AGENDADO") ? (
                            <SelectItem value="AGENDADO">Automática</SelectItem>
                          ) : null}
                          {editing.supported_modes.includes("PULL") ? (
                            <SelectItem value="PULL">Consulta por período</SelectItem>
                          ) : null}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                  {editing.mode === "AGENDADO" ? (
                    <>
                      {editing.feature_code === "pessoas" ? (
                        <div className="flex flex-col gap-1.5">
                          <Label htmlFor="policy-record-scope-pessoas">Pessoas atualizadas</Label>
                          <Select
                            value={editing.record_scope}
                            onValueChange={(recordScope) =>
                              setEditing({
                                ...editing,
                                record_scope: recordScope as ErpPolicy["record_scope"],
                              })
                            }
                          >
                            <SelectTrigger id="policy-record-scope-pessoas">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="LINKED_ONLY">
                                Somente pessoas já vinculadas
                              </SelectItem>
                              <SelectItem value="ALL_EXTERNAL">
                                Todas as pessoas do ERP
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-muted-foreground">
                            {editing.record_scope === "ALL_EXTERNAL"
                              ? "Registros ausentes serão criados no AgroSaaS. Use somente quando todo o cadastro do ERP for necessário."
                              : "Atualiza apenas pessoas que possuem um ID do ERP vinculado no AgroSaaS."}
                          </p>
                        </div>
                      ) : null}
                      <div className="flex flex-col gap-1.5">
                        <Label htmlFor={`policy-schedule-${editing.feature_code}`}>
                          Frequência
                        </Label>
                        <Select
                          value={editing.trigger_expression || "*/15 * * * *"}
                          onValueChange={(triggerExpression) =>
                            setEditing({ ...editing, trigger_expression: triggerExpression })
                          }
                        >
                          <SelectTrigger id={`policy-schedule-${editing.feature_code}`}>
                            <SelectValue placeholder="Selecione a frequência" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              {SCHEDULES.map((schedule) => (
                                <SelectItem key={schedule.value} value={schedule.value}>
                                  {schedule.label}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  ) : null}
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor={`policy-timeout-${editing.feature_code}`}>
                      Tempo limite (segundos)
                    </Label>
                    <Input
                      id={`policy-timeout-${editing.feature_code}`}
                      type="number"
                      min={1}
                      max={3600}
                      required
                      value={editing.timeout_seconds}
                      onChange={(event) =>
                        setEditing({ ...editing, timeout_seconds: Number(event.target.value) })
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Interrompe a tentativa se o ERP não responder dentro deste período.
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-4 rounded-sm border bg-muted/30 px-3 py-2.5">
                  <div className="flex flex-col gap-0.5">
                    <Label htmlFor={`policy-active-${editing.feature_code}`}>
                      Sincronização ativa
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Permite execuções manuais ou agendadas deste cadastro.
                    </p>
                  </div>
                  <Switch
                    id={`policy-active-${editing.feature_code}`}
                    checked={editing.ativa}
                    onCheckedChange={(active) => setEditing({ ...editing, ativa: active })}
                  />
                </div>
              </DialogBody>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() => setEditing(null)}
                >
                  Cancelar
                </Button>
                <Button type="submit" size="sm" disabled={mutation.isPending}>
                  {mutation.isPending ? (
                    <Loader2 data-icon="inline-start" className="animate-spin" />
                  ) : null}
                  Salvar regra
                </Button>
              </DialogFooter>
            </form>
          ) : null}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
