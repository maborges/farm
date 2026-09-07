"use client";

import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod/v4";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const tarefaSchema = z.object({
  titulo: z.string().min(3, "Título obrigatório"),
  type: z.string().min(1, "Tipo obrigatório"),
  module: z.enum(["agricola", "pecuaria"]),
  data_programada: z.string().min(1, "Data obrigatória"),
  prioridade: z.enum(["BAIXA", "NORMAL", "ALTA", "URGENTE"]),
  unidade_produtiva_id: z.string().uuid("Fazenda obrigatória"),
  area_rural_id: z.string().uuid().optional().or(z.literal("")),
  lote_id: z.string().uuid().optional().or(z.literal("")),
  operador_id: z.string().uuid().optional().or(z.literal("")),
  dispositivo_id: z.string().uuid().optional().or(z.literal("")),
});

type TarefaFormData = z.infer<typeof tarefaSchema>;

interface Fazenda {
  id: string;
  nome: string;
}

interface Talhao {
  id: string;
  nome: string;
  unidade_produtiva_id: string;
}

interface Dispositivo {
  id: string;
  nome: string;
  status: string;
}

interface PessoaResumo {
  id: string;
  nome_exibicao: string;
}

export interface TarefaProgramada {
  id: string;
  titulo: string | null;
  type: string;
  module: string;
  origem: string;
  status_execucao: string;
  data_programada: string | null;
  prioridade: string;
  operador_id: string | null;
  dispositivo_id: string | null;
  unidade_produtiva_id: string | null;
  area_rural_id: string | null;
  lote_id: string | null;
  fase?: string | null;
  dados?: Record<string, unknown>;
  fotos?: string[];
  invalidado_em?: string | null;
  invalidado_por?: string | null;
  motivo_invalidacao?: string | null;
  created_at: string;
  updated_at: string;
}

const TIPOS_AGRICOLA = [
  { value: "APLICACAO_DEFENSIVO", label: "Aplicação de Defensivo" },
  { value: "APLICACAO_FERTILIZANTE", label: "Aplicação de Fertilizante" },
  { value: "COLHEITA_REGISTRO", label: "Registro de Colheita" },
  { value: "PLANTIO_REGISTRO", label: "Plantio" },
  { value: "IRRIGACAO_EVENTO", label: "Irrigação" },
  { value: "MONITORAMENTO_PRAGA", label: "Monitoramento de Praga" },
  { value: "AMOSTRAGEM_SOLO", label: "Amostragem de Solo" },
  { value: "PREPARO_SOLO", label: "Preparo de Solo" },
  { value: "ABASTECIMENTO_MAQUINA", label: "Abastecimento de Máquina" },
  { value: "MANUTENCAO_OCORRENCIA", label: "Ocorrência de Manutenção" },
  { value: "CHECKLIST_CAMPO", label: "Checklist de Campo" },
  { value: "OPERACAO_MECANIZADA", label: "Operação Mecanizada" },
  { value: "OUTROS_AGRICOLA", label: "Outros" },
];

const TIPOS_PECUARIA = [
  { value: "PESAGEM", label: "Pesagem" },
  { value: "PESAGEM_ANIMAL", label: "Pesagem de Animal" },
  { value: "VACINACAO", label: "Vacinação" },
  { value: "VACINACAO_LOTE", label: "Vacinação de Lote" },
  { value: "COBERTURA", label: "Cobertura" },
  { value: "DIAGNOSTICO_PRENHEZ", label: "Diagnóstico de Prenhez" },
  { value: "DESMAME", label: "Desmama" },
  { value: "MEDICACAO_ANIMAL", label: "Medicação Animal" },
  { value: "MOVIMENTACAO_LOTE", label: "Movimentação de Lote" },
  { value: "PARTO", label: "Parto" },
  { value: "PARTO_REGISTRO", label: "Registro de Parto" },
  { value: "MORTE_REGISTRO", label: "Registro de Morte" },
  { value: "INSEMINACAO", label: "Inseminação" },
];

const TIPO_LABEL = Object.fromEntries(
  [...TIPOS_AGRICOLA, ...TIPOS_PECUARIA].map((tipo) => [tipo.value, tipo.label])
) as Record<string, string>;

const QUALQUER_DISPOSITIVO_VALUE = "__qualquer_dispositivo__";

type DrawerMode = "create" | "edit" | "view";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode?: DrawerMode;
  tarefa?: TarefaProgramada | null;
}

const defaultValues: TarefaFormData = {
  titulo: "",
  type: "",
  module: "agricola",
  data_programada: new Date().toISOString().slice(0, 10),
  prioridade: "NORMAL",
  unidade_produtiva_id: "",
  area_rural_id: "",
  lote_id: "",
  operador_id: "",
  dispositivo_id: "",
};

function toFormValues(tarefa?: TarefaProgramada | null): TarefaFormData {
  if (!tarefa) return defaultValues;
  return {
    titulo: tarefa.titulo ?? "",
    type: tarefa.type ?? "",
    module: tarefa.module === "pecuaria" ? "pecuaria" : "agricola",
    data_programada: tarefa.data_programada ?? new Date().toISOString().slice(0, 10),
    prioridade: (tarefa.prioridade as TarefaFormData["prioridade"]) ?? "NORMAL",
    unidade_produtiva_id: tarefa.unidade_produtiva_id ?? "",
    area_rural_id: tarefa.area_rural_id ?? "",
    lote_id: tarefa.lote_id ?? "",
    operador_id: tarefa.operador_id ?? "",
    dispositivo_id: tarefa.dispositivo_id ?? "",
  };
}

export function TarefaDrawer({ open, onOpenChange, mode = "create", tarefa = null }: Props) {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<TarefaFormData>({
    resolver: zodResolver(tarefaSchema),
    defaultValues,
  });

  const modulo = watch("module");
  const fazendaId = watch("unidade_produtiva_id");
  const isReadOnly = mode === "view";

  useEffect(() => {
    if (!open) return;
    reset(toFormValues(tarefa));
  }, [open, tarefa, reset]);

  const { data: fazendas = [] } = useQuery<Fazenda[]>({
    queryKey: ["fazendas-list"],
    queryFn: () => apiFetch("/unidades-produtivas?limit=100"),
    enabled: open,
  });

  const { data: talhoes = [] } = useQuery<Talhao[]>({
    queryKey: ["talhoes-list", fazendaId],
    queryFn: () =>
      apiFetch(`/cadastros/areas-rurais?unidade_produtiva_id=${fazendaId}&tipo=TALHAO&limit=100`),
    enabled: !!fazendaId && open,
  });

  const { data: dispositivos = [] } = useQuery<Dispositivo[]>({
    queryKey: ["campo-dispositivos"],
    queryFn: () => apiFetch("/campo/devices"),
    enabled: open,
  });

  const { data: pessoas = [] } = useQuery<PessoaResumo[]>({
    queryKey: ["cadastros-pessoas-resumo", "ativo"],
    queryFn: () => apiFetch("/cadastros/pessoas?ativo=true&limit=500"),
    enabled: open,
  });

  const tiposDisponiveis = useMemo(
    () => (modulo === "agricola" ? TIPOS_AGRICOLA : TIPOS_PECUARIA),
    [modulo]
  );

  const fazendaNome = useMemo(
    () => fazendas.find((f) => f.id === tarefa?.unidade_produtiva_id)?.nome ?? tarefa?.unidade_produtiva_id ?? "—",
    [fazendas, tarefa?.unidade_produtiva_id]
  );
  const talhaoNome = useMemo(
    () => talhoes.find((t) => t.id === tarefa?.area_rural_id)?.nome ?? tarefa?.area_rural_id ?? "—",
    [talhoes, tarefa?.area_rural_id]
  );
  const dispositivoNome = useMemo(
    () => dispositivos.find((d) => d.id === tarefa?.dispositivo_id)?.nome ?? tarefa?.dispositivo_id ?? "—",
    [dispositivos, tarefa?.dispositivo_id]
  );
  const operadorNome = useMemo(
    () => resolveOperadorNome(tarefa, pessoas),
    [pessoas, tarefa]
  );

  const createMut = useMutation({
    mutationFn: (data: TarefaFormData) =>
      apiFetch("/campo/tarefas", {
        method: "POST",
        body: JSON.stringify({
          ...data,
          area_rural_id: data.area_rural_id || undefined,
          lote_id: data.lote_id || undefined,
          operador_id: data.operador_id || undefined,
          dispositivo_id: data.dispositivo_id || undefined,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campo-tarefas"] });
      toast.success("Tarefa programada com sucesso!");
      reset(defaultValues);
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMut = useMutation({
    mutationFn: (data: TarefaFormData) => {
      if (!tarefa) throw new Error("Tarefa não encontrada.");
      return apiFetch(`/campo/tarefas/${tarefa.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...data,
          area_rural_id: data.area_rural_id || undefined,
          lote_id: data.lote_id || undefined,
          operador_id: data.operador_id || undefined,
          dispositivo_id: data.dispositivo_id || null,
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campo-tarefas"] });
      toast.success("Tarefa atualizada com sucesso!");
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const title = mode === "view" ? "Detalhe da Tarefa" : mode === "edit" ? "Editar Tarefa" : "Nova Tarefa de Campo";
  const submitLabel = mode === "edit" ? "Salvar Alterações" : "Programar Tarefa";
  const submitHandler = mode === "edit" ? updateMut : createMut;

  const statusLabel =
    tarefa?.status_execucao === "PENDENTE"
      ? "Pendente"
      : tarefa?.status_execucao === "EM_EXECUCAO"
        ? "Em execução"
        : tarefa?.status_execucao === "CONCLUIDA"
          ? "Concluída"
          : tarefa?.status_execucao === "CANCELADA"
            ? "Cancelada"
            : tarefa?.status_execucao === "INVALIDADA"
              ? "Invalidada"
            : tarefa?.status_execucao ?? "—";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto border-l border-border/50 bg-card/95 backdrop-blur-md shadow-2xl p-0">
        <div className="flex flex-col h-full">
          <SheetHeader className="p-6 border-b border-border/40 bg-muted/10">
            <SheetTitle className="text-xl font-light">{title}</SheetTitle>
            <p className="text-xs text-muted-foreground">
              {isReadOnly
                ? "Consulte os dados da tarefa."
                : "Preencha os detalhes para programar uma nova atividade no campo."}
            </p>
          </SheetHeader>

          {isReadOnly ? (
            <div className="flex-1 space-y-4 p-6">
              <InfoRow label="Título" value={tarefa?.titulo ?? "—"} />
              <InfoRow label="Tipo de Atividade" value={formatTipoTarefa(tarefa?.type)} />
              <InfoRow label="Módulo" value={tarefa?.module === "pecuaria" ? "Pecuária" : "Agrícola"} />
              <InfoRow label="Data programada" value={tarefa?.data_programada ? new Date(`${tarefa.data_programada}T00:00:00`).toLocaleDateString("pt-BR") : "—"} />
              <InfoRow label="Prioridade" value={tarefa?.prioridade ?? "—"} />
              <InfoRow label="Status" value={statusLabel} />
              <InfoRow label="Fazenda" value={fazendaNome} />
              <InfoRow label="Talhão" value={talhaoNome} />
              <InfoRow label="Dispositivo" value={dispositivoNome} />
              <InfoRow label="Operador" value={operadorNome} />
              {tarefa?.status_execucao === "INVALIDADA" && (
                <>
                  <InfoRow label="Motivo da invalidação" value={tarefa.motivo_invalidacao ?? "—"} />
                  <InfoRow
                    label="Invalidada em"
                    value={tarefa.invalidado_em ? new Date(tarefa.invalidado_em).toLocaleString("pt-BR") : "—"}
                  />
                </>
              )}
              <InfoRow
                label="Observação"
                value={String(tarefa?.dados?.obs_execucao ?? tarefa?.dados?.obs ?? tarefa?.dados?.observacao ?? "—")}
              />
              {(tarefa?.fotos?.length ?? 0) > 0 && (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Imagens</p>
                  <div className="grid grid-cols-2 gap-3">
                    {tarefa?.fotos?.map((foto, index) => (
                      <img
                        key={`${tarefa.id}-${index}`}
                        src={foto}
                        alt={`Imagem da tarefa ${index + 1}`}
                        className="h-28 w-full rounded-sm border object-cover"
                      />
                    ))}
                  </div>
                </div>
              )}
              <div className="pt-4">
                <Button type="button" variant="outline" className="w-full rounded-sm h-11 active:scale-[0.98] transition-transform" onClick={() => onOpenChange(false)}>
                  Fechar
                </Button>
              </div>
            </div>
          ) : (
            <>
              <form
                onSubmit={handleSubmit((d) => submitHandler.mutate(d))}
                className="flex-1 p-6 space-y-6"
              >
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Título da Atividade *</Label>
                  <Input {...register("titulo")} placeholder="Ex: Aplicar herbicida no talhão 3" className="rounded-sm" />
                  {errors.titulo && <p className="text-[10px] text-destructive font-medium">{errors.titulo.message}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Módulo *</Label>
                    <Select
                      value={modulo}
                      onValueChange={(v) => {
                        setValue("module", v as "agricola" | "pecuaria");
                        setValue("type", "");
                      }}
                    >
                      <SelectTrigger className="rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        <SelectItem value="agricola">Agrícola</SelectItem>
                        <SelectItem value="pecuaria">Pecuária</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Tipo de Atividade *</Label>
                    <Select value={watch("type")} onValueChange={(v) => setValue("type", v)}>
                      <SelectTrigger className="rounded-sm">
                        <SelectValue placeholder="Selecione..." />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        {tiposDisponiveis.map((t) => (
                          <SelectItem key={t.value} value={t.value}>
                            {t.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.type && <p className="text-[10px] text-destructive font-medium">{errors.type.message}</p>}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold">Fazenda *</Label>
                  <Select value={watch("unidade_produtiva_id")} onValueChange={(v) => setValue("unidade_produtiva_id", v)}>
                    <SelectTrigger className="rounded-sm">
                      <SelectValue placeholder="Selecione a fazenda..." />
                    </SelectTrigger>
                    <SelectContent className="rounded-sm">
                      {fazendas.map((f) => (
                        <SelectItem key={f.id} value={f.id}>
                          {f.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.unidade_produtiva_id && (
                    <p className="text-[10px] text-destructive font-medium">{errors.unidade_produtiva_id.message}</p>
                  )}
                </div>

                {modulo === "agricola" && talhoes.length > 0 && (
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Talhão (opcional)</Label>
                    <Select value={watch("area_rural_id")} onValueChange={(v) => setValue("area_rural_id", v)}>
                      <SelectTrigger className="rounded-sm">
                        <SelectValue placeholder="Todos os talhões" />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        {talhoes.map((t) => (
                          <SelectItem key={t.id} value={t.id}>
                            {t.nome}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Data Programada *</Label>
                    <Input type="date" {...register("data_programada")} className="rounded-sm" />
                    {errors.data_programada && (
                      <p className="text-[10px] text-destructive font-medium">{errors.data_programada.message}</p>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Prioridade</Label>
                    <Select value={watch("prioridade")} onValueChange={(v) => setValue("prioridade", v as TarefaFormData["prioridade"])}>
                      <SelectTrigger className="rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        <SelectItem value="BAIXA">Baixa</SelectItem>
                        <SelectItem value="NORMAL">Normal</SelectItem>
                        <SelectItem value="ALTA">Alta</SelectItem>
                        <SelectItem value="URGENTE">Urgente</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {dispositivos.filter((d) => d.status === "ATIVO").length > 0 && (
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold">Dispositivo Designado (opcional)</Label>
                    <Select
                      value={watch("dispositivo_id") || QUALQUER_DISPOSITIVO_VALUE}
                      onValueChange={(v) =>
                        setValue("dispositivo_id", v === QUALQUER_DISPOSITIVO_VALUE ? "" : v, {
                          shouldDirty: true,
                          shouldValidate: true,
                        })
                      }
                    >
                      <SelectTrigger className="rounded-sm">
                        <SelectValue placeholder="Qualquer dispositivo autorizado" />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        <SelectItem value={QUALQUER_DISPOSITIVO_VALUE}>
                          Qualquer dispositivo autorizado
                        </SelectItem>
                        {dispositivos
                          .filter((d) => d.status === "ATIVO")
                          .map((d) => (
                            <SelectItem key={d.id} value={d.id}>
                              {d.nome}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </form>

              <div className="p-6 border-t border-border/40 bg-muted/10 flex items-center gap-3">
                <Button type="button" variant="outline" size="sm" className="flex-1 rounded-sm h-11 active:scale-[0.98] transition-transform" onClick={() => onOpenChange(false)}>
                  Cancelar
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="flex-1 rounded-sm h-11 bg-primary text-primary-foreground hover:bg-primary/90 border-primary/20 active:scale-[0.98] transition-transform"
                  disabled={submitHandler.isPending}
                  onClick={handleSubmit((d) => submitHandler.mutate(d))}
                >
                  {submitHandler.isPending ? "Salvando..." : submitLabel}
                </Button>
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b py-2 last:border-0">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="text-right font-medium text-foreground">{value}</span>
    </div>
  );
}

function formatTipoTarefa(type?: string | null): string {
  if (!type) return "—";
  return TIPO_LABEL[type] ?? formatEnumLabel(type);
}

function formatEnumLabel(value: string): string {
  return value
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function resolveOperadorNome(tarefa: TarefaProgramada | null, pessoas: PessoaResumo[]): string {
  if (!tarefa?.operador_id) return "—";

  const operadorNomePayload = tarefa.dados?.operador_nome;
  if (typeof operadorNomePayload === "string" && operadorNomePayload.trim()) {
    return operadorNomePayload;
  }

  const pessoa = pessoas.find((item) => item.id === tarefa.operador_id);
  if (pessoa?.nome_exibicao) return pessoa.nome_exibicao;

  return `${tarefa.operador_id.slice(0, 8)}…`;
}
