"use client";

import Link from "next/link";
import { useMemo, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock, Play, ShieldAlert, SquareCheckBig, Tractor, UserRound, XCircle } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { TierUpgradeCard } from "@/components/shared/tier-upgrade-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import { useHasTier } from "@/hooks/use-has-tier";
import { useAppStore } from "@/lib/stores/app-store";
import { cn } from "@/lib/utils";

type StatusJornada = "ABERTA" | "FINALIZADA" | "CANCELADA";

interface JornadaResumo {
  total: number;
  abertas: number;
  finalizadas: number;
  canceladas: number;
  em_uso: number;
  horas_trabalhadas: number;
  km_trabalhados: number;
}

interface JornadaItem {
  id: string;
  equipamento_id: string;
  equipamento_nome: string;
  equipamento_tipo: string;
  operador_id: string | null;
  operador_nome: string | null;
  unidade_produtiva_id: string | null;
  unidade_produtiva_nome: string | null;
  safra_id: string | null;
  safra_nome: string | null;
  talhao_id: string | null;
  talhao_nome: string | null;
  tipo_operacao: string;
  data_inicio: string;
  data_fim: string | null;
  horimetro_inicial: number | null;
  horimetro_final: number | null;
  km_inicial: number | null;
  km_final: number | null;
  status: StatusJornada;
  observacoes: string | null;
  duracao_horas: number | null;
  horas_trabalhadas: number | null;
  km_trabalhados: number | null;
  custo_estimado: number | null;
  metrica_custo: "HORA" | "KM" | "INDISPONIVEL";
}

interface JornadaResponse {
  resumo: JornadaResumo;
  jornadas: JornadaItem[];
}

interface EquipamentoOption {
  id: string;
  nome: string;
  tipo: string;
}

interface PessoaOption {
  id: string;
  nome_exibicao: string;
}

interface SafraOption {
  id: string;
  ano_safra: string;
  cultura: string | null;
}

interface TalhaoOption {
  id: string;
  nome: string;
}

const EMPTY_OPTION_VALUE = "__empty__";
const INPUT_CLASSNAME = "h-8 rounded-sm text-xs";
const SELECT_TRIGGER_CLASSNAME = "h-8 rounded-sm text-xs";
const SELECT_CONTENT_CLASSNAME = "rounded-sm text-xs";
const TEXTAREA_CLASSNAME = "min-h-24 rounded-sm text-xs";

export default function FrotaJornadasPage() {
  const { activeFazendaId } = useAppStore();
  const hasProfessionalTier = useHasTier("PROFISSIONAL");
  const queryClient = useQueryClient();
  const [selectedJornadaId, setSelectedJornadaId] = useState<string | null>(null);

  const [form, setForm] = useState({
    equipamento_id: "",
    operador_id: "",
    safra_id: "",
    talhao_id: "",
    tipo_operacao: "",
    data_inicio: toLocalDateTime(new Date()),
    horimetro_inicial: "",
    km_inicial: "",
    observacoes: "",
  });

  const [finalizacao, setFinalizacao] = useState({
    data_fim: toLocalDateTime(new Date()),
    horimetro_final: "",
    km_final: "",
    observacoes: "",
  });

  const { data, isLoading, isError, error } = useQuery<JornadaResponse>({
    queryKey: ["frota", "jornadas", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota/jornadas", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const { data: equipamentos = [] } = useQuery<EquipamentoOption[]>({
    queryKey: ["frota", "equipamentos-opcoes", activeFazendaId],
    queryFn: () =>
      apiFetch("/frota", {
        params: activeFazendaId ? { unidade_produtiva_id: activeFazendaId } : undefined,
      }),
    enabled: hasProfessionalTier,
  });

  const { data: pessoas = [] } = useQuery<PessoaOption[]>({
    queryKey: ["frota", "operadores-opcoes"],
    queryFn: () => apiFetch("/cadastros/pessoas"),
    enabled: hasProfessionalTier,
  });

  const { data: safras = [] } = useQuery<SafraOption[]>({
    queryKey: ["frota", "safras-opcoes"],
    queryFn: () => apiFetch("/safras/"),
    enabled: hasProfessionalTier,
  });

  const { data: talhoes = [] } = useQuery<TalhaoOption[]>({
    queryKey: ["frota", "talhoes-opcoes", activeFazendaId],
    queryFn: () =>
      apiFetch("/cadastros/areas-rurais", {
        params: {
          tipo: "TALHAO",
          unidade_produtiva_id: activeFazendaId || undefined,
        },
      }),
    enabled: hasProfessionalTier && Boolean(activeFazendaId),
  });

  const jornadasAbertas = useMemo(
    () => data?.jornadas.filter((item) => item.status === "ABERTA") ?? [],
    [data?.jornadas]
  );

  const selectedJornada = useMemo(
    () => data?.jornadas.find((item) => item.id === selectedJornadaId) ?? null,
    [data?.jornadas, selectedJornadaId]
  );

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["frota", "jornadas"] });
    queryClient.invalidateQueries({ queryKey: ["frota", "dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["frota", "disponibilidade"] });
  };

  const criarMutation = useMutation({
    mutationFn: () =>
      apiFetch("/frota/jornadas", {
        method: "POST",
        body: {
          equipamento_id: form.equipamento_id,
          operador_id: form.operador_id || null,
          unidade_produtiva_id: activeFazendaId || null,
          safra_id: form.safra_id || null,
          talhao_id: form.talhao_id || null,
          tipo_operacao: form.tipo_operacao,
          data_inicio: new Date(form.data_inicio).toISOString(),
          horimetro_inicial: form.horimetro_inicial ? Number(form.horimetro_inicial) : null,
          km_inicial: form.km_inicial ? Number(form.km_inicial) : null,
          observacoes: form.observacoes || null,
        },
      }),
    onSuccess: () => {
      invalidateAll();
      setForm({
        equipamento_id: "",
        operador_id: "",
        safra_id: "",
        talhao_id: "",
        tipo_operacao: "",
        data_inicio: toLocalDateTime(new Date()),
        horimetro_inicial: "",
        km_inicial: "",
        observacoes: "",
      });
      toast.success("Jornada iniciada com sucesso.");
    },
    onError: (mutationError: Error) => toast.error(mutationError.message || "Erro ao iniciar jornada."),
  });

  const finalizarMutation = useMutation({
    mutationFn: () => {
      if (!selectedJornadaId) {
        throw new Error("Selecione uma jornada aberta.");
      }
      return apiFetch(`/frota/jornadas/${selectedJornadaId}/finalizar`, {
        method: "POST",
        body: {
          data_fim: new Date(finalizacao.data_fim).toISOString(),
          horimetro_final: finalizacao.horimetro_final ? Number(finalizacao.horimetro_final) : null,
          km_final: finalizacao.km_final ? Number(finalizacao.km_final) : null,
          observacoes: finalizacao.observacoes || null,
        },
      });
    },
    onSuccess: () => {
      invalidateAll();
      setSelectedJornadaId(null);
      setFinalizacao({
        data_fim: toLocalDateTime(new Date()),
        horimetro_final: "",
        km_final: "",
        observacoes: "",
      });
      toast.success("Jornada finalizada com sucesso.");
    },
    onError: (mutationError: Error) => toast.error(mutationError.message || "Erro ao finalizar jornada."),
  });

  const cancelarMutation = useMutation({
    mutationFn: (jornadaId: string) =>
      apiFetch(`/frota/jornadas/${jornadaId}/cancelar`, {
        method: "POST",
        body: { observacoes: "Cancelada pela operação." },
      }),
    onSuccess: () => {
      invalidateAll();
      setSelectedJornadaId(null);
      toast.success("Jornada cancelada.");
    },
    onError: (mutationError: Error) => toast.error(mutationError.message || "Erro ao cancelar jornada."),
  });

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Jornadas"
        description="Apontamento de uso dos equipamentos com início, fim, operação, operador e atualização de leitura."
        icon={<Clock className="text-primary" size={22} />}
        breadcrumbs={[
          { label: "Operacional", href: "/operacional" },
          { label: "Frota", href: "/dashboard/operacional/frota" },
          { label: "Jornadas" },
        ]}
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota">
                <Tractor className="size-3.5" />
                Dashboard Frota
              </Link>
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard/operacional/frota/disponibilidade">
                <ShieldAlert className="size-3.5" />
                Disponibilidade
              </Link>
            </Button>
          </>
        }
      />

      {!hasProfessionalTier ? (
        <TierUpgradeCard
          title="Jornadas disponíveis no Profissional"
          description="Acompanhamento operacional de uso real, horas, km e custo estimado exige o plano Profissional."
          requiredTier="PROFISSIONAL"
          feature="frota_jornadas"
          surface="frota_jornadas_page"
        />
      ) : null}

      {isLoading ? <JornadasSkeleton /> : null}

      {hasProfessionalTier && !isLoading && isError ? (
        <Card className="rounded-sm shadow-sm">
          <CardContent className="p-6">
            <EmptyState
              icon={<ShieldAlert />}
              title="Não foi possível carregar as jornadas"
              description={error instanceof Error ? error.message : "Erro ao consultar o backend."}
            />
          </CardContent>
        </Card>
      ) : null}

      {hasProfessionalTier && !isLoading && !isError && data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            <ResumoCard title="Em uso" value={data.resumo.em_uso} icon={Play} tone={data.resumo.em_uso > 0 ? "warning" : "default"} />
            <ResumoCard title="Abertas" value={data.resumo.abertas} icon={Clock} tone={data.resumo.abertas > 0 ? "warning" : "default"} />
            <ResumoCard title="Finalizadas" value={data.resumo.finalizadas} icon={SquareCheckBig} />
            <ResumoCard title="Canceladas" value={data.resumo.canceladas} icon={XCircle} tone={data.resumo.canceladas > 0 ? "danger" : "default"} />
            <ResumoCard title="Horas trabalhadas" value={formatNumber(data.resumo.horas_trabalhadas)} icon={Tractor} />
            <ResumoCard title="KM trabalhados" value={formatNumber(data.resumo.km_trabalhados)} icon={UserRound} />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,1fr)]">
            <Card className="rounded-sm shadow-sm">
              <CardHeader>
                <CardTitle>Iniciar jornada</CardTitle>
                <CardDescription>Abra uma jornada para um equipamento disponível no contexto operacional atual.</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <Field label="Equipamento">
                  <Select value={form.equipamento_id} onValueChange={(value) => setForm((current) => ({ ...current, equipamento_id: value }))}>
                    <SelectTrigger className={SELECT_TRIGGER_CLASSNAME}>
                      <SelectValue placeholder="Selecione" />
                    </SelectTrigger>
                    <SelectContent className={SELECT_CONTENT_CLASSNAME}>
                      {equipamentos.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.nome} • {item.tipo}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Operador">
                  <Select
                    value={form.operador_id || EMPTY_OPTION_VALUE}
                    onValueChange={(value) => setForm((current) => ({ ...current, operador_id: value === EMPTY_OPTION_VALUE ? "" : value }))}
                  >
                    <SelectTrigger className={SELECT_TRIGGER_CLASSNAME}>
                      <SelectValue placeholder="Sem operador" />
                    </SelectTrigger>
                    <SelectContent className={SELECT_CONTENT_CLASSNAME}>
                      <SelectItem value={EMPTY_OPTION_VALUE}>Sem operador</SelectItem>
                      {pessoas.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.nome_exibicao}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Tipo de operação">
                  <Input
                    className={INPUT_CLASSNAME}
                    value={form.tipo_operacao}
                    onChange={(event) => setForm((current) => ({ ...current, tipo_operacao: event.target.value }))}
                    placeholder="Ex: Plantio, Transporte, Pulverização"
                  />
                </Field>
                <Field label="Início">
                  <Input
                    className={INPUT_CLASSNAME}
                    type="datetime-local"
                    value={form.data_inicio}
                    onChange={(event) => setForm((current) => ({ ...current, data_inicio: event.target.value }))}
                  />
                </Field>
                <Field label="Horímetro inicial">
                  <Input
                    className={INPUT_CLASSNAME}
                    type="number"
                    step="0.01"
                    value={form.horimetro_inicial}
                    onChange={(event) => setForm((current) => ({ ...current, horimetro_inicial: event.target.value }))}
                    placeholder="Opcional"
                  />
                </Field>
                <Field label="KM inicial">
                  <Input
                    className={INPUT_CLASSNAME}
                    type="number"
                    step="0.01"
                    value={form.km_inicial}
                    onChange={(event) => setForm((current) => ({ ...current, km_inicial: event.target.value }))}
                    placeholder="Opcional"
                  />
                </Field>
                <Field label="Safra">
                  <Select
                    value={form.safra_id || EMPTY_OPTION_VALUE}
                    onValueChange={(value) => setForm((current) => ({ ...current, safra_id: value === EMPTY_OPTION_VALUE ? "" : value }))}
                  >
                    <SelectTrigger className={SELECT_TRIGGER_CLASSNAME}>
                      <SelectValue placeholder="Sem safra" />
                    </SelectTrigger>
                    <SelectContent className={SELECT_CONTENT_CLASSNAME}>
                      <SelectItem value={EMPTY_OPTION_VALUE}>Sem safra</SelectItem>
                      {safras.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {[item.ano_safra, item.cultura].filter(Boolean).join(" • ")}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Talhão">
                  <Select
                    value={form.talhao_id || EMPTY_OPTION_VALUE}
                    onValueChange={(value) => setForm((current) => ({ ...current, talhao_id: value === EMPTY_OPTION_VALUE ? "" : value }))}
                  >
                    <SelectTrigger className={SELECT_TRIGGER_CLASSNAME}>
                      <SelectValue placeholder="Sem talhão" />
                    </SelectTrigger>
                    <SelectContent className={SELECT_CONTENT_CLASSNAME}>
                      <SelectItem value={EMPTY_OPTION_VALUE}>Sem talhão</SelectItem>
                      {talhoes.map((item) => (
                        <SelectItem key={item.id} value={item.id}>
                          {item.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <div className="md:col-span-2">
                  <Field label="Observações">
                    <Textarea
                      className={TEXTAREA_CLASSNAME}
                      value={form.observacoes}
                      onChange={(event) => setForm((current) => ({ ...current, observacoes: event.target.value }))}
                      placeholder="Contexto opcional da jornada"
                    />
                  </Field>
                </div>
                <div className="md:col-span-2 flex justify-end">
                  <Button
                    onClick={() => criarMutation.mutate()}
                    disabled={criarMutation.isPending || !form.equipamento_id || !form.tipo_operacao || !form.data_inicio}
                  >
                    <Play className="size-4" />
                    Iniciar jornada
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-sm shadow-sm">
              <CardHeader>
                <CardTitle>Finalizar jornada</CardTitle>
                <CardDescription>Selecione uma jornada aberta para fechar uso, duração e leitura final.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select
                  value={selectedJornadaId || EMPTY_OPTION_VALUE}
                  onValueChange={(value) => setSelectedJornadaId(value === EMPTY_OPTION_VALUE ? null : value)}
                >
                  <SelectTrigger className={SELECT_TRIGGER_CLASSNAME}>
                    <SelectValue placeholder="Selecione uma jornada aberta" />
                  </SelectTrigger>
                  <SelectContent className={SELECT_CONTENT_CLASSNAME}>
                    <SelectItem value={EMPTY_OPTION_VALUE}>Selecione uma jornada aberta</SelectItem>
                    {jornadasAbertas.map((item) => (
                      <SelectItem key={item.id} value={item.id}>
                        {item.equipamento_nome} • {item.tipo_operacao} • {formatDateTime(item.data_inicio)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedJornada ? (
                  <div className="space-y-4 rounded-sm border p-4">
                    <div className="text-sm font-medium">{selectedJornada.equipamento_nome}</div>
                    <div className="text-xs text-muted-foreground">
                      {selectedJornada.tipo_operacao} • início em {formatDateTime(selectedJornada.data_inicio)}
                    </div>
                    <Field label="Fim">
                      <Input
                        className={INPUT_CLASSNAME}
                        type="datetime-local"
                        value={finalizacao.data_fim}
                        onChange={(event) => setFinalizacao((current) => ({ ...current, data_fim: event.target.value }))}
                      />
                    </Field>
                    <Field label="Horímetro final">
                      <Input
                        className={INPUT_CLASSNAME}
                        type="number"
                        step="0.01"
                        value={finalizacao.horimetro_final}
                        onChange={(event) => setFinalizacao((current) => ({ ...current, horimetro_final: event.target.value }))}
                        placeholder="Opcional"
                      />
                    </Field>
                    <Field label="KM final">
                      <Input
                        className={INPUT_CLASSNAME}
                        type="number"
                        step="0.01"
                        value={finalizacao.km_final}
                        onChange={(event) => setFinalizacao((current) => ({ ...current, km_final: event.target.value }))}
                        placeholder="Opcional"
                      />
                    </Field>
                    <Field label="Observações">
                      <Textarea
                        className={TEXTAREA_CLASSNAME}
                        value={finalizacao.observacoes}
                        onChange={(event) => setFinalizacao((current) => ({ ...current, observacoes: event.target.value }))}
                        placeholder="Observações de encerramento"
                      />
                    </Field>
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        onClick={() => cancelarMutation.mutate(selectedJornada.id)}
                        disabled={cancelarMutation.isPending}
                      >
                        <XCircle className="size-4" />
                        Cancelar
                      </Button>
                      <Button onClick={() => finalizarMutation.mutate()} disabled={finalizarMutation.isPending}>
                        <SquareCheckBig className="size-4" />
                        Finalizar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-sm border border-dashed p-4 text-sm text-muted-foreground">
                    Nenhuma jornada aberta selecionada.
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {data.jornadas.length === 0 ? (
            <Card className="rounded-sm shadow-sm">
              <CardContent className="p-6">
                <EmptyState
                  icon={<Clock />}
                  title="Nenhuma jornada registrada"
                  description="Inicie a primeira jornada para registrar uso operacional dos equipamentos."
                />
              </CardContent>
            </Card>
          ) : (
            <Card className="rounded-sm shadow-sm">
              <CardHeader>
                <CardTitle>Histórico de jornadas</CardTitle>
                <CardDescription>Uso operacional por equipamento com duração, leitura trabalhada e custo estimado.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Equipamento</TableHead>
                      <TableHead>Operador</TableHead>
                      <TableHead>Operação</TableHead>
                      <TableHead>Início / Fim</TableHead>
                      <TableHead>Duração</TableHead>
                      <TableHead>Leituras</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.jornadas.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="font-medium">{item.equipamento_nome}</div>
                            <div className="text-xs text-muted-foreground">{item.equipamento_tipo}</div>
                          </div>
                        </TableCell>
                        <TableCell className="align-top text-xs text-muted-foreground">
                          {item.operador_nome || "—"}
                        </TableCell>
                        <TableCell className="align-top">
                          <div className="space-y-1">
                            <div className="font-medium">{item.tipo_operacao}</div>
                            <div className="text-xs text-muted-foreground">
                              {[item.safra_nome, item.talhao_nome].filter(Boolean).join(" • ") || "Sem safra/talhão"}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="align-top text-xs">
                          <div>{formatDateTime(item.data_inicio)}</div>
                          <div className="text-muted-foreground">{item.data_fim ? formatDateTime(item.data_fim) : "Em andamento"}</div>
                        </TableCell>
                        <TableCell className="align-top text-xs">
                          <div>{item.duracao_horas !== null ? `${formatNumber(item.duracao_horas)} h` : "—"}</div>
                          <div className="text-muted-foreground">
                            {item.custo_estimado !== null ? `${formatCurrency(item.custo_estimado)} estimado` : "Sem base de custo"}
                          </div>
                        </TableCell>
                        <TableCell className="align-top text-xs">
                          <div>H: {formatRange(item.horimetro_inicial, item.horimetro_final)}</div>
                          <div>KM: {formatRange(item.km_inicial, item.km_final)}</div>
                        </TableCell>
                        <TableCell className="align-top">
                          <span className={cn("rounded-sm border px-2 py-1 text-xs", getStatusClass(item.status))}>
                            {STATUS_LABELS[item.status]}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      ) : null}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="space-y-1.5">
      <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{label}</div>
      {children}
    </label>
  );
}

function ResumoCard({
  title,
  value,
  icon: Icon,
  tone = "default",
}: {
  title: string;
  value: string | number;
  icon: typeof Clock;
  tone?: "default" | "warning" | "danger";
}) {
  return (
    <Card className={cn("rounded-sm shadow-sm", tone === "warning" && "border-amber-200", tone === "danger" && "border-red-200")}>
      <CardContent className="flex items-start gap-4 p-5">
        <div
          className={cn(
            "flex size-10 items-center justify-center rounded-sm",
            tone === "default" && "bg-primary/10 text-primary",
            tone === "warning" && "bg-amber-100 text-amber-700",
            tone === "danger" && "bg-red-100 text-red-700"
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{title}</div>
          <div className="mt-0.5 text-2xl font-black tracking-tight">{value}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function JornadasSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-32 rounded-sm" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,1fr)]">
        <Skeleton className="h-[420px] rounded-sm" />
        <Skeleton className="h-[420px] rounded-sm" />
      </div>
      <Skeleton className="h-[420px] rounded-sm" />
    </div>
  );
}

const STATUS_LABELS: Record<StatusJornada, string> = {
  ABERTA: "Aberta",
  FINALIZADA: "Finalizada",
  CANCELADA: "Cancelada",
};

function getStatusClass(status: StatusJornada) {
  switch (status) {
    case "ABERTA":
      return "border-amber-200 text-amber-700";
    case "FINALIZADA":
      return "border-emerald-200 text-emerald-700";
    default:
      return "border-red-200 text-red-700";
  }
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value ?? 0);
}

function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString("pt-BR");
}

function formatRange(initial: number | null | undefined, final: number | null | undefined) {
  return `${formatNumber(initial)} → ${formatNumber(final)}`;
}

function toLocalDateTime(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
