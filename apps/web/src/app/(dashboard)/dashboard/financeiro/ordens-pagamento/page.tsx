"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CircleAlert,
  Landmark,
  LoaderCircle,
  SendHorizonal,
} from "lucide-react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { PageHeader } from "@/components/shared/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type Candidato = {
  id: string;
  descricao: string;
  fornecedor: string | null;
  valor_total: number;
  data_vencimento: string;
};

type ContaBancaria = {
  id: string;
  nome: string;
  banco: string | null;
  agencia: string | null;
  conta: string | null;
  ativa: boolean;
  convenio_pagamentos: string | null;
  layout_remessa: string | null;
  homologada_para_remessa: boolean;
};

type OrdemPagamento = {
  id: string;
  status: string;
  ambiente: string;
  banco_codigo: string;
  conta_nome: string;
  data_pagamento: string;
  total_valor: number;
  created_at: string;
};

type OrdemCriada = Pick<OrdemPagamento, "id" | "status" | "total_valor">;

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const data = new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" });

const nomesBancos: Record<string, string> = {
  "001": "Banco do Brasil",
  "237": "Bradesco",
  "748": "Sicredi",
  "756": "Sicoob",
};

function mensagemErro(error: Error) {
  return error.message || "Não foi possível concluir a operação.";
}

function statusOrdem(status: string) {
  if (status === "LIQUIDADA_SIMULADA") return <Badge variant="success">Liquidada (simulada)</Badge>;
  if (status === "REJEITADA_SIMULADA") return <Badge variant="danger">Rejeitada (simulada)</Badge>;
  return <Badge variant="warning">Pronta para retorno</Badge>;
}

export default function OrdensPagamentoPage() {
  const queryClient = useQueryClient();
  const [selecionadas, setSelecionadas] = useState<Set<string>>(new Set());
  const [contaId, setContaId] = useState("");
  const [confirmarCriacao, setConfirmarCriacao] = useState(false);

  const candidatosQuery = useQuery<Candidato[]>({
    queryKey: ["financeiro", "ordens-pagamento", "candidatos"],
    queryFn: () => apiFetch("/financeiro/integracao/ordens-pagamento/candidatos"),
  });
  const contasQuery = useQuery<ContaBancaria[]>({
    queryKey: ["financeiro", "contas-bancarias"],
    queryFn: () => apiFetch("/financeiro/integracao/contas-bancarias"),
  });
  const ordensQuery = useQuery<OrdemPagamento[]>({
    queryKey: ["financeiro", "ordens-pagamento"],
    queryFn: () => apiFetch("/financeiro/integracao/ordens-pagamento"),
  });

  const candidatos = candidatosQuery.data ?? [];
  const contasHomologadas = useMemo(
    () => (contasQuery.data ?? []).filter((conta) => conta.ativa && conta.homologada_para_remessa && Boolean(conta.convenio_pagamentos) && conta.layout_remessa === "CNAB240"),
    [contasQuery.data],
  );
  const titulosSelecionados = useMemo(
    () => candidatos.filter((titulo) => selecionadas.has(titulo.id)),
    [candidatos, selecionadas],
  );
  const totalSelecionado = useMemo(
    () => titulosSelecionados.reduce((total, titulo) => total + titulo.valor_total, 0),
    [titulosSelecionados],
  );
  const todosSelecionados = candidatos.length > 0 && selecionadas.size === candidatos.length;

  const criarOrdem = useMutation<OrdemCriada, Error>({
    mutationFn: () => apiFetch("/financeiro/integracao/ordens-pagamento", {
      method: "POST",
      body: { conta_bancaria_id: contaId, despesa_ids: titulosSelecionados.map((titulo) => titulo.id) },
    }),
    onSuccess: () => {
      setSelecionadas(new Set());
      setContaId("");
      setConfirmarCriacao(false);
      void queryClient.invalidateQueries({ queryKey: ["financeiro", "ordens-pagamento"] });
      void queryClient.invalidateQueries({ queryKey: ["financeiro", "ordens-pagamento", "candidatos"] });
      void queryClient.invalidateQueries({ queryKey: ["financeiro", "despesas"] });
      toast.success("Ordem de pagamento criada para homologação.");
    },
    onError: (error) => toast.error(mensagemErro(error)),
  });

  function alternarTitulo(id: string, marcado: boolean) {
    setSelecionadas((atual) => {
      const proxima = new Set(atual);
      if (marcado) proxima.add(id);
      else proxima.delete(id);
      return proxima;
    });
  }

  function alternarTodos(marcado: boolean) {
    setSelecionadas(marcado ? new Set(candidatos.map((titulo) => titulo.id)) : new Set());
  }

  function solicitarCriacao() {
    if (!titulosSelecionados.length) {
      toast.error("Selecione ao menos um título.");
      return;
    }
    if (!contaId) {
      toast.error("Selecione a conta bancária homologada.");
      return;
    }
    setConfirmarCriacao(true);
  }

  const emCarregamento = candidatosQuery.isLoading || contasQuery.isLoading;

  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Ordens de Pagamento"
        description="Monte o lote e escolha a conta homologada para a remessa."
        breadcrumbs={[
          { label: "Financeiro", href: "/dashboard/financeiro" },
          { label: "Minhas Despesas", href: "/dashboard/financeiro/despesas" },
          { label: "Ordens de Pagamento" },
        ]}
        icon={<Landmark className="size-8 text-primary" />}
        actions={
          <Button asChild variant="outline">
            <Link href="/dashboard/financeiro/conciliacao">Ir para Conciliação Bancária</Link>
          </Button>
        }
      />

      <Alert variant="warning">
        <CircleAlert />
        <AlertTitle>Ambiente de homologação</AlertTitle>
        <AlertDescription>As ordens são internas e os retornos abaixo são simulados. Nenhum arquivo é enviado ao banco nesta etapa.</AlertDescription>
      </Alert>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Títulos liberados</CardTitle>
            <CardDescription>Selecione os pagamentos que devem entrar no próximo lote de remessa.</CardDescription>
          </CardHeader>
          <CardContent>
            {emCarregamento ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : candidatos.length === 0 ? (
              <p className="text-sm text-muted-foreground">Não há títulos liberados. Em Minhas Despesas, selecione os títulos e use Liberar para pagamento.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox checked={todosSelecionados} onCheckedChange={alternarTodos} aria-label="Selecionar todos os títulos" />
                    </TableHead>
                    <TableHead>Descrição</TableHead>
                    <TableHead>Vencimento</TableHead>
                    <TableHead className="text-right">Valor</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {candidatos.map((titulo) => (
                    <TableRow key={titulo.id} data-state={selecionadas.has(titulo.id) ? "selected" : undefined}>
                      <TableCell>
                        <Checkbox checked={selecionadas.has(titulo.id)} onCheckedChange={(marcado) => alternarTitulo(titulo.id, marcado)} aria-label={`Selecionar ${titulo.descricao}`} />
                      </TableCell>
                      <TableCell>
                        <p className="font-medium">{titulo.descricao}</p>
                        {titulo.fornecedor && <p className="text-xs text-muted-foreground">{titulo.fornecedor}</p>}
                      </TableCell>
                      <TableCell>{data.format(new Date(`${titulo.data_vencimento}T00:00:00Z`))}</TableCell>
                      <TableCell className="text-right font-medium">{moeda.format(titulo.valor_total)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Resumo da ordem</CardTitle>
            <CardDescription>Defina a conta de débito antes de criar o lote.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <div className="rounded-lg border bg-muted/30 p-4">
              <p className="text-xs text-muted-foreground">Total selecionado</p>
              <p className="mt-1 text-2xl font-semibold">{moeda.format(totalSelecionado)}</p>
              <p className="mt-1 text-xs text-muted-foreground">{titulosSelecionados.length} título(s) no lote</p>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium" htmlFor="conta-remessa">Conta bancária homologada</label>
              <Select value={contaId} onValueChange={setContaId}>
                <SelectTrigger id="conta-remessa"><SelectValue placeholder="Selecione a conta" /></SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {contasHomologadas.map((conta) => (
                      <SelectItem key={conta.id} value={conta.id}>
                        {nomesBancos[conta.banco ?? ""] ?? conta.banco ?? "Banco"} · {conta.nome}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              {contasHomologadas.length === 0 && <p className="text-xs text-destructive">Não existe conta ativa e homologada com convênio e layout CNAB 240.</p>}
            </div>
          </CardContent>
          <CardFooter>
            <Button className="w-full" onClick={solicitarCriacao} disabled={emCarregamento || criarOrdem.isPending || candidatos.length === 0}>
              {criarOrdem.isPending ? <LoaderCircle data-icon="inline-start" className="animate-spin" /> : <SendHorizonal data-icon="inline-start" />}
              Criar ordem de homologação
            </Button>
          </CardFooter>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ordens criadas</CardTitle>
          <CardDescription>O processamento do retorno bancário é realizado em Conciliação Bancária.</CardDescription>
        </CardHeader>
        <CardContent>
          {ordensQuery.isLoading ? <Skeleton className="h-20 w-full" /> : (ordensQuery.data ?? []).length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhuma ordem criada neste ambiente.</p>
          ) : (
            <Table>
              <TableHeader><TableRow><TableHead>Conta</TableHead><TableHead>Data</TableHead><TableHead>Valor</TableHead><TableHead>Status</TableHead></TableRow></TableHeader>
              <TableBody>
                {(ordensQuery.data ?? []).map((ordem) => (
                  <TableRow key={ordem.id}>
                    <TableCell><p className="font-medium">{ordem.conta_nome}</p><p className="text-xs text-muted-foreground">{nomesBancos[ordem.banco_codigo] ?? ordem.banco_codigo}</p></TableCell>
                    <TableCell>{data.format(new Date(`${ordem.data_pagamento}T00:00:00Z`))}</TableCell>
                    <TableCell className="font-medium">{moeda.format(ordem.total_valor)}</TableCell>
                    <TableCell>{statusOrdem(ordem.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmarCriacao}
        title="Criar ordem de pagamento?"
        description={`Serão incluídos ${titulosSelecionados.length} título(s), totalizando ${moeda.format(totalSelecionado)}, em uma ordem de homologação.`}
        confirmText="Criar ordem"
        onConfirm={() => criarOrdem.mutate()}
        onCancel={() => setConfirmarCriacao(false)}
      />
    </div>
  );
}
