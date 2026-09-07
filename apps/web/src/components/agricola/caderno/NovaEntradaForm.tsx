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
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { BookOpen, UserCircle2 } from "lucide-react";
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
      <DialogContent className="sm:max-w-[720px] p-0 gap-0 overflow-hidden">
        <form onSubmit={handleSubmit(onFormSubmit)} className="flex max-h-[85vh] min-h-0 flex-col">
          <DialogHeader className="border-b px-6 py-5">
            <DialogTitle className="flex items-center gap-2">
              <BookOpen />
              Novo Registro no Caderno
            </DialogTitle>
            <DialogDescription>
              Registre observações, monitoramentos e eventos do talhão com data, tipo e contexto.
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="min-h-0 flex-1">
            <div className="px-6 py-5">
              <div className="flex flex-col gap-5">
                <section className="rounded-sm border bg-muted/30 p-4">
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-foreground">Identificação do registro</h3>
                    <p className="text-xs text-muted-foreground">
                      Escolha o talhão, o tipo e a data do lançamento.
                    </p>
                  </div>

                  <div className="flex flex-col gap-4">
                    <div className="space-y-1.5">
                      <Label>
                        Talhão <span className="text-destructive">*</span>
                      </Label>
                      <Controller
                        name="talhao_id"
                        control={control}
                        rules={{ required: "Selecione um talhão" }}
                        render={({ field }) => (
                          <Select onValueChange={field.onChange} value={field.value || ""}>
                            <SelectTrigger disabled={talhoes.length === 0}>
                              <SelectValue placeholder="Selecionar talhão..." />
                            </SelectTrigger>
                            <SelectContent>
                              {talhoes.length === 0 ? (
                                <SelectItem value="__empty" disabled>
                                  Nenhum talhão vinculado a esta safra
                                </SelectItem>
                              ) : (
                                talhoes.map((t) => (
                                  <SelectItem key={t.id} value={t.id}>
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

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div className="space-y-1.5">
                        <Label>Tipo de Registro</Label>
                        <Controller
                          name="tipo"
                          control={control}
                          rules={{ required: true }}
                          render={({ field }) => (
                            <Select onValueChange={field.onChange} value={field.value}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {TIPOS.map((t) => (
                                  <SelectItem key={t.value} value={t.value}>
                                    {t.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        />
                      </div>

                      <div className="space-y-1.5">
                        <Label>Data do Registro</Label>
                        <Input type="date" {...register("data_registro", { required: true })} />
                      </div>
                    </div>

                    <div className="space-y-1.5 pt-2 border-t border-border/50">
                      <Label className="flex items-center gap-1.5 text-muted-foreground">
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
                  </div>
                </section>

                <section className="rounded-sm border bg-muted/30 p-4">
                  <div className="mb-4">
                    <h3 className="text-sm font-medium text-foreground">Conteúdo do lançamento</h3>
                    <p className="text-xs text-muted-foreground">
                      Descreva o que foi observado e inclua dados complementares quando necessário.
                    </p>
                  </div>

                  <div className="flex flex-col gap-4">
                    <div className="space-y-1.5">
                      <Label>
                        Descrição <span className="text-destructive">*</span>
                      </Label>
                      <Textarea
                        rows={3}
                        placeholder="Descreva o que foi observado..."
                        {...register("descricao", { required: true })}
                      />
                    </div>

                    {tipo === "MONITORAMENTO" && (
                      <div className="rounded-sm border border-amber-500/20 bg-amber-500/5 p-4">
                        <div className="mb-4">
                          <h4 className="text-sm font-medium text-foreground">
                            Dados complementares do monitoramento
                          </h4>
                          <p className="text-xs text-muted-foreground">
                            Use estes campos para detalhar severidade, receituário e recomendação técnica.
                          </p>
                        </div>

                        <div className="flex flex-col gap-4">
                          <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-1.5">
                              <Label>Nível de Severidade</Label>
                              <Controller
                                name="nivel_severidade"
                                control={control}
                                render={({ field }) => (
                                  <Select onValueChange={field.onChange} value={field.value ?? ""}>
                                    <SelectTrigger>
                                      <SelectValue placeholder="Selecionar..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {SEVERIDADES.map((s) => (
                                        <SelectItem key={s.value} value={s.value}>
                                          {s.label}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                )}
                              />
                            </div>

                            <div className="space-y-1.5">
                              <Label>
                                N° Receituário <span className="text-xs text-muted-foreground">(Lei 7.802/89)</span>
                              </Label>
                              <Input placeholder="Ex: RA-2024-001" {...register("numero_receituario")} />
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <Label>Recomendação</Label>
                            <Textarea
                              rows={2}
                              placeholder="Ação recomendada..."
                              {...register("recomendacao")}
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="rounded-sm border bg-background p-4">
                      <div className="flex items-start gap-3">
                        <Controller
                          name="digitalizacao_retroativa"
                          control={control}
                          render={({ field }) => (
                            <Checkbox
                              id="retroativa"
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          )}
                        />
                        <div className="space-y-1">
                          <Label htmlFor="retroativa" className="text-sm cursor-pointer">
                            Digitalização retroativa (caderno de papel)
                          </Label>
                          <p className="text-xs text-muted-foreground">
                            Marque quando o lançamento vier de apontamentos feitos fora da plataforma.
                          </p>
                        </div>
                      </div>
                    </div>

                    {retroativa && (
                      <div className="space-y-1.5">
                        <Label>
                          Justificativa <span className="text-destructive">*</span>
                        </Label>
                        <Textarea
                          rows={2}
                          placeholder="Motivo da digitalização retroativa..."
                          {...register("justificativa_retroativa", { required: retroativa })}
                        />
                      </div>
                    )}
                  </div>
                </section>
              </div>
            </div>
          </ScrollArea>

          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading || talhoes.length === 0}>
              {isLoading ? "Salvando..." : "Registrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
