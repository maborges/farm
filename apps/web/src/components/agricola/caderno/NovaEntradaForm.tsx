"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
  DialogBody,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { BookOpen, UserCircle2, Check, Loader2 } from "lucide-react";
import { PessoaSelect } from "@/components/cadastros/PessoaSelect";

interface Talhao {
  id: string;
  nome: string;
  codigo: string | null;
  area_ha: number | null;
  principal: boolean;
  unidade_produtiva_id?: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  safraId: string;
  talhoes: Talhao[];
  talhaoIdSelecionado?: string;
  onSubmit: (data: any) => Promise<void>;
  isLoading?: boolean;
}

const TIPOS = [
  { value: "MONITORAMENTO", label: "Monitoramento (praga/doença/daninha)" },
  { value: "OBSERVACAO", label: "Observação geral" },
  { value: "CLIMA", label: "Condição climática" },
  { value: "SOLO", label: "Condição do solo" },
];

const SEVERIDADES = [
  { value: "BAIXO", label: "Baixo" },
  { value: "MEDIO", label: "Médio" },
  { value: "ALTO", label: "Alto" },
  { value: "CRITICO", label: "Crítico" },
];

export function NovaEntradaForm({ open, onClose, safraId, talhoes, talhaoIdSelecionado, onSubmit, isLoading }: Props) {
  const { register, handleSubmit, control, watch, reset, setValue } = useForm({
    defaultValues: {
      talhao_id: talhaoIdSelecionado || "",
      tipo: "OBSERVACAO",
      descricao: "",
      data_registro: new Date().toISOString().split("T")[0],
      executado_por_pessoa_id: null as string | null,
      nivel_severidade: undefined as string | undefined,
      recomendacao: "",
      numero_receituario: "",
      digitalizacao_retroativa: false,
      justificativa_retroativa: "",
    },
  });

  // Sincroniza talhao_id quando o filtro externo muda
  useEffect(() => {
    if (talhaoIdSelecionado && open) {
      setValue("talhao_id", talhaoIdSelecionado);
    }
  }, [talhaoIdSelecionado, open, setValue]);

  const tipo = watch("tipo");
  const retroativa = watch("digitalizacao_retroativa");
  const dataRegistro = watch("data_registro");
  const selectedTalhaoId = watch("talhao_id");
  const selectedTalhao = talhoes.find((t) => t.id === selectedTalhaoId);
  const unidadeProdutivaId = selectedTalhao?.unidade_produtiva_id;

  const handleClose = () => {
    reset();
    onClose();
  };

  const onFormSubmit = async (data: any) => {
    if (!data.talhao_id) {
      toast.error("Selecione um talhão.");
      return;
    }
    await onSubmit({
      ...data,
      safra_id: safraId,
      talhao_id: data.talhao_id,
    });
    handleClose();
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="max-w-xl p-0">
        <DialogHeader>
          <div className="flex items-center gap-2.5">
            <div className="size-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
              <BookOpen className="size-4 text-primary" />
            </div>
            <div>
              <DialogTitle>Novo Registro no Caderno</DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Registre observações, monitoramentos e eventos do talhão com data, tipo e contexto.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form id="nova-entrada-form" onSubmit={handleSubmit(onFormSubmit)}>
          <DialogBody className="space-y-4 max-h-[70vh]">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">
                Talhão <span className="text-destructive">*</span>
              </Label>
              <Controller
                name="talhao_id"
                control={control}
                rules={{ required: "Selecione um talhão" }}
                render={({ field }) => (
                  <Select onValueChange={field.onChange} value={field.value || ""}>
                    <SelectTrigger className="h-8 text-xs rounded-sm" disabled={talhoes.length === 0}>
                      <SelectValue placeholder="Selecionar talhão..." />
                    </SelectTrigger>
                    <SelectContent className="rounded-sm">
                      {talhoes.length === 0 ? (
                        <SelectItem value="__empty" disabled>
                          Nenhum talhão vinculado a esta safra
                        </SelectItem>
                      ) : (
                        talhoes.map((t) => (
                          <SelectItem key={t.id} value={t.id} className="text-xs">
                            {t.nome}
                            {t.codigo ? ` (${t.codigo})` : ""}
                            {t.principal ? " ★" : ""}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                )}
              />
              {talhoes.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  Nenhum talhão está disponível para esta safra no momento.
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Tipo de Registro</Label>
                <Controller
                  name="tipo"
                  control={control}
                  rules={{ required: true }}
                  render={({ field }) => (
                    <Select onValueChange={field.onChange} value={field.value}>
                      <SelectTrigger className="h-8 text-xs rounded-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-sm">
                        {TIPOS.map((t) => (
                          <SelectItem key={t.value} value={t.value} className="text-xs">
                            {t.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Data do Registro</Label>
                <Input
                  type="date"
                  {...register("data_registro", { required: true })}
                  className="h-8 text-xs rounded-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <UserCircle2 className="size-3.5" />
                Executor da Operação (Opcional)
              </Label>
              <Controller
                name="executado_por_pessoa_id"
                control={control}
                render={({ field }) => (
                  <PessoaSelect
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Selecione quem executou no campo..."
                    unidadeProdutivaId={unidadeProdutivaId}
                    dataReferencia={dataRegistro}
                  />
                )}
              />
              <p className="text-[11px] text-muted-foreground">
                Deixe em branco se você mesmo executou ou se for um apontamento apenas sistêmico.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">
                Descrição <span className="text-destructive">*</span>
              </Label>
              <Textarea
                rows={3}
                placeholder="Descreva o que foi observado..."
                {...register("descricao", { required: true })}
                className="text-xs rounded-sm"
              />
            </div>

            {tipo === "MONITORAMENTO" && (
              <div className="rounded-sm border border-amber-500/20 bg-amber-500/5 p-3 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">Nível de Severidade</Label>
                    <Controller
                      name="nivel_severidade"
                      control={control}
                      render={({ field }) => (
                        <Select onValueChange={field.onChange} value={field.value ?? ""}>
                          <SelectTrigger className="h-8 text-xs rounded-sm bg-background">
                            <SelectValue placeholder="Selecionar..." />
                          </SelectTrigger>
                          <SelectContent className="rounded-sm">
                            {SEVERIDADES.map((s) => (
                              <SelectItem key={s.value} value={s.value} className="text-xs">
                                {s.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs font-medium">
                      N° Receituário <span className="text-[10px] text-muted-foreground">(Lei 7.802/89)</span>
                    </Label>
                    <Input
                      placeholder="Ex: RA-2024-001"
                      {...register("numero_receituario")}
                      className="h-8 text-xs rounded-sm bg-background"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs font-medium">Recomendação</Label>
                  <Textarea
                    rows={2}
                    placeholder="Ação recomendada..."
                    {...register("recomendacao")}
                    className="text-xs rounded-sm bg-background"
                  />
                </div>
              </div>
            )}

            <div className="flex items-start gap-2 pt-1">
              <Controller
                name="digitalizacao_retroativa"
                control={control}
                render={({ field }) => (
                  <Checkbox
                    id="retroativa"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                    className="rounded-xs mt-0.5"
                  />
                )}
              />
              <div className="space-y-0.5">
                <Label htmlFor="retroativa" className="text-xs font-medium cursor-pointer">
                  Digitalização retroativa (caderno de papel)
                </Label>
                <p className="text-[11px] text-muted-foreground">
                  Marque quando o lançamento vier de apontamentos feitos fora da plataforma.
                </p>
              </div>
            </div>

            {retroativa && (
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">
                  Justificativa <span className="text-destructive">*</span>
                </Label>
                <Textarea
                  rows={2}
                  placeholder="Motivo da digitalização retroativa..."
                  {...register("justificativa_retroativa", { required: retroativa })}
                  className="text-xs rounded-sm"
                />
              </div>
            )}
          </DialogBody>

          <DialogFooter>
            <Button variant="outline" size="sm" type="button" className="rounded-sm" onClick={handleClose} disabled={isLoading}>
              Cancelar
            </Button>
            <Button size="sm" type="submit" className="rounded-sm gap-1.5" disabled={isLoading || talhoes.length === 0}>
              {isLoading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Check className="size-3.5" />
                  Registrar
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
