"use client";

import * as React from "react";
import { AlertCircle, ExternalLink, RefreshCw } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
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
    <Card>
      <CardHeader className="border-b border-border/60">
        <div>
          <CardTitle className="text-sm font-semibold tracking-tight">Cacau e pimenta-do-reino</CardTitle>
          <CardDescription className="text-xs">Referência anual ao produtor calculada com dados oficiais da PAM/IBGE.</CardDescription>
        </div>
        <CardAction>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setTentativa((atual) => atual + 1)}
            disabled={carregando}
            aria-label="Atualizar valores anuais do cacau e da pimenta-do-reino"
          >
            <RefreshCw className={`size-3.5 ${carregando ? "animate-spin" : ""}`} />
            <span>Atualizar</span>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PRODUTOS.map((produto) => {
            const estado = estados[produto.id];
            return (
              <Card key={produto.id} variant="muted" size="sm">
                <CardContent className="flex flex-col gap-1">
                  <p className="text-xs font-medium text-muted-foreground">{produto.nome}</p>
                  {carregando && !estado ? (
                    <Skeleton className="mt-1 h-7 w-32" aria-label="Carregando valor" />
                  ) : estado?.valor ? (
                    <>
                      <p className="text-xl font-bold tracking-tight text-foreground">{moedaPorKg(estado.valor.valorPorKg)}<span className="ml-1 text-xs font-normal text-muted-foreground">/ kg</span></p>
                      <p className="text-[11px] text-muted-foreground">Média anual implícita · Brasil · {estado.valor.ano}{estado.valor.fonteIndisponivel ? " · último dado salvo" : ""}</p>
                      <a href={estado.valor.urlTabela} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-[11px] text-emerald-700 hover:underline dark:text-emerald-400">
                        Fonte: IBGE/SIDRA <ExternalLink className="size-3" />
                      </a>
                    </>
                  ) : (
                    <p className="mt-1 text-xs text-muted-foreground">{estado?.erro ? "Valor anual indisponível no momento." : "Sem produção e valor publicados em período comum."}</p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
        <Alert variant="warning">
          <AlertCircle className="size-4" />
          <AlertDescription className="text-xs">
            Estimativa derivada de valor da produção (mil R$) ÷ quantidade produzida (toneladas). É uma média anual agregada, não cotação spot, oferta de compra ou preço atualizado diariamente.
          </AlertDescription>
        </Alert>
        <div>
          <Badge variant="outline">Fonte pública · PAM/IBGE · valores nominais do ano de referência</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
