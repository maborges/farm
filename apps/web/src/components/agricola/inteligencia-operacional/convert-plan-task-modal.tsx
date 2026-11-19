"use client";

import { useEffect, useMemo } from "react";
import { addDays, format } from "date-fns";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { z } from "zod/v4";
import { FilePlus2, TriangleAlert } from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";

type Severidade = "INFO" | "ATENCAO" | "RISCO_OPERACIONAL" | "RISCO_ECONOMICO" | "PRIORIDADE_CRITICA";
type PrioridadeTarefa = "BAIXA" | "MEDIA" | "ALTA" | "URGENTE";
type TipoTarefa =
  | "CALAGEM"
  | "ADUBACAO_FOSFORO"
  | "ADUBACAO_POTASSIO"
  | "ADUBACAO_NITROGENIO"
  | "GRADAGEM"
  | "PLANTIO"
  | "PULVERIZACAO"
  | "IRRIGACAO"
  | "COLHEITA"
  | "OUTRO";

interface PlanoFonte {
  origem_analitica: "PRIORIDADE" | "DIAGNOSTICO" | "RECOMENDACAO";
  codigo: string;
  titulo: string;
  severidade: Severidade;
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY" | "TENANT";
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
}

interface PlanoItem {
  id: string;
  chave: string;
  scope: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  titulo: string;
  resumo: string;
  motivo: string;
  severidade: Severidade;
  impacto_estimado?: number | null;
  acoes_sugeridas: string[];
  prazo_sugerido: string;
  contexto_operacional: string;
  origem_primaria: PlanoFonte;
  fontes_analiticas: PlanoFonte[];
  safra_id: string;
  production_unit_id?: string | null;
  unidade_produtiva_id?: string | null;
  entidade_tipo: "SAFRA" | "PRODUCTION_UNIT" | "EQUIPMENT" | "OPERATION" | "JOURNEY";
  entidade_id: string;
  entidade_label: string;
}

const taskTypes: Array<{ value: TipoTarefa; label: string }> = [
  { value: "OUTRO", label: "Outro" },
  { value: "CALAGEM", label: "Calagem" },
  { value: "ADUBACAO_FOSFORO", label: "Adubação de fósforo" },
  { value: "ADUBACAO_POTASSIO", label: "Adubação de potássio" },
  { value: "ADUBACAO_NITROGENIO", label: "Adubação de nitrogênio" },
  { value: "GRADAGEM", label: "Gradagem" },
  { value: "PLANTIO", label: "Plantio" },
  { value: "PULVERIZACAO", label: "Pulverização" },
  { value: "IRRIGACAO", label: "Irrigação" },
  { value: "COLHEITA", label: "Colheita" },
];

const priorityBySeverity: Record<Severidade, PrioridadeTarefa> = {
  PRIORIDADE_CRITICA: "URGENTE",
  RISCO_ECONOMICO: "ALTA",
  RISCO_OPERACIONAL: "ALTA",
  ATENCAO: "MEDIA",
  INFO: "BAIXA",
};

const severityTone: Record<Severidade, { label: string; className: string }> = {
  PRIORIDADE_CRITICA: { label: "Prioridade crítica", className: "bg-red-200 text-red-900 border-red-300" },
  RISCO_ECONOMICO: { label: "Risco econômico", className: "bg-red-100 text-red-700 border-red-200" },
  RISCO_OPERACIONAL: { label: "Risco operacional", className: "bg-orange-100 text-orange-700 border-orange-200" },
  ATENCAO: { label: "Atenção", className: "bg-amber-100 text-amber-700 border-amber-200" },
  INFO: { label: "Info", className: "bg-slate-100 text-slate-700 border-slate-200" },
};

const schema = z.object({
  titulo: z.string().min(3, "Título obrigatório").max(120),
  descricao: z.string().min(3, "Descrição obrigatória").max(1000),
  data_prevista: z.string().optional().transform((value) => (value?.trim() ? value : undefined)),
  prioridade: z.enum(["BAIXA", "MEDIA", "ALTA", "URGENTE"]),
  tipo: z.enum([
    "CALAGEM",
    "ADUBACAO_FOSFORO",
    "ADUBACAO_POTASSIO",
    "ADUBACAO_NITROGENIO",
    "GRADAGEM",
    "PLANTIO",
    "PULVERIZACAO",
    "IRRIGACAO",
    "COLHEITA",
    "OUTRO",
  ]),
  confirmado: z.boolean().refine((value) => value === true, { message: "Confirmação humana obrigatória." }),
});

type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

function formatScopeLabel(item: PlanoItem) {
  return `${item.entidade_tipo === "PRODUCTION_UNIT" ? "ProductionUnit" : item.entidade_tipo} • ${item.entidade_label}`;
}

function prazoParaData(prazo: string | undefined | null) {
  if (!prazo) return "";
  const normalized = prazo.toLowerCase();
  const hoje = new Date();
  if (normalized.includes("imediato")) return format(hoje, "yyyy-MM-dd");
  if (normalized.includes("48h")) return format(addDays(hoje, 2), "yyyy-MM-dd");
  if (normalized.includes("7 dias")) return format(addDays(hoje, 7), "yyyy-MM-dd");
  if (normalized.includes("15 dias")) return format(addDays(hoje, 15), "yyyy-MM-dd");
  return "";
}

function defaultValuesFor(plano: PlanoItem | null): FormInput {
  return {
    titulo: plano?.titulo ?? "",
    descricao: `${plano?.resumo ?? ""}\n\n${plano?.motivo ?? ""}`.trim(),
    data_prevista: prazoParaData(plano?.prazo_sugerido),
    prioridade: plano ? priorityBySeverity[plano.severidade] : "MEDIA",
    tipo: "OUTRO",
    confirmado: false,
  };
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  plano: PlanoItem | null;
  safraId: string;
  productionUnitId?: string | null;
  unidadeProdutivaId?: string | null;
  dataInicio?: string | null;
  dataFim?: string | null;
}

export function ConvertPlanoTaskModal({
  open,
  onOpenChange,
  plano,
  safraId,
  productionUnitId,
  unidadeProdutivaId,
  dataInicio,
  dataFim,
}: Props) {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => defaultValuesFor(plano), [plano]);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    control,
    formState: { errors },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: defaults,
  });

  useEffect(() => {
    reset(defaults);
  }, [defaults, reset]);

  const prioridadeAtual = useWatch({ control, name: "prioridade" });
  const tipoAtual = useWatch({ control, name: "tipo" });
  const confirmado = useWatch({ control, name: "confirmado" });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      if (!plano) {
        throw new Error("Plano assistido indisponível.");
      }
      return apiFetch(`/agricola/inteligencia-operacional/planos/${plano.id}/converter-tarefa`, {
        method: "POST",
        params: {
          safra_id: safraId,
          production_unit_id: productionUnitId || undefined,
          unidade_produtiva_id: unidadeProdutivaId || undefined,
          data_inicio: dataInicio || undefined,
          data_fim: dataFim || undefined,
        },
        body: values,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agricola-inteligencia-operacional"], exact: false });
      toast.success("Tarefa criada com aprovação humana explícita.");
      onOpenChange(false);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onOpenChange(false)}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FilePlus2 className="size-5 text-primary" />
            Criar tarefa real
          </DialogTitle>
        </DialogHeader>

        {plano ? (
          <div className="space-y-4">
            <div className="rounded-sm border border-border/70 bg-muted/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className={cn("rounded-sm", severityTone[plano.severidade].className)}>
                  {severityTone[plano.severidade].label}
                </Badge>
                <Badge variant="outline" className="rounded-sm bg-slate-50 text-slate-700 border-slate-200">
                  {formatScopeLabel(plano)}
                </Badge>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-semibold">{plano.titulo}</p>
                <p className="text-xs text-muted-foreground">{plano.resumo}</p>
                <p className="text-xs text-muted-foreground">{plano.motivo}</p>
              </div>
              <Alert variant="warning">
                <TriangleAlert />
                <AlertDescription>
                  Esta ação criará uma tarefa real. Nenhuma operação será executada automaticamente.
                </AlertDescription>
              </Alert>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit((values) => mutation.mutate(values))}>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="titulo">Título da tarefa *</Label>
                  <Input id="titulo" {...register("titulo")} placeholder="Ex: Revisar reconciliação econômica" />
                  {errors.titulo && <p className="text-xs text-destructive">{errors.titulo.message}</p>}
                </div>

                <div className="space-y-1.5 md:col-span-2">
                  <Label htmlFor="descricao">Descrição detalhada *</Label>
                  <Textarea
                    id="descricao"
                    {...register("descricao")}
                    rows={4}
                    placeholder="Descreva o contexto operacional e o que precisa ser validado pelo time."
                  />
                  {errors.descricao && <p className="text-xs text-destructive">{errors.descricao.message}</p>}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="data_prevista">Prazo sugerido</Label>
                  <Input id="data_prevista" type="date" {...register("data_prevista")} />
                </div>

                <div className="space-y-1.5">
                  <Label>Prioridade</Label>
                  <Select value={prioridadeAtual} onValueChange={(value) => setValue("prioridade", value as PrioridadeTarefa)}>
                    <SelectTrigger className="rounded-sm">
                      <SelectValue placeholder="Selecione a prioridade" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="BAIXA">Baixa</SelectItem>
                      <SelectItem value="MEDIA">Média</SelectItem>
                      <SelectItem value="ALTA">Alta</SelectItem>
                      <SelectItem value="URGENTE">Urgente</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label>Tipo da tarefa</Label>
                  <Select value={tipoAtual} onValueChange={(value) => setValue("tipo", value as TipoTarefa)}>
                    <SelectTrigger className="rounded-sm">
                      <SelectValue placeholder="Selecione o tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      {taskTypes.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2 md:col-span-2 rounded-sm border border-dashed border-border/70 p-3 bg-background">
                  <div className="flex items-start gap-3">
                    <Checkbox
                      id="confirmado"
                      checked={confirmado}
                      onCheckedChange={(checked) => setValue("confirmado", checked === true)}
                    />
                    <div className="space-y-1">
                      <Label htmlFor="confirmado" className="text-sm font-medium">
                        Confirmo que esta ação criará uma tarefa real
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        A conversão será auditada e vinculada ao plano assistido, sem execução automática.
                      </p>
                      {errors.confirmado && (
                        <p className="text-xs text-destructive">{errors.confirmado.message}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <DialogFooter className="pt-2">
                <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={mutation.isPending || !confirmado}>
                  {mutation.isPending ? "Criando tarefa..." : "Criar tarefa"}
                </Button>
              </DialogFooter>
            </form>
          </div>
        ) : (
          <div className="rounded-sm border border-border/70 bg-muted/20 p-4 text-sm text-muted-foreground">
            Selecione um plano assistido para converter em tarefa.
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
