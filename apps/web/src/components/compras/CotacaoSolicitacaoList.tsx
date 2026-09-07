"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { useState } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { DollarSign, Truck, Check, Loader2, ClipboardList, AlertTriangle, FileDown, PackageCheck, Send, Pencil, Save, Package, CreditCard, XCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { Form, FormField, FormItem, FormControl } from "@/components/ui/form";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogBody
} from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { cn, parseLocaleNumber } from "@/lib/utils";
import { formatNumberBR } from "@farm/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface CotacaoItem {
  id: string;
  solicitacao_item_id: string;
  produto_id: string;
  produto_nome?: string | null;
  quantidade: number;
  valor_unitario: number;
  valor_total: number;
  tem_pedido_gerado?: boolean;
}

interface Cotacao {
  id: string;
  numero?: string | null;
  fornecedor_nome: string;
  fornecedor_contato?: string;
  condicoes_pagamento?: string | null;
  valor_unitario: number | null;
  valor_total: number;
  prazo_entrega_dias?: number;
  status: "RECEBIDA" | "APROVADA" | "RECUSADA";
  acima_media?: boolean;
  percentual_acima_media?: number;
  mensagem_alerta?: string;
  score_compra?: number;
  classificacao_score?: "BOA" | "ATENCAO" | "RUIM";
  motivos_score?: string[];
  posicao_ranking?: number;
  melhor_opcao?: boolean;
  explicacao_compra?: string;
  pontos_fortes?: string[];
  pontos_atencao?: string[];
  itens: CotacaoItem[];
  created_at: string;
}

interface SolicitacaoItem {
  id: string;
  produto_id: string;
  produto_nome?: string | null;
  quantidade_solicitada: number;
  unidade: string;
  quantidade_alocada: number;
  status_atendimento: "PENDENTE" | "PARCIAL" | "ATENDIDO";
}

interface PrecoHistoricoItem {
  fornecedor_nome: string;
  valor_unitario: number;
  data: string;
  origem: "COTACAO" | "PEDIDO";
}

interface PrecoHistoricoResponse {
  menor_preco: number;
  maior_preco: number;
  preco_medio: number;
  historico: PrecoHistoricoItem[];
}

interface CotacaoSolicitacaoListProps {
  solicitacaoId: string;
  itens: SolicitacaoItem[];
}

interface AlocacaoFormItem {
  solicitacao_item_id: string;
  cotacao_item_id: string;
  quantidade: string;
}

interface AlocacaoFormValues {
  linhas: AlocacaoFormItem[];
}

export function CotacaoSolicitacaoList({ solicitacaoId, itens }: CotacaoSolicitacaoListProps) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [isExporting, setIsExporting] = useState(false);
  const [editando, setEditando] = useState<Cotacao | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [quantidades, setQuantidades] = useState<Record<string, string>>({});
  const [condicoesPagamento, setCondicoesPagamento] = useState("");
  const [prazoEntregaDias, setPrazoEntregaDias] = useState("");
  const [aprovando, setAprovando] = useState<Cotacao | null>(null);
  const produtoId = itens.length === 1 ? itens[0].produto_id : "";
  // Se algum item já tem alocação parcial registrada (fluxo "Alocação por
  // Item", usado quando um fornecedor sozinho não atende a quantidade
  // solicitada), o botão "Aprovar" fica bloqueado — ele recusaria TODAS as
  // outras cotações da solicitação e destruiria a divisão entre fornecedores
  // já feita. Nesse cenário, use "Alocação por Item" + "Gerar Pedidos".
  const temAlocacaoParcial = itens.some((i) => i.quantidade_alocada > 0);

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const blob = await apiFetch<Blob>(`/compras/solicitacoes/${solicitacaoId}/cotacoes/export.pdf`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `comparativo_cotacoes_${solicitacaoId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success("Mapa comparativo exportado com sucesso!");
    } catch (error) {
      console.error("Erro ao exportar PDF:", error);
      toast.error("Falha ao gerar PDF comparativo.");
    } finally {
      setIsExporting(false);
    }
  };

  const { data: cotacoes = [], isLoading: isLoadingCotacoes } = useQuery<Cotacao[]>({
    queryKey: ["compras-solicitacoes-cotacoes", solicitacaoId],
    queryFn: () => apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes`),
  });

  const { data: historico, isLoading: isLoadingHistorico } = useQuery<PrecoHistoricoResponse>({
    queryKey: ["compras-precos-historico", produtoId],
    queryFn: () => apiFetch(`/compras/precos/historico?item_id=${produtoId}`),
    enabled: !!produtoId,
  });

  const approveMutation = useMutation({
    mutationFn: (cotacaoId: string) => 
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes/${cotacaoId}/aprovar`, {
        method: "PATCH",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success("Cotação aprovada e pedido gerado!");
      setAprovando(null);
      router.push("/suprimentos/compras");
    },
    onError: () => {
      toast.error("Falha ao aprovar cotação.");
      setAprovando(null);
    },
  });

  const editarItemMutation = useMutation({
    mutationFn: ({ cotacaoId, itemId, valorUnitario, quantidadeAtendida }: { cotacaoId: string; itemId: string; valorUnitario: number; quantidadeAtendida?: number }) =>
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes/${cotacaoId}/itens/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ valor_unitario: valorUnitario, quantidade_atendida: quantidadeAtendida }),
      }),
  });

  const editarCotacaoMutation = useMutation({
    mutationFn: ({ cotacaoId, condicoesPagamento, prazoEntregaDias }: { cotacaoId: string; condicoesPagamento: string; prazoEntregaDias: string }) =>
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/cotacoes/${cotacaoId}`, {
        method: "PATCH",
        body: JSON.stringify({
          condicoes_pagamento: condicoesPagamento || null,
          prazo_entrega_dias: prazoEntregaDias ? parseInt(prazoEntregaDias, 10) : null,
        }),
      }),
  });

  const abrirEdicao = (cot: Cotacao) => {
    setEditando(cot);
    setValores(Object.fromEntries(cot.itens.map((i) => [i.id, i.valor_unitario.toFixed(2)])));
    setQuantidades(Object.fromEntries(cot.itens.map((i) => [i.id, String(i.quantidade)])));
    setCondicoesPagamento(cot.condicoes_pagamento ?? "");
    setPrazoEntregaDias(cot.prazo_entrega_dias != null ? String(cot.prazo_entrega_dias) : "");
  };

  const quantidadeSolicitadaDoItem = (item: CotacaoItem) =>
    itens.find((i) => i.id === item.solicitacao_item_id)?.quantidade_solicitada ?? Infinity;

  const salvarEdicao = async () => {
    if (!editando) return;

    for (const item of editando.itens) {
      const novaQtd = parseLocaleNumber(quantidades[item.id], NaN);
      const solicitada = quantidadeSolicitadaDoItem(item);
      if (!Number.isNaN(novaQtd) && novaQtd > solicitada) {
        toast.error(`Quantidade atendida de "${item.produto_nome}" não pode superar a solicitada (${solicitada}).`);
        return;
      }
    }

    const alterados = editando.itens.filter((i) => {
      const novoValor = parseLocaleNumber(valores[i.id], NaN);
      const novaQtd = parseLocaleNumber(quantidades[i.id], NaN);
      const valorMudou = !Number.isNaN(novoValor) && novoValor > 0 && novoValor !== i.valor_unitario;
      const qtdMudou = !Number.isNaN(novaQtd) && novaQtd > 0 && novaQtd !== i.quantidade;
      return valorMudou || qtdMudou;
    });
    const cabecalhoAlterado =
      condicoesPagamento !== (editando.condicoes_pagamento ?? "") ||
      prazoEntregaDias !== (editando.prazo_entrega_dias != null ? String(editando.prazo_entrega_dias) : "");

    if (alterados.length === 0 && !cabecalhoAlterado) {
      setEditando(null);
      return;
    }
    try {
      for (const item of alterados) {
        const novaQtd = parseLocaleNumber(quantidades[item.id], NaN);
        await editarItemMutation.mutateAsync({
          cotacaoId: editando.id,
          itemId: item.id,
          valorUnitario: parseLocaleNumber(valores[item.id], NaN),
          quantidadeAtendida: !Number.isNaN(novaQtd) && novaQtd > 0 && novaQtd !== item.quantidade ? novaQtd : undefined,
        });
      }
      if (cabecalhoAlterado) {
        await editarCotacaoMutation.mutateAsync({
          cotacaoId: editando.id,
          condicoesPagamento,
          prazoEntregaDias,
        });
      }
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes-cotacoes", solicitacaoId] });
      toast.success("Cotação atualizada!");
      setEditando(null);
    } catch (err: any) {
      toast.error(err?.message || "Falha ao atualizar cotação.");
    }
  };

  const alocarForm = useForm<AlocacaoFormValues>({
    defaultValues: { linhas: itens.map((item) => ({ solicitacao_item_id: item.id, cotacao_item_id: "", quantidade: "" })) },
  });
  const { fields: linhasAlocacao } = useFieldArray({ control: alocarForm.control, name: "linhas" });

  const cotacaoItensPorId = new Map(
    cotacoes.flatMap((c) => (c.itens || []).map((ci) => [ci.id, ci] as const))
  );

  const alocarMutation = useMutation({
    mutationFn: (values: AlocacaoFormValues) =>
      apiFetch(`/compras/solicitacoes/${solicitacaoId}/alocar`, {
        method: "POST",
        body: JSON.stringify({
          itens: values.linhas
            .filter((l) => l.cotacao_item_id && parseLocaleNumber(l.quantidade) > 0)
            .map((l) => ({
              solicitacao_item_id: l.solicitacao_item_id,
              cotacao_item_id: l.cotacao_item_id,
              quantidade: parseLocaleNumber(l.quantidade),
            })),
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes-cotacoes", solicitacaoId] });
      toast.success("Alocação registrada!");
      alocarForm.reset({ linhas: itens.map((item) => ({ solicitacao_item_id: item.id, cotacao_item_id: "", quantidade: "" })) });
    },
    onError: (err: any) => toast.error(err?.message || "Falha ao alocar itens."),
  });

  const gerarPedidosMutation = useMutation({
    mutationFn: () => apiFetch(`/compras/solicitacoes/${solicitacaoId}/gerar-pedidos`, { method: "POST" }),
    onSuccess: (pedidos: any[]) => {
      queryClient.invalidateQueries({ queryKey: ["compras-solicitacoes"] });
      queryClient.invalidateQueries({ queryKey: ["compras-pedidos"] });
      toast.success(`${pedidos.length} pedido(s) gerado(s)!`);
      router.push("/suprimentos/compras");
    },
    onError: () => toast.error("Falha ao gerar pedidos."),
  });

  if (isLoadingCotacoes) {
    return (
      <div className="space-y-2 p-4 bg-muted/5 rounded-sm border border-dashed">
        <Skeleton className="h-4 w-1/4" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  const getTrend = () => {
    if (!historico?.historico || historico.historico.length < 2) return null;
    const last = historico.historico[0].valor_unitario;
    const prev = historico.historico[1].valor_unitario;
    if (last < prev) return "down";
    if (last > prev) return "up";
    return "stable";
  };

  const trend = getTrend();

  return (
    <div className="space-y-4 mx-4 mb-4 mt-4">
      {/* Recomendação do Sistema (Step 161) */}
      {cotacoes.length > 0 && cotacoes[0].melhor_opcao && (
        <div className={cn(
          "rounded-sm p-4 flex items-start gap-4 border",
          cotacoes[0].classificacao_score === "BOA" ? "bg-emerald-50 border-emerald-200" :
          cotacoes[0].classificacao_score === "ATENCAO" ? "bg-amber-50 border-amber-200" :
          "bg-rose-50 border-rose-200"
        )}>
          <div className={cn(
            "p-2 rounded-sm text-white",
            cotacoes[0].classificacao_score === "BOA" ? "bg-emerald-500" :
            cotacoes[0].classificacao_score === "ATENCAO" ? "bg-amber-500" :
            "bg-rose-500"
          )}>
            <ClipboardList className="size-5" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className={cn(
                "text-[11px] font-black uppercase tracking-tight",
                cotacoes[0].classificacao_score === "BOA" ? "text-emerald-900" :
                cotacoes[0].classificacao_score === "ATENCAO" ? "text-amber-900" :
                "text-rose-900"
              )}>Assistente de Compra</h4>
              <Badge className={cn(
                "text-[9px] h-4 rounded-sm border-none",
                cotacoes[0].classificacao_score === "BOA" ? "bg-emerald-600" :
                cotacoes[0].classificacao_score === "ATENCAO" ? "bg-amber-600" :
                "bg-rose-600"
              )}>{cotacoes[0].classificacao_score}</Badge>
            </div>
            
            <p className="text-[10px] font-bold mb-3 text-slate-800">
              {cotacoes[0].explicacao_compra}
            </p>

            <div className="grid grid-cols-2 gap-4 mb-3">
              {cotacoes[0].pontos_fortes && cotacoes[0].pontos_fortes.length > 0 && (
                <div>
                  <h5 className="text-[8px] font-black uppercase text-emerald-700 mb-1">Pontos Fortes:</h5>
                  <ul className="space-y-1">
                    {cotacoes[0].pontos_fortes.map((p, i) => (
                      <li key={i} className="text-[9px] text-emerald-800 flex items-center gap-1">
                        <Check className="size-2" /> {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {cotacoes[0].pontos_atencao && cotacoes[0].pontos_atencao.length > 0 && (
                <div>
                  <h5 className="text-[8px] font-black uppercase text-amber-700 mb-1">Atenção:</h5>
                  <ul className="space-y-1">
                    {cotacoes[0].pontos_atencao.map((p, i) => (
                      <li key={i} className="text-[9px] text-amber-800 flex items-center gap-1">
                        <AlertTriangle className="size-2" /> {p}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm" 
                className={cn(
                  "bg-white font-semibold",
                  cotacoes[0].classificacao_score === "BOA" ? "border-emerald-600 text-emerald-700 hover:bg-emerald-100" :
                  cotacoes[0].classificacao_score === "ATENCAO" ? "border-amber-600 text-amber-700 hover:bg-amber-100" :
                  "border-rose-600 text-rose-700 hover:bg-rose-100"
                )}
                onClick={() => setAprovando(cotacoes[0])}
                disabled={approveMutation.isPending || cotacoes[0].status !== "RECEBIDA" || temAlocacaoParcial}
                title={temAlocacaoParcial ? "Há alocação parcial entre fornecedores em andamento — use Alocação por Item + Gerar Pedidos." : undefined}
              >
                {approveMutation.isPending ? (
                  <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
                ) : (
                  <Check data-icon="inline-start" className="size-3.5" />
                )}
                Seguir Recomendação
              </Button>
            </div>
          </div>
          <div className="text-right">
            <div className={cn(
              "text-[16px] font-black leading-none",
              cotacoes[0].classificacao_score === "BOA" ? "text-emerald-900" :
              cotacoes[0].classificacao_score === "ATENCAO" ? "text-amber-900" :
              "text-rose-900"
            )}>#{cotacoes[0].posicao_ranking}</div>
            <div className="text-[8px] font-bold text-muted-foreground uppercase">no ranking</div>
          </div>
        </div>
      )}

      {/* Cotações Atuais */}
      <div className="bg-muted/5 rounded-sm border border-dashed overflow-hidden">
        <div className="bg-muted/20 px-4 py-2 border-b border-dashed flex items-center justify-between">
          <h4 className="text-[10px] font-black uppercase tracking-wider flex items-center gap-2">
            <DollarSign className="size-3" /> Cotações Recebidas ({cotacoes.length})
          </h4>
          
          {cotacoes.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="border-dashed font-semibold"
              onClick={handleExport}
              disabled={isExporting}
            >
              {isExporting ? (
                <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
              ) : (
                <FileDown data-icon="inline-start" className="size-3.5" />
              )}
              Exportar Comparativo
            </Button>
          )}
        </div>
        {cotacoes.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-[10px] font-bold uppercase text-muted-foreground">Nenhuma cotação registrada ainda.</p>
          </div>
        ) : (
          <Table className="table-fixed">
            <TableHeader className="bg-white/50">
              <TableRow className="hover:bg-transparent border-dashed">
                <TableHead className="h-8 w-[56px] text-center text-[9px] font-bold uppercase">Rank</TableHead>
                <TableHead className="h-8 w-[24%] text-[9px] font-bold uppercase">Fornecedor</TableHead>
                <TableHead className="h-8 w-[13%] text-right text-[9px] font-bold uppercase">Unitário</TableHead>
                <TableHead className="h-8 w-[13%] text-right text-[9px] font-bold uppercase">Total</TableHead>
                <TableHead className="h-8 w-[82px] text-center text-[9px] font-bold uppercase">Prazo</TableHead>
                <TableHead className="h-8 w-[130px] text-center text-[9px] font-bold uppercase">Score</TableHead>
                <TableHead className="h-8 w-[112px] text-center text-[9px] font-bold uppercase">Status</TableHead>
                <TableHead className="h-8 w-[120px] text-right text-[9px] font-bold uppercase"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {cotacoes.map((cot) => (
                <TableRow 
                  key={cot.id} 
                  className={cn(
                    "hover:bg-muted/10 border-dashed",
                    cot.melhor_opcao && cot.status === "RECEBIDA" && "bg-emerald-50/30"
                  )}
                >
                  <TableCell className="py-2 text-center font-black text-[11px] text-muted-foreground">
                    #{cot.posicao_ranking}
                  </TableCell>
                  <TableCell className="py-2">
                    <div className="flex flex-col gap-0.5">
                      {cot.numero && (
                        <span className="font-mono text-[9px] font-bold text-muted-foreground">{cot.numero}</span>
                      )}
                      <div className="flex items-start gap-2 justify-between">
                        <span className="text-[11px] font-black uppercase leading-tight">{cot.fornecedor_nome}</span>
                        <div className="flex items-center gap-1 shrink-0">
                          {cot.melhor_opcao && (
                            <Badge className="bg-emerald-500 text-[8px] h-4 rounded-sm border-none p-1">Melhor</Badge>
                          )}
                          {cot.acima_media && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <AlertTriangle className="size-3 text-amber-600 animate-pulse cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent side="right" className="bg-amber-50 border-amber-200 text-amber-900 text-[10px] font-bold">
                                  {cot.mensagem_alerta}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                        </div>
                      </div>
                      {cot.condicoes_pagamento && (
                        <span className="truncate text-[9px] text-muted-foreground">Pagamento: {cot.condicoes_pagamento}</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-2 text-right font-bold text-[11px] tabular-nums">
                    <div className="flex flex-col items-end">
                      {cot.valor_unitario !== null ? (
                        <span>{cot.valor_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</span>
                      ) : (
                        <span className="text-[9px] text-muted-foreground font-normal normal-case">{cot.itens.length} itens</span>
                      )}
                      {cot.acima_media && (
                        <span className="text-[8px] text-amber-600 font-black">+{cot.percentual_acima_media}%</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-2 text-right font-black text-[11px] tabular-nums text-primary">
                    {cot.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                  </TableCell>
                  <TableCell className="py-2 text-center">
                    <span className="text-[10px] font-bold uppercase flex items-center justify-center gap-1">
                      <Truck className="size-3" /> {cot.prazo_entrega_dias || 0}d
                    </span>
                  </TableCell>
                  <TableCell className="py-2 text-center">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge 
                            variant="outline" 
                            className={cn(
                              "text-[8px] font-black uppercase rounded-sm cursor-help",
                              cot.classificacao_score === "BOA" && "bg-emerald-500 text-white border-emerald-600",
                              cot.classificacao_score === "ATENCAO" && "bg-amber-400 text-amber-950 border-amber-500",
                              cot.classificacao_score === "RUIM" && "bg-rose-500 text-white border-rose-600"
                            )}
                          >
                            {Math.round(cot.score_compra || 0)}% {cot.classificacao_score}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent className="bg-slate-900 text-white border-slate-800 text-[10px]">
                          <div className="space-y-1">
                            <p className="font-black border-b border-white/10 pb-1 mb-1">MOTIVOS DO SCORE:</p>
                            {cot.motivos_score?.map((m, i) => (
                              <p key={i} className="flex items-center gap-1">• {m}</p>
                            ))}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableCell>
                  <TableCell className="py-2 text-center">
                    <Badge 
                      variant="outline" 
                      className={`text-[8px] font-bold uppercase rounded-sm ${
                        cot.status === "APROVADA" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                        cot.status === "RECUSADA" ? "bg-red-50 text-red-700 border-red-200" :
                        "bg-blue-50 text-blue-700 border-blue-200"
                      }`}
                    >
                      {cot.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-2 text-right">
                    <div className="flex items-center gap-0 justify-end">
                      {cot.status === "RECEBIDA" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-7 text-primary hover:text-primary"
                          onClick={() => abrirEdicao(cot)}
                          aria-label="Corrigir valor da cotação"
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-primary hover:text-primary"
                        onClick={() => setAprovando(cot)}
                        disabled={approveMutation.isPending || cot.status !== "RECEBIDA" || temAlocacaoParcial}
                        aria-label={
                          temAlocacaoParcial
                            ? "Há alocação parcial entre fornecedores em andamento — use Alocação por Item + Gerar Pedidos."
                            : cot.status === "APROVADA" ? "Vencedora" : cot.status === "RECUSADA" ? "Recusada" : "Aprovar"
                        }
                      >
                        {approveMutation.isPending && aprovando?.id === cot.id ? (
                          <Loader2 className="size-3.5 animate-spin" />
                        ) : (
                          <Check className="size-3.5" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Alocação item×fornecedor — permite dividir um item entre vários fornecedores
          (atendimento parcial) em vez de "1 cotação vence tudo". */}
      {cotacoes.length > 0 && (
        <div className="bg-muted/5 rounded-sm border border-dashed overflow-hidden">
          <div className="bg-muted/20 px-4 py-2 border-b border-dashed flex items-center justify-between">
            <h4 className="text-[10px] font-black uppercase tracking-wider flex items-center gap-2">
              <PackageCheck className="size-3" /> Alocação por Item
            </h4>
            <Button
              variant="outline"
              size="sm"
              className="border-dashed font-semibold"
              onClick={() => gerarPedidosMutation.mutate()}
              disabled={gerarPedidosMutation.isPending}
            >
              {gerarPedidosMutation.isPending ? (
                <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
              ) : (
                <Send data-icon="inline-start" className="size-3.5" />
              )}
              Gerar Pedidos
            </Button>
          </div>

          <Form {...alocarForm}>
            <form onSubmit={alocarForm.handleSubmit((values) => {
              for (const linha of values.linhas) {
                if (!linha.cotacao_item_id) continue;
                const qtd = parseLocaleNumber(linha.quantidade, NaN);
                if (Number.isNaN(qtd)) continue;
                if (qtd < 0) {
                  toast.error("A quantidade não pode ser menor que zero.");
                  return;
                }
                const disponivel = cotacaoItensPorId.get(linha.cotacao_item_id)?.quantidade;
                if (disponivel != null && qtd > disponivel) {
                  toast.error(`A quantidade não pode superar a informada pelo fornecedor (${disponivel}).`);
                  return;
                }
                // Saldo do item pode ter diminuído (ex: atendido parcialmente por outro
                // pedido) desde que a tela foi carregada — reforça aqui além do backend.
                const solItem = itens.find((i) => i.id === linha.solicitacao_item_id);
                const saldoItem = solItem ? solItem.quantidade_solicitada - solItem.quantidade_alocada : Infinity;
                if (qtd > saldoItem) {
                  toast.error(`A quantidade não pode superar o saldo pendente do item (${saldoItem}).`);
                  return;
                }
              }
              // DIAGNÓSTICO TEMPORÁRIO — remover após identificar a causa do 422 "itens: []".
              console.log("[alocarForm] valores no submit:", JSON.stringify(values));
              alocarMutation.mutate(values);
            })}>
              <div className="divide-y">
            {linhasAlocacao.map((linha, index) => {
              const item = itens[index];
              const saldo = item.quantidade_solicitada - item.quantidade_alocada;
              if (saldo <= 0) return null; // item já totalmente atendido — não faz sentido alocar mais

              const opcoes = cotacoes
                .filter((c) => c.status !== "RECUSADA")
                .flatMap((c) => (c.itens || [])
                  .filter((ci) => ci.solicitacao_item_id === item.id && !ci.tem_pedido_gerado)
                  .map((ci) => ({ ...ci, fornecedor_nome: c.fornecedor_nome })));

              return (
                <div key={linha.id} className="flex flex-col md:flex-row md:items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-semibold text-foreground">{item.produto_nome}</span>
                    <span className="text-[10px] text-muted-foreground font-medium flex items-center gap-1 mt-0.5">
                      Saldo pendente: <strong className="font-mono">{formatNumberBR(saldo, 2)} {item.unidade}</strong>
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-2 shrink-0">
                    <FormField
                      control={alocarForm.control}
                      name={`linhas.${index}.cotacao_item_id`}
                      render={({ field }) => (
                        <FormItem className="space-y-0">
                          <FormControl>
                            <Select
                              value={field.value}
                              onValueChange={(value) => {
                                field.onChange(value);
                                const op = opcoes.find((o) => o.id === value);
                                if (op) {
                                  // Arredonda para 2 casas antes de exibir — op.quantidade/saldo
                                  // costumam carregar erro de ponto flutuante (ex.: 43.740000000000001)
                                  // vindo de somas/subtrações anteriores, e sem isso ele vaza pro campo.
                                  const quantidadeAtribuida = Math.round(Math.min(op.quantidade, saldo) * 100) / 100;
                                  alocarForm.setValue(`linhas.${index}.quantidade`, formatNumberBR(quantidadeAtribuida, 2));
                                }
                              }}
                            >
                              <SelectTrigger className="h-8 w-[220px] rounded-sm text-xs">
                                <SelectValue placeholder="Selecione o fornecedor..." />
                              </SelectTrigger>
                              <SelectContent className="rounded-sm">
                                {opcoes.length === 0 ? (
                                  <div className="px-2 py-1.5 text-[10px] text-muted-foreground">Nenhuma cotação para este item</div>
                                ) : (
                                  opcoes.map((op) => (
                                    <SelectItem key={op.id} value={op.id} className="text-xs">
                                      {op.fornecedor_nome} — {op.valor_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} ({formatNumberBR(op.quantidade, 2)} disp.)
                                    </SelectItem>
                                  ))
                                )}
                              </SelectContent>
                            </Select>
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={alocarForm.control}
                      name={`linhas.${index}.quantidade`}
                      render={({ field }) => {
                        const cotacaoItemId = alocarForm.watch(`linhas.${index}.cotacao_item_id`);
                        const opSelecionada = opcoes.find((o) => o.id === cotacaoItemId);
                        const maxQuantidade = opSelecionada ? Math.min(opSelecionada.quantidade, saldo) : saldo;
                        return (
                          <FormItem className="space-y-0">
                            <FormControl>
                              <Input
                                type="text"
                                inputMode="decimal"
                                placeholder="Qtd."
                                className="h-8 w-24 rounded-sm text-xs"
                                {...field}
                                onBlur={(e) => {
                                  const valor = parseLocaleNumber(e.target.value, NaN);
                                  if (!Number.isNaN(valor)) {
                                    if (valor < 0) field.onChange("0");
                                    else if (maxQuantidade != null && valor > maxQuantidade) field.onChange(formatNumberBR(maxQuantidade, 2));
                                    else field.onChange(formatNumberBR(valor, 2));
                                  }
                                  field.onBlur();
                                }}
                              />
                            </FormControl>
                          </FormItem>
                        );
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-t border-dashed px-4 py-2.5 flex justify-end">
            <Button
              type="submit"
              variant="default"
              size="sm"
              disabled={alocarMutation.isPending}
            >
              {alocarMutation.isPending ? (
                <Loader2 data-icon="inline-start" className="size-3.5 animate-spin" />
              ) : (
                <PackageCheck data-icon="inline-start" className="size-3.5" />
              )}
              Alocar Itens
            </Button>
          </div>
            </form>
          </Form>
        </div>
      )}

      {/* Histórico de Preços */}
      <div className="bg-muted/5 rounded-sm border border-dashed overflow-hidden">
        <div className="bg-muted/20 px-4 py-2 border-b border-dashed flex items-center justify-between">
          <h4 className="text-[10px] font-black uppercase tracking-wider flex items-center gap-2">
            <ClipboardList className="size-3" /> Histórico de Preços Interno
          </h4>
          {historico && historico.historico.length > 0 && (
            <div className="flex gap-2">
               <Badge variant="outline" className="text-[8px] font-bold bg-white rounded-sm border-dashed">
                Min: {historico.menor_preco.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </Badge>
              <Badge variant="outline" className="text-[8px] font-bold bg-white rounded-sm border-dashed">
                Méd: {historico.preco_medio.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </Badge>
              {trend && (
                <Badge variant="outline" className={cn(
                  "text-[8px] font-bold rounded-sm border-dashed",
                  trend === "down" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                  trend === "up" ? "bg-red-50 text-red-700 border-red-200" :
                  "bg-blue-50 text-blue-700 border-blue-200"
                )}>
                  {trend === "down" ? "Tendência: Queda" : trend === "up" ? "Tendência: Alta" : "Estável"}
                </Badge>
              )}
            </div>
          )}
        </div>
        
        {isLoadingHistorico ? (
          <div className="p-4 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : !historico || historico.historico.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-[10px] font-bold uppercase text-muted-foreground">Sem histórico para este item.</p>
          </div>
        ) : (
          <Table>
            <TableHeader className="bg-white/50">
              <TableRow className="hover:bg-transparent border-dashed">
                <TableHead className="h-7 text-[8px] font-bold uppercase">Data</TableHead>
                <TableHead className="h-7 text-[8px] font-bold uppercase">Fornecedor</TableHead>
                <TableHead className="h-7 text-[8px] font-bold uppercase text-right">Valor Unit.</TableHead>
                <TableHead className="h-7 text-[8px] font-bold uppercase text-center">Origem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {historico.historico.map((item, idx) => (
                <TableRow key={idx} className="hover:bg-muted/10 border-dashed">
                  <TableCell className="py-1 text-[10px] font-bold">
                    {format(new Date(item.data), "dd/MM/yyyy", { locale: ptBR })}
                  </TableCell>
                  <TableCell className="py-1">
                    <span className="text-[10px] font-black uppercase truncate max-w-[150px] block">{item.fornecedor_nome}</span>
                  </TableCell>
                  <TableCell className="py-1 text-right tabular-nums text-[10px] font-bold">
                    <div className="flex items-center justify-end gap-1">
                      {item.valor_unitario === historico.menor_preco && (
                        <Badge variant="outline" className="p-0 border-none bg-amber-100 text-amber-700">
                          <Check className="size-2" />
                        </Badge>
                      )}
                      {item.valor_unitario.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                    </div>
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    <Badge variant="ghost" className="text-[7px] p-0 font-bold opacity-60 uppercase">
                      {item.origem}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <Dialog open={!!editando} onOpenChange={(o) => !o && setEditando(null)}>
        <DialogContent className="sm:max-w-[620px] rounded-sm p-0">
          <DialogHeader className="border-b px-4 py-2.5">
            <div className="flex items-center gap-3">
              <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
                <Pencil className="size-4" />
              </div>
              <div className="min-w-0">
                <DialogTitle>Corrigir Cotação</DialogTitle>
                <DialogDescription className="truncate text-xs leading-tight">
                  {editando?.fornecedor_nome}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <DialogBody className="grid min-h-0 flex-1 gap-4 overflow-y-auto px-4 py-2.5">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Condições de Pagamento</Label>
                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    placeholder="Ex: 30% adiantado + 30 dias"
                    className="pl-9 h-8 rounded-sm text-xs"
                    value={condicoesPagamento}
                    onChange={(e) => setCondicoesPagamento(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <Label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Prazo (Dias)</Label>
                <div className="relative">
                  <Truck className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                  <Input
                    type="number"
                    min="0"
                    step="1"
                    placeholder="0"
                    className="pl-9 h-8 rounded-sm text-xs"
                    value={prazoEntregaDias}
                    onChange={(e) => setPrazoEntregaDias(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-1.5 mt-2">
              <Label className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Itens Cotados</Label>
              <div className="rounded-sm border divide-y overflow-hidden">
                {editando?.itens.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 px-3 py-2.5 bg-card">
                    <div className="flex size-8 items-center justify-center rounded-sm bg-primary/10 text-primary shrink-0">
                      <Package className="size-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-semibold">{item.produto_nome}</span>
                      <span className="text-[10px] text-muted-foreground font-mono font-medium">
                        Solicitado: {quantidadeSolicitadaDoItem(item)}
                      </span>
                    </div>
                    <div className="w-24 shrink-0 space-y-1">
                      <Label className="text-[9px] font-black uppercase text-muted-foreground tracking-wider">Qtd.</Label>
                      <Input
                        type="text"
                        inputMode="decimal"
                        placeholder="Qtd."
                        className="h-8 rounded-sm text-xs font-mono font-medium"
                        value={quantidades[item.id] ?? ""}
                        onChange={(e) => setQuantidades((v) => ({ ...v, [item.id]: e.target.value }))}
                      />
                    </div>
                    <div className="w-32 shrink-0 space-y-1">
                      <Label className="text-[9px] font-black uppercase text-muted-foreground tracking-wider">Valor Unit.</Label>
                      <div className="relative">
                        <DollarSign className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
                        <Input
                          type="text"
                          inputMode="decimal"
                          className="pl-7 h-8 rounded-sm text-xs font-mono font-medium"
                          value={valores[item.id] ?? ""}
                          onChange={(e) => setValores((v) => ({ ...v, [item.id]: e.target.value }))}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </DialogBody>

          <DialogFooter className="border-t px-4 py-2.5">
            <Button type="button" variant="outline" size="sm" onClick={() => setEditando(null)}>
              <XCircle data-icon="inline-start" className="size-3" />
              Cancelar
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={salvarEdicao} disabled={editarItemMutation.isPending}>
              {editarItemMutation.isPending ? (
                <>
                  <Loader2 data-icon="inline-start" className="size-3 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Save data-icon="inline-start" className="size-3" />
                  Salvar Alterações
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!aprovando} onOpenChange={(o) => !o && setAprovando(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Aprovar cotação?</AlertDialogTitle>
            <AlertDialogDescription>
              {aprovando && (
                <>
                  Ao aprovar a cotação de <strong>{aprovando.fornecedor_nome}</strong>
                  {" "}({aprovando.valor_total.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}),
                  as demais cotações desta solicitação serão recusadas e um pedido de compra será gerado
                  automaticamente. Esta ação não pode ser desfeita.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={approveMutation.isPending}
              onClick={() => aprovando && approveMutation.mutate(aprovando.id)}
            >
              {approveMutation.isPending ? "Aprovando…" : "Aprovar"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
