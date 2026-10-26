"use client";

import { useEffect, useState } from "react";
import {
  Building2,
  Calendar,
  Clock3,
  Coins,
  Percent,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  WifiOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  fetchIndicadoresMacro,
  formatarDataReferencia,
  formatarValorMacro,
  markMacroUnavailable,
  readSavedMacro,
  saveMacro,
  type IndicadorMacroItem,
  type IndicadoresMacroResponse,
} from "@/lib/mercado/macro";

function obterIconeIndicador(id: string) {
  if (id === "EURO_PTAX") return Coins;
  if (id === "SELIC_META") return Percent;
  return TrendingUp;
}

function obterSubtituloIndicador(id: string) {
  switch (id) {
    case "SELIC_META":
      return "Taxa básica de juros da economia";
    case "IPCA_MENSAL":
      return "Inflação oficial do mês de referência";
    case "IPCA_12M":
      return "Inflação acumulada nos últimos 12 meses";
    case "EURO_PTAX":
      return "Cotação oficial de câmbio comercial";
    default:
      return "Indicador oficial de referência";
  }
}

export function IndicadoresMacroCard() {
  const [data, setData] = useState<IndicadoresMacroResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isOffline, setIsOffline] = useState<boolean>(false);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  useEffect(() => {
    // Carrega dado salvo inicialmente do localStorage
    const saved = readSavedMacro(window.localStorage);
    if (saved) {
      setData(saved);
    }

    if (!navigator.onLine) {
      setIsOffline(true);
      setLoading(false);
      return;
    }

    let active = true;
    const controller = new AbortController();

    async function loadData() {
      try {
        const response = await fetchIndicadoresMacro(window.location, controller.signal);
        if (active && response && response.sucesso) {
          setData(response);
          saveMacro(window.localStorage, response);
          setIsOffline(false);
        }
      } catch {
        if (active && saved) {
          setData(markMacroUnavailable(saved));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadData();

    const handleOnline = () => {
      setIsOffline(false);
      loadData();
    };

    const handleOffline = () => {
      setIsOffline(true);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      active = false;
      controller.abort();
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const handleManualRefresh = async () => {
    if (!navigator.onLine) {
      setIsOffline(true);
      return;
    }
    setRefreshing(true);
    try {
      const response = await fetchIndicadoresMacro(window.location);
      if (response && response.sucesso) {
        setData(response);
        saveMacro(window.localStorage, response);
        setIsOffline(false);
      }
    } catch {
      setData((current) => current ? markMacroUnavailable(current) : null);
    } finally {
      setRefreshing(false);
    }
  };

  const statusDisponibilidade = isOffline
    ? "OFFLINE"
    : data?.estadoDisponibilidade ?? (loading ? "CARREGANDO" : "INDISPONIVEL");

  return (
    <Card className="rounded-sm border-border/70 shadow-xs">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm sm:text-base font-semibold text-foreground flex items-center gap-2">
                <Percent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                Indicadores Econômicos e Câmbio Oficial
              </CardTitle>
              <Badge variant="outline" className="text-[10px] hidden sm:inline-flex">
                BCB &amp; IBGE
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Séries oficiais do Banco Central do Brasil para balizamento de crédito, custos financeiros e inflação no agronegócio.
            </p>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            {isOffline ? (
              <Badge variant="warning" className="text-[10px] flex items-center gap-1">
                <WifiOff className="w-3 h-3" /> Modo offline — dado salvo
              </Badge>
            ) : statusDisponibilidade === "NORMAL" ? (
              <Badge variant="success" className="text-[10px] flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Séries Oficiais Homologadas
              </Badge>
            ) : statusDisponibilidade === "PARCIAL" ? (
              <Badge variant="warning" className="text-[10px] flex items-center gap-1">
                <Clock3 className="w-3 h-3" /> Atualização parcial
              </Badge>
            ) : statusDisponibilidade === "FONTE_INDISPONIVEL" || statusDisponibilidade === "DEFASADO" ? (
              <Badge variant="warning" className="text-[10px] flex items-center gap-1">
                <Clock3 className="w-3 h-3" /> Último fechamento conhecido
              </Badge>
            ) : null}

            <Button
              variant="outline"
              size="sm"
              onClick={handleManualRefresh}
              disabled={refreshing || loading}
              className="rounded-sm h-7 px-2 text-xs"
              aria-label="Atualizar indicadores macroeconômicos"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-3.5 space-y-3.5">
        {loading && !data ? (
          /* Skeletons de carregamento com alturas fixas para zero layout shift */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="p-3 rounded-sm border border-border/50 bg-muted/20 animate-pulse space-y-2.5 h-[118px]"
              >
                <div className="flex items-center justify-between">
                  <div className="h-3 w-20 bg-muted/60 rounded-xs" />
                  <div className="h-4 w-12 bg-muted/60 rounded-xs" />
                </div>
                <div className="h-6 w-24 bg-muted/80 rounded-xs" />
                <div className="h-3 w-32 bg-muted/40 rounded-xs" />
              </div>
            ))}
          </div>
        ) : data && data.itens.length > 0 ? (
          /* Grid Responsivo de Indicadores */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {data.itens.map((item: IndicadorMacroItem) => {
              const Icon = obterIconeIndicador(item.id);
              const dataFormatada = formatarDataReferencia(item.dataReferencia, item.periodicidade);
              const valorFormatado = formatarValorMacro(item);

              return (
                <div
                  key={item.id}
                  className="p-3 rounded-sm border border-border/70 bg-card hover:border-emerald-600/40 transition-colors flex flex-col justify-between space-y-2"
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <div className="flex items-center gap-1.5">
                      <div className="p-1.5 rounded-sm bg-muted text-foreground flex-shrink-0">
                        <Icon className="w-3.5 h-3.5 text-emerald-700 dark:text-emerald-400" />
                      </div>
                      <span className="text-xs font-semibold text-foreground truncate max-w-[130px] sm:max-w-[150px]">
                        {item.id === "SELIC_META"
                          ? "Meta Selic"
                          : item.id === "IPCA_MENSAL"
                          ? "IPCA (Mensal)"
                          : item.id === "IPCA_12M"
                          ? "IPCA (12 Meses)"
                          : "Euro PTAX"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      {item.estadoDisponibilidade === "FONTE_INDISPONIVEL" ? (
                        <Badge variant="warning" className="text-[8px] px-1 py-0 h-4 flex items-center gap-0.5">
                          <Clock3 className="w-2.5 h-2.5" /> Último
                        </Badge>
                      ) : item.estadoDisponibilidade === "DEFASADO" ? (
                        <Badge variant="warning" className="text-[8px] px-1 py-0 h-4">
                          Defasado
                        </Badge>
                      ) : null}
                      <Badge variant="outline" className="text-[9px] px-1.5 py-0 h-4 border-border/60">
                        {item.unidade}
                      </Badge>
                    </div>
                  </div>

                  {/* Valor Principal */}
                  <div>
                    <div className="text-lg font-bold tracking-tight text-foreground">
                      {valorFormatado}
                    </div>
                    <p className="text-[10px] text-muted-foreground line-clamp-1">
                      {obterSubtituloIndicador(item.id)}
                    </p>
                  </div>

                  {/* Compra e Venda para Câmbio Euro */}
                  {item.id === "EURO_PTAX" && item.valorCompra && item.valorVenda ? (
                    <div className="text-[10px] text-muted-foreground border-t border-border/40 pt-1 flex justify-between">
                      <span>C: R$ {item.valorCompra.toFixed(4).replace(".", ",")}</span>
                      <span>V: R$ {item.valorVenda.toFixed(4).replace(".", ",")}</span>
                    </div>
                  ) : null}

                  {/* Metadados: Data de Referência e Fonte */}
                  <div className="text-[10px] text-muted-foreground border-t border-border/40 pt-1.5 flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-2.5 h-2.5" />
                      {dataFormatada}
                    </span>
                    <span className="flex items-center gap-1 truncate max-w-[100px]">
                      <Building2 className="w-2.5 h-2.5" />
                      {item.codigoSerieBcb ? `SGS ${item.codigoSerieBcb}` : "BCB"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 rounded-sm border border-border/60 bg-muted/20 text-center text-xs text-muted-foreground">
            Indicadores macroeconômicos temporariamente indisponíveis no servidor oficial.
          </div>
        )}

        {/* Rodapé Informativo */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[10px] text-muted-foreground pt-1 border-t border-border/40">
          <p>
            Fontes primárias: <strong>Banco Central do Brasil (SGS)</strong> e <strong>IBGE</strong>. Séries 432, 433, 13522 e 21619.
          </p>
          {data?.cacheAtualizadoEmIso && (
            <p className="flex items-center gap-1">
              <Clock3 className="w-2.5 h-2.5" />
              Sincronizado em: {new Date(data.cacheAtualizadoEmIso).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" })}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
