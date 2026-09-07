"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod/v4";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Form, FormControl, FormField, FormItem,
  FormLabel, FormMessage
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { DollarSign, Truck, Loader2, Sparkles, TrendingDown, AlertTriangle, Brain, CheckCircle2, Clock, HandCoins, ThumbsUp, ThumbsDown, CreditCard } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { FornecedorCombobox } from "@/components/shared";
import { TendenciaPrecosChart } from "./TendenciaPrecosChart";
import { cn } from "@/lib/utils";

const cotacaoSchema = z.object({
  fornecedor_id: z.string().min(1, "Selecione um fornecedor"),
  condicoes_pagamento: z.string().max(100).optional(),
  valor_unitario: z.number({ error: "Informe o valor unitário" }).gt(0, "Valor deve ser maior que zero"),
  prazo_entrega_dias: z.number().int("Informe dias inteiros").min(0, "Prazo não pode ser negativo").optional(),
});

type CotacaoFormValues = z.infer<typeof cotacaoSchema>;

interface PrecoHistoricoItem {
  fornecedor_nome: string;
  valor_unitario: number;
  data: string;
  origem: string;
}

interface PrecoHistoricoResponse {
  menor_preco: number;
  maior_preco: number;
  preco_medio: number;
  historico: PrecoHistoricoItem[];
}

interface PrecoIdealResponse {
  preco_minimo_referencia: number;
  preco_ideal: number;
  preco_maximo_recommended: number;
  base_calculo: string;
}

interface FornecedorConsistencia {
  fornecedor_nome: string;
  preco_medio: number;
  desvio_padrao: number;
  variacao_percentual: number;
  classificacao: 'ESTAVEL' | 'MODERADO' | 'INSTAVEL';
}

interface RecomendacaoFornecedor {
  fornecedor_nome: string;
  preco_medio: number;
  ultimo_preco: number;
  qtd_compras: number;
  score: number;
}

interface EstrategiaCompra {
  resumo: string;
  estrategia: "Comprar agora" | "Negociar" | "Aguardar";
  justificativas: string[];
  nivel_confianca: number;
  fonte: string;
  ia_disponivel: boolean;
  limite_atingido: boolean;
}

interface RecomendacaoHistorico {
  id: string;
  estrategia: string;
  resumo: string;
  nivel_confianca: number;
  fonte: string;
  feedback_util: boolean | null;
  feedback_comentario: string | null;
  created_at: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  solicitacaoId: string;
  produtoNome: string;
  produtoId: string;
}

const ESTRATEGIA_CONFIG = {
  "Comprar agora": { icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/20 dark:border-emerald-800/40" },
  "Negociar":      { icon: HandCoins,   color: "text-amber-600",   bg: "bg-amber-50 border-amber-200 dark:bg-amber-950/20 dark:border-amber-800/40" },
  "Aguardar":      { icon: Clock,       color: "text-blue-600",    bg: "bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-800/40" },
} as const;

/** Cotação de UM item — inclui histórico, preço ideal, recomendações e estratégia por IA.
 * Para solicitações com múltiplos itens, ver `CotacaoMultiItemDialog`. */
export function CotacaoSolicitacaoDialog({ isOpen, onClose, solicitacaoId, produtoNome, produtoId }: Props) {
  const queryClient = useQueryClient();
  const [estrategia, setEstrategia] = useState<EstrategiaCompra | null>(null);

  const form = useForm<CotacaoFormValues>({
    resolver: zodResolver(cotacaoSchema),
    defaultValues: {
      fornecedor_id: "",
      condicoes_pagamento: "",
      valor_unitario: undefined,
      prazo_entrega_dias: undefined,
    },
  });
  const [fornecedorNomeSelecionado, setFornecedorNomeSelecionado] = useState("");

  const { data: recomendacao, isLoading: isLoadingRec } = useQuery<RecomendacaoFornecedor>({
    queryKey: ["melhor-fornecedor", produtoId],
    queryFn: () => apiFetch(`compras/precos/melhor-fornecedor?item_id=${produtoId}`),
    enabled: !!produtoId && isOpen,
  });

  const { data: historicoRes, isLoading: isLoadingHist } = useQuery<PrecoHistoricoResponse>({
    queryKey: ["preco-historico", produtoId],
    queryFn: () => apiFetch(`compras/precos/historico?item_id=${produtoId}`),
    enabled: !!produtoId && isOpen,
  });

  const { data: precoIdealRes, isLoading: isLoadingIdeal } = useQuery<PrecoIdealResponse>({
    queryKey: ["preco-ideal", produtoId],
    queryFn: () => apiFetch(`compras/precos/preco-ideal?item_id=${produtoId}`),
    enabled: !!produtoId && isOpen,
  });

  const { data: consistenciaRes } = useQuery<FornecedorConsistencia[]>({
    queryKey: ["fornecedor-consistencia", produtoId],
    queryFn: () => apiFetch(`compras/fornecedores/consistencia?item_id=${produtoId}`),
    enabled: !!produtoId && isOpen,
  });

  const { data: historicoIA } = useQuery<RecomendacaoHistorico[]>({
    queryKey: ["ia-recomendacoes", solicitacaoId],
    queryFn: () => apiFetch(`ia/compras/recomendacoes?solicitacao_id=${solicitacaoId}`),
    enabled: !!solicitacaoId && isOpen,
  });

  const valorDigitado = useWatch({ control: form.control, name: "valor_unitario" });

  const consistenciaAtual = consistenciaRes?.find(c => c.fornecedor_nome === fornecedorNomeSelecionado);

  const mutation = useMutation({
    mutationFn: (values: CotacaoFormValues) => 
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes`, {
        method: "POST",
        body: JSON.stringify(values),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes-cotacoes", solicitacaoId] });
      toast.success("Cotação registrada com sucesso!");
      form.reset();
      onClose();
    },
    onError: () => {
      toast.error("Erro ao registrar cotação.");
    },
  });

  const feedbackMut = useMutation<RecomendacaoHistorico, Error, { id: string; util: boolean }>({
    mutationFn: ({ id, util }) =>
      apiFetch(`/ia/compras/recomendacoes/${id}/feedback`, {
        method: "PATCH",
        body: JSON.stringify({ feedback_util: util }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ia-recomendacoes", solicitacaoId] });
      toast.success("Avaliação registrada!");
    },
    onError: () => toast.error("Erro ao registrar avaliação."),
  });

  const estrategiaMut = useMutation<EstrategiaCompra, Error>({
    mutationFn: () =>
      apiFetch("/ia/compras/estrategia", {
        method: "POST",
        body: JSON.stringify({ item_id: produtoId, solicitacao_id: solicitacaoId }),
      }),
    onSuccess: (data) => setEstrategia(data),
    onError: () => toast.error("Não foi possível gerar a estratégia. Tente novamente."),
  });

  function onSubmit(values: CotacaoFormValues) {
    mutation.mutate(values);
  }

  const handleApplyRec = async () => {
    if (!recomendacao) return;
    try {
      const encontrados = await apiFetch<{ id: string; nome_fantasia: string; condicoes_pagamento: string | null; prazo_entrega_dias: number | null }[]>(
        `/compras/fornecedores?q=${encodeURIComponent(recomendacao.fornecedor_nome)}`
      );
      const match = encontrados.find(f => f.nome_fantasia === recomendacao.fornecedor_nome) ?? encontrados[0];
      if (!match) {
        toast.error("Fornecedor recomendado não encontrado no cadastro.");
        return;
      }
      form.setValue("fornecedor_id", match.id);
      form.setValue("condicoes_pagamento", match.condicoes_pagamento ?? "");
      if (match.prazo_entrega_dias != null) form.setValue("prazo_entrega_dias", match.prazo_entrega_dias);
      setFornecedorNomeSelecionado(match.nome_fantasia);
      toast.info("Fornecedor recomendado selecionado!");
    } catch {
      toast.error("Não foi possível aplicar a recomendação.");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[1123px] rounded-sm p-0">
        <DialogHeader className="border-b px-4 py-2.5">
          <div className="flex items-center gap-3">
            <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
              <DollarSign className="size-4" />
            </div>
            <div className="min-w-0">
              <DialogTitle>Registrar Cotação</DialogTitle>
              <DialogDescription className="truncate text-xs leading-tight">{produtoNome}</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
            <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-2.5">
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="size-4 text-primary" />
                    <h4 className="text-sm font-medium">Tendência de Preços</h4>
                  </div>
                  <TendenciaPrecosChart
                    data={historicoRes?.historico || []}
                    precoMedio={historicoRes?.preco_medio}
                  />
                </div>

                {precoIdealRes && (
                  <div className="rounded-sm border bg-muted/20 p-3">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">Preço Ideal Sugerido</p>
                      <Badge variant="outline" className="h-4 rounded-sm border-slate-300 bg-white text-[9px] text-slate-600">
                        REF: {precoIdealRes.base_calculo}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="text-center">
                        <p className="mb-0.5 text-[9px] font-bold uppercase text-muted-foreground">Mínimo</p>
                        <p className="text-xs font-black text-foreground">R$ {precoIdealRes.preco_minimo_referencia.toFixed(2)}</p>
                      </div>
                      <div className="border-x text-center">
                        <p className="mb-0.5 text-[9px] font-bold uppercase text-primary">Ideal</p>
                        <p className="text-xs font-black text-primary">R$ {precoIdealRes.preco_ideal.toFixed(2)}</p>
                      </div>
                      <div className="text-center">
                        <p className="mb-0.5 text-[9px] font-bold uppercase text-muted-foreground">Máximo</p>
                        <p className="text-xs font-black text-destructive">R$ {precoIdealRes.preco_maximo_recommended.toFixed(2)}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {recomendacao && (
                <button
                  type="button"
                  onClick={handleApplyRec}
                  className="group relative overflow-hidden rounded-sm border border-emerald-200 bg-emerald-50 p-3 text-left transition-colors hover:bg-emerald-100"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex size-8 shrink-0 items-center justify-center rounded-sm bg-emerald-500 text-white">
                      <Sparkles className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="mb-1 flex items-center gap-2">
                        <p className="text-[10px] font-black uppercase tracking-wider text-emerald-600">Sugestão de Melhor Compra</p>
                        <Badge className="h-4 rounded-sm bg-emerald-600 text-[8px]">
                          SCORE {Math.round(recomendacao.score * 100)}%
                        </Badge>
                        {consistenciaRes?.find((c) => c.fornecedor_nome === recomendacao.fornecedor_nome)?.classificacao === "ESTAVEL" && (
                          <Badge variant="outline" className="h-4 rounded-sm border-emerald-300 bg-emerald-100 text-[7px] font-black uppercase text-emerald-600">
                            Preço Estável
                          </Badge>
                        )}
                      </div>
                      <h4 className="truncate text-sm font-black uppercase leading-tight text-foreground">
                        {recomendacao.fornecedor_nome}
                      </h4>
                      <div className="mt-1 flex flex-wrap items-center gap-3">
                        <span className="flex items-center gap-1 text-[11px] font-bold text-muted-foreground">
                          <TrendingDown className="size-3" />
                          Média: R$ {recomendacao.preco_medio.toFixed(2)}
                        </span>
                        <span className="text-[11px] font-bold text-muted-foreground">
                          {recomendacao.qtd_compras} Compras
                        </span>
                      </div>
                    </div>
                  </div>
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[9px] font-black uppercase text-emerald-600 opacity-0 transition-opacity group-hover:opacity-100">
                    Usar este
                  </span>
                </button>
              )}

              <div className="space-y-2">
                {!estrategia && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => estrategiaMut.mutate()}
                    disabled={estrategiaMut.isPending}
                    className="w-full"
                  >
                    {estrategiaMut.isPending ? (
                      <>
                        <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                        Analisando...
                      </>
                    ) : (
                      <>
                        <Brain data-icon="inline-start" className="size-3" />
                        Consultar Estratégia pela IA
                      </>
                    )}
                  </Button>
                )}

                {estrategia && (() => {
                  const cfg = ESTRATEGIA_CONFIG[estrategia.estrategia] ?? ESTRATEGIA_CONFIG["Negociar"];
                  const Icon = cfg.icon;
                  return (
                    <div className={cn("rounded-sm border p-3", cfg.bg)}>
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="flex items-center gap-1 text-[10px] font-black uppercase text-muted-foreground">
                          <Brain className="size-3" />
                          Estratégia sugerida pela IA
                        </p>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] font-black text-muted-foreground">
                            Confiança: {Math.round(estrategia.nivel_confianca * 100)}%
                          </span>
                          {!estrategia.ia_disponivel && (
                            <span className="rounded-sm bg-slate-100 px-1 py-0.5 text-[8px] font-black uppercase text-slate-500">
                              Offline
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mb-2 flex items-center gap-2">
                        <Icon className={cn("size-4 shrink-0", cfg.color)} />
                        <p className={cn("text-sm font-black", cfg.color)}>{estrategia.estrategia}</p>
                      </div>

                      <p className="mb-2 text-xs leading-relaxed text-muted-foreground">{estrategia.resumo}</p>

                      {estrategia.justificativas.length > 0 && (
                        <ul className="space-y-1">
                          {estrategia.justificativas.map((j, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-[11px] text-muted-foreground">
                              <span className={cn("mt-0.5 font-black", cfg.color)}>•</span>
                              {j}
                            </li>
                          ))}
                        </ul>
                      )}

                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => { setEstrategia(null); estrategiaMut.reset(); }}
                        className="mt-2 h-5 px-0 text-[9px] text-muted-foreground hover:text-foreground"
                      >
                        Nova consulta
                      </Button>
                    </div>
                  );
                })()}
              </div>

              {historicoIA && historicoIA.length > 0 && (
                <div className="space-y-2 rounded-sm border p-3">
                  <p className="flex items-center gap-1 text-[10px] font-black uppercase text-muted-foreground">
                    <Brain className="size-3" />
                    Histórico de estratégias consultadas
                  </p>
                  <div className="max-h-[140px] space-y-1.5 overflow-y-auto pr-1">
                    {historicoIA.map((r) => {
                      const cfg = ESTRATEGIA_CONFIG[r.estrategia as keyof typeof ESTRATEGIA_CONFIG] ?? ESTRATEGIA_CONFIG["Negociar"];
                      const Icon = cfg.icon;
                      const jaAvaliado = r.feedback_util !== null;
                      return (
                        <div key={r.id} className="flex items-start gap-2 py-0.5 text-[11px]">
                          <Icon className={cn("mt-0.5 size-3 shrink-0", cfg.color)} />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-1.5">
                              <span className={cn("font-black", cfg.color)}>{r.estrategia}</span>
                              {r.fonte !== "IA" && (
                                <span className="rounded-sm bg-slate-100 px-1 text-[8px] text-slate-500">Offline</span>
                              )}
                              <span className="ml-auto text-[9px] tabular-nums text-muted-foreground">
                                {new Date(r.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}
                              </span>
                            </div>
                            <p className="truncate text-[10px] text-muted-foreground">{r.resumo}</p>
                          </div>
                          <div className="flex shrink-0 items-center gap-0.5">
                            {jaAvaliado ? (
                              <span className={cn(
                                "rounded-sm px-1.5 py-0.5 text-[9px] font-black",
                                r.feedback_util ? "bg-emerald-100 text-emerald-600" : "bg-rose-100 text-rose-600"
                              )}>
                                {r.feedback_util ? "Útil" : "Não útil"}
                              </span>
                            ) : (
                              <>
                                <button
                                  type="button"
                                  onClick={() => feedbackMut.mutate({ id: r.id, util: true })}
                                  disabled={feedbackMut.isPending}
                                  className="rounded-sm p-1 text-muted-foreground transition-colors hover:bg-emerald-50 hover:text-emerald-600"
                                  title="Útil"
                                >
                                  <ThumbsUp className="size-3" />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => feedbackMut.mutate({ id: r.id, util: false })}
                                  disabled={feedbackMut.isPending}
                                  className="rounded-sm p-1 text-muted-foreground transition-colors hover:bg-rose-50 hover:text-rose-600"
                                  title="Não útil"
                                >
                                  <ThumbsDown className="size-3" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

            <FormField
              control={form.control}
              name="fornecedor_id"
              render={({ field }) => (
                <FormItem className="space-y-1">
                  <div className="flex items-center justify-between">
                    <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Fornecedor</FormLabel>
                    {consistenciaAtual && (
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-[8px] h-4 rounded-sm font-black uppercase px-1.5",
                          consistenciaAtual.classificacao === 'ESTAVEL' && "border-emerald-200 text-emerald-600 bg-emerald-50",
                          consistenciaAtual.classificacao === 'MODERADO' && "border-amber-200 text-amber-600 bg-amber-50",
                          consistenciaAtual.classificacao === 'INSTAVEL' && "border-rose-200 text-rose-600 bg-rose-50"
                        )}
                      >
                        {consistenciaAtual.classificacao === 'ESTAVEL' && "Preço Consistente"}
                        {consistenciaAtual.classificacao === 'MODERADO' && "Variação Moderada"}
                        {consistenciaAtual.classificacao === 'INSTAVEL' && "Preço Instável"}
                      </Badge>
                    )}
                  </div>
                  <FormControl>
                    <FornecedorCombobox
                      value={field.value}
                      onChange={field.onChange}
                      onSelectFornecedor={(f) => {
                        setFornecedorNomeSelecionado(f.nome_fantasia);
                        if (!form.getValues("condicoes_pagamento")) {
                          form.setValue("condicoes_pagamento", f.condicoes_pagamento ?? "");
                        }
                        if (f.prazo_entrega_dias != null && form.getValues("prazo_entrega_dias") == null) {
                          form.setValue("prazo_entrega_dias", f.prazo_entrega_dias);
                        }
                      }}
                    />
                  </FormControl>
                  {consistenciaAtual?.classificacao === 'INSTAVEL' && (
                    <p className="text-[9px] text-rose-500 font-bold uppercase mt-1 flex items-center gap-1">
                      <AlertTriangle className="size-3" /> Histórico instável — preços variam bastante
                    </p>
                  )}
                  <FormMessage className="text-[10px]" />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="condicoes_pagamento"
              render={({ field }) => (
                <FormItem className="space-y-1">
                  <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Condições de Pagamento (negociadas nesta cotação)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                      <Input placeholder="Ex: 30% adiantado + 30 dias" {...field} className="pl-9 h-8 rounded-sm" />
                    </div>
                  </FormControl>
                  <FormMessage className="text-[10px]" />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="valor_unitario"
                render={({ field }) => (
                  <FormItem className="space-y-1">
                    <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Valor Unitário</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                        <Input
                          type="number"
                          step="any"
                          min="0.01"
                          placeholder="0.00"
                          name={field.name}
                          ref={field.ref}
                          onBlur={field.onBlur}
                          value={field.value ?? ""}
                          onChange={(event) => {
                            field.onChange(event.target.value === "" ? undefined : event.target.valueAsNumber);
                          }}
                          className="pl-9 h-8 rounded-sm"
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-[10px]" />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="prazo_entrega_dias"
                render={({ field }) => (
                  <FormItem className="space-y-1">
                    <FormLabel className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Prazo (Dias)</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Truck className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                        <Input
                          type="number"
                          min="0"
                          step="1"
                          placeholder="0"
                          name={field.name}
                          ref={field.ref}
                          onBlur={field.onBlur}
                          value={field.value ?? ""}
                          onChange={(event) => {
                            field.onChange(event.target.value === "" ? undefined : event.target.valueAsNumber);
                          }}
                          className="pl-9 h-8 rounded-sm"
                        />
                      </div>
                    </FormControl>
                    <FormMessage className="text-[10px]" />
                  </FormItem>
                )}
              />
            </div>

            </DialogBody>

            <DialogFooter className="border-t px-4 py-2.5">
              <Button 
                type="button" 
                variant="ghost" 
                size="sm" 
                onClick={onClose}
              >
                Cancelar
              </Button>
              <Button 
                type="submit" 
                variant="default"
                size="sm" 
                disabled={mutation.isPending}
              >
                {mutation.isPending ? (
                  <>
                    <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                    Salvando...
                  </>
                ) : "Registrar Cotação"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
