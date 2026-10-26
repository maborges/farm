"use client";

import * as React from "react";
import { AlertCircle, ExternalLink, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchIbgeEstatisticas, type EstatisticasIbgeResponse } from "@/lib/mercado/ibge";

const PRODUTOS = [
  { id: "pimenta-do-reino", nome: "Pimenta-do-reino" },
  { id: "cacau", nome: "Cacau (em amêndoa)" },
] as const;

type ValorAnual = { valorPorKg: number; ano: string; urlTabela: string; fonteIndisponivel: boolean };
type EstadoProduto = { valor: ValorAnual | null; erro: boolean };

function obterValorAnual(resposta: EstatisticasIbgeResponse | null): ValorAnual | null {
  if (!resposta?.sucesso) return null;
  const producao = resposta.indicadores.find((item) => item.id === "PRODUCAO");
  const valorProducao = resposta.indicadores.find((item) => item.id === "VALOR_PRODUCAO");
  if (!producao || !valorProducao) return null;

  const valores = new Map(valorProducao.pontos.map((ponto) => [ponto.periodo, ponto.valor]));
  const ponto = [...producao.pontos]
    .reverse()
    .find((item) => item.valor !== null && item.valor > 0 && (valores.get(item.periodo) ?? 0) > 0);
  const quantidadeToneladas = ponto?.valor;
  const valorTotalMilReais = ponto ? valores.get(ponto.periodo) : null;
  if (!ponto || quantidadeToneladas === null || quantidadeToneladas === undefined || valorTotalMilReais === null || valorTotalMilReais === undefined) return null;

  // Mil reais / mil kg (toneladas) resulta em reais por kg.
  return {
    valorPorKg: valorTotalMilReais / quantidadeToneladas,
    ano: ponto.periodo,
    urlTabela: resposta.urlTabela,
    fonteIndisponivel: resposta.estadoDisponibilidade === "FONTE_INDISPONIVEL",
  };
}

function moedaPorKg(valor: number): string {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }).format(valor);
}

export function IbgeValorProducaoCard() {
  const [estados, setEstados] = React.useState<Record<string, EstadoProduto>>({});
  const [carregando, setCarregando] = React.useState(true);
  const [tentativa, setTentativa] = React.useState(0);

  React.useEffect(() => {
    const controller = new AbortController();
    setCarregando(true);
    Promise.all(
      PRODUTOS.map(async (produto) => {
        try {
          const resposta = await fetchIbgeEstatisticas(
            window.location,
            { produto: produto.id, nivel: "BRASIL", anos: 10 },
            controller.signal
          );
          return [produto.id, { valor: obterValorAnual(resposta), erro: !resposta?.sucesso }] as const;
        } catch {
          return [produto.id, { valor: null, erro: true }] as const;
        }
      })
    ).then((resultados) => {
      if (!controller.signal.aborted) setEstados(Object.fromEntries(resultados));
    }).finally(() => {
      if (!controller.signal.aborted) setCarregando(false);
    });

    return () => controller.abort();
  }, [tentativa]);

  return (
    <Card className="rounded-sm border border-border bg-card shadow-sm">
      <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border/60 p-4 pb-3">
        <div className="space-y-1">
          <CardTitle className="text-sm font-semibold tracking-tight">Cacau e pimenta-do-reino</CardTitle>
          <p className="text-xs text-muted-foreground">Referência anual ao produtor calculada com dados oficiais da PAM/IBGE.</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="h-7 shrink-0 gap-1 rounded-sm px-2.5 text-xs"
          onClick={() => setTentativa((atual) => atual + 1)}
          disabled={carregando}
          aria-label="Atualizar valores anuais do cacau e da pimenta-do-reino"
        >
          <RefreshCw className={`h-3 w-3 ${carregando ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </CardHeader>
      <CardContent className="space-y-3 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PRODUTOS.map((produto) => {
            const estado = estados[produto.id];
            return (
              <div key={produto.id} className="rounded-sm border border-border/80 bg-background/50 p-3">
                <p className="text-xs font-medium text-muted-foreground">{produto.nome}</p>
                {carregando && !estado ? (
                  <div className="mt-2 h-7 w-32 animate-pulse rounded-sm bg-muted" aria-label="Carregando valor" />
                ) : estado?.valor ? (
                  <>
                    <p className="mt-1 text-xl font-bold tracking-tight">{moedaPorKg(estado.valor.valorPorKg)}<span className="ml-1 text-xs font-normal text-muted-foreground">/ kg</span></p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Média anual implícita · Brasil · {estado.valor.ano}{estado.valor.fonteIndisponivel ? " · último dado salvo" : ""}</p>
                    <a href={estado.valor.urlTabela} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-[11px] text-emerald-700 hover:underline dark:text-emerald-400">
                      Fonte: IBGE/SIDRA <ExternalLink className="h-3 w-3" />
                    </a>
                  </>
                ) : (
                  <p className="mt-2 text-xs text-muted-foreground">{estado?.erro ? "Valor anual indisponível no momento." : "Sem produção e valor publicados em período comum."}</p>
                )}
              </div>
            );
          })}
        </div>
        <div className="flex items-start gap-2 rounded-sm border border-amber-500/25 bg-amber-500/5 p-2.5 text-[11px] text-muted-foreground">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-700 dark:text-amber-400" />
          <p>Estimativa derivada de valor da produção (mil R$) ÷ quantidade produzida (toneladas). É uma média anual agregada, não cotação spot, oferta de compra ou preço atualizado diariamente.</p>
        </div>
        <Badge variant="outline" className="text-[10px]">Fonte pública · PAM/IBGE · valores nominais do ano de referência</Badge>
      </CardContent>
    </Card>
  );
}
